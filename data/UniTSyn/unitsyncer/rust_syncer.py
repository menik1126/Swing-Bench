"""Replacement Synchronizer for Rust"""
from typing import Optional
from pip._vendor import tomli
from os.path import join as pjoin, isfile, isdir, abspath
import os
from returns.maybe import Maybe, Nothing, Some
from returns.result import Result, Success, Failure
from frontend.parser.ast_util import ASTLoc, ASTUtil
from frontend.parser import RUST_LANGUAGE
from tree_sitter import Language, Parser, Tree
from tree_sitter import Node
from pylspclient.lsp_structs import Location, LANGUAGE_IDENTIFIER, Range, Position
from unitsyncer.source_code import get_function_code
from unitsyncer.util import path2uri, uri2path
from returns.converters import maybe_to_result
from unitsyncer.sync import Synchronizer
from fuzzywuzzy import process
from functools import partial


class RustSynchronizer(Synchronizer):
    def __init__(self, workspace_dir: str, language="rust") -> None:
        super().__init__(workspace_dir, LANGUAGE_IDENTIFIER.RUST)
        self.file_func_map: dict[str, list[tuple[str, Node]]] = {}

    def initialize(self, timeout: int = 10):
        """index all files and functions in the workdir/src"""
        for root, _, files in os.walk(self.workspace_dir):
            for file in files:
                if file.endswith(".rs"):
                    file_path = pjoin(root, file)
                    funcs = self._get_file_functions(file_path)
                    self.file_func_map[file_path] = funcs

    def _get_file_functions(self, file_path: str) -> list[tuple[str, Node]]:
        """get all function items in the given file

        Args:
            file_path (str): path to source code file

        Returns:
            list[tuple[str, Node]]: [(function_name, function_node)]
        """
        with open(file_path) as code_file:
            ast_util = ASTUtil(code_file.read())
        tree = ast_util.tree(RUST_LANGUAGE)
        nodes = ast_util.get_all_nodes_of_type(tree.root_node, "function_item")
        names = [ast_util.get_name(node).value_or("") for node in nodes]
        return list(zip(names, nodes))

    def get_source_of_call(
        self,
        focal_name: str,
        file_path: Optional[str] = None,
        line: Optional[int] = None,
        col: Optional[int] = None,
        verbose: bool = False,
    ) -> Result[tuple[str, str | None, str | None], str]:
        match self.goto_definition(focal_name):
            case [] | None:
                return Failure("Not Definition Found")
            case [(_, loc), *_]:
                # todo: find best match based on imports of test file

                def not_found_error(_):
                    file_path = uri2path(loc.uri).value_or("")
                    lineno = loc.range.start.line
                    col_offset = loc.range.start.character
                    return f"Source code not found: {file_path}:{lineno}:{col_offset}"

                return (
                    maybe_to_result(get_function_code(loc, LANGUAGE_IDENTIFIER.RUST))
                    .alt(not_found_error)
                    .bind(
                        lambda t: Failure("Empty Source Code")
                        if t[0] == ""
                        else Success(t)
                    )
                )
            case _:
                return Failure("Unexpected Error")

    def goto_definition(self, focal_name: str) -> list[tuple[str, Location]]:
        """get the definition of the given function name

        Args:
            focal_name (str): name of the function

        Returns:
            list[tuple[str, Location]]: [(source_file_path, location))],
                source_file_path is used for sorting the results
        """
        results: list[tuple[str, Location]] = []  # [(file_path, location)]
        include_name: str
        base_name: str

        match focal_name.split("."):
            case [obj_name, *xs, method_name]:
                include_name = obj_name

                # if method_name is unwrap, use the previous splitted name as method_name
                if "unwrap" in method_name:
                    method_name = obj_name if len(xs) == 0 else xs[-1]
                base_name = method_name.split("(")[0]
            case _:
                temp_name = focal_name.split("(")[0]
                include_name = temp_name
                base_name = temp_name

        for file_path, funcs in self.file_func_map.items():
            for name, node in funcs:
                if name == base_name:
                    uri = path2uri(file_path)
                    range_ = Range(
                        Position(*node.start_point),
                        Position(*node.end_point),
                    )
                    results.append((file_path, Location(uri, range_)))

        # sort by fuzzy match with base name
        return sorted(
            results,
            key=partial(self.fuzzy_comparator, include_name),
            reverse=True,
        )

    def fuzzy_comparator(self, include_name: str, x: tuple[str, Location]) -> float:
        """similarity score of file path with include_name

        Args:
            include_name (str): **engine::GeneralPurpose::new(&URL_SAFE, PAD)**.encode(bytes)
            x (tuple[str, Location]): (file_path, location)

        Returns:
            float: similarity score
        """
        file_path = x[0].split(self.workspace_dir)[-1]
        match process.extractOne(file_path, [include_name]):
            case (_, score):
                return score
            case _:
                return 0

    def stop(self):
        pass


def main():
    workdir = "data/repos/marshallpierce-rust-base64/marshallpierce-rust-base64-4ef33cc"
    lsp = RustSynchronizer(workdir)
    lsp.initialize()

    print(
        lsp.get_source_of_call(
            "engine::GeneralPurpose::new(&URL_SAFE, PAD).encode(bytes)"
        )
    )


if __name__ == "__main__":
    main()
