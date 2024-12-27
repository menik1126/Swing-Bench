"""tests for rust coverage module"""

import json
from typing import Iterable
import fire
import os
from tree_sitter import Node
from frontend.parser import RUST_LANGUAGE
from frontend.parser.ast_util import ASTUtil
from unitsyncer.util import replace_tabs
from evaluation.rust.coverage import get_testcase_coverages
import unittest
import logging


class TestRustCoverage(unittest.TestCase):
    def test_base64(self):
        workspace_dir = os.path.abspath(
            "data/rust_repos//marshallpierce-rust-base64/marshallpierce-rust-base64-4ef33cc"
        )

        cov_map = get_testcase_coverages(workspace_dir)
        self.assertTrue(len(cov_map) >= 13)  # there are 13 hand-written tests

        self.assertEqual(cov_map["encode_all_ascii"], 3.94)
        self.assertEqual(cov_map["encode_all_bytes"], 4.95)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
