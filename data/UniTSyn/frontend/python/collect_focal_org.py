"""script to collect focal call and its file path using Jedi language server"""
import os
import sys
import ast
import fire
import json
import jedi
import pathlib
import traceback
import astunparse
from tqdm import tqdm
from typing import Optional
from collections import Counter

from frontend.util import wrap_repo, mp_map_repos, time_limit, TimeoutException
from navigate import ModuleNavigator, load_ast_func, dump_ast_func, is_assert



class NotFoundException(Exception):
    """Exception wrapper for not found focal call"""

    pass  # pylint: disable=unnecessary-pass


def parse_func_name(node: ast.AST):
    """recursively get the full name of a called function"""
    # TODO: use unparse from build-in ast module
    return astunparse.unparse(node).strip()
    if isinstance(node, ast.Name):  # pylint: disable=unreachable
        return node.id
    return f"{parse_func_name(node.value)}.{node.attr}"


def is_subpath(anchor: pathlib.Path, target: pathlib.Path):
    try:
        target.relative_to(anchor)
        return True
    except ValueError:
        return False


def parse_focal_call(test_func: ast.AST, module: ModuleNavigator, repo: jedi.Project):
    """guess target focal function from testing function according to
    1. trace back all the function calls from the first assertion and
       return the first call that invoke a function definition in the repo
    2. if found focal class by removing "Test" in name,
    """
    script = jedi.Script(path=module.path, project=repo)
    last_call = None  # pylint: disable=unused-variable
    calls_before_assert, found_assert = [], False
    for node in module.postorder(root=test_func):
        found_assert |= is_assert(node)
        if isinstance(node, ast.Call):
            if not found_assert:
                calls_before_assert.append(node)
            last_call = node
    while calls_before_assert:
        node = calls_before_assert.pop()
        # col_offset should be shifted to get the definition of the target function
        # say we have the function being called is api.load_image_file
        # and the lineno and col_offset of it is x and y
        # if we call script.got(x, y),
        #   jedi will try to find the definition of api rather than load_image_file
        # so we need to split api.load_image_file into (api, load_image_file)
        # then drop the last item to get (api,)
        # after that, shifted_col_offset is computed as col_offset + len(api)
        # then we can get the definition of the function of interests
        node_name = parse_func_name(node.func)
        shift_col_offset = node.col_offset + (
            len(node_name) - len(node_name.split(".")[-1])
        )
        defs = script.goto(
            node.lineno,
            shift_col_offset,
            follow_imports=True,
            follow_builtin_imports=False,
        )
        if (
            len(defs) > 0  # and defs[0].type == 'function'
            and not defs[0].in_builtin_module()
            and is_subpath(repo.path, defs[0].module_path)
        ):
            return node, defs[0]
    return None


def jedi2ast(jedi_node: jedi.api.classes.Name):
    """convert a jedi node into an ast"""
    module_path = jedi_node.module_path
    module = ModuleNavigator(module_path)
    module_name = module_path.stem
    node_ids = jedi_node.full_name.split(".")
    if module_name not in node_ids:
        return None
    node_ids = node_ids[node_ids.index(module_name) + 1 :]
    node = None
    while node_ids:
        try:
            node = module.find_by_name(node_ids.pop(0), root=node)
        except TimeoutException:
            raise
        except:  # pylint: disable=bare-except
            return None
    if not node:
        return None
    return node, module


