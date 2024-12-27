import unittest
import os
import logging
from returns.maybe import Nothing, Some
from frontend.go.collect_focal import get_focal_call, is_test_fn
from frontend.parser.ast_util import ASTUtil
from frontend.parser import GO_LANGUAGE


class TestGoFrontend(unittest.TestCase):
    def test_is_test_fn(self):
        code = """
func TestDatasets(t *testing.T) {
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
        self.assertTrue(is_test_fn(fn, ast_util))

        code = """
func GetDataset(name string) (*Dataset, error) {
	out, err := zfsOutput("list", "-Hp", "-o", dsPropListOptions, name)
	if err != nil {
		return nil, err
	}

	ds := &Dataset{Name: name}
	for _, line := range out {
		if err := ds.parseLine(line); err != nil {
			return nil, err
		}
	}

	return ds, nil
}
"""
        ast_util = ASTUtil(code)
        tree = ast_util.tree(GO_LANGUAGE)
        root_node = tree.root_node
        fn = ast_util.get_all_nodes_of_type(root_node, "function_declaration")[0]
        self.assertFalse(is_test_fn(fn, ast_util))

    def test_focal(self):
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

        name, loc = get_focal_call(ast_util, fn).value_or((None, None))
        self.assertEqual(name, "Datasets")
        self.assertEqual(loc, (3, 15))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
