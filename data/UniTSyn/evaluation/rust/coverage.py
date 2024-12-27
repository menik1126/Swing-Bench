"""Functions for running cargo-fuzz and get coverage for test cases"""

import json
from typing import Iterable, Iterator
import fire
import os
from tree_sitter import Node
from frontend.parser import RUST_LANGUAGE
from frontend.parser.ast_util import ASTUtil
from unitsyncer.util import replace_tabs
import subprocess
from unitsyncer.common import UNITSYNCER_HOME
from returns.maybe import Maybe, Some, Nothing
from frontend.rust.rust_util import get_test_functions
from frontend.rust.collect_all import collect_test_files
from unitsyncer.util import concatMap


def clean_workspace(workspace_dir: str):
    subprocess.run(["rm", "rust_test_coverage.sh"], cwd=workspace_dir)
    subprocess.run(["rm", "-r", "target"], cwd=workspace_dir)


def init_workspace(workspace_dir: str):
    cov_script_path = f"{UNITSYNCER_HOME}/evaluation/rust/rust_test_coverage.sh"
    subprocess.run(["cp", cov_script_path, workspace_dir])


def get_coverage(
    workspace_dir: str, test_target: str, clean_run: bool = False
) -> Maybe[float]:
    if clean_run:
        clean_workspace(workspace_dir)

    init_workspace(workspace_dir)

    subprocess.run(
        ["./rust_test_coverage.sh", test_target],
        cwd=workspace_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        cov_path = f"{workspace_dir}/target/debug/coverage/{test_target}/coverage.json"
        with open(cov_path) as f:
            cov_obj = json.load(f)
    except FileNotFoundError:
        return Nothing

    if cov_obj["label"] != "coverage" or "message" not in cov_obj:
        return Nothing
    return Some(float(cov_obj["message"][:-1]))


def get_tests(workspace_dir: str) -> Iterable[str]:
    """get all test targets from project by looking for fn with #[test] in tests dir"""

    def get_tests_from_file(fpath: str) -> list[str]:
        with open(fpath) as f:
            code = f.read()
        ast_util = ASTUtil(code)
        tree = ast_util.tree(RUST_LANGUAGE)
        test_nodes = get_test_functions(ast_util, tree.root_node)
        return [t.unwrap() for t in map(ast_util.get_name, test_nodes) if t != Nothing]

    return concatMap(
        get_tests_from_file,
        collect_test_files(os.path.join(workspace_dir, "tests"), False),
    )


def get_testcase_coverages(workspace_dir: str) -> dict[str, float]:
    """get coverage of each individual testcase in the tests sub-directory

    Args:
        workspace_dir (str): root of the project workspace

    Returns:
        dict[str, float]: {testcase_name: its coverage}
    """
    coverages = {}
    for test_name in get_tests(workspace_dir):
        cov = get_coverage(workspace_dir, test_name).unwrap()
        coverages[test_name] = cov
    return coverages


def main():
    workspace_dir = os.path.abspath(
        "data/repos/marshallpierce-rust-base64/marshallpierce-rust-base64-4ef33cc"
    )

    print(get_testcase_coverages(workspace_dir))


if __name__ == "__main__":
    fire.Fire(main)
