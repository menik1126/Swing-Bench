"""main script for UniTSyncer backend"""
from tqdm import tqdm
from unitsyncer.sync import Synchronizer, LSPSynchronizer
from unitsyncer.rust_syncer import RustSynchronizer
from unitsyncer.sansio_lsp_syncer import SansioLSPSynchronizer
from pylspclient.lsp_structs import LANGUAGE_IDENTIFIER, Location, Position, Range
from returns.maybe import Maybe, Nothing, Some
from returns.result import Result, Success, Failure
from unitsyncer.util import parallel_starmap as starmap, path2uri, convert_to_seconds
from unitsyncer.common import CORES
from unitsyncer.extract_def import get_def_header
import math
from unitsyncer.source_code import get_function_code
import json
import jsonlines
import os
from pathos.multiprocessing import ProcessPool
import logging
import fire
from itertools import groupby
import pathlib


def id2path(func_id: str) -> str:
    return func_id.split("::")[0]


def java_workdir_dict(objs: list[dict]) -> dict[str, list[dict]]:
    """split a list of test ids into a dict of workdir to file path
    this solves the LSP TimeoutError for JAVA with too much subdirectories

    Args:
        objs (list[dict]): [focal_ids parsed into dict]

    Returns:
        dict[str, list[dict]]: {workdir: [corresponding focal objects, ...], ...}
    """
    workdir_dict: dict[str, list[dict]] = {}
    for obj in objs:
        test_id = obj["test_id"]
        file_path = id2path(test_id)
        workdir = file_path.split("/test")[0]
        if workdir not in workdir_dict:
            workdir_dict[workdir] = []
        workdir_dict[workdir].append(obj)
    return workdir_dict


def focal2result(syncer: Synchronizer, repos_root, obj):
    p = id2path(obj["test_id"])
    file_path = os.path.join(repos_root, p)
    src_lineno, src_col_offset = obj["focal_loc"]
    test_lineno, test_col_offset = obj["test_loc"]

    langID = syncer.langID  # pylint: disable=invalid-name

    # only python ast is 1-indexed, tree-sitter and LSP are 0-indexed
    match langID:
        case LANGUAGE_IDENTIFIER.PYTHON:
            src_lineno -= 1
            test_lineno -= 1

    # since the test's delc node is already capture by frontend, it can store the test code
    if "test" in obj.keys():
        test = obj["test"]
    else:
        fake_loc = Location(
            path2uri(file_path),
            Range(
                Position(test_lineno, test_col_offset),
                Position(test_lineno, test_col_offset + 1),
            ),
        )
        test, _, _ = get_function_code(fake_loc, syncer.langID).unwrap()

    result = {
        "test_id": obj["test_id"],
        "test": test,
    }

    # todo: conform return format when Failure
    match syncer.get_source_of_call(
        obj["focal_id"],
        file_path,
        src_lineno,
        src_col_offset,
    ):
        case Success((code, docstring, code_id)):
            result["code_id"] = (
                obj["focal_id"]
                if code_id is None
                else code_id.removeprefix(repos_root + "/")
            )
            result["code"] = code
            result["docstring"] = docstring
            result["test_header"] = get_def_header(test, langID)
        case Failure(e):
            logging.debug(e)
            result["error"] = e

    return result


def process_one_focal_file(
    focal_file="./data/focal/ageitgey-face_recognition.jsonl",
    repos_root="data/repos",
    language="python",
    skip_processed=True,
) -> tuple[int, int]:
    with open(focal_file) as f:
        objs = [json.loads(line) for line in f.readlines()]

    if len(objs) == 0:
        return 0, 0

    n_focal = len(objs)
    match language:
        case LANGUAGE_IDENTIFIER.JAVA:
            wd = java_workdir_dict(objs)
        case _:
            first_test_id = objs[0]["test_id"]
            workdir = "/".join(id2path(first_test_id).split("/")[:2])
            wd = {
                workdir: objs,
            }

    success_results = []
    failure_results = []
    source_file = focal_file.replace("focal", "source")
    success_file = source_file.replace(".jsonl", ".success.jsonl")
    failure_file = source_file.replace(".jsonl", ".failure.jsonl")

    # check if this file is already processed
    if skip_processed and os.path.exists(success_file) and os.path.exists(failure_file):
        with open(success_file, "rb") as f:
            n_succ = sum(1 for _ in f)
        with open(failure_file, "rb") as f:
            n_fail = sum(1 for _ in f)

        if language == LANGUAGE_IDENTIFIER.JAVA:
            return n_focal, n_succ
        if n_succ + n_fail >= n_focal:
            return n_focal, n_succ

    pathlib.Path(success_file).touch()
    pathlib.Path(failure_file).touch()

    logging.debug(f"number of workdir_dict: {len(wd.keys())}")
    repos_root = os.path.abspath(repos_root)
    for workdir, workdir_objs in wd.items():
        succ = []
        fail = []
        full_workdir = os.path.join(repos_root, workdir)
        logging.debug(f"workdir: {full_workdir}")
        syncer: Synchronizer

        match language:
            case LANGUAGE_IDENTIFIER.RUST:
                syncer = RustSynchronizer(full_workdir, language)
            case LANGUAGE_IDENTIFIER.GO:
                syncer = SansioLSPSynchronizer(full_workdir, language)
            case _:
                syncer = LSPSynchronizer(full_workdir, language)

        try:
            syncer.initialize(timeout=60)

            for obj in workdir_objs:
                result = focal2result(syncer, repos_root, obj)
                if "error" in result:
                    fail.append(result)
                else:
                    succ.append(result)

            syncer.stop()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.debug(e)
            syncer.stop()
            continue

        # append to source file in loop to avoid losing data
        with jsonlines.open(success_file, "a") as f:
            f.write_all(succ)
        with jsonlines.open(failure_file, "a") as f:
            f.write_all(fail)

        success_results.extend(succ)
        failure_results.extend(fail)

    return n_focal, len(success_results)


def main(
    repos_root="data/repos",
    focal_path="data/focal",
    language="python",
    jobs=CORES,
    debug=False,
    timeout="30m",
):
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    all_focal_files = []
    if os.path.isdir(focal_path):
        focal_dir = focal_path
        for root, _, files in os.walk(os.path.abspath(focal_dir)):
            for file in files:
                if file.endswith(".jsonl"):
                    all_focal_files.append(os.path.join(root, file))
    elif os.path.isfile(focal_path):
        all_focal_files.append(focal_path)
    else:
        logging.error(f"{focal_path} is not a valid file or directory")
        exit(1)

    logging.info(f"Processing {len(all_focal_files)} focal files")
    os.makedirs("./data/source", exist_ok=True)

    # starting jobs / 2 since each job will spawn 2 processes (main and LSP)
    with ProcessPool(math.ceil(jobs / 2)) as pool:
        rnt = list(
            tqdm(
                pool.imap(
                    lambda f: process_one_focal_file(
                        f, repos_root=repos_root, language=language
                    ),
                    all_focal_files,
                ),
                total=len(all_focal_files),
            )
        )
    nfocal, ncode = zip(*rnt)
    logging.info(
        f"Processed {sum(ncode)} have source code in {sum(nfocal)} focal functions"
    )


if __name__ == "__main__":
    fire.Fire(main)
