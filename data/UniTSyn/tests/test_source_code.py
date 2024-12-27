import unittest
import os
import logging
from unitsyncer.source_code import get_function_code
from returns.maybe import Nothing, Some
from pylspclient.lsp_structs import Location, Position, Range

from unitsyncer.util import path2uri


class TestSourceCode(unittest.TestCase):
    def test_python_get_function_code(self):
        uri = f"file://{os.getcwd()}/data/repos/py_example/src/add.py"
        range_ = Range(Position(0, 4), Position(0, 7))
        loc = Location(uri, range_)
        add_src = "def add(x: int, y: int) -> int:\n    return x + y"

        self.assertEqual(get_function_code(loc, "python").unwrap()[0], add_src)

    def test_python_get_function_code_not_found(self):
        uri = f"file://{os.getcwd()}/data/repos/py_example/src/add.py"
        range_ = Range(Position(1, 4), Position(1, 7))
        loc = Location(uri, range_)

        self.assertEqual(get_function_code(loc, "python"), Nothing)

    def test_java_get_function_code(self):
        uri = f"file://{os.getcwd()}/data/repos/java_example/Add.java"
        # range_ = Range(Position(29, 36), Position(29, 37))
        range_ = Range(Position(17, 22), Position(17, 23))
        loc = Location(uri, range_)

        add_src = "public static int add(int a, int b) {\n    return a + b;\n}"

        self.assertEqual(get_function_code(loc, "java").unwrap()[0], add_src)

    def test_java_get_function_code_w_annotation(self):
        uri = f"file://{os.getcwd()}/data/repos/java_example/Add.java"
        range_ = Range(Position(22, 3), Position(22, 4))
        loc = Location(uri, range_)
        sub_src = (
            "@Deprecated\npublic static int sub(int a, int b) {\n    return a - b;\n}"
        )

        self.assertEqual(get_function_code(loc, "java").unwrap()[0], sub_src)

    def test_real_java_method_w_annotation(self):
        uri = f"file://{os.getcwd()}/data/java_repos/spring-cloud-spring-cloud-netflix/spring-cloud-spring-cloud-netflix-630151f/spring-cloud-netflix-eureka-client/src/main/java/org/springframework/cloud/netflix/eureka/EurekaInstanceConfigBean.java"

        range_ = Range(Position(297, 22), Position(297, 23))
        loc = Location(uri, range_)
        self.assertIsNotNone(get_function_code(loc, "java").value_or(None))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
