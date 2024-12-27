"""find focal call in Java test functions"""

from typing import Optional
import fire
import re
from tree_sitter import Node
from frontend.parser import JAVA_LANGUAGE
from frontend.parser.ast_util import ASTUtil, ASTLoc, flatten_postorder
from returns.maybe import Maybe, Nothing, Some, maybe


def is_test_fn(node: Node, ast_util: ASTUtil):
    def has_test_modifier(node: Node):
        modifiers = ast_util.get_method_modifiers(node)
        return modifiers.map(lambda x: "@Test" in x).value_or(False)

    return has_test_modifier(node)


def fuzzy_focal_name(test_func_name: str) -> str:
    patterns = [r"test_(\w+)", r"(\w+)_test", r"Test(\w+)", r"(\w+)Test"]

    for pattern in patterns:
        match = re.search(pattern, test_func_name, re.IGNORECASE)
        if match:
            return match.group(1)

    return test_func_name


def get_focal_call(ast_util: ASTUtil, func: Node) -> Maybe[tuple[str, ASTLoc]]:
    """Find the focal call in the given function

    Args:
        ast_util (ASTUtil): ASTUtil for the file
        func (Node): a method_declaration node

    Returns:
        Maybe[tuple[str, ASTLoc]]: focal call and its location
    """

    # todo: find better heuristic to match object on imports
    calls = flatten_postorder(func, "method_invocation")

    # reverse for postorder
    func_calls = [ast_util.get_source_from_node(call) for call in calls]
    calls_before_assert: list[str] = []
    has_assert = False
    for call in func_calls:
        if "assert" in call:
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
        else:
            return Nothing

    return get_loc(calls_before_assert[-1])


def main():
    code = """
@Test
void catalogLoads() {
	@SuppressWarnings("rawtypes")
	ResponseEntity<Map> entity = new TestRestTemplate()
			.getForEntity("http://localhost:" + this.port + "/context/eureka/apps", Map.class);
	String computedPath = entity.getHeaders().getFirst("X-Version-Filter-Computed-Path");
	assertThat(computedPath).isEqualTo("/context/eureka/v2/apps");
}"""
    ast_util = ASTUtil(code)
    tree = ast_util.tree(JAVA_LANGUAGE)
    root_node = tree.root_node

    func_delcs = ast_util.get_all_nodes_of_type(root_node, "method_declaration")
    func = func_delcs[0]

    print(get_focal_call(ast_util, func))


if __name__ == "__main__":
    fire.Fire(main)
