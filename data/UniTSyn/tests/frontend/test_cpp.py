import unittest
import os
import logging
from returns.maybe import Nothing, Some
from frontend.cpp.collect_focal import get_focal_call
from frontend.parser.ast_util import ASTUtil
from frontend.parser import CPP_LANGUAGE, JAVA_LANGUAGE


class TestCppFrontend(unittest.TestCase):
    """testing C++ frontend for gtest"""

    def __test_focal_helper(self, code: str):
        ast_util = ASTUtil(code)
        tree = ast_util.tree(CPP_LANGUAGE)
        root_node = tree.root_node

        fn = ast_util.get_all_nodes_of_type(root_node, "function_definition")[0]
        return get_focal_call(ast_util, fn)

    def test_focal(self):
        """
        For a regular @Test function, with function call in `EXPECT`,
        that function call should be the focal
        """
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

        name, loc = self.__test_focal_helper(code).unwrap()
        self.assertEqual(name, "getOpenACCDirectiveKind")
        self.assertEqual(loc, (2, 12))

    def test_focal_not_in_assert(self):
        """
        if there is no function call in the first `assertThat`,
        the the last call before first `assertThat` is the focal
        """
        code = """
TEST(AsmWriterTest, DebugPrintDetachedArgument) {
  LLVMContext Ctx;
  auto Ty = Type::getInt32Ty(Ctx);
  auto Arg = new Argument(Ty);

  std::string S;
  raw_string_ostream OS(S);
  Arg->print(OS);
  EXPECT_EQ(S, "i32 <badref>");
  delete Arg;
}"""

        name, loc = self.__test_focal_helper(code).unwrap()
        self.assertEqual(name, "print")
        self.assertEqual(loc, (8, 7))

        code = """
TEST(BFSTest, InstantiateGraphFromEdges)
{
    Graph<int> g({ {1, 2}, {1, 3}, {2, 3} });

    std::vector<int> bfs = g.BFS(1);
    std::vector<int> expected{ 1, 2, 3 };

    ASSERT_EQ(bfs, expected);
}
"""
        name, loc = self.__test_focal_helper(code).unwrap()
        self.assertEqual(name, "BFS")
        self.assertEqual(loc, (5, 29))

    def test_focal_not_assert(self):
        """If no assert in test function, then fail"""

        code = """
TEST(TestNothing, SomeTest) {
    int a = 1 + 2;
    int b = 2 + 3;
}
"""
        self.assertEqual(self.__test_focal_helper(code), Nothing)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
