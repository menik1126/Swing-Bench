from dataclasses import dataclass
import subprocess
import os
import re
import tempfile
import threading
from queue import Queue
import json

def run_script(script_content):

    with tempfile.NamedTemporaryFile(mode="w", delete=True, suffix=".sh") as temp_script:
        temp_script.write(script_content)
        temp_script.flush()
        temp_path = temp_script.name

        try:
            subprocess.run(["bash", temp_path], check=True)
        except:
            # TODO: handle except
            pass

@dataclass
class Task:
    id: str
    env_script: list[str]
    eval_script: list[str]
    patch: str
    target_dir: str
    output_dir: str
    previous_eval_script: list[str] = None

class CIToolBase:
    def __init__(self, config):
        self.config = config

    def construct(self):
        pass
    
    def run_ci(self, log_file):
        pass

class CargoCITool(CIToolBase):
    def __init__(self, config):
        super().__init__(config)
        self.construct()

    def _build_repo_base_env(self):
        script = ["#!/bin/bash"]

        if subprocess.run(['rustc', '--version'], capture_output=True).returncode != 0:
            script.extend(RUST_INSTALL)

        package_list = RUST_BASE_ENV[self.config["repo"]]
        script.extend(["apt install " + package for package in package_list])
        script.extend(["cd " + self.config["workdir"], "git clone https://github.com/" + self.config["repo"] + ".git"])

        return script

    def _build_eval_script(self):
        script = ["#!/bin/bash", 
                    "cd " + self.config["workdir"] + "/" + self.config["repo"].split("/")[1],
                    "git checkout " + self.config["merge_commit"],
                ]

        return script

    def construct(self):
        env_script = self._build_repo_base_env()
        eval_script = self._build_eval_script()
        target_dir = self.config["workdir"] + "/" + self.config["repo"].split("/")[1]
        self.task = Task("", env_script, eval_script, self.config["patch"], target_dir, self.config["output_dir"])

    def run_ci(self, log_file):
        task = self.task
        with open(log_file, "w") as f:
            result = subprocess.run(["cargo", "test"], cwd=task.target_dir, stdout=f, stderr=f, text=True)
        if result.returncode != 0:
            print(f"[ERROR] Task {task.id} cargo test failed with return code {result.returncode}")
            return None
        return result

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
        self.cloned_repo_path = self.config["repo"].split("/")[1] + "_" + self.config["merge_commit"]
        self.ci_dict = dict()
        self.result_lock = threading.Lock()
        self.semaphore = threading.Semaphore(1)
        self.act_mq = Queue()
        self.construct()

    def _build_repo_base_env(self):
        script = ["#!/bin/bash"]
        script.extend(["cd " + self.config["workdir"],
                       "git clone https://github.com/" + self.config["repo"] + ".git " + self.cloned_repo_path])

        return script

    def _build_previous_eval_script(self):
        script = ["#!/bin/bash", 
                    "cd " + os.path.join(self.config["workdir"], self.cloned_repo_path),
                    "prev_commit=$(git rev-parse " + self.config["base_commit"] + "^)",
                    "git checkout $prev_commit"
                ]

        return script

    def _build_eval_script(self):
        script = ["#!/bin/bash", 
                    "cd " + os.path.join(self.config["workdir"], self.cloned_repo_path),
                    "git checkout " + self.config["merge_commit"]
                ]

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
        script.extend(["act --list > {}".format(self.act_list_path)])
        os.system("\n".join(script))
        # only absolute path? 
        act_list_path = os.path.join(target_dir, self.act_list_path)
        self.ci_dict = _extract_jobs(os.path.expanduser(act_list_path))
        os.system("rm " + act_list_path)
                    
    def _process_act_output(self, stdout):
        results = []
        for line in stdout.split('\n'):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                # {
                # "dryrun": false,
                # "job": "checks/test-linux",
                # "jobID": "test-linux",
                # "level": "info",
                # "matrix": {},
                # "msg": "  ✅  Success - Main actions/setup-go@v5",
                # "stage": "Main",
                # "step": "actions/setup-go@v5",
                # "stepID": [
                #     "2"
                # ],
                # "stepResult": "success",
                # "time": "2025-03-05T13:49:03+08:00"
                # }
                result = {
                    'dryrun': data.get('dryrun', ''),
                    'job': data.get('job', ''),
                    'jobID': data.get('jobID', ''),
                    'level': data.get('level', ''),
                    'matrix': data.get('matrix', ''),
                    'msg': data.get('msg', ''),
                    'raw_output': data.get('raw_output', ''),
                    'stage': data.get('stage', ''),
                    'step': data.get('step', ''),
                    'stepID': data.get('stepID', ''),
                    'stepResult': data.get('stepResult', ''),
                    'time': data.get('time', ''),
                }
                results.append(result)
            except json.JSONDecodeError:
                continue
        return results

    def _run_act_with_semaphore(self, ci, target_dir, order):
        with self.semaphore:
            value = self.ci_dict.get(ci[0])
            if value is not None:
                process = subprocess.Popen(["act", "-j", value,
                                            "-W", ci[1], 
                                             "--json"], 
                                        cwd=target_dir,
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
                path = self.config["output_dir"] + "/" + self.task.id + "_" + order + "_" + value + "_output.json"
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=4)
                self.act_mq.put(result)

    def run_ci(self):
        task = self.task
        run_script("\n".join(task.env_script))
        run_script("\n".join(task.eval_script))

        self._get_ci_job_name_id_dict(task.target_dir)
        eval_result = []
        threads = []
        for ci in self.config["ci_name_list"]:
            thread = threading.Thread(
                target=lambda ci=ci: self._run_act_with_semaphore(ci, task.target_dir, "merged")
            )
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
        
        while not self.act_mq.empty():
            eval_result.append(self.act_mq.get())
        
        run_script("\n".join(task.previous_eval_script))
        previous_eval_result = []
        threads = []
        for ci in self.config["ci_name_list"]:
            thread = threading.Thread(
                target=lambda ci=ci: self._run_act_with_semaphore(ci, task.target_dir, "based")
            )
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
            
        while not self.act_mq.empty():
            previous_eval_result.append(self.act_mq.get())

        os.system("rm -rf " + task.target_dir)

        return [eval_result, previous_eval_result]

    def construct(self):
        env_script = self._build_repo_base_env()
        eval_script = self._build_eval_script()
        previous_eval_script = self._build_previous_eval_script()
        target_dir = os.path.join(self.config["workdir"],
                                  self.cloned_repo_path)
        self.task = Task(self.config["id"], env_script, eval_script, self.config["patch"], target_dir, self.config["output_dir"], previous_eval_script)


