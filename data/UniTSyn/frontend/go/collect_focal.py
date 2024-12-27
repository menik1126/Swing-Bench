"""find focal call in Golang test function"""

import fire
import re
from tree_sitter import Node
from frontend.parser import GO_LANGUAGE
from frontend.parser.ast_util import ASTUtil, ASTLoc, flatten_postorder
from returns.maybe import Maybe, Nothing, Some, maybe


def get_focal_call(ast_util: ASTUtil, func: Node) -> Maybe[tuple[str, ASTLoc]]:
    """Find the focal call in the given function

    Args:
        ast_util (ASTUtil): ASTUtil for the file
        func (Node): a method_declaration node

    Returns:
        Maybe[tuple[str, ASTLoc]]: focal call and its location
    """

    # todo: find better heuristic to match object on imports
    # get the focal call from the given function

    calls = flatten_postorder(func, "call_expression")

    def get_basename(call: Node) -> str:
        func_name = ast_util.get_all_nodes_of_type(call, "identifier")[0]
        return ast_util.get_source_from_node(func_name)

    calls_before_assert: list[tuple[str, Node]] = []
    has_assert = False
    for call in calls:
        base_name = get_basename(call)
        if base_name in {"ok", "equals", "assert"}:
            has_assert = True
            break

        full_name = ast_util.get_source_from_node(call).split("(")[0]
        calls_before_assert.append((full_name, call))

    if not has_assert or not calls_before_assert:
        return Nothing

    # todo: check if focal is imported from workdir package
    def get_loc(n: tuple[str, Node]) -> tuple[str, ASTLoc]:
        full_name, node = n
        lineno, col = node.start_point
        match full_name.split("."):
            case [obj_name, *_, method_name]:  # pylint: disable=unused-variable
                offset = len(full_name) - len(method_name)
                return method_name, (lineno, col + offset)
            case _:
                return full_name, (lineno, col)

    return Some(get_loc(calls_before_assert[-1]))


def is_test_fn(node: Node, ast_util: ASTUtil) -> bool:
    """check if the function is a Golang test function

    Golang requires a test function to have `t *testing.T` input parameter

    Args:
        node (Node): a function_delc node
        ast_util (ASTUtil): node's util object

    Returns:
        bool: true if node is a unit test function, otherwise not
    """
    # func delc always have parameter_list
    params = ast_util.get_all_nodes_of_type(node, "parameter_list")[0]
    param_types = ast_util.get_all_nodes_of_type(params, "qualified_type")

    return "testing.T" in map(ast_util.get_source_from_node, param_types)


def main():
    code = """func TestDatasets(t *testing.T) {
	defer setupZPool(t).cleanUp()

	_, err := zfs.Datasets("")
	ok(t, err)

	ds, err := zfs.GetDataset("test")
	ok(t, err)
	equals(t, zfs.DatasetFilesystem, ds.Type)
	equals(t, "", ds.Origin)
	if runtime.GOOS != "solaris" {
		assert(t, ds.Logicalused != 0, "Logicalused is not greater than 0")
	}
}"""

    ast_util = ASTUtil(code)
    tree = ast_util.tree(GO_LANGUAGE)
    root_node = tree.root_node

    fn = ast_util.get_all_nodes_of_type(root_node, "function_declaration")[0]
    print(get_focal_call(ast_util, fn))


if __name__ == "__main__":
    fire.Fire(main)
