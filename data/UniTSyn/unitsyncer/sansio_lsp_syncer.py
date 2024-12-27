"""Synchronizer Based on sansio_lsp"""

from unitsyncer.sync import Synchronizer, get_lsp_cmd
import pprint
import pathlib
import subprocess
import sys
import threading
import queue
import time
import os
from returns.result import Result, Success, Failure
from returns.converters import maybe_to_result
import logging
from unitsyncer.util import path2uri, replace_tabs, uri2path
from unitsyncer.source_code import get_function_code

import sansio_lsp_client as lsp

# ============================utils ========================
# from https://github.com/PurpleMyst/sansio-lsp-client/blob/master/tests/test_actual_langservers.py

METHOD_COMPLETION = "completion"
METHOD_HOVER = "hover"
METHOD_SIG_HELP = "signatureHelp"
METHOD_DEFINITION = "definition"
METHOD_REFERENCES = "references"
METHOD_IMPLEMENTATION = "implementation"
METHOD_DECLARATION = "declaration"
METHOD_TYPEDEF = "typeDefinition"
METHOD_DOC_SYMBOLS = "documentSymbol"
METHOD_FORMAT_DOC = "formatting"
METHOD_FORMAT_SEL = "rangeFormatting"

RESPONSE_TYPES = {
    METHOD_COMPLETION: lsp.Completion,
    METHOD_HOVER: lsp.Hover,
    METHOD_SIG_HELP: lsp.SignatureHelp,
    METHOD_DEFINITION: lsp.Definition,
    METHOD_REFERENCES: lsp.References,
    METHOD_IMPLEMENTATION: lsp.Implementation,
    METHOD_DECLARATION: lsp.Declaration,
    METHOD_TYPEDEF: lsp.TypeDefinition,
    METHOD_DOC_SYMBOLS: lsp.MDocumentSymbols,
    METHOD_FORMAT_DOC: lsp.DocumentFormatting,
    METHOD_FORMAT_SEL: lsp.DocumentFormatting,
}


class ThreadedServer:
    """
    Gathers all messages received from server - to handle random-order-messages
    that are not a response to a request.
    """

    def __init__(self, process, root_uri):
        self.process = process
        self.root_uri = root_uri
        self.lsp_client = lsp.Client(
            root_uri=root_uri,
            workspace_folders=[lsp.WorkspaceFolder(uri=self.root_uri, name="Root")],
            trace="verbose",
        )
        self.msgs = []

        self._pout = process.stdout
        self._pin = process.stdin

        self._read_q: queue.Queue[bytes] = queue.Queue()
        self._send_q: queue.Queue[bytes | None] = queue.Queue()

        self.reader_thread = threading.Thread(
            target=self._read_loop, name="lsp-reader", daemon=True
        )
        self.writer_thread = threading.Thread(
            target=self._send_loop, name="lsp-writer", daemon=True
        )

        self.reader_thread.start()
        self.writer_thread.start()

        self.exception = None

    # threaded
    def _read_loop(self):
        try:
            while True:
                data = self.process.stdout.read(1)

                if data == b"":
                    break

                self._read_q.put(data)
        except Exception as ex:  # pylint: disable=broad-exception-caught
            self.exception = ex
        self._send_q.put_nowait(None)  # stop send loop

    # threaded
    def _send_loop(self):
        try:
            while True:
                chunk = self._send_q.get()
                if chunk is None:
                    break

                # print(f"\nsending: {buf}\n")
                self.process.stdin.write(chunk)
                self.process.stdin.flush()
        except Exception as ex:  # pylint: disable=broad-exception-caught
            self.exception = ex

    def _queue_data_to_send(self):
        send_buf = self.lsp_client.send()
        if send_buf:
            self._send_q.put(send_buf)

    def _read_data_received(self):
        while not self._read_q.empty():
            data = self._read_q.get()
            events = self.lsp_client.recv(data)
            for ev in events:
                self.msgs.append(ev)
                self._try_default_reply(ev)

    def _try_default_reply(self, msg):
        if isinstance(
            msg,
            (
                lsp.ShowMessageRequest,
                lsp.WorkDoneProgressCreate,
                lsp.RegisterCapabilityRequest,
                lsp.ConfigurationRequest,
            ),
        ):
            msg.reply()

        elif isinstance(msg, lsp.WorkspaceFolders):
            msg.reply([lsp.WorkspaceFolder(uri=self.root_uri, name="Root")])

    def wait_for_message_of_type(self, type_, timeout=60):
        end_time = time.monotonic() + timeout
        while time.monotonic() < end_time:
            self._queue_data_to_send()
            self._read_data_received()

            # raise thread's exception if have any
            if self.exception:
                raise self.exception

            for msg in self.msgs:
                if isinstance(msg, type_):
                    self.msgs.remove(msg)
                    return msg

            time.sleep(0.2)

        raise Exception(  # pylint: disable=broad-exception-raised
            f"Didn't receive {type_} in time; have: " + pprint.pformat(self.msgs)
        )

    def exit_cleanly(self):
        # Not necessarily error, gopls sends logging messages for example
        #        if self.msgs:
        #            print(
        #                "* unprocessed messages: " + pprint.pformat(self.msgs)
        #            )

        assert self.lsp_client.state == lsp.ClientState.NORMAL
        self.lsp_client.shutdown()
        self.wait_for_message_of_type(lsp.Shutdown)
        self.lsp_client.exit()
        self._queue_data_to_send()
        self._read_data_received()

    def do_method(
        self, text, file_uri, method, pos, response_type=None
    ):  # pylint: disable=unused-argument, too-many-arguments
        def doc_pos():
            return lsp.TextDocumentPosition(
                textDocument=lsp.TextDocumentIdentifier(uri=file_uri),
                position=pos,
            )

        if not response_type:
            response_type = RESPONSE_TYPES[method]

        if method == METHOD_COMPLETION:
            event_id = self.lsp_client.completion(
                text_document_position=doc_pos(),
                context=lsp.CompletionContext(
                    triggerKind=lsp.CompletionTriggerKind.INVOKED, triggerCharacter=None
                ),
            )
        elif method == METHOD_HOVER:
            event_id = self.lsp_client.hover(text_document_position=doc_pos())
        elif method == METHOD_SIG_HELP:
            event_id = self.lsp_client.signatureHelp(text_document_position=doc_pos())
        elif method == METHOD_DEFINITION:
            event_id = self.lsp_client.definition(text_document_position=doc_pos())
        elif method == METHOD_REFERENCES:
            event_id = self.lsp_client.references(text_document_position=doc_pos())
        elif method == METHOD_IMPLEMENTATION:
            event_id = self.lsp_client.implementation(text_document_position=doc_pos())
        elif method == METHOD_DECLARATION:
            event_id = self.lsp_client.declaration(text_document_position=doc_pos())
        elif method == METHOD_TYPEDEF:
            event_id = self.lsp_client.typeDefinition(text_document_position=doc_pos())
        elif method == METHOD_DOC_SYMBOLS:
            _docid = lsp.TextDocumentIdentifier(uri=file_uri)
            event_id = self.lsp_client.documentSymbol(text_document=_docid)
        else:
            raise NotImplementedError(method)

        resp = self.wait_for_message_of_type(response_type)
        assert not hasattr(resp, "message_id") or resp.message_id == event_id
        return resp