HANDLER = {
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
    # Comment(wdxu): fake data for test only.
    act = ActCITool({"act_path": "/mnt/Data/wdxu/github/act/bin/act", \
                     "repo": "cplee/github-actions-demo", \
                     "base_commit": "2dcabf3769c2613687310c7b71b89af681e8ee50", \
                     "merge_commit": "2dcabf3769c2613687310c7b71b89af681e8ee50", \
                     "patch": "patch_content", \
                     "workdir": "/home/wdxu/testbed", \
                     "output_dir": "output_dir"})
    result = act.run_ci(['test'])
    with open('./result.log', 'w') as f:
        f.write(str(result))

    # def _run_act_with_semaphore(self, ci, target_dir, order, port_pool):
    #     if ci in self.ci_dict.values():
    #         with self.semaphone:
    #             port = 34567
    #             os.makedirs(f"./act/{port}", exist_ok=True)
    #             process = subprocess.Popen(["act", "-j", ci, "--artifact-server-port", str(port),
    #                                         "--artifact-server-addr", "0.0.0.0", 
    #                                         "--artifact-server-path", f"./act/{port}", 
    #                                         "--json"], 
    #                                     cwd=target_dir,
    #                                     stdout=subprocess.PIPE,
    #                                     stderr=subprocess.PIPE,
    #                                     text=True)
    #             stdout, stderr = process.communicate()
    #             result = {
    #                 "stdout": stdout,
    #                 "stderr": stderr,
    #                 "returncode": process.returncode,
    #                 "processed_output": self._process_act_output(stdout)
    #             }
    #             path = self.config["output_dir"] + "/" + self.task.id + "_" + order + "_" + ci + "_output.json"
    #             with open(path, 'w', encoding='utf-8') as f:
    #                 json.dump(result, f, ensure_ascii=False, indent=4)
    #             self.act_mq.put(result)
    #             port_pool.release_port(port)

    # def run_ci(self, port_pool):
    #     task = self.task
    #     run_script("\n".join(task.env_script))
    #     run_script("\n".join(task.eval_script))

    #     self._get_ci_job_name_id_dict(task.target_dir)
    #     eval_result = []
    #     threads = []
    #     for ci in self.config["ci_name_list"]:
    #         thread = threading.Thread(
    #             target=lambda ci=ci: self._run_act_with_semaphore(ci, task.target_dir, "merged", port_pool)
    #         )
    #         thread.start()
    #         threads.append(thread)
        
    #     for thread in threads:
    #         thread.join()
        
    #     while not self.act_mq.empty():
    #         eval_result.append(self.act_mq.get())
        
    #     run_script("\n".join(task.previous_eval_script))
    #     previous_eval_result = []
    #     threads = []
    #     for ci in self.config["ci_name_list"]:
    #         thread = threading.Thread(
    #             target=lambda ci=ci: self._run_act_with_semaphore(ci, task.target_dir, "based", port_pool)
    #         )
    #         thread.start()
    #         threads.append(thread)
        
    #     for thread in threads:
    #         thread.join()
            
    #     while not self.act_mq.empty():
    #         previous_eval_result.append(self.act_mq.get())

    #     os.system("rm -rf " + task.target_dir)

    #     return [eval_result, previous_eval_result]
