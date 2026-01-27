import subprocess
import re
import os
import tempfile
import threading
import json
from dataclasses import dataclass
import logging
import time

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
        dst_path = os.path.join(self.config["workdir"], f"{self.config['repo'].split('/')[1]}_{instance_id}")
        
        script.append(f"mkdir -p {dst_path}")
        script.append(f"cp -r {src_path}/. {dst_path}/")

        return script

    def _build_eval_script(self):
        instance_id = self.config.get("instance_id", "unknown")
        target_dir = os.path.join(self.config["workdir"], f"{self.config['repo'].split('/')[1]}_{instance_id}")

        script = ["#!/bin/bash", 
                  f"cd {target_dir}",
                 ]

        script.append("git stash -u || true")
        
        if "merge_commit" in self.config and self.config["merge_commit"]:
            script.append("git checkout " + self.config["merge_commit"])
            
            # Apply test_patch if it exists
            if self.config.get("test_patch"):
                test_patch_file = f"{target_dir}/test_patch.diff"
                script.append(f"cat > {test_patch_file} << 'EOL'\n{self.config['test_patch']}\nEOL")
                script.append(f"git apply {test_patch_file} || echo 'Failed to apply test_patch'")
            
            # Apply patch only if apply_patch is specified
            if self.config.get("apply_patch", False) and self.config.get("patch"):
                patch_file = f"{target_dir}/patch.diff"
                script.append(f"cat > {patch_file} << 'EOL'\n{self.config['patch']}\nEOL")
                script.append(f"git apply {patch_file} || echo 'Failed to apply patch'")

        return script

    def construct(self):
        env_script = self._build_repo_base_env()
        eval_script = self._build_eval_script()
        
        instance_id = self.config.get("instance_id", "unknown")
        target_dir = os.path.join(self.config["workdir"], f"{self.config['repo'].split('/')[1]}_{instance_id}")
        
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
        # Ensure each repository uses unique script file paths
        repo_name = self.config["repo"].split("/")[1]
        instance_id = self.config.get("instance_id", "unknown")
        script_dir = os.path.join(self.config["workdir"], f"{repo_name}_{instance_id}")
        
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


