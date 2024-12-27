"""definition for general Synchronizer and LSPSynchronizer based on pylspclient"""
from code import compile_command
import pylspclient
import subprocess
import sys
import os
from pylspclient.lsp_structs import (
    Location,
    Position,
    Range,
    TextDocumentIdentifier,
    LANGUAGE_IDENTIFIER,
)
from unitsyncer.util import path2uri, replace_tabs, uri2path, ReadPipe
from unitsyncer.source_code import get_function_code
from unitsyncer.common import (
    CAPABILITIES,
    UNITSYNCER_HOME,
    RUST_CAPABILITIES,
    RUST_INIT_OPTIONS,
)
from typing import Optional, Union
from returns.maybe import Maybe, Nothing, Some
from returns.result import Result, Success, Failure
from returns.converters import maybe_to_result
import logging
from unitsyncer.util import silence
import json
from os.path import realpath


def get_lsp_cmd(language: str) -> Optional[list[str]]:
    match language:
        case LANGUAGE_IDENTIFIER.PYTHON:
            return ["python3", "-m", "pylsp"]
        case LANGUAGE_IDENTIFIER.C | LANGUAGE_IDENTIFIER.CPP:
            return ["clangd"]
        case LANGUAGE_IDENTIFIER.JAVA:
            return [
                "bash",
                f"{UNITSYNCER_HOME}/java-language-server/dist/lang_server_linux.sh",
            ]
        case LANGUAGE_IDENTIFIER.JAVASCRIPT:
            return ["typescript-language-server", "--stdio"]
        case LANGUAGE_IDENTIFIER.RUST:
            return ["rust-analyzer"]
        case LANGUAGE_IDENTIFIER.GO:
            return ["gopls"]
        case _:
            return None


class Synchronizer:
    """interface definition for all Synchronizer"""

    def __init__(self, workspace_dir: str, language: str) -> None:
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.langID = language

    def initialize(self, timeout: int):
        raise NotImplementedError

    def get_source_of_call(
        self,
        focal_name: str,
        file_path: str,
        line: int,
        col: int,
        verbose: bool = False,
    ) -> Result[tuple[str, str | None, str | None], str]:
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError


class LSPSynchronizer(Synchronizer):
    """Synchronizer implementation based on pylspclient"""

    def __init__(self, workspace_dir: str, language: str) -> None:
        super().__init__(workspace_dir, language)

        self.root_uri = path2uri(self.workspace_dir)
        workspace_name = os.path.basename(self.workspace_dir)
        self.workspace_folders = [{"name": workspace_name, "uri": self.root_uri}]
        self.lsp_proc: subprocess.Popen
        self.lsp_client: pylspclient.LspClient

    @silence
    def start_lsp_server(self, timeout: int = 10):
        lsp_cmd = get_lsp_cmd(self.langID)
        if lsp_cmd is None:
            sys.stderr.write("Language {language} is not supported\n")
            exit(1)

        self.lsp_proc = subprocess.Popen(
            lsp_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        read_pipe = ReadPipe(self.lsp_proc.stderr)
        read_pipe.start()
        json_rpc_endpoint = pylspclient.JsonRpcEndpoint(
            self.lsp_proc.stdin, self.lsp_proc.stdout
        )
        lsp_endpoint = pylspclient.LspEndpoint(json_rpc_endpoint, timeout=timeout)
        self.lsp_client = pylspclient.LspClient(lsp_endpoint)

    @silence
    def initialize(self, timeout: int = 10):
        self.start_lsp_server(timeout)
        response = self.lsp_client.initialize(
            self.lsp_proc.pid,
            self.workspace_dir,
            self.root_uri,
            None,
            CAPABILITIES,
            "off",
            self.workspace_folders,
        )
        logging.debug(json.dumps(response))
        self.lsp_client.initialized()

        if self.langID == LANGUAGE_IDENTIFIER.CPP:
            # https://gitlab.kitware.com/cmake/cmake/-/issues/16588
            # produces compile_commands.json in workspace for clangd to run
            compile_commands = os.path.join(self.workspace_dir, "compile_commands.json")
            if not os.path.exists(compile_commands):
                logging.debug(
                    f"Calling cmake to produce compile_commands.json in {self.workspace_dir}"
                )
                subprocess.run(
                    ["cmake", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", "."],
                    cwd=self.workspace_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )

    def open_file(self, file_path: str) -> str:
        """send a file to LSP server

        Args:
            file_path (str): absolute path to the file

        Returns:
            str: uri of the opened file
        """
        uri = path2uri(file_path)
        with open(file_path, "r", errors="replace") as f:
            text = replace_tabs(f.read())
        version = 1
        self.lsp_client.didOpen(
            pylspclient.lsp_structs.TextDocumentItem(uri, self.langID, version, text)
        )
        return uri

    def get_source_of_call(
        self,
        focal_name: str,
        file_path: str,
        line: int,
        col: int,
        verbose: bool = False,
    ) -> Result[tuple[str, str | None, str | None], str]:
        """get the source code of a function called at a specific location in a file

        Args:
            file_path (str): absolute path to file that contains the call
            line (int): line number of the call, 0-indexed
            col (int): column number of the call, 0-indexed

        Returns:
            Maybe[tuple[str, str | None]]: the source code and docstring of the called function
        """
        try:
            uri = self.open_file(file_path)
        except Exception as e:  # pylint: disable=broad-exception-caught
            return Failure(str(e))

        try:
            goto_def = self.lsp_client.definition
            if not verbose:
                goto_def = silence(goto_def)

            response = goto_def(
                TextDocumentIdentifier(uri),
                Position(line, col),
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return Failure(str(e))

        def_location: Location
        match response:
            case None | []:
                return Failure(f"No definition found: {response}")
            case [loc, *_]:
                def_location = loc
            case loc:
                if isinstance(loc, Location):
                    def_location = loc
                else:
                    return Failure(f"Unexpected response from LSP server: {loc}")

        file_path = uri2path(def_location.uri).value_or(str(def_location.uri))
        logging.debug(file_path)

        # check if file path is relative to workspace root
        if not (
            file_path.startswith(self.workspace_dir)
            or file_path.startswith(realpath(self.workspace_dir))
        ):
            return Failure(f"Source code not in workspace: {file_path}")

        def not_found_error(_):
            lineno = def_location.range.start.line
            col_offset = def_location.range.start.character
            return f"Source code not found: {file_path}:{lineno}:{col_offset}"

        return (
            maybe_to_result(get_function_code(def_location, self.langID))
            .alt(not_found_error)
            .bind(lambda t: Failure("Empty Source Code") if t[0] == "" else Success(t))
        )

    def stop(self):
        self.lsp_client.shutdown()
        self.lsp_client.exit()
        self.lsp_proc.kill()


def main():
    # workspace_dir = os.path.abspath(
    #     "data/repos/google-googletest/google-googletest-f8d7d77/"
    # )
    # test_file = os.path.join(workspace_dir, "googletest", "src", "gtest-test-part.cc")
    # func_loc = (51, 30)

    workspace_dir = os.path.abspath("data/repos/cpp_example/")
    test_file = os.path.join(workspace_dir, "main.cpp")
    func_loc = (3, 12)

    sync = LSPSynchronizer(workspace_dir, "cpp")
    sync.initialize()

    print(sync.get_source_of_call("", test_file, *func_loc))

    # with open(test_file, "r") as f:
    #     code = f.read()

    # lines = code.splitlines()
    # for i, l in enumerate(lines):
    #     for j in range(len(l)):
    #         match sync.get_source_of_call("", test_file, i, j):
    #             case Success(x):
    #                 print(i, j)
    #                 print(x)
    #             case Failure(_):
    #                 pass
    sync.stop()


if __name__ == "__main__":
    main()
