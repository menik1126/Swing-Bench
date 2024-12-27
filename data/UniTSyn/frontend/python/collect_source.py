import os
import sys
import ast
import fire
import json
import astor
import traceback
import astunparse
from tqdm import tqdm

from frontend.util import wrap_repo, timestamp
from navigate import load_ast_func


def ast2source(node: ast.AST):
    """convert ast node into its source using astor
    we are not using astunparse is because there's something wrong when it parsing docstring
    to_source is not used here to avoid calling pretty_source which will make the line shorter if too long
    """
    generator = astor.SourceGenerator(" " * 4)
    generator.visit(node)
    generator.result.append("\n")
    if set(generator.result[0]) == set("\n"):
        generator.result[0] = ""
    return "".join(generator.result)


def collect_source(func_id: str, repo_root: str):
    """collect the source code given its function id"""
    func, mod = None, None
    try:
        func, mod = load_ast_func(os.path.join(repo_root, func_id), return_nav=True)
    except:
        pass
    if func is None:
        return False, None

    try:
        source = ast2source(func)
    except:
        source = ""

    try:
        docstr = ast.get_docstring(func)
    except:
        docstr = None
    if docstr is None:
        docstr = ""
    return True, (source, docstr)


def main(
    repo_id_list: str = "ageitgey/face_recognition",
    repo_root: str = "data/repos",
    focal_root: str = "data/focal",
    source_path: str = "data/source/all.jsonl",
    timeout: int = 5,
    nprocs: int = 0,
    limits: int = -1,
):
    try:
        repo_id_list = [l.strip() for l in open(repo_id_list, "r").readlines()]
    except FileNotFoundError:
        repo_id_list = [repo_id_list]
    if limits > 0:
        repo_id_list = repo_id_list[:limits]
    print(f"Loaded {len(repo_id_list)} repos to be processed")
    if os.path.exists(source_path):
        os.remove(source_path)
    total, failed = 0, {"repo": 0, "func": 0}
    for repo_id in (pbar := tqdm(repo_id_list)):
        pbar.set_description(f"{timestamp()} Processing {repo_id}")
        # load test-focal pairs to be processed
        path = os.path.join(focal_root, wrap_repo(repo_id) + ".jsonl")
        if not os.path.exists(path):
            failed["repo"] += 1
            continue
        data = [json.loads(l.strip()) for l in open(path, "r").readlines()]
        total += len(data)
        for item in data:
            test_id, focal_id = item["test"], item["focal"]
            test_status, test = collect_source(test_id, repo_root)
            focal_status, focal = collect_source(focal_id, repo_root)
            if not test_status or not focal_status:
                failed["func"] += 1
                continue
            with open(source_path, "a") as ofile:
                dict2write = {
                    "test_id": test_id,
                    "test": test[0],
                    "code_id": focal_id,
                    "code": focal[0],
                    "docstring": focal[1],
                }
                ofile.write(json.dumps(dict2write) + "\n")
    print(f'Processed {len(repo_id_list) - failed["repo"]}/{len(repo_id_list)} repos')
    print(f'Collected {total - failed["func"]}/{total} code-test pairs')


if __name__ == "__main__":
    fire.Fire(main)
