"""find focal call in Java test functions"""

from typing import Optional
import fire
import re
from tree_sitter import Node
from frontend.parser import CPP_LANGUAGE
from frontend.parser.ast_util import ASTUtil, ASTLoc, flatten_postorder
from returns.maybe import Maybe, Nothing, Some, maybe
from unitsyncer.util import get_cpp_func_name


def is_test_fn(n: Node, ast_util: ASTUtil):
    def is_gtest_testcase(node: Node):
        return (
            get_cpp_func_name(ast_util, node)
            .map(lambda name: name == "TEST")
            .value_or(False)
        )

    return is_gtest_testcase(n)


def get_focal_call(ast_util: ASTUtil, func: Node) -> Maybe[tuple[str, ASTLoc]]:
    """Find the focal call in the given function

    Args:
        ast_util (ASTUtil): ASTUtil for the file
        func (Node): a method_declaration node

    Returns:
        Maybe[tuple[str, ASTLoc]]: focal call and its location
    """

    calls = flatten_postorder(func, "call_expression")

    # reverse for postorder
    func_calls = [ast_util.get_source_from_node(call) for call in calls]
    calls_before_assert: list[str] = []
    has_assert = False
    for call in func_calls:
        if "EXPECT" in call or "ASSERT" in call:
            has_assert = True
            break
        calls_before_assert.append(call)

    if not has_assert or not calls_before_assert:
        return Nothing

    def get_loc(call: str) -> Maybe[tuple[str, ASTLoc]]:
        """add offset to nested function calls

        Args:
            call (str): code str of a method_invocation

        Returns:
            Maybe[tuple[str, ASTLoc]]: (method_name, its location)
        """
        idx = func_calls.index(call)
        node = calls[idx]
        lineno, col = node.start_point

        # regular expression to find method names
        pattern = r"(\w+)\s*\("
        matches = list(re.finditer(pattern, call))

        if matches:
            last_match = matches[-1]
            method_name = last_match.group(1)
            offset = last_match.start(1)
            loc = (lineno, col + offset)
            return Some((method_name, loc))

        return Nothing

    return get_loc(calls_before_assert[-1])


def main():
    code = """
TEST(OpenACCTest, DirectiveHelpers) {
  EXPECT_EQ(getOpenACCDirectiveKind(""), ACCD_unknown);
  EXPECT_EQ(getOpenACCDirectiveKind("dummy"), ACCD_unknown);
  EXPECT_EQ(getOpenACCDirectiveKind("atomic"), ACCD_atomic);
  EXPECT_EQ(getOpenACCDirectiveKind("cache"), ACCD_cache);
  EXPECT_EQ(getOpenACCDirectiveKind("data"), ACCD_data);
  EXPECT_EQ(getOpenACCDirectiveKind("declare"), ACCD_declare);
}
"""

    ast_util = ASTUtil(code)
    tree = ast_util.tree(CPP_LANGUAGE)
    root_node = tree.root_node

    func_delcs = ast_util.get_all_nodes_of_type(root_node, "function_definition")
    func = func_delcs[0]

    print(get_focal_call(ast_util, func))


if __name__ == "__main__":
    fire.Fire(main)
