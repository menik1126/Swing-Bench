"""Execution Runtime Metrics for Python, Java, Go, C++, and JS"""

import logging
import fire
import json
import docker
import contextlib
import os
import tempfile
import subprocess
import random
from multiprocessing import Pool
from tqdm import tqdm


@contextlib.contextmanager
def build_image(repo_id: str):
    _, workdir = repo_id.split("/")
    dockerfile = f"""
FROM unitsyncer-eval:python
ENV DEBIAN_FRONTEND noninteractive
RUN git clone https://github.com/{repo_id}
WORKDIR {workdir}
RUN pip install -r requirements.txt
"""
    temp_file = tempfile.NamedTemporaryFile(prefix="unitsyncer_")
    with open(temp_file.name, "w") as f:
        f.write(dockerfile)
    try:
        subprocess.run(
            ["docker", "build", "--tag", repo_id, ".", "-f", temp_file.name],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        yield
    finally:
        subprocess.run(
            ["docker", "rmi", repo_id, "-f"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def parse_pytest_output_coverage(stdout: str) -> float | None:
    lines = stdout.splitlines()
    for line in reversed(lines):
        if "TOTAL" in line:
            elems = line.split(" ")
            return float(elems[-1].strip("%"))
    return None


def get_py_coverage(repo_id: str):
    try:
        with build_image(repo_id):
            client = docker.from_env()
            res = client.containers.run(repo_id, "pytest --cov=. tests")
            if isinstance(res, bytes):
                stdout = res.decode("utf-8")
                return parse_pytest_output_coverage(stdout)
    except:
        with open("coverage.log", "a") as fp:
            fp.write(repo_id + "\n")
        return None

    return None


def main(repo_list_path: str, lang: str, nproc: int = 20, seed: int = 0):
    with open(repo_list_path, "r") as fp:
        repo_list = fp.read().splitlines()[:10000]

    with open("coverage.log", "r") as fp:
        skip_list = fp.read().splitlines()

    repo_list = [repo for repo in repo_list if repo not in skip_list]

    # with Pool(nproc) as pool:
    #     covs = list(tqdm(pool.imap(get_py_coverage, repo_list), total=len(repo_list)))

    with open(f"{lang}_coverage.jsonl", "a") as writer:
        for repo_id in tqdm(repo_list):
            cov = get_py_coverage(repo_id)
            if cov is not None:
                writer.write(json.dumps({"repo_id": repo_id, "coverage": cov}) + "\n")
            else:
                logging.warning(f"{repo_id} no coverage")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fire.Fire(main)
