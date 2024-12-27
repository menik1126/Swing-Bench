"""
Collects all the test functions from projects following
"Conventions for Python test discovery" in
https://docs.pytest.org/en/7.4.x/explanation/goodpractices.html#test-discovery
"""

import os
import re
import sys
import ast
import fire
import traceback
from tqdm import tqdm
from pathlib import Path
from collections import Counter
from typing import List, Optional

from frontend.util import run_with_timeout, wrap_repo, mp_map_repos, TimeoutException
from navigate import ModuleNavigator, dump_ast_func



def collect_test_files(root: str):
    """collect all files in the root folder recursively and filter to match the given patterns"""
    patterns = [
        ".*_test\.py",  # pylint: disable=anomalous-backslash-in-string
        "test_.*\.py",  # pylint: disable=anomalous-backslash-in-string
    ]
    test_files = []
    for parent, _, files in os.walk(root):
        for file in files:
            if any([re.match(ptn, file) for ptn in patterns]):
                test_files.append(os.path.join(parent, file))
    return test_files


def collect_test_funcs(module_path: str):
    """collect testing functions from the target file"""
    nav = ModuleNavigator(module_path)
    funcs = nav.find_all(ast.FunctionDef)
    # funcs = nav.find_all(lambda x:isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)))

    def is_test_cls(node: ast.AST):
        """is a test class if
        1.1 class name starts with Test
        1.2 inherit from unittest.TestCase
        2. a static class without a init function
        """
        if not isinstance(node, ast.ClassDef):
            return False
        # if not node.name.startswith('Test'): return False
        test_prefix = node.name.startswith("Test")
        inherit_unittest_attr = any(
            [
                isinstance(base, ast.Attribute) and base.attr == "TestCase"
                for base in node.bases
            ]
        )
        inherit_unittest_name = any(
            [
                isinstance(base, ast.Name) and base.id == "TestCase"
                for base in node.bases
            ]
        )
        if not any([test_prefix, inherit_unittest_name, inherit_unittest_attr]):
            return False
        cls_funcs = nav.find_all(ast.FunctionDef, root=node)
        return not any(func.name == "__init__" for func in cls_funcs)

    def has_assert(func: ast.AST):
        # builtin assertion
        if len(nav.find_all(ast.Assert, root=func)) > 0:
            return True
        # Testcase in unittest, eg. self.assertEqual
        for call in nav.find_all(ast.Call, root=func):
            if isinstance(call.func, ast.Attribute) and call.func.attr.startswith(
                "assert"
            ):
                return True
        return False

    def is_test_outside_cls(func: ast.AST):
        """decide if the function is a testing function outside a class
        return true if its name starts with "test"
        """
        return func.name.startswith("test")

    def is_test_inside_cls(func: ast.AST, path: List[ast.AST]):
        """decide if the function is a testing function inside a class
        return true if its class is prefixed by "Test" and either
        + it is prefixed by "test"
        + it is decorated with @staticmethod and @classmethods
        """
        # keep only the node in path whose name is prefixed by "Test"
        cls_path = [n for n in path if is_test_cls(n)]
        if len(cls_path) == 0:
            return False
        if func.name.startswith("test"):
            return True
        decorators = getattr(func, "decorator_list", [])
        return any(
            isinstance(d, ast.Name) and d.id in ("staticmethod", "classmethods")
            for d in decorators
        )

    test_funcs = []
    for func in funcs:
        path = nav.get_path_to(func)
        is_cls = [isinstance(n, ast.ClassDef) for n in path]
        is_test = False
        is_test |= any(is_cls) and is_test_inside_cls(func, path)
        is_test |= not any(is_cls) and is_test_outside_cls(func)
        is_test &= has_assert(func)
        if not is_test:
            continue
        func_id = dump_ast_func(func, module_path, nav, path)
        test_funcs.append(func_id)

    return test_funcs


@run_with_timeout
def collect_from_repo(repo_id: str, repo_root: str, test_root: str):
    """collect all test functions in the given project
    return (status, nfile, ntest)
    status can be 0: success, 1: repo not found, 2: test not found, 3: skip when output file existed
    """
   # assert 1==0
    repo_path = os.path.join(repo_root, wrap_repo(repo_id))
    if not os.path.exists(repo_path) or not os.path.isdir(repo_path):
        return 1, 0, 0
    test_path = os.path.join(test_root, wrap_repo(repo_id) + ".txt")
    print("test_path:{}".format(test_path))
    # skip if exist
    if os.path.exists(test_path):
        return 3, 0, 0
    # collect potential testing modules
    all_files = collect_test_files(repo_path)
    test_files, test_funcs = [], []
    for f in all_files:
        try:
            funcs = collect_test_funcs(f)
        except TimeoutException:
            raise
        except:  # pylint: disable=bare-except
            funcs = None
        if funcs is None or len(funcs) == 0:
            continue
        test_files.append(f)
        test_funcs.extend(funcs)
    if len(test_funcs) == 0:
        return 2, len(test_files), len(test_funcs)
    # save to disk
    with open(test_path, "w") as outfile:
        for func_id in test_funcs:
            parts = func_id.split("::")
            parts[0] = str(
                Path(os.path.abspath(parts[0])).relative_to(os.path.abspath(repo_root))
            )
            func_id = "::".join(parts)
            outfile.write(f"{func_id}\n")
    return 0, len(test_files), len(test_funcs)


def main(
    repo_id: str = "ageitgey/face_recognition",
    repo_root: str = "data/repos/",
    test_root: str = "data/tests",
    timeout: int = 120,
    nprocs: int = 0,
    limits: int = -1,
):
    # if repo_id_list is a file then load lines
    # otherwise it is the id of a specific repo
    try:
        repo_id_list = [l.strip() for l in open(repo_id, "r").readlines()]
    except FileNotFoundError:
        repo_id_list = [repo_id]
    if limits > 0:
        repo_id_list = repo_id_list[:limits]
    print(f"Loaded {len(repo_id_list)} repos to be processed")

    status_nfile_ntest = mp_map_repos(
        collect_from_repo,
        repo_id_list=repo_id_list,
        nprocs=nprocs,
        repo_root=repo_root,
        test_root=test_root,
        timeout=timeout,
    )
    print("status_nfile_ntest:{}".format(status_nfile_ntest))
    
    filtered_results = [i for i in status_nfile_ntest if i is not None]
    if len(filtered_results) < len(status_nfile_ntest):
        print(f"{len(status_nfile_ntest) - len(filtered_results)} repos timeout")
    status, nfile, ntest = zip(*filtered_results)
    status_counter: Counter[int] = Counter(status)
    print("status:{}".format(status))
    print(
        f"Processed {sum(status_counter.values())} repos with {status_counter[3]} skipped, {status_counter[1]} not found, and {status_counter[2]} failed to mine any testing functions"
    )
    print(f"Collected {sum(ntest)} tests from {sum(nfile)} files in total")
   # assert 1==0

if __name__ == "__main__":
    fire.Fire(main)