def collect_focal_func(
    repo_id: str = "ageitgey/face_recognition",
    test_id: str = "ageitgey?face_recognition/ageitgey-face_recognition-59cff93/tests/test_face_recognition.py::Test_face_recognition::test_load_image_file",
    iroot: str = "data/repos",
    repo: Optional[jedi.Project] = None,
):
    # construct jedi project if it is not given
    if repo is None:
        repo = jedi.Project(os.path.join(iroot, wrap_repo(repo_id)))
    # load testing function from its id
    test_func, test_mod = load_ast_func(os.path.join(iroot, test_id), return_nav=True)
    # find call to to the potential focal function
    result = parse_focal_call(test_func, test_mod, repo)
    if result is not None:
        focal_call, focal_func_jedi = result  # pylint: disable=unused-variable
    else:
        raise NotFoundException(f"Failed to find potential focal call in {test_id}")
    # convert focal_func from jedi Name to ast object
    result = jedi2ast(focal_func_jedi)
    if result is not None:
        focal_func, focal_mod = result
    else:
        raise NotFoundException(
            f"Failed to locate focal function {focal_func_jedi.full_name} for {test_id}"
        )
    # get focal path to dump focal func
    focal_path = str(focal_func_jedi.module_path.relative_to(os.path.abspath(iroot)))
    focal_id = dump_ast_func(focal_func, focal_path, focal_mod)
    return focal_id


def collect_from_repo(
    repo_id: str = "ageitgey/face_recognition",
    repo_root: str = "data/repos",
    test_root: str = "data/tests",
    focal_root: str = "data/focal",
):
    """collect all focal func from a repo
    this is implemented to support multiprocessing
    return (status, #tests, #focals)
    status can be
        0: success,
        1: repo or test not found,
        2: repo exist but no focal found,
        3: skip if output file existed
    """
#    assert 1==0
    repo_path = os.path.join(repo_root, wrap_repo(repo_id))
    if not os.path.exists(repo_path) or not os.path.isdir(repo_path):
        return 1, 0, 0
    test_path = os.path.join(test_root, wrap_repo(repo_id) + ".txt")
    if not os.path.exists(test_path):
        return 1, 0, 0
    focal_path = os.path.join(focal_root, wrap_repo(repo_id) + ".jsonl")
    if os.path.exists(focal_path):
        return 3, 0, 0
    # build jedi project
    repo = jedi.Project(path=repo_path)
    # load test func id to be parsed
    test_ids, focal_ids = [l.strip() for l in open(test_path, "r").readlines()], []
    failed = 0
    for test_id in test_ids:
        try:
            focal_ids.append(collect_focal_func(repo_id, test_id, repo_root, repo))
        except TimeoutException:
            raise
        except Exception as e:  # pylint: disable=broad-exception-caught
            focal_ids.append(str(e))
            failed += 1
    if len(test_ids) == failed:
        return 2, len(test_ids), len(test_ids) - failed
    # save to disk
    with open(focal_path, "w") as ofile:
        for test_id, focal_id in zip(test_ids, focal_ids):
            ofile.write(json.dumps({"test": test_id, "focal": focal_id}) + "\n")
    return 0, len(test_ids), len(test_ids) - failed


def collect_from_repo_with_timeout(*args, timeout: int = -1, **kwargs):
    if timeout <= 0:
        return collect_from_repo(*args, **kwargs)
    try:
        with time_limit(timeout):
            return collect_from_repo(*args, **kwargs)
    except TimeoutException:
        pass
    return None


def main(
    repo_id: str = "ageitgey/face_recognition",
    test_root: str = "data/tests",
    repo_root: str = "data/repos",
    focal_root: str = "data/focal",
    timeout: int = 300,
    nprocs: int = 0,
    limits: int = -1,
):  # pylint: disable=too-many-arguments
    assert 1==0
    try:
        repo_id_list = [l.strip() for l in open(repo_id, "r").readlines()]
    except FileNotFoundError:
        repo_id_list = [repo_id]
    if limits > 0:
        repo_id_list = repo_id_list[:limits]
    print(f"Loaded {len(repo_id_list)} repos to be processed")
    
    
    # collect focal function from each repo
    status_ntest_nfocal = mp_map_repos(
        collect_from_repo_with_timeout,
        repo_id_list=repo_id_list,
        nprocs=nprocs,
        timeout=timeout,
        repo_root=repo_root,
        test_root=test_root,
        focal_root=focal_root,
    )
    assert 1==0
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
