import unittest
import os
import logging
from returns.maybe import Nothing, Some
from frontend.parser.ast_util import ASTUtil
from frontend.parser import RUST_LANGUAGE
from frontend.rust.rust_util import get_focal_call, get_test_functions
from unitsyncer.util import replace_tabs


class TestRustFrontend(unittest.TestCase):
    def test_get_focal_wo_unwrap(self):
        code = """#[test]
fn encode_all_bytes_url() {
    let bytes: Vec<u8> = (0..=255).collect();

    assert_eq!(
        "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8gISIjJCUmJygpKissLS4vMDEyMzQ1Njc4OTo7PD0\
         -P0BBQkNERUZHSElKS0xNTk9QUVJTVFVWV1hZWltcXV5fYGFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6e3x9fn\
         -AgYKDhIWGh4iJiouMjY6PkJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6ytrq\
         -wsbKztLW2t7i5uru8vb6_wMHCw8TFxsfIycrLzM3Oz9DR0tPU1dbX2Nna29zd3t_g4eLj5OXm5-jp6uvs7e7v8PHy\
         8_T19vf4-fr7_P3-_w==",
        &engine::GeneralPurpose::new(&URL_SAFE, PAD).encode(bytes)
    );
}
"""
        ast_util = ASTUtil(replace_tabs(code))
        tree = ast_util.tree(RUST_LANGUAGE)
        root_node = tree.root_node

        test_func = get_test_functions(ast_util, root_node)[0]
        focal_call = get_focal_call(ast_util, test_func)
        name, _ = focal_call.unwrap()
        self.assertEqual(
            name, "engine::GeneralPurpose::new(&URL_SAFE, PAD).encode(bytes)"
        )

    def test_get_focal_w_unwrap(self):
        code = '#[test]\nfn encode_engine_slice_error_when_buffer_too_small() {\n    for num_triples in 1..100 {\n        let input = "AAA".repeat(num_triples);\n        let mut vec = vec![0; (num_triples - 1) * 4];\n        assert_eq!(\n            EncodeSliceError::OutputSliceTooSmall,\n            STANDARD.encode_slice(&input, &mut vec).unwrap_err()\n        );\n        vec.push(0);\n        assert_eq!(\n            EncodeSliceError::OutputSliceTooSmall,\n            STANDARD.encode_slice(&input, &mut vec).unwrap_err()\n        );\n        vec.push(0);\n        assert_eq!(\n            EncodeSliceError::OutputSliceTooSmall,\n            STANDARD.encode_slice(&input, &mut vec).unwrap_err()\n        );\n        vec.push(0);\n        assert_eq!(\n            EncodeSliceError::OutputSliceTooSmall,\n            STANDARD.encode_slice(&input, &mut vec).unwrap_err()\n        );\n        vec.push(0);\n        assert_eq!(\n            num_triples * 4,\n            STANDARD.encode_slice(&input, &mut vec).unwrap()\n        );\n    }\n}'

        ast_util = ASTUtil(replace_tabs(code))
        tree = ast_util.tree(RUST_LANGUAGE)
        root_node = tree.root_node

        test_func = get_test_functions(ast_util, root_node)[0]
        focal_call = get_focal_call(ast_util, test_func)
        name, _ = focal_call.unwrap()
        self.assertEqual(name, "STANDARD.encode_slice(&input, &mut vec)")

    def test_no_focal_in_assert(self):
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

        test_func = get_test_functions(ast_util, root_node)[0]

        focal_call = get_focal_call(ast_util, test_func)
        name, _ = focal_call.unwrap()
        self.assertEqual(name, "engine.decode(&encoded)")

    def test_focal_no_assert(self):
        code = """
#[test]
fn test_23() {
    let data = [];
    let engine = utils::random_engine(data);
    let _ = engine.decode(data);
}
"""
        ast_util = ASTUtil(replace_tabs(code))
        tree = ast_util.tree(RUST_LANGUAGE)
        root_node = tree.root_node

        test_func = get_test_functions(ast_util, root_node)[0]

        focal_call = get_focal_call(ast_util, test_func)
        name, _ = focal_call.unwrap()
        self.assertEqual(name, "engine.decode(data)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