class ActCITool(CIToolBase):
    def __init__(self, config):
        super().__init__(config)
        self.act_list_path = 'act_list.txt'
        self.apply_patch = self.config["apply_patch"]
        self.cloned_repo_path = self.config["repo"].split("/")[1] + "__" + self.config["merge_commit"]
        self.ci_dict = dict()
        self.result_lock = threading.Lock()
        self.result_list = []

        self.construct()

    # TODO(wdxu): make these two functions to be public methods.
    def _build_repo_base_env(self):
        script = ["#!/bin/bash"]
        
        repo_dir_name = self.config["repo"].replace('/', '__')
        instance_id = self.config.get("instance_id", "unknown")
        src_path = os.path.join(self.config["src_folder"], repo_dir_name)
        dst_path = os.path.join(self.config["workdir"], f"{self.config['repo'].split('/')[1]}_{instance_id}")
        
        script.append(f"mkdir -p {dst_path}")
        script.append(f"cp -r {src_path}/. {dst_path}/")

        return script

    def _build_eval_script(self):
        instance_id = self.config.get("instance_id", "unknown")
        target_dir = os.path.join(self.config["workdir"], f"{self.config['repo'].split('/')[1]}_{instance_id}")

        script = ["#!/bin/bash", 
                  f"cd {target_dir}",
                 ]
        
        script.append("git stash -u || true")
        
        if "merge_commit" in self.config and self.config["merge_commit"]:
            script.append("git checkout " + self.config["merge_commit"])
            
            # Apply test_patch if it exists
            if self.config.get("test_patch"):
                test_patch_file = f"{target_dir}/test_patch.diff"
                script.append(f"cat > {test_patch_file} << 'EOL'\n{self.config['test_patch']}\nEOL")
                script.append(f"git apply {test_patch_file} || echo 'Failed to apply test_patch'")
            
            # Apply patch only if apply_patch is specified
            if self.config.get("apply_patch", False) and self.config.get("patch"):
                patch_file = f"{target_dir}/patch.diff"
                script.append(f"cat > {patch_file} << 'EOL'\n{self.config['patch']}\nEOL")
                script.append(f"git apply {patch_file} || echo 'Failed to apply patch'")

        return script


    def _get_ci_job_name_id_dict(self, target_dir):
        def _extract_jobs(filename):
            jobs = {}
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

        script = ["#!/bin/bash"]
        script.extend(["cd " + target_dir])
        script.extend([f"act --list > {self.act_list_path}"])
        os.system("\n".join(script))
        # only absolute path? 
        act_list_path = os.path.join(target_dir, self.act_list_path)
        self.ci_dict = _extract_jobs(os.path.expanduser(act_list_path))
        os.system("rm " + act_list_path)
                    
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
        stdout_list = stdout.split('\n')
        for line in stdout_list:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                job = data.get('job')
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
            step = data.get('step', None)
            step_result = data.get('stepResult', None)
            job_result = data.get('jobResult', None)
            if step and step_result:
                results[data.get('job')]['steps'].append((step, data.get('stage', None), step_result))
            if job_result:
                results[data.get('job')]['jobResult'] = job_result

            # parse unit test results
            target = ["cargo test", "test", "tests"]
            passed = [r"(\d+)\s*passed", r"(\d+)\s*pass"]
            failed = [r"(\d+)\s*failed", r"(\d+)\s*fail"]
            ignored = [r"(\d+)\s*ignored", r"(\d+)\s*ignore"]
            for tar in target:
                if tar in data.get('job').lower():
                    msg = data.get('msg')
                    if "test result" in msg:
                        for p in passed:
                            match = re.search(p, msg, re.IGNORECASE)
                            if match:
                                results[data.get('job')]['testResult'][0] += int(match.group(1))

                        for f in failed:
                            match = re.search(f, msg, re.IGNORECASE)
                            if match:
                                results[data.get('job')]['testResult'][1] += int(match.group(1))

                        for i in ignored:
                            match = re.search(i, msg, re.IGNORECASE)
                            if match:
                                results[data.get('job')]['testResult'][2] += int(match.group(1))

        return results

    def _run_act_with_lock(self, ci, target_dir, order, pool):
        if type(ci) == str:
            import ast
            # cast str to list
            ci = ast.literal_eval(ci)
        value = self.ci_dict.get(ci[0])
        # if value is None:
            # print("value is None ci and its type: ", ci, type(ci))
            # print(self.ci_dict)
        if value is not None:
            port = pool.acquire_port()
            path = self.config["output_dir"] + "/" + \
                   self.task.instance_id + "_"  + \
                   value + "_" + \
                   order + "_output.json"
            # Do not ignore the existing results.
            # if os.path.exists(path):
            #     print(f"path exists: {path}. Ignore...")
            #     return
            # print(target_dir)
            # print(os.path.join(target_dir, ci[1]))
            print("Run Act with command: " + "act " + "-j " + value + " " \
                                            "-P " + "ubuntu-latest=catthehacker/ubuntu:full-latest " + \
                                            "--artifact-server-port " + str(port) + " " +\
                                            "--artifact-server-addr " + "0.0.0.0" + " " +\
                                            "--artifact-server-path " + f"./act/{port}" + " " +\
                                            # "-W " + os.path.join(target_dir, ci[1]) + " " +\
                                            "-v " +\
                                            "--json")

            process = subprocess.Popen(["act", "-j", value,
                                        "-P", "ubuntu-latest=catthehacker/ubuntu:full-latest",
                                        "--artifact-server-port", str(port),
                                        "--artifact-server-addr", "0.0.0.0",
                                        "--artifact-server-path", f"./act/{port}",
                                        # "-W", os.path.join(target_dir, ci[1]),
                                        "-v",
                                        "--json"],
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

    def _run_act_without_lock(self, ci, target_dir):
        # for debug
        value = self.ci_dict.get(ci[0])
        if value is not None:
            path = self.config["output_dir"] + "/" + \
                   self.task.instance_id + "_"  + \
                   value + "_output.json"
            print("Run Act with command: " + "act " + "-j " + value + " " \
                                            "-P " + "ubuntu-latest=catthehacker/ubuntu:full-latest " + \
                                            "--json")

            process = subprocess.Popen(["act", "-j", value,
                                        "-P", "ubuntu-latest=catthehacker/ubuntu:full-latest",
                                        "--json"],
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

    def run_ci(self, pool):
        task = self.task
        run_script("\n".join(task.env_script))
        self.check_env()
        run_script("\n".join(task.eval_script))

        # Ensure Docker image exists before running CI
        self._ensure_docker_image("catthehacker/ubuntu:full-latest")

        print(f"Starting CI run for {self.config['repo']} (ID: {self.config.get('instance_id', 'unknown')})")

        self._get_ci_job_name_id_dict(task.target_dir)
        print(f'Collected CI job name and id dict: {self.ci_dict}')
        print(f'Run ci list: {self.config["ci_name_list"]}')
        threads = []
        for ci in self.config["ci_name_list"]:
            thread = threading.Thread(
                target=lambda ci=ci: self._run_act_with_lock(ci, task.target_dir, "merged", pool)
            )
            thread.start()
            threads.append(thread)
            time.sleep(0.5)

        for thread in threads:
            thread.join()

        # for ci in self.config["ci_name_list"]:
        #     self._run_act_without_lock(ci, task.target_dir)

        result = ActCITool._process_result(self.result_list)
        print(f"CI run completed for {self.config['repo']} (ID: {self.config.get('instance_id', 'unknown')})")
        return result

    def construct(self):
        env_script = self._build_repo_base_env()
        eval_script = self._build_eval_script()

        instance_id = self.config.get("instance_id", "unknown")
        target_dir = os.path.join(self.config["workdir"], f"{self.config['repo'].split('/')[1]}_{instance_id}")
        
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