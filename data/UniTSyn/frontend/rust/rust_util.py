"""Util functions for rust frontend"""

from typing import Iterable, Optional
from tree_sitter import Node
from frontend.parser import RUST_LANGUAGE
from frontend.parser.ast_util import ASTUtil, ASTLoc, flatten_postorder
from returns.maybe import Maybe, Nothing, Some, maybe
from unitsyncer.util import replace_tabs


def get_test_functions(ast_util: ASTUtil, root_node: Node) -> list[Node]:
    if root_node.type != "source_file":
        return []

    def has_test_annotation(idx: int):
        if root_node.children[idx].type != "attribute_item":
            return False

        # check if the attributes have #[test]
        for child in root_node.children[idx].children:
            for node in ast_util.get_all_nodes_of_type(child, "identifier"):
                if ast_util.get_source_from_node(node) == "test":
                    return True
        return False

    function_items = []
    for idx, child in enumerate(root_node.children):
        if child.type == "function_item" and has_test_annotation(idx - 1):
            function_items.append(child)
    return function_items


def get_first_assert(ast_util: ASTUtil, test_func: Node) -> Maybe[Node]:
    macro_invocations = ast_util.get_all_nodes_of_type(test_func, "macro_invocation")

    for macro_invocation in macro_invocations:
        if (
            ast_util.get_name(macro_invocation)
            .map(lambda name: "assert" in name)
            .value_or(False)
        ):
            return Some(macro_invocation)
    return Nothing


@maybe
def get_first_valid_call(calls: list[Node], ast_util: ASTUtil) -> Optional[Node]:
    """find first valid call not for focal

    Args:
        calls (list[Node]): a list of candidate call nodes
        ast_util (ASTUtil): ast_util build with the source code

    Returns:
        Optional[Node]: first node that should not be skipped, check `do_skip` for detail
    """

    def do_skip(call_node: Node) -> bool:
        skip_list = ["unwrap", "len", "as_slice", "into_iter"]
        call_node_name = ast_util.get_source_from_node(call_node)
        return any(skip_str in call_node_name for skip_str in skip_list)

    return next(
        (call for call in calls if not do_skip(call)),
        None,
    )


def get_focal_call(ast_util: ASTUtil, test_func: Node) -> Maybe[tuple[str, ASTLoc]]:
    """Get the focal call from the given test function

    Heuristic:
        1. find the first assert macro
        2. expand the macro and find the first call expression in the macro
        3. if no call expression in the macro, back track to find the last call before assert
    """

    def expand_assert_and_get_call(assert_macro: Node) -> Maybe[tuple[str, ASTLoc]]:
        token_tree = ast_util.get_all_nodes_of_type(assert_macro, "token_tree")[0]
        code = ast_util.get_source_from_node(token_tree)
        assert_ast_util = ASTUtil(code)
        assert_ast = assert_ast_util.tree(RUST_LANGUAGE)
        assert_root = assert_ast.root_node

        match assert_ast_util.get_all_nodes_of_type(assert_root, "call_expression"):
            case []:
                # todo: no call expression in assert macro,
                # back track to find the last call before assert
                return Nothing
            case calls:

                def to_result(node: Node) -> tuple[str, ASTLoc]:
                    name = assert_ast_util.get_source_from_node(node)
                    lineno = node.start_point[0] + assert_macro.start_point[0]
                    col = node.start_point[1]
                    return name, (lineno, col)

                return get_first_valid_call(calls, assert_ast_util).map(to_result)

        return Nothing

    focal_in_assert = get_first_assert(ast_util, test_func).bind(
        expand_assert_and_get_call
    )
    if focal_in_assert != Nothing:
        return focal_in_assert

    match flatten_postorder(test_func, "call_expression"):
        case []:
            return Nothing
        case calls:

            def to_name_loc(n: Node):
                return (ast_util.get_source_from_node(n), n.start_point)

            return get_first_valid_call(calls[::-1], ast_util).map(to_name_loc)
    return Nothing


def main():
    code = """
#[test]
fn test_1() {
    let data = [];
    let engine = utils::random_engine(data);
    let encoded = engine.encode(data);
    let decoded = engine.decode(&encoded).unwrap();
    assert_eq!(data, decoded.as_slice());
}
"""
    ast_util = ASTUtil(replace_tabs(code))
    tree = ast_util.tree(RUST_LANGUAGE)
    root_node = tree.root_node

    test_funcs = get_test_functions(ast_util, root_node)
    func = test_funcs[0]
    print(ast_util.get_source_from_node(func))

    focal_call = get_focal_call(ast_util, func)
    print(focal_call)


if __name__ == "__main__":
    main()