# ============================ ends utils ========================


class SansioLSPSynchronizer(Synchronizer):
    def __init__(self, workspace_dir: str, language: str) -> None:
        super().__init__(workspace_dir, language)

        self.workspace_path: pathlib.Path = pathlib.Path(self.workspace_dir)
        self.root_uri = self.workspace_path.as_uri()

        self.lsp_proc: subprocess.Popen
        self.lsp_server: ThreadedServer
        self.lsp_client: lsp.Client

    def start_lsp_server(self):
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
        self.lsp_server = ThreadedServer(self.lsp_proc, self.root_uri)
        self.lsp_client = self.lsp_server.lsp_client

    def initialize(self, timeout: int = 20):
        self.start_lsp_server()
        self.lsp_server.wait_for_message_of_type(lsp.Initialized, timeout=timeout)

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
        file_item = lsp.TextDocumentItem(
            uri=uri, languageId=self.langID, text=text, version=0
        )
        self.lsp_client.did_open(file_item)
        return uri

    def get_source_of_call(
        self,
        focal_name: str,
        file_path: str,
        line: int,
        col: int,
        verbose: bool = False,
    ) -> Result[tuple[str, str | None, str | None], str]:
        file_uri = self.open_file(file_path)
        pos = lsp.Position(line=line, character=col)
        try:
            defn_response = self.lsp_server.do_method(
                focal_name,
                file_uri,
                METHOD_DEFINITION,
                pos,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return Failure(f"GoDef Request Failed: {e}")

        logging.debug(defn_response)

        def_location: lsp.Location
        match defn_response.result:
            case []:
                return Failure("No definition found")
            case [fst, *_]:
                def_location = fst
            case _:
                return Failure(
                    f"Unexpected response from LSP server: {str(defn_response)}"
                )

        file_path = uri2path(def_location.uri).value_or(str(def_location.uri))
        logging.debug(file_path)

        # check if file path is relative to workspace root
        if not file_path.startswith(str(self.workspace_dir)):
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
        pass
