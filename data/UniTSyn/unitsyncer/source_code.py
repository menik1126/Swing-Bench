"""fetching source code from repo dir"""
import ast
from typing import Optional, TypeAlias
from pylspclient.lsp_structs import LANGUAGE_IDENTIFIER, Location as PyLSPLoc
from sansio_lsp_client import Location as SansioLoc
from unitsyncer.util import replace_tabs, uri2path, get_cpp_func_name
from returns.maybe import Maybe, Nothing, Some
from frontend.parser.ast_util import ASTUtil
from frontend.parser import (
    GO_LANGUAGE,
    JAVA_LANGUAGE,
    JAVASCRIPT_LANGUAGE,
    RUST_LANGUAGE,
    CPP_LANGUAGE,
)
from tree_sitter import Node
from frontend.parser.ast_util import remove_leading_spaces

Location: TypeAlias = PyLSPLoc | SansioLoc


def get_function_code(
    func_location: Location, lang: str
) -> Maybe[tuple[str, str | None, str | None]]:
    """Extract the source code of a function from a Location LSP response

    Args:
        func_location (Location): location of function responded by LS
        lang (str): language of the file as in LANGUAGE_IDENTIFIER

    Returns:
        Maybe[tuple[str, str | None, str | None]]: source code of function, its docstring, code_id
    """
    lineno = func_location.range.start.line
    col_offset = func_location.range.start.character  # pylint: disable=unused-variable

    def _get_function_code(file_path) -> Maybe[tuple[str, str | None, str | None]]:
        try:
            with open(file_path, "r", errors="replace") as file:
                code = file.read()
        except FileNotFoundError:
            return Nothing

        match lang:
            case LANGUAGE_IDENTIFIER.PYTHON:
                node = ast.parse(code, filename=file_path)
                return py_get_def(node, lineno).map(
                    lambda node: (ast.unparse(node), ast.get_docstring(node), None)
                )
            case LANGUAGE_IDENTIFIER.JAVA:
                ast_util = ASTUtil(replace_tabs(code))
                tree = ast_util.tree(JAVA_LANGUAGE)
                return java_get_def(tree.root_node, lineno, ast_util).map(
                    lambda node: (
                        ast_util.get_source_from_node(node),
                        None,
                        f"{file_path}::{ast_util.get_method_name(node).unwrap()}",
                    )
                )
            case LANGUAGE_IDENTIFIER.JAVASCRIPT:
                ast_util = ASTUtil(replace_tabs(code))
                tree = ast_util.tree(JAVASCRIPT_LANGUAGE)

                return js_get_def(tree.root_node, lineno, ast_util).map(
                    lambda node: (
                        ast_util.get_source_from_node(node),
                        None,
                        # js focal may not be a function, so directly unwrap may fail
                        f"{file_path}::{ast_util.get_name(node).value_or(None)}",
                    )
                )
            case LANGUAGE_IDENTIFIER.RUST:
                ast_util = ASTUtil(replace_tabs(code))
                tree = ast_util.tree(RUST_LANGUAGE)

                return rust_get_def(tree.root_node, lineno, ast_util).map(
                    lambda node: (
                        ast_util.get_source_from_node(node),
                        None,
                        f"{file_path}::{ast_util.get_name(node).value_or(None)}",
                    )
                )
            case LANGUAGE_IDENTIFIER.GO:
                ast_util = ASTUtil(replace_tabs(code))
                tree = ast_util.tree(GO_LANGUAGE)

                return go_get_def(tree.root_node, lineno, ast_util).map(
                    lambda node: (
                        ast_util.get_source_from_node(node),
                        None,
                        f"{file_path}::{ast_util.get_name(node).value_or(None)}",
                    )
                )
            case LANGUAGE_IDENTIFIER.C | LANGUAGE_IDENTIFIER.CPP:
                ast_util = ASTUtil(replace_tabs(code))
                tree = ast_util.tree(CPP_LANGUAGE)

                return cpp_get_def(tree.root_node, lineno, ast_util).map(
                    lambda node: (
                        ast_util.get_source_from_node(node),
                        None,
                        f"{file_path}::{get_cpp_func_name(ast_util, node).value_or(None)}",
                    )
                )

            case _:
                return Nothing

    return uri2path(func_location.uri).bind(_get_function_code)


def py_get_def(node: ast.AST, lineno: int) -> Maybe[ast.FunctionDef]:
    for child in ast.iter_child_nodes(node):
        if (
            isinstance(child, ast.FunctionDef)
            # AST is 1-indexed, LSP is 0-indexed
            and child.lineno == lineno + 1
            # AST count from def, LSP count from function name
            # and child.col_offset == col_offset - 4
        ):
            return Some(child)
        result = py_get_def(child, lineno)
        if result != Nothing:
            return result

    return Nothing


def java_get_def(node: Node, lineno: int, ast_util: ASTUtil) -> Maybe[Node]:
    def in_modifier_range(method_node: Node, lineno: int) -> bool:
        n_modifier = ast_util.get_method_modifiers(method_node).map(len).value_or(0)
        defn_lineno: int = method_node.start_point[0]
        return defn_lineno + n_modifier >= lineno

    for defn in ast_util.get_all_nodes_of_type(node, "method_declaration"):
        # tree-sitter AST is 0-indexed
        defn_lineno = defn.start_point[0]
        if defn_lineno == lineno or in_modifier_range(defn, lineno):
            return Some(defn)
    return Nothing


def js_get_def(node: Node, lineno: int, ast_util: ASTUtil) -> Maybe[Node]:
    for defn in ast_util.get_all_nodes_of_type(node, None):
        # tree-sitter AST is 0-indexed
        defn_lineno = defn.start_point[0]
        if defn_lineno == lineno:
            return Some(defn)
    return Nothing


def rust_get_def(node: Node, lineno: int, ast_util: ASTUtil) -> Maybe[Node]:
    for defn in ast_util.get_all_nodes_of_type(node, "function_item"):
        # tree-sitter AST is 0-indexed
        defn_lineno = defn.start_point[0]
        if defn_lineno == lineno:
            return Some(defn)
    return Nothing


def go_get_def(node: Node, lineno: int, ast_util: ASTUtil) -> Maybe[Node]:
    def find_in(node_type: str):
        for defn in ast_util.get_all_nodes_of_type(node, node_type):
            # tree-sitter AST is 0-indexed
            defn_lineno = defn.start_point[0]
            if defn_lineno == lineno:
                return defn
        return None

    # NOTE: in python
    # None or some_value === some_value
    # None or None === None
    return Maybe.from_optional(
        find_in("method_declaration") or find_in("function_declaration")
    )


def cpp_get_def(node: Node, lineno: int, ast_util: ASTUtil) -> Maybe[Node]:
    for defn in ast_util.get_all_nodes_of_type(node, "function_definition"):
        # tree-sitter AST is 0-indexed
        defn_lineno = defn.start_point[0]
        if defn_lineno == lineno:
            return Some(defn)
    return Nothing
