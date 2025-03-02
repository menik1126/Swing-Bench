from dataclasses import dataclass
import subprocess

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
    
    def construct(self):
        pass

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