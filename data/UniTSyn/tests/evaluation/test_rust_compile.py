import json
from typing import Iterable
import fire
import os
from tree_sitter import Node
from frontend.parser import RUST_LANGUAGE
from frontend.parser.ast_util import ASTUtil
from unitsyncer.util import replace_tabs
import json
from evaluation.rust.compile import flatten_use_delc, construct_use_delcs
import unittest
import os
import logging


class TestRustCompile(unittest.TestCase):
    def test_flatten_base64(self):
        code = "use rand::{Rng, SeedableRng};"
        expected = ["use rand::Rng;", "use rand::SeedableRng;"]
        self.assertEqual(flatten_use_delc(code), expected)

        code = "use base64::engine::{general_purpose::STANDARD, Engine};"
        expected = [
            "use base64::engine::general_purpose::STANDARD;",
            "use base64::engine::Engine;",
        ]
        self.assertEqual(flatten_use_delc(code), expected)

        code = "use base64::engine::general_purpose::{GeneralPurpose, NO_PAD};"
        expected = [
            "use base64::engine::general_purpose::GeneralPurpose;",
            "use base64::engine::general_purpose::NO_PAD;",
        ]
        self.assertEqual(flatten_use_delc(code), expected)

        # use wildcard only
        code = "use base64::*;"
        expected = ["use base64::*;"]
        self.assertEqual(flatten_use_delc(code), expected)

        # use wildcard in list
        code = "use base64::{alphabet::URL_SAFE, engine::general_purpose::PAD, engine::general_purpose::STANDARD, *,};"
        expected = [
            "use base64::alphabet::URL_SAFE;",
            "use base64::engine::general_purpose::PAD;",
            "use base64::engine::general_purpose::STANDARD;",
            "use base64::*;",
        ]
        self.assertEqual(flatten_use_delc(code), expected)

        # use_as clause in list
        code = "use base64::{engine::general_purpose::STANDARD, Engine as _};"
        expected = [
            "use base64::engine::general_purpose::STANDARD;",
            "use base64::Engine as _;",
        ]
        self.assertEqual(flatten_use_delc(code), expected)

        # with indent
        code = """
use base64::{
    alphabet::URL_SAFE, engine::general_purpose::PAD, engine::general_purpose::STANDARD, *,
};"""
        expected = [
            "use base64::alphabet::URL_SAFE;",
            "use base64::engine::general_purpose::PAD;",
            "use base64::engine::general_purpose::STANDARD;",
            "use base64::*;",
        ]
        self.assertEqual(flatten_use_delc(code), expected)

    def test_construct_use_lists(self):
        workspace_dir = os.path.abspath(
            "data/repos/marshallpierce-rust-base64/marshallpierce-rust-base64-4ef33cc"
        )

        tests_expected = {
            "use base64::alphabet::URL_SAFE;",
            "use base64::engine::general_purpose::PAD;",
            "use base64::engine::general_purpose::STANDARD;",
            "use base64::*;",
            "use rand::Rng;",
            "use rand::SeedableRng;",
            "use base64::engine::Engine;",
            "use base64::engine::general_purpose::GeneralPurpose;",
            "use base64::engine::general_purpose::NO_PAD;",
        }

        self.assertEqual(construct_use_delcs(workspace_dir, "tests"), tests_expected)

        fuzz_expected = {
            "use base64::Engine as _;",
            "use base64::engine::general_purpose::STANDARD;",
            "use self::rand::SeedableRng;",
            "use self::rand::Rng;",
            "use base64::*;",
            "use base64::alphabet;",
        }
        self.assertEqual(construct_use_delcs(workspace_dir, "fuzz"), fuzz_expected)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
