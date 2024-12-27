"""Helper Class and Functions for tree-sitter AST"""

from tree_sitter import Language, Parser, Tree
from tree_sitter import Node
from returns.maybe import Maybe, Nothing, Some
from unitsyncer.common import UNITSYNCER_HOME
from typing import Optional, Tuple

ASTLoc = tuple[int, int]


class ASTUtil:
    """Helper Class to build/read/manipulate AST with tree-sitter"""

    def __init__(self, source_code: str) -> None:
        self.src = source_code

    def tree(self, lang: Language) -> Tree:
        parser = Parser()
        parser.set_language(lang)
        return parser.parse(bytes(self.src, "utf8"))

    def get_source_from_node(self, node: Node) -> str:
        match node.type:
            case "method_declaration":
                start = node.start_point[0]
                end = node.end_point[0]
                src_lines = self.src.splitlines()[start : end + 1]
                src_lines = remove_leading_spaces(src_lines)
                return "\n".join(src_lines)
            case _:
                start = node.start_byte
                end = node.end_byte
                return self.src[start:end]

    def get_method_name(self, method_node: Node) -> Maybe[str]:
        if method_node.type != "method_declaration":
            return Nothing

        # for a method decl, its name is the first identifier
        for child in method_node.children:
            if child.type == "identifier":
                return Some(self.get_source_from_node(child))

        return Nothing

    def get_name(self, node: Node) -> Maybe[str]:
        for child in node.children:
            if child.type == "identifier":
                return Some(self.get_source_from_node(child))

        return Nothing

    def get_method_modifiers(self, method_node: Node) -> Maybe[list[str]]:
        if method_node.type != "method_declaration":
            return Nothing

        modifiers = []
        for child in method_node.children:
            if child.type == "modifiers":
                for modifier_child in child.children:
                    modifiers.append(self.get_source_from_node(modifier_child))
        return Some(modifiers)

    def get_all_nodes_of_type(
        self, root: Node, node_type: str | None, max_level=50
    ) -> list[Node]:
        """walk on AST and collect all nodes of the given type

        Args:
            root (Node): root node of tree
            node_type (str | None): type of node to collect, if None collect all Node
            max_level (int, optional): maximum recursion level. Defaults to 50.

        Returns:
            list[Node]: collected nodes
        """
        nodes: list[Node] = []
        if max_level == 0:
            return nodes

        for child in root.children:
            if node_type is None or child.type == node_type:
                nodes.append(child)
            nodes += self.get_all_nodes_of_type(
                child, node_type, max_level=max_level - 1
            )
        return nodes


def remove_leading_spaces(lines: list[str]) -> list[str]:
    """remove leading spaces from each line"""
    space_idx = len(lines[0]) - len(lines[0].lstrip())
    return [s[space_idx:] for s in lines]


def flatten_postorder(
    root: Node, node_type: Optional[str] = None, max_level=50
) -> list[Node]:
    """flatten a tree in postorder

    Args:
        root (Node): root of tree
        node_type (str | None): type of node to collect, if None collect all Node
        max_level (int, optional): maximum recursion level. Defaults to 50.

    Returns:
        list[Node]: flattened tree
    """
    nodes: list[Node] = []
    if max_level == 0:
        return nodes

    for child in root.children:
        nodes += flatten_postorder(child, node_type, max_level - 1)

    if node_type is None or root.type == node_type:
        nodes.append(root)
    return nodes
