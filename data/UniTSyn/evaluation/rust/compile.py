import json
from typing import Iterable
import fire
import os
from tree_sitter import Node
from frontend.parser import RUST_LANGUAGE
from frontend.parser.ast_util import ASTUtil
import json
import subprocess
from unitsyncer.common import UNITSYNCER_HOME
from returns.maybe import Maybe, Some, Nothing
from functools import reduce
from operator import add
from unitsyncer.util import concatMap


def flatten_use_delc(use_delc_code: str) -> list[str]:
    """flatten a nested use declaration line to multiple use declarations

    e.g.

    from:
        use rand::{Rng, SeedableRng};
    to:
        use rand::Rng;\n
        use rand::SeedableRng;


    Args:
        use_delc_code (str): code of a use delc

    Returns:
        list[str]: flattened use declarations
    """
    ast_util = ASTUtil(use_delc_code)
    tree = ast_util.tree(RUST_LANGUAGE)
    root = tree.root_node
    use_delc_nodes = ast_util.get_all_nodes_of_type(root, "use_declaration")
    if len(use_delc_nodes) != 1:
        return []

    delc_node = use_delc_nodes[0]
    scoped_use_list_nodes = ast_util.get_all_nodes_of_type(delc_node, "scoped_use_list")
    if len(scoped_use_list_nodes) == 0:
        # example: use base64::*;
        wildcard_nodes = ast_util.get_all_nodes_of_type(delc_node, "use_wildcard")
        if len(wildcard_nodes) >= 1:
            return [use_delc_code]
        return []

    def fold_nodes(nodes: list[Node]) -> str:
        # NOTE: ignore type since `str` is a Iterable, but not compatible with `Iterable[U]` type
        # `type String = List[Char]` is not valid in Python since there is no `Char`
        # the type checker would then infer it as `Iterable[str]`, which != `str`
        return concatMap(ast_util.get_source_from_node, nodes)  # type: ignore

    def get_use_src(node: Node) -> str | None:
        match node.type:
            case "identifier" | "use_wildcard" | "use_as_clause":
                return ast_util.get_source_from_node(node)
            case "scoped_identifier":
                return fold_nodes(node.children)
            case _:
                return None

    node = scoped_use_list_nodes[0]
    match node.children:
        case []:
            return []
        case [*base_nodes, use_list_node]:
            if use_list_node.type != "use_list":
                return []

            base = fold_nodes(base_nodes)
            use_list = map(get_use_src, use_list_node.children)
            return [f"use {base + u};" for u in use_list if u]
        case _:
            return []


def collect_rs_files(root: str):
    """Get all files end with .rs in the given root directory

    Args:
        root (str): path to repo root
    """
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(".rs"):
                yield os.path.join(dirpath, filename)


def construct_use_delcs(workspace_dir: str, type: str) -> set[str]:
    """construct a set of unique use_list for a project from all use declarations in
    a subdirectory to

        1. solve generated tests' dependency error
        2. avoid compile error caused by duplicated imports

    Args:
        workspace_dir (str): path to project's workdir
        type (str): tests or fuzz to collect use_delcs.

    Returns:
        set[str]: set of use declarations to write to generated test files
    """
    subdir = os.path.join(workspace_dir, type)

    def get_use_list_from_file(fpath: str) -> Iterable[str]:
        with open(fpath) as f:
            code = f.read()
        ast_util = ASTUtil(code)
        tree = ast_util.tree(RUST_LANGUAGE)
        use_list_nodes = ast_util.get_all_nodes_of_type(
            tree.root_node, "use_declaration"
        )
        return list(map(ast_util.get_source_from_node, use_list_nodes))

    use_lists = concatMap(get_use_list_from_file, collect_rs_files(subdir))

    # flatten and remove duplicate
    return set(concatMap(flatten_use_delc, use_lists))


def write_tests_to_workspace(workspace_dir: str, tests: list[str], test_type: str):
    """get compile rate of generated testcases

    Args:
        workspace_dir (str): path to the project/crate's workspace dir
        tests (list[str]): list of generated test functions
        test_type (str): tests (unittest) or fuzz
    """
    use_delc = "\n".join(construct_use_delcs(workspace_dir, test_type))
    for i, test in enumerate(tests):
        p = os.path.join(workspace_dir, "tests", f"generated_{test_type}_{i}.rs")
        with open(p, "w") as f:
            f.write(use_delc + "\n\n" + "#[test]\n" + test)


def main():
    workspace_dir = os.path.abspath(
        "data/repos/marshallpierce-rust-base64/marshallpierce-rust-base64-4ef33cc"
    )

    print(construct_use_delcs(workspace_dir, "tests"))


if __name__ == "__main__":
    fire.Fire(main)
