"""main script for Java frontend"""

from typing import Iterable
import fire
import os
from tree_sitter import Node
from frontend.parser import JAVA_LANGUAGE
from frontend.parser.ast_util import ASTUtil
from returns.maybe import Maybe, Nothing, Some
from frontend.java.collect_focal import get_focal_call, is_test_fn
from unitsyncer.util import replace_tabs
import json
from frontend.util import mp_map_repos, wrap_repo, run_with_timeout
from collections import Counter


def has_test(file_path):
    # follow TeCo to check for JUnit4 and JUnit5
    # todo: support different usage as in google/closure-compiler
    def has_junit4(code):
        return "@Test" in code and "import org.junit.Test" in code

    def has_junit5(code):
        return "@Test" in code and "import org.junit.jupiter.api.Test" in code

    with open(file_path, "r", errors="replace") as f:
        code = f.read()
    return has_junit4(code) or has_junit5(code)


def collect_test_files(root: str):
    """Get all files end with .java in the given root directory

    Args:
        root (str): path to repo root
    """
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(".java"):
                if has_test(p := os.path.join(dirpath, filename)):
                    yield p


def collect_test_funcs(ast_util: ASTUtil) -> Iterable[Node]:
    """collect testing functions from the target file"""

    tree = ast_util.tree(JAVA_LANGUAGE)
    root_node = tree.root_node

    decls = ast_util.get_all_nodes_of_type(root_node, "method_declaration")

    return filter(lambda n: is_test_fn(n, ast_util), decls)


def collect_test_n_focal(file_path: str):
    with open(file_path, "r", errors="replace") as f:
        ast_util = ASTUtil(replace_tabs(f.read()))

    def get_focal_for_test(test_func: Node):
        test_name = ast_util.get_method_name(test_func).value_or(None)
        focal, focal_loc = get_focal_call(ast_util, test_func).value_or((None, None))
        return {
            "test_id": test_name,
            "test_loc": test_func.start_point,
            "test": ast_util.get_source_from_node(test_func),
            "focal_id": focal,
            "focal_loc": focal_loc,
        }

    return map(get_focal_for_test, collect_test_funcs(ast_util))


@run_with_timeout
def collect_from_repo(
    repo_id: str, repo_root: str, test_root: str, focal_root: str
):  # pylint: disable=unused-argument
    """collect all test functions in the given project
    return (status, nfile, ntest)
    status can be 0: success, 1: repo not found, 2: test not found, 3: skip when output file existed
    """
    repo_path = os.path.join(repo_root, wrap_repo(repo_id))
    if not os.path.exists(repo_path) or not os.path.isdir(repo_path):
        return 1, 0, 0
    focal_path = os.path.join(focal_root, wrap_repo(repo_id) + ".jsonl")
    # skip if exist
    if os.path.exists(focal_path):
        return 3, 0, 0
    # collect potential testing modules
    all_files = collect_test_files(repo_path)
    tests = {}
    for f in all_files:
        funcs = collect_test_n_focal(f)
        tests[f] = funcs
    if len(tests.keys()) == 0:
        return 2, 0, sum(len(list(v)) for v in tests.values())
    # save to disk
    n_test_func = 0
    n_focal_func = 0
    with open(focal_path, "w") as outfile:
        for k, ds in tests.items():
            for d in ds:
                test_id = f"{k.removeprefix(repo_root)}::{d['test_id']}"
                d["test_id"] = test_id[1:] if test_id[0] == "/" else test_id
                if d["focal_loc"] is None:
                    continue
                outfile.write(json.dumps(d) + "\n")
                n_test_func += int(d["test_loc"] is not None)
                n_focal_func += int(d["focal_loc"] is not None)
    return 0, n_test_func, n_focal_func


def main(
    repo_id: str = "spring-cloud/spring-cloud-netflix",
    repo_root: str = "data/repos/",
    test_root: str = "data/tests/",
    focal_root: str = "data/focal/",
    timeout: int = 120,
    nprocs: int = 0,
    limits: int = -1,
):
    try:
        repo_id_list = [l.strip() for l in open(repo_id, "r").readlines()]
    except FileNotFoundError:
        repo_id_list = [repo_id]
    if limits > 0:
        repo_id_list = repo_id_list[:limits]
    print(f"Loaded {len(repo_id_list)} repos to be processed")

    # collect focal function from each repo
    status_ntest_nfocal = mp_map_repos(
        collect_from_repo,
        repo_id_list=repo_id_list,
        nprocs=nprocs,
        timeout=timeout,
        repo_root=repo_root,
        test_root=test_root,
        focal_root=focal_root,
    )

    filtered_results = [i for i in status_ntest_nfocal if i is not None]
    if len(filtered_results) < len(status_ntest_nfocal):
        print(f"{len(status_ntest_nfocal) - len(filtered_results)} repos timeout")
    status, ntest, nfocal = zip(*filtered_results)
    status_counter: Counter[int] = Counter(status)
    print(
        f"Processed {sum(status_counter.values())} repos with",
        f"{status_counter[3]} skipped, {status_counter[1]} not found,",
        f"and {status_counter[2]} failed to locate any focal functions",
    )
    print(f"Collected {sum(nfocal)} focal functions for {sum(ntest)} tests")
    print("Done!")


if __name__ == "__main__":
    fire.Fire(main)
