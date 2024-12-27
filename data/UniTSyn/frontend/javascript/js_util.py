"""util functions for JS frontend"""

from typing import Iterable
from tree_sitter import Node
from frontend.parser import JAVASCRIPT_LANGUAGE
from frontend.parser.ast_util import ASTUtil, ASTLoc, flatten_postorder
from returns.maybe import Maybe, Nothing, Some
from unitsyncer.util import replace_tabs


def is_test_fn(n: Node, ast_util: ASTUtil):

    def is_call_to_test(node: Node):
        return ast_util.get_name(node).map(lambda n: n == "describe").value_or(False)

    return is_call_to_test(n)


def js_get_test_args(
    ast_util: ASTUtil, test_call_expr: Node
) -> Maybe[tuple[str, Node]]:
    """extract the test name and the test function from a call to `describe`

    Returns:
        Maybe[tuple[str, Node]]: test name/description, and the test function
    """
    if test_call_expr.type != "call_expression":
        return Nothing

    # get the first argument of the call expression
    args_node = None
    for child in test_call_expr.children:
        if child.type == "arguments":
            args_node = child
            break
    if args_node is None:
        return Nothing

    # a call to `describe` has the following structure:
    # describe(test_name, test_func)
    # args_node.children should be a list of 5 nodes:
    # "(", "test_name", ",", "test_func", ")
    args = args_node.children
    if len(args) != 5 or args[1].type != "string" or args[3].type != "function":
        return Nothing

    return Some((ast_util.get_source_from_node(args[1]), args[3]))


def get_focal_call(ast_util: ASTUtil, test_func: Node) -> Maybe[tuple[str, ASTLoc]]:
    calls = flatten_postorder(test_func, "call_expression")

    func_calls = [ast_util.get_source_from_node(call) for call in calls]
    calls_before_expect = []
    has_expect = False
    for call in func_calls:
        if "expect" in call or "test" in call:
            has_expect = True
            break
        calls_before_expect.append(call)

    if not has_expect:
        return Nothing
    if len(calls_before_expect) == 0:
        return Nothing

    def get_loc(call: str) -> tuple[str, ASTLoc]:
        idx = func_calls.index(call)
        node = calls[idx]
        lineno, col = node.start_point
        match call.split("."):
            case [*_, method_name]:
                offset = len(call) - len(method_name)
                method_name = method_name.split("(")[0]
                return method_name, (lineno, col + offset)
            case _:
                return call, (lineno, col)

    return Some(get_loc(calls_before_expect[-1]))


def main():
    code = """
  describe('loading a non-existent value (from memory and disk)', function () {
    fixtureUtils.mkdir({folderName: 'non-existent'});
    storeUtils.init();
    storeUtils.get('nothing');

    it('calls back with `null`', function () {
      expect(this.err).to.equal(null);
      expect(this.val).to.equal(null);
    });
  });
"""
    ast_util = ASTUtil(replace_tabs(code))
    tree = ast_util.tree(JAVASCRIPT_LANGUAGE)
    root_node = tree.root_node

    # print(root_node.sexp())

    # js test function is a higher order function that takes a function as input
    call_exprs = ast_util.get_all_nodes_of_type(root_node, "call_expression")

    def is_call_to_test(node: Node):
        return ast_util.get_name(node).map(lambda n: n == "describe").value_or(False)

    focal = list(filter(is_call_to_test, call_exprs))[0]
    test_name, test_func = js_get_test_args(ast_util, focal).unwrap()
    print(test_name)
    print(ast_util.get_source_from_node(test_func))

    print(get_focal_call(ast_util, test_func))


if __name__ == "__main__":
    main()
