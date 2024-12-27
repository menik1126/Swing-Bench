"""extract test def header for LLM to generate the body"""
import fire
import ast
from frontend.parser.ast_util import ASTUtil
from frontend.parser import (
    GO_LANGUAGE,
    JAVASCRIPT_LANGUAGE,
    CPP_LANGUAGE,
    JAVA_LANGUAGE,
)
from itertools import takewhile
from tqdm import tqdm
import json
import os
import logging


def py_get_def(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code.split(":\n")[0]

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            args = [arg.arg for arg in node.args.args]
            return f"def {func_name}({', '.join(args)}):\n"

    return None


def go_get_def(code: str) -> str | None:
    ast_util = ASTUtil(code)
    tree = ast_util.tree(GO_LANGUAGE)
    root = tree.root_node
    func_delcs = ast_util.get_all_nodes_of_type(root, "function_declaration")
    if not func_delcs:
        return None

    test_delc = func_delcs[0]
    test_name_node = ast_util.get_all_nodes_of_type(test_delc, "identifier")[0]
    test_name = ast_util.get_source_from_node(test_name_node)
    return f"func {test_name}(t *testing.T) {{\n"


def js_get_def(code: str) -> str | None:
    ast_util = ASTUtil(code)
    tree = ast_util.tree(JAVASCRIPT_LANGUAGE)
    root = tree.root_node
    func_delcs = ast_util.get_all_nodes_of_type(root, "lexical_declaration")
    if not func_delcs:
        return None

    test_delc = func_delcs[0]
    test_name_node = ast_util.get_all_nodes_of_type(test_delc, "identifier")[0]
    test_name = ast_util.get_source_from_node(test_name_node)
    return f"const {test_name} = () => {{\n"


def cpp_get_def(code: str) -> str | None:
    ast_util = ASTUtil(code)
    tree = ast_util.tree(CPP_LANGUAGE)
    root = tree.root_node
    func_delcs = ast_util.get_all_nodes_of_type(root, "function_definition")
    if not func_delcs:
        return None

    test_delc = func_delcs[0]
    test_name_node = ast_util.get_all_nodes_of_type(test_delc, "identifier")[0]
    test_name = ast_util.get_source_from_node(test_name_node)
    test_params = ast_util.get_all_nodes_of_type(test_delc, "parameter_declaration")[:2]
    return f"{test_name}({', '.join(map(ast_util.get_source_from_node, test_params))}) {{\n"


def java_get_def(code: str) -> str | None:
    return "".join(takewhile(lambda c: c != "{", code)) + "{\n"


def get_def_header(code: str, lang: str) -> str | None:
    header: str | None = None
    if lang == "python":
        header = py_get_def(code)
    elif lang == "cpp":
        header = cpp_get_def(code)
    elif lang == "java":
        header = java_get_def(code)
    elif lang == "go":
        header = go_get_def(code)
    elif lang in ("js", "javascript"):
        header = js_get_def(code)

    return header


def main(in_path: str, out_path: str):
    with tqdm(total=os.path.getsize(in_path)) as p_bar:
        with open(in_path, "r") as in_f, open(out_path, "a") as out_f:
            for j_line in in_f:
                j = json.loads(j_line)
                test = j["test"]
                lang = j["lang"]

                try:
                    header = get_def_header(test, lang)
                    j["test_header"] = header
                    out_f.write(json.dumps(j) + "\n")
                except Exception as e:
                    logging.error(e)
                    logging.error(j)

                p_bar.update(len(j_line))


if __name__ == "__main__":
    fire.Fire(main)
