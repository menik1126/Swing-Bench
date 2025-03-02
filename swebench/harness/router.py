from dataclasses import dataclass
import subprocess
import os
import re

tasks = []

@dataclass
class Task:
    id: int
    env_script: list[str]
    eval_script: list[str]
    patch: str
    target_dir: str
    output_dir: str

class CIToolBase:
    def __init__(self, config):
        self.config = config

    def construct(self):
        pass
    
    def run_ci(self, task, log_file):
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
                    "git checkout " + self.config["base_commit"],
                ]

        return script

    def construct(self):
        env_script = self._build_repo_base_env()
        eval_script = self._build_eval_script()
        target_dir = self.config["workdir"] + "/" + self.config["repo"].split("/")[1]
        task = Task(len(tasks), env_script, eval_script, self.config["patch"], target_dir, self.config["output_dir"])
        tasks.append(task)

    def run_ci(self, task, log_file):
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
        tasks.append()


class ActCITool(CIToolBase):
    def __init__(self, config):
        super().__init__(config)
        self.construct()
        self.ci_dict = dict()

    def _build_repo_base_env(self):
        script = ["#!/bin/bash"]
        script.extend(["cd " + self.config["workdir"], "git clone https://github.com/" + self.config["repo"] + ".git"])

        return script

    def _build_eval_script(self):
        script = ["#!/bin/bash", 
                    "cd " + self.config["workdir"] + "/" + self.config["repo"].split("/")[1],
                    "git checkout " + self.config["base_commit"],
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
        script.extend(["act --list > act_list.txt"])
        os.system("\n".join(script))
        self.ci_dict = _extract_jobs(target_dir + "/act_list.txt")
        os.system("rm " + target_dir + "/act_list.txt")
                    
    def run_ci(self, task, log_file, ci_list):
        self._get_ci_job_name_id_dict(task.target_dir)
        result = []
        for ci in ci_list:
            subprocess.run(["act", "-j", self.ci_dict[ci]], cwd=task.target_dir)
            result.append(self._run_ci(task, log_file, ci))
        return result

    def construct(self):
        env_script = self._build_repo_base_env()
        eval_script = self._build_eval_script()
        target_dir = self.config["workdir"] + "/" + self.config["repo"].split("/")[1]
        task = Task(len(tasks), env_script, eval_script, self.config["patch"], target_dir, self.config["output_dir"])
        tasks.append(task)

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
                     "repo": "vectordotdev/servo", \
                     "base_commit": "d49c542930267cc69d577e8d3b86a6c119fcf331", \
                     "patch": "patch_content", \
                     "workdir": "/home/wdxu/github", \
                     "output_dir": "output_dir"})
    act.run_ci(tasks[0], './debug.log', ['Android Build'])