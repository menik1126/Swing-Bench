import ast
import subprocess
import re
import os
import sys
import glob
import shutil
import tempfile
import threading
import json
import uuid
from dataclasses import dataclass
import logging
import time

import yaml

logger = logging.getLogger(__name__)

def run_script(script_content, cwd=None):
    with tempfile.NamedTemporaryFile(mode="w", delete=True, suffix=".sh") as temp_script:
        temp_script.write(script_content)
        temp_script.flush()
        temp_path = temp_script.name
        try:
            subprocess.run(["bash", temp_path], 
                           cwd=cwd,
                           check=True, 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
        except Exception as e:
            return e
    return None

@dataclass
class Task:
    instance_id: str
    env_script: list[str]
    eval_script: list[str]
    target_dir: str
    output_dir: str
    patch: str = None
    apply_patch: bool = False

class CIToolBase:
    def __init__(self, config):
        self.config = config

    def construct(self):
        pass
    
    def run_ci(self, log_file: str = None):
        pass

class CargoCITool(CIToolBase):
    def __init__(self, config):
        super().__init__(config)
        self.construct()

    def _build_repo_base_env(self):
        script = ["#!/bin/bash"]

        repo_dir_name = self.config["repo"].replace('/', '__')
        instance_id = self.config.get("instance_id", "unknown")
        src_path = os.path.join(self.config["src_folder"], repo_dir_name)
        # Use instance_id directly as directory name (it already contains repo info)
        dst_path = os.path.join(self.config["workdir"], instance_id)

        # Quote paths to handle special characters
        script.append(f"mkdir -p \"{dst_path}\"")
        script.append(f"cp -r \"{src_path}\"/. \"{dst_path}\"/")

        return script

    def _build_eval_script(self):
        instance_id = self.config.get("instance_id", "unknown")
        # Use instance_id directly as directory name
        target_dir = os.path.join(self.config["workdir"], instance_id)

        script = ["#!/bin/bash",
                  f"cd \"{target_dir}\"",
                 ]

        script.append("git stash -u || true")

        if "merge_commit" in self.config and self.config["merge_commit"]:
            script.append("git checkout " + self.config["merge_commit"])

            # Apply test_patch if it exists
            if self.config.get("test_patch"):
                test_patch_file = f"{target_dir}/test_patch.diff"
                script.append(f"cat > \"{test_patch_file}\" << 'EOL'\n{self.config['test_patch']}\nEOL")
                script.append(f"git apply \"{test_patch_file}\" || echo 'Failed to apply test_patch'")

            # Apply patch only if apply_patch is specified
            if self.config.get("apply_patch", False) and self.config.get("patch"):
                patch_file = f"{target_dir}/patch.diff"
                script.append(f"cat > \"{patch_file}\" << 'EOL'\n{self.config['patch']}\nEOL")
                script.append(f"git apply \"{patch_file}\" || echo 'Failed to apply patch'")

        return script

    def construct(self):
        env_script = self._build_repo_base_env()
        eval_script = self._build_eval_script()

        instance_id = self.config.get("instance_id", "unknown")
        # Use instance_id directly as directory name
        target_dir = os.path.join(self.config["workdir"], instance_id)
        
        self.task = Task(instance_id=instance_id,
                         env_script=env_script,
                         eval_script=eval_script,
                         patch=self.config["patch"],
                         target_dir=target_dir,
                         output_dir=self.config["output_dir"],
                         apply_patch=self.config["apply_patch"])

    def parse_test_results(self, output):
        passed_pattern = r"test ([\w:]+) \.\.\. ok"
        failed_pattern = r"test ([\w:]+) \.\.\. FAILED"
        ignored_pattern = r"test ([\w:]+) \.\.\. ignored"
        
        passed_tests = re.findall(passed_pattern, output)
        failed_tests = re.findall(failed_pattern, output)
        ignored_tests = re.findall(ignored_pattern, output)
        
        test_results = {
            "passed": passed_tests,
            "failed": failed_tests,
            "ignored": ignored_tests,
            "failure_details": {}
        }
        
        for test in failed_tests:
            regex_pattern = rf"---- {re.escape(test)} stdout ----\n(.*?)(?:\n\nfailures:|\n\ntest result:|$)"
            failure_details = re.search(regex_pattern, output, re.DOTALL)
            if failure_details:
                test_results["failure_details"][test] = failure_details.group(1).strip()
        
        return test_results

    def check_env(self):
        if not os.path.exists(self.task.target_dir):
            raise Exception(f'Repo {self.task.target_dir} does not exist. Please check.')
        if not os.path.exists(self.config["workdir"]):
            raise Exception(f'Workdir {self.config["workdir"]} does not exist. Please check.')

    def run_ci(self):
        """Run tests and save results to log file"""
        try:
            print(f"Starting CI run for {self.config['repo']} (ID: {self.config.get('instance_id', 'unknown')})")

            task = self.task
            self._execute_scripts(cwd=task.target_dir)
            print(f"Running cargo test in {task.target_dir}")
            
            result = subprocess.run(
                ["cargo", "test"],
                cwd=task.target_dir,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            print(f"Cargo test completed with return code: {result.returncode}")
            
            test_results = self.parse_test_results(result.stdout)
            output = {"unit_test": {
                "returncode": result.returncode,
                "test_results": test_results
            }}
            
            return output

        except Exception as e:
            logger.error(f"Task failed with exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"unit_test": {
                "returncode": 1,
                "error": str(e),
                "test_results": {"passed": [], "failed": [], "ignored": [], "failure_details": {}}
            }}
            
    def _execute_scripts(self, cwd="~"):
        """Execute environment setup and evaluation scripts, hide output"""
        # Use instance_id directly as directory name
        instance_id = self.config.get("instance_id", "unknown")
        script_dir = os.path.join(self.config["workdir"], instance_id)
        
        print(f"Creating script directory: {script_dir}")
        # Create script directory
        os.makedirs(script_dir, exist_ok=True)
        
        # Execute environment setup script
        env_script_path = os.path.join(script_dir, "env_setup.sh")
        with open(env_script_path, 'w') as f:
            f.write('\n'.join(self.task.env_script))
        
        print("Executing environment setup script")
        subprocess.run(
            ['chmod', '+x', env_script_path], 
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        subprocess.run(
            ['bash', env_script_path], 
            check=True,
            # cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Execute evaluation script
        eval_script_path = os.path.join(script_dir, "eval.sh")
        with open(eval_script_path, 'w') as f:
            f.write('\n'.join(self.task.eval_script))

        self.check_env()

        print("Executing evaluation script")
        subprocess.run(
            ['chmod', '+x', eval_script_path], 
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        subprocess.run(
            [eval_script_path], 
            check=True,
            # cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

class DockerCITool(CIToolBase):
    def __init__(self, config):
        super().__init__(config)
        self.construct()

    def construct(self):
        pass


DEFAULT_MAX_CONCURRENT_CI_JOBS = 4
DEFAULT_ACT_TIMEOUT_SECONDS = 30 * 60  # 30 minutes per CI job

ACT_DEFAULT_IMAGE = "catthehacker/ubuntu:full-latest"
ACT_PLATFORM_MAPPINGS = [
    f"ubuntu-latest={ACT_DEFAULT_IMAGE}",
    f"ubuntu-24.04={ACT_DEFAULT_IMAGE}",
    f"ubuntu-22.04={ACT_DEFAULT_IMAGE}",
    f"ubuntu-20.04={ACT_DEFAULT_IMAGE}",
    f"macos-latest={ACT_DEFAULT_IMAGE}",
    f"macos-14={ACT_DEFAULT_IMAGE}",
    f"macos-13={ACT_DEFAULT_IMAGE}",
    f"macos-12={ACT_DEFAULT_IMAGE}",
    f"windows-latest={ACT_DEFAULT_IMAGE}",
    f"windows-2022={ACT_DEFAULT_IMAGE}",
    f"windows-2019={ACT_DEFAULT_IMAGE}",
]

class ActCITool(CIToolBase):
    def __init__(self, config):
        super().__init__(config)
        self.act_list_path = 'act_list.txt'
        self.apply_patch = self.config["apply_patch"]
        self.cloned_repo_path = self.config["repo"].split("/")[1] + "__" + self.config["merge_commit"]
        self.ci_dict = dict()
        self.result_lock = threading.Lock()
        self.result_list = []
        self.max_concurrent = self.config.get("max_concurrent_ci_jobs", DEFAULT_MAX_CONCURRENT_CI_JOBS)
        self.act_timeout = self.config.get("act_timeout_seconds", DEFAULT_ACT_TIMEOUT_SECONDS)
        self.act_matrix_filters = self._parse_matrix_filters(
            self.config.get("act_matrix_filter", "")
        )
        self.act_env_flags = self._build_act_env_flags()
        self.act_platform_overrides = self._parse_platform_overrides(
            os.environ.get("ACT_PLATFORM_OVERRIDES", "")
        )

        self.construct()

    @staticmethod
    def _build_act_env_flags() -> list:
        """Build --env flags to inject proxy settings into act containers.

        Checks ACT_PROXY first, then falls back to host http_proxy/https_proxy.
        """
        proxy = os.environ.get("ACT_PROXY", "")
        if not proxy:
            proxy = os.environ.get("https_proxy") or os.environ.get("http_proxy", "")
        if not proxy:
            return []
        flags = []
        for var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
            flags.extend(["--env", f"{var}={proxy}"])
        no_proxy = os.environ.get("no_proxy") or os.environ.get("NO_PROXY", "")
        if no_proxy:
            flags.extend(["--env", f"no_proxy={no_proxy}"])
            flags.extend(["--env", f"NO_PROXY={no_proxy}"])
        return flags

    @staticmethod
    def _parse_matrix_filters(raw: str) -> list:
        """Parse ACT_MATRIX_FILTER env var into --matrix flags for act.

        Format: "key1:val1,key2:val2" e.g. "os:ubuntu-latest,python-version:3.10"
        Returns list like ["--matrix", "os:ubuntu-latest", "--matrix", "python-version:3.10"]
        """
        if not raw or not raw.strip():
            return []
        flags = []
        for entry in raw.split(","):
            entry = entry.strip()
            if ":" in entry:
                flags.extend(["--matrix", entry])
        return flags

    @staticmethod
    def _parse_platform_overrides(raw: str) -> list:
        """Parse ACT_PLATFORM_OVERRIDES env var into extra -P flags for act.

        Allows users to map workflow container images to custom images that
        have additional tools (curl, git, etc.) pre-installed.

        Format: comma-separated "original=replacement" pairs, e.g.
          "node:16-bullseye-slim=my-registry/node:16-with-tools,python:3.9-slim=my-python:3.9"
        Returns list like ["-P", "node:16-bullseye-slim=my-registry/node:16-with-tools",
                           "-P", "python:3.9-slim=my-python:3.9"]
        """
        if not raw or not raw.strip():
            return []
        flags = []
        for entry in raw.split(","):
            entry = entry.strip()
            if "=" in entry:
                flags.extend(["-P", entry])
        return flags

    # TODO(wdxu): make these two functions to be public methods.
    def _build_repo_base_env(self):
        script = ["#!/bin/bash"]

        repo_dir_name = self.config["repo"].replace('/', '__')
        instance_id = self.config.get("instance_id", "unknown")
        src_path = os.path.join(self.config["src_folder"], repo_dir_name)
        # Use instance_id directly as directory name
        dst_path = os.path.join(self.config["workdir"], instance_id)

        # Quote paths to handle special characters
        script.append(f"mkdir -p \"{dst_path}\"")
        script.append(f"cp -r \"{src_path}\"/. \"{dst_path}\"/")

        return script

    def _build_eval_script(self):
        instance_id = self.config.get("instance_id", "unknown")
        # Use instance_id directly as directory name
        target_dir = os.path.join(self.config["workdir"], instance_id)

        script = ["#!/bin/bash",
                  f"cd \"{target_dir}\"",
                 ]

        script.append("git stash -u || true")

        if "merge_commit" in self.config and self.config["merge_commit"]:
            script.append("git checkout " + self.config["merge_commit"])

            # Apply test_patch if it exists
            if self.config.get("test_patch"):
                test_patch_file = f"{target_dir}/test_patch.diff"
                script.append(f"cat > \"{test_patch_file}\" << 'EOL'\n{self.config['test_patch']}\nEOL")
                script.append(f"git apply \"{test_patch_file}\" || echo 'Failed to apply test_patch'")

            # Apply patch only if apply_patch is specified
            if self.config.get("apply_patch", False) and self.config.get("patch"):
                patch_file = f"{target_dir}/patch.diff"
                script.append(f"cat > \"{patch_file}\" << 'EOL'\n{self.config['patch']}\nEOL")
                script.append(f"git apply \"{patch_file}\" || echo 'Failed to apply patch'")

        return script


    def _get_ci_job_name_id_dict(self, target_dir):
        def _extract_jobs(filename):
            jobs = {}
            if not os.path.exists(filename):
                print(f"Warning: act list file not found: {filename}")
                return jobs
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("Stage"):
                        continue
                    columns = re.split(r'\s{2,}', line)
                    if len(columns) >= 3:
                        job_id = columns[1]
                        job_name = columns[2]
                        jobs[job_name] = job_id
            return jobs

        act_list_path = os.path.join(target_dir, self.act_list_path)
        result = subprocess.run(
            ["act", "--list"],
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            print(f"Warning: 'act --list' failed (exit {result.returncode}) in {target_dir}")
            print(f"  stderr: {result.stderr.strip()}")
            self.ci_dict = {}
            return

        with open(act_list_path, 'w', encoding='utf-8') as f:
            f.write(result.stdout)

        self.ci_dict = _extract_jobs(act_list_path)

        if not self.ci_dict:
            print(f"Warning: No CI jobs parsed from 'act --list'. Raw output:")
            for line in result.stdout.strip().split('\n')[:10]:
                print(f"  | {line}")

        if os.path.exists(act_list_path):
            os.remove(act_list_path)
                    
    def _process_act_output(self, stdout):
        # result format:
        # for normal result
        # result = {
        #     'job': data.get('job', ''), unique key
        #     'jobID': data.get('jobID', ''),
        #     'steps': [
        #       ('step', 'stage', 'stepResult'),
        #       ...
        #     ]
        #     'jobResult': data.get('jobResult', ''),
        #     'testResult': [pass number, fail number, ignore number],
        # }
        # for unit test
        results = {}
        # Strip per-run UUIDs from job names so results are comparable across runs.
        # e.g. "CI_tests_86db90de/Check code linting" -> "CI_tests/Check code linting"
        _uuid_suffix_re = re.compile(r'_[0-9a-f]{8}/')

        def _normalize_job(name):
            return _uuid_suffix_re.sub('/', name, count=1) if name else name

        stdout_list = stdout.split('\n')
        for line in stdout_list:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                job = _normalize_job(data.get('job'))
                if job not in results.keys():
                    results[job] = {
                        'job': job,
                        'jobID': data.get('jobID', ''),
                        'steps': [],
                        'jobResult': None,
                        'testResult': [0, 0, 0], # for unit tests
                    }
            except json.JSONDecodeError:
                continue

        for data in stdout_list:
            if not data.strip():
                continue
            data = json.loads(data)
            job = _normalize_job(data.get('job'))
            step = data.get('step', None)
            step_result = data.get('stepResult', None)
            job_result = data.get('jobResult', None)
            if step and step_result:
                results[job]['steps'].append((step, data.get('stage', None), step_result))
            if job_result:
                results[job]['jobResult'] = job_result

            # parse unit test results
            target = ["cargo test", "test", "tests"]
            passed = [r"(\d+)\s*passed", r"(\d+)\s*pass"]
            failed = [r"(\d+)\s*failed", r"(\d+)\s*fail"]
            ignored = [r"(\d+)\s*ignored", r"(\d+)\s*ignore"]
            for tar in target:
                if tar in job.lower():
                    msg = data.get('msg')
                    if "test result" in msg:
                        for p in passed:
                            match = re.search(p, msg, re.IGNORECASE)
                            if match:
                                results[job]['testResult'][0] += int(match.group(1))

                        for f in failed:
                            match = re.search(f, msg, re.IGNORECASE)
                            if match:
                                results[job]['testResult'][1] += int(match.group(1))

                        for i in ignored:
                            match = re.search(i, msg, re.IGNORECASE)
                            if match:
                                results[job]['testResult'][2] += int(match.group(1))

        return results

    def _normalize_ci_list(self, ci_list):
        """Normalize ci_list from flat [name, file, name, file, ...] to [[name, file], ...]."""
        if not ci_list:
            return []
        if isinstance(ci_list[0], list):
            return ci_list

        parsed = []
        for item in ci_list:
            if isinstance(item, str):
                try:
                    val = ast.literal_eval(item)
                    if isinstance(val, list):
                        parsed.append(val)
                        continue
                except (ValueError, SyntaxError):
                    pass
            parsed.append(item)

        if all(isinstance(item, list) for item in parsed):
            return parsed

        if all(isinstance(item, str) for item in parsed) and len(parsed) >= 2:
            pairs = []
            for i in range(0, len(parsed) - 1, 2):
                pairs.append([parsed[i], parsed[i + 1]])
            return pairs

        return ci_list

    def _deduplicate_ci_list(self, ci_list):
        """Deduplicate ci_list by resolved job id so each job only runs once.

        Handles matrix-expanded names (e.g. 'MacOS / 3.10') that map to the
        same template job (e.g. '${{matrix.os}} / ${{ matrix.python-version }}').
        """
        seen_job_ids = set()
        deduped = []
        for ci in ci_list:
            if not isinstance(ci, list) or len(ci) < 2:
                deduped.append(ci)
                continue
            job_name = ci[0]
            job_id = self.ci_dict.get(job_name)
            if job_id is None:
                for key, value in self.ci_dict.items():
                    if '${{' not in key:
                        continue
                    pattern = re.escape(key)
                    pattern = re.sub(r'\\\$\\\{\\\{.*?\\\}\\\}', '.*', pattern)
                    if re.fullmatch(pattern.strip(), job_name.strip()):
                        job_id = value
                        ci = [key, ci[1]]
                        break
            if job_id is None:
                print(f"Warning: CI job '{job_name}' not found in ci_dict (available: {list(self.ci_dict.keys())}). Skipping.")
                continue
            if job_id not in seen_job_ids:
                seen_job_ids.add(job_id)
                deduped.append(ci)
            else:
                print(f"Skipping duplicate job '{job_name}' (job_id '{job_id}' already queued)")
        return deduped

    def _run_act_with_lock(self, ci, target_dir, order, pool):
        # ci is expected to be a list: [job_name, workflow_file]
        if not isinstance(ci, list) or len(ci) < 2:
            print(f"Warning: Invalid ci format: {ci}")
            return
        value = self.ci_dict.get(ci[0])
        if value is None:
            print(f"Warning: CI job '{ci[0]}' not found in ci_dict (available: {list(self.ci_dict.keys())}). Skipping.")
            return
        if value is not None:
            port = pool.acquire_port()
            unique_workflow = None
            job_dir = None
            path = self.config["output_dir"] + "/" + \
                   self.task.instance_id + "_"  + \
                   value + "_" + \
                   order + "_output.json"

            # Create a per-job copy of the testbed so concurrent act processes
            # don't race on git operations / Docker volume initialization.
            job_dir = f"{target_dir}_act_{value}"
            try:
                shutil.copytree(target_dir, job_dir, symlinks=True)
            except Exception as e:
                logger.warning("Failed to create per-job testbed copy for '%s': %s. Using shared dir.", value, e)
                job_dir = None
            work_dir = job_dir if job_dir else target_dir

            workflow_file = os.path.join(work_dir, ci[1])
            try:
                unique_workflow = self._create_unique_workflow_copy(workflow_file, value)
            except Exception as e:
                logger.warning("Failed to create unique workflow copy for '%s': %s. Using original.", value, e)
                unique_workflow = None
            act_workflow = unique_workflow if unique_workflow else workflow_file
            act_cmd = ["act", "-j", value]
            for mapping in ACT_PLATFORM_MAPPINGS:
                act_cmd.extend(["-P", mapping])
            act_cmd.extend(self.act_platform_overrides)
            act_cmd.extend(self.act_matrix_filters)
            act_cmd.extend(self.act_env_flags)
            act_cmd.extend([
                       "--artifact-server-port", str(port),
                       "--artifact-server-addr", "0.0.0.0",
                       "--artifact-server-path", f"./act/{port}",
                       "-W", act_workflow,
                       "-v",
                       "--json"])
            print(f"Run Act with command: {' '.join(act_cmd)}")

            act_cache_dir = os.path.join(work_dir, f".act_cache_{port}")
            try:
                env = os.environ.copy()
                env["XDG_CACHE_HOME"] = act_cache_dir
                os.makedirs(act_cache_dir, exist_ok=True)

                process = subprocess.Popen(act_cmd,
                                        cwd=work_dir,
                                        env=env,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        text=True)

                stdout_lines = []
                stderr_lines = []
                timed_out = False

                def _timeout_kill():
                    nonlocal timed_out
                    timed_out = True
                    process.kill()

                timer = threading.Timer(self.act_timeout, _timeout_kill)
                timer.start()

                stderr_thread = threading.Thread(
                    target=lambda: stderr_lines.extend(process.stderr.readlines()),
                    daemon=True,
                )
                stderr_thread.start()

                job_tracker = {}
                step_tracker = {}
                start_time = time.time()
                for line in process.stdout:
                    stdout_lines.append(line)
                    try:
                        data = json.loads(line.strip())
                        job_name = data.get('job', '')
                        job_result = data.get('jobResult')
                        step_name = data.get('step', '')
                        step_result = data.get('stepResult')

                        if job_name and job_name not in job_tracker:
                            job_tracker[job_name] = 'running'
                            elapsed = time.time() - start_time
                            print(f"  [Act {value}] ({elapsed:.0f}s) Job started: {job_name}")
                            sys.stdout.flush()

                        if step_name and job_name:
                            step_key = (job_name, step_name)
                            if step_result:
                                if step_key in step_tracker:
                                    elapsed = time.time() - start_time
                                    print(f"  [Act {value}] ({elapsed:.0f}s)   Step: {step_name} -> {step_result}")
                                    sys.stdout.flush()
                            elif step_key not in step_tracker:
                                step_tracker[step_key] = True
                                elapsed = time.time() - start_time
                                print(f"  [Act {value}] ({elapsed:.0f}s)   Step: {step_name} ...")
                                sys.stdout.flush()

                        if job_result and job_name in job_tracker:
                            job_tracker[job_name] = job_result
                            done = sum(1 for s in job_tracker.values() if s != 'running')
                            elapsed = time.time() - start_time
                            print(f"  [Act {value}] ({elapsed:.0f}s) [{done}/{len(job_tracker)}] {job_name} -> {job_result}")
                            sys.stdout.flush()
                    except json.JSONDecodeError:
                        pass

                process.wait()
                timer.cancel()
                stderr_thread.join(timeout=5)

                if timed_out:
                    print(f"Warning: act job '{ci[0]}' (workflow: {ci[1]}) timed out after {self.act_timeout}s. Killed.")
                    self._cleanup_act_containers()
                    return

                stdout = ''.join(stdout_lines)
                stderr = ''.join(stderr_lines)

                # Diagnostic: log when act exits with partial results (helps debug early exit)
                completed = sum(1 for v in job_tracker.values() if v != 'running')
                total = len(job_tracker)
                if completed < total and not timed_out:
                    logger.warning(
                        "Act job '%s' exited early: %d/%d jobs completed, returncode=%s. stderr (last 800 chars): %s",
                        ci[0], completed, total, process.returncode,
                        stderr[-800:] if stderr else "(empty)"
                    )
                elif process.returncode != 0:
                    logger.warning(
                        "Act job '%s' exited with returncode=%s. stderr (last 500 chars): %s",
                        ci[0], process.returncode,
                        stderr[-500:] if stderr else "(empty)"
                    )

                result = {
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": process.returncode,
                    "processed_output": self._process_act_output(stdout)
                }
                # dump result to file in specific path
                # DEBUG
                try:
                    debug_path = os.environ["SWING_DEBUG_DIR"]
                except KeyError:
                    debug_path = ''

                if debug_path != '':
                    if not os.path.exists(debug_path):
                        os.makedirs(debug_path)

                    print('dump ci result to file {}'.format(os.path.join(debug_path, self.task.instance_id + "_"  + \
                        value + "_" + \
                        order + "_output.json")))
                    with open(os.path.join(debug_path, self.task.instance_id + "_"  + \
                        value + "_" + \
                        order + "_output.json"), 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=4)

                result_path = os.path.join(target_dir, path) 
                if not os.path.exists(os.path.dirname(result_path)):
                    os.makedirs(os.path.dirname(result_path))
                with open(result_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=4)

                self.result_lock.acquire()
                self.result_list.append(result)
                self.result_lock.release()
            finally:
                if unique_workflow and os.path.exists(unique_workflow):
                    try:
                        os.remove(unique_workflow)
                    except OSError:
                        pass
                shutil.rmtree(act_cache_dir, ignore_errors=True)
                if job_dir and job_dir != target_dir:
                    shutil.rmtree(job_dir, ignore_errors=True)

    def _run_act_without_lock(self, ci, target_dir):
        # for debug
        if not isinstance(ci, list) or len(ci) < 2:
            print(f"Warning: Invalid ci format: {ci}")
            return
        value = self.ci_dict.get(ci[0])
        if value is not None:
            unique_workflow = None
            path = self.config["output_dir"] + "/" + \
                   self.task.instance_id + "_"  + \
                   value + "_output.json"
            workflow_file = os.path.join(target_dir, ci[1])
            try:
                unique_workflow = self._create_unique_workflow_copy(workflow_file, value)
            except Exception as e:
                logger.warning("Failed to create unique workflow copy for '%s': %s. Using original.", value, e)
                unique_workflow = None
            act_workflow = unique_workflow if unique_workflow else workflow_file
            act_cmd = ["act", "-j", value]
            for mapping in ACT_PLATFORM_MAPPINGS:
                act_cmd.extend(["-P", mapping])
            act_cmd.extend(self.act_platform_overrides)
            act_cmd.extend(self.act_matrix_filters)
            act_cmd.extend(self.act_env_flags)
            act_cmd.extend(["-W", act_workflow,
                       "--json"])
            print(f"Run Act with command: {' '.join(act_cmd)}")

            try:
                process = subprocess.Popen(act_cmd,
                                        cwd=target_dir,
                                        env=os.environ.copy(),
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        text=True)
                stdout, stderr = process.communicate()
                result = {
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": process.returncode,
                    "processed_output": self._process_act_output(stdout)
                }
                result_path = os.path.join(target_dir, path) 
                if not os.path.exists(os.path.dirname(result_path)):
                    os.makedirs(os.path.dirname(result_path))
                with open(result_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=4)

                self.result_list.append(result)
            finally:
                if unique_workflow and os.path.exists(unique_workflow):
                    try:
                        os.remove(unique_workflow)
                    except OSError:
                        pass

    @staticmethod
    def _process_result(result_list: list[str]) -> dict:
        processed_result = {}

        for result in result_list:
            if type(result) == str:
                result_json = json.loads(result)
            else:
                result_json = result

            for job in result_json["processed_output"].keys():
                # collect jobResult
                if job not in processed_result.keys():
                    processed_result[job] = {
                        "returncode": result_json["processed_output"][job]["jobResult"],
                        "test_results": {
                            "success": [],
                            "failure": [],
                            "skipped": [],
                        },
                        "unit_test": [0, 0, 0]
                    }
                    # collect step results
                    for item in result_json["processed_output"][job]["steps"]:
                        step_name = item[0]
                        if item[2] == "success":
                            processed_result[job]["test_results"]["success"].append(step_name)
                        elif item[2] == "failure":
                            processed_result[job]["test_results"]["failure"].append(step_name)
                        elif item[2] == "skipped":
                            processed_result[job]["test_results"]["skipped"].append(step_name)

                    processed_result[job]["unit_test"] = result_json["processed_output"][job]["testResult"]

        return processed_result

    def check_env(self):
        if not os.path.exists(self.task.target_dir):
            raise Exception(f'Repo {self.task.target_dir} does not exist. Please check.')
        if not os.path.exists(self.config["workdir"]):
            raise Exception(f'Workdir {self.config["workdir"]} does not exist. Please check.')

    @staticmethod
    def _create_unique_workflow_copy(workflow_file, job_value):
        """Create a temp copy of the workflow with a unique name field to avoid
        Docker container name conflicts when running multiple act processes concurrently.

        act generates deterministic container names from <workflow_name>/<job_name>/<hash>.
        When multiple act processes target the same workflow, they produce identical
        container names for shared dependency jobs, causing Docker conflicts.

        A short UUID is appended to make names unique across runs as well,
        preventing collisions with leftover containers from previous runs.
        """
        run_id = uuid.uuid4().hex[:8]

        with open(workflow_file, 'r', encoding='utf-8') as f:
            content = f.read()

        match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
        if match:
            original_name = match.group(1).strip().strip("'\"")
            new_name = f"{original_name}_{job_value}_{run_id}"
            content = content[:match.start()] + f"name: {new_name}" + content[match.end():]
        else:
            content = f"name: workflow_{job_value}_{run_id}\n" + content

        dir_name = os.path.dirname(workflow_file)
        base_name = os.path.basename(workflow_file)
        name, ext = os.path.splitext(base_name)
        unique_file = os.path.join(dir_name, f"{name}_{job_value}{ext}")

        with open(unique_file, 'w', encoding='utf-8') as f:
            f.write(content)

        return unique_file

    @staticmethod
    def _cleanup_act_containers(include_stopped=False):
        """Remove act-created Docker containers to free resources.

        Args:
            include_stopped: If True, also remove stopped/exited containers
                (needed before starting a new run to avoid container name conflicts).
                If False, only remove running containers (used after timeout kill).
        """
        try:
            cmd = ["docker", "ps", "--filter", "name=act-", "-q"]
            if include_stopped:
                cmd.insert(2, "-a")
            result = subprocess.run(cmd, capture_output=True, text=True)
            container_ids = result.stdout.strip().split('\n')
            container_ids = [c for c in container_ids if c]
            if container_ids:
                subprocess.run(["docker", "rm", "-f"] + container_ids,
                               capture_output=True, text=True)
                print(f"Cleaned up {len(container_ids)} act containers.")
        except Exception as e:
            print(f"Warning: Failed to cleanup act containers: {e}")

    def _ensure_docker_image(self, image_name):
        """Check if Docker image exists, pull it if not"""
        print(f"Checking Docker image: {image_name}")

        # Check if image exists
        check_cmd = ["docker", "images", "-q", image_name]
        result = subprocess.run(check_cmd, capture_output=True, text=True, env=os.environ.copy())

        if result.stdout.strip():
            print(f"✓ Docker image {image_name} already exists")
            return True

        # Image doesn't exist, pull it
        print(f"Docker image {image_name} not found")
        print(f"Pulling image from Docker Hub (size: ~15-20GB)...")
        print(f"This may take 10-60 minutes depending on network speed. Please wait...")

        pull_cmd = ["docker", "pull", image_name]
        try:
            # Don't capture output, let user see progress
            result = subprocess.run(pull_cmd, env=os.environ.copy())

            if result.returncode == 0:
                print(f"✓ Successfully pulled Docker image {image_name}")
                return True
            else:
                print(f"✗ Failed to pull Docker image {image_name}")
                raise Exception(f"Failed to pull Docker image: {image_name}")

        except Exception as e:
            print(f"✗ Error pulling Docker image: {e}")
            raise

    # Tools commonly available on GitHub-hosted runners but missing in slim
    # container images (e.g. node:16-bullseye-slim).  When a workflow job
    # specifies `container:`, act runs inside that image directly, so we
    # inject a setup step to install these tools before anything else.
    _CONTAINER_BOOTSTRAP_TOOLS = ["curl", "wget", "git", "gnupg", "ca-certificates"]

    class _WorkflowDumper(yaml.SafeDumper):
        """Custom YAML dumper that preserves boolean-like keys (on/off/yes/no)
        as their original string form instead of converting them to true/false."""
        pass

    @staticmethod
    def _bool_key_representer(dumper, data):
        if data is True:
            return dumper.represent_scalar('tag:yaml.org,2002:str', 'on')
        if data is False:
            return dumper.represent_scalar('tag:yaml.org,2002:str', 'off')
        return dumper.represent_data(data)

    _WorkflowDumper.add_representer(bool, _bool_key_representer)

    def _patch_workflow_files(self, target_dir):
        """Inject tool-installation step into workflow jobs that use `container:`."""
        workflows_dir = os.path.join(target_dir, ".github", "workflows")
        if not os.path.isdir(workflows_dir):
            return

        tools = " ".join(self._CONTAINER_BOOTSTRAP_TOOLS)
        install_cmd = (
            "if command -v apt-get >/dev/null 2>&1; then "
            f"apt-get update -qq && apt-get install -y -qq --no-install-recommends {tools}; "
            "elif command -v dnf >/dev/null 2>&1; then "
            f"dnf install -y -q {tools}; "
            "elif command -v yum >/dev/null 2>&1; then "
            f"yum install -y -q {tools}; "
            "elif command -v apk >/dev/null 2>&1; then "
            f"apk add --no-cache {tools}; "
            "fi"
            " > /dev/null 2>&1 || true"
        )

        setup_step = {
            "name": "Install CI tools (act compatibility)",
            "run": install_cmd,
        }

        for wf_path in glob.glob(os.path.join(workflows_dir, "*.yml")) + \
                        glob.glob(os.path.join(workflows_dir, "*.yaml")):
            try:
                with open(wf_path, "r", encoding="utf-8") as f:
                    wf = yaml.safe_load(f)
            except Exception:
                continue

            if not isinstance(wf, dict) or "jobs" not in wf:
                continue

            modified = False
            for job_name, job_def in wf["jobs"].items():
                if not isinstance(job_def, dict):
                    continue
                if "container" not in job_def:
                    continue

                steps = job_def.get("steps", [])
                if not steps:
                    continue

                # Avoid duplicate injection (idempotent)
                if steps and steps[0].get("name") == setup_step["name"]:
                    continue

                job_def["steps"] = [setup_step] + steps
                modified = True

            if modified:
                with open(wf_path, "w", encoding="utf-8") as f:
                    yaml.dump(wf, f, Dumper=self._WorkflowDumper,
                              default_flow_style=False, sort_keys=False,
                              allow_unicode=True)
                logger.info("Patched workflow for act container compatibility: %s", wf_path)

    def run_ci(self, pool):
        task = self.task
        try:
            run_script("\n".join(task.env_script))
            self.check_env()
            run_script("\n".join(task.eval_script))

            # Ensure Docker image exists before running CI
            self._ensure_docker_image(ACT_DEFAULT_IMAGE)

            # Remove stale act containers from previous runs to avoid name conflicts
            self._cleanup_act_containers(include_stopped=True)

            # Patch workflow files so container-based jobs have common tools
            self._patch_workflow_files(task.target_dir)

            print(f"Starting CI run for {self.config['repo']} (ID: {self.config.get('instance_id', 'unknown')})")

            self._get_ci_job_name_id_dict(task.target_dir)
            print(f'Collected CI job name and id dict: {self.ci_dict}')
            print(f'Run ci list: {self.config["ci_name_list"]}')
            threads = []
            ci_list = self._normalize_ci_list(self.config["ci_name_list"])
            print(f'Normalized ci list: {ci_list}')
            ci_list = self._deduplicate_ci_list(ci_list)
            print(f'Deduplicated ci list: {ci_list}')
            semaphore = threading.Semaphore(self.max_concurrent)
            print(f'Max concurrent CI jobs: {self.max_concurrent}')

            def _throttled_run(ci, target_dir, order, pool, sem):
                with sem:
                    self._run_act_with_lock(ci, target_dir, order, pool)

            for ci in ci_list:
                thread = threading.Thread(
                    target=lambda ci=ci: _throttled_run(ci, task.target_dir, "merged", pool, semaphore)
                )
                thread.start()
                threads.append(thread)
                time.sleep(0.5)

            for thread in threads:
                thread.join()

            result = ActCITool._process_result(self.result_list)
            print(f"CI run completed for {self.config['repo']} (ID: {self.config.get('instance_id', 'unknown')})")
            return result
        finally:
            ActCITool._cleanup_act_containers(include_stopped=True)

    def construct(self):
        env_script = self._build_repo_base_env()
        eval_script = self._build_eval_script()

        instance_id = self.config.get("instance_id", "unknown")
        # Use instance_id directly as directory name
        target_dir = os.path.join(self.config["workdir"], instance_id)
        
        self.task = Task(instance_id=instance_id,
                         env_script=env_script,
                         eval_script=eval_script,
                         patch=self.config["patch"],
                         target_dir=target_dir,
                         output_dir=self.config["output_dir"],
                         apply_patch=self.config["apply_patch"])

EVAL_HANDLER = {
    "cargo": CargoCITool,
    "docker": DockerCITool,
    "act": ActCITool
}

RUST_BASE_ENV={
    "vectordotdev/vector": ["protobuf-compiler", "libsasl2-dev"]
}

RUST_INSTALL = ["if ! command -v rustc >/dev/null 2>&1; then",
                "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
                "source \"$HOME/.cargo/env\"", "fi"]


if __name__ == '__main__':
    # inputs = ''
    # with open(os.path.join(os.environ["SWING_TESTBED_PATH"], "cplee__github-actions-demo-1_test_merged_output.json"), 'r') as f:
    #     while x := f.readline():
    #         inputs += x
    #     result = ActCITool._process_result([inputs])
    #     for each in result:
    #         print(each, result[each])
    # exit()

    from swingarena.harness.utils import PortPool
    port_pool = PortPool([i for i in range(50505, 52505)])

    # Comment(wdxu): fake data for test only.
    # act = ActCITool({"act_path": "/mnt/Data/wdxu/github/act/bin/act", \
    #                  "instance_id": "cplee__github-actions-demo-1", \
    #                  "repo": "cplee/github-actions-demo", \
    #                  "base_commit": "2dcabf3769c2613687310c7b71b89af681e8ee50", \
    #                  "merge_commit": "2dcabf3769c2613687310c7b71b89af681e8ee50", \
    #                  "patch": "", \
    #                  "apply_patch": True, \
    #                  "src_folder": os.environ["SWING_TESTBED_PATH"], \
    #                  "workdir": os.environ["SWING_TESTBED_PATH"], \
    #                  "ci_name_list": [["test", ".github/workflows/main.yml"]], \
    #                  "output_dir": os.environ["SWING_TESTBED_PATH"]})
    act = ActCITool({"act_path": "/usr/local/bin/act",
                     "instance_id": "",
                     "repo": "rustzx/rustzx",
                     "base_commit": "",
                     "merge_commit": "",
                     "patch": "",
                     "src_folder": "/home/tmpdata/rust-repos",
                     "output_dir": "logs",
                     "workdir": "/home/tmpdata/rust-repos",
                     "apply_patch": False,
                     "ci_name_list": [["Unit tests", 0], ["Typos check", 0]]})

    result = act.run_ci(port_pool)
    print(result)
    with open('./result.log', 'w') as f:
        f.write(str(result))