import json
import re
import requests
import time
import traceback
import logging
import tempfile
import subprocess
import os

from argparse import ArgumentTypeError
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from datasets import Dataset, load_dataset, load_from_disk
from dotenv import load_dotenv
from pathlib import Path
from tqdm import tqdm
from typing import cast
from swingarena.harness.constants.swing_constants import SwingbenchInstance

from unidiff import PatchSet
import threading
from queue import Queue
import socket

logger = logging.getLogger("agent_battle")
load_dotenv()

class PortPool:
    # Aborted paramter: `ports`
    def __init__(self, ports=None):
        pass

    def acquire_port(self):
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('', 0))
                port = sock.getsockname()[1]
                sock.close()
                print(f"Port {port} acquired")
                return port
            except Exception as e:
                print(f"Failed to acquire port: {e}, retrying...")
                time.sleep(0.1)

    def release_port(self, port):
        print(f"Port {port} released")


class EvaluationError(Exception):
    def __init__(self, instance_id, message, logger):
        super().__init__(message)
        self.instance_id = instance_id
        self.log_file = logger.log_file
        self.logger = logger

    def __str__(self):
        log_msg = traceback.format_exc()
        self.logger.info(log_msg)
        return (
            f"{self.instance_id}: {super().__str__()}\n"
            f"Check ({self.log_file}) for more information."
        )

# We assign [34000 ~ 38000] for ci running and 5 ports for each task
ports_per_instance = 10
port_start = 32000
concurrency = 40
available_group = [i for i in range(concurrency)]
used_ports = set()
mutex = threading.Lock()
condition = threading.Condition(mutex)

def get_ports(timeout=None):
    with condition:
        wait_start_time = time.time()
        while not available_group:
            if timeout is not None:
                elapsed = time.time() - wait_start_time
                if elapsed >= timeout:
                    raise RuntimeError(f"Timed out waiting for available port group after {timeout} seconds")
                condition.wait(timeout - elapsed)
            else:
                condition.wait()
                
        group_index = available_group.pop(0)
        start_port = port_start + group_index * ports_per_instance
        ports = list(range(start_port, start_port + ports_per_instance))
        used_ports.update(ports)        
        return ports

def release_ports(ports):
    with condition:
        for port in ports:
            if port in used_ports:
                used_ports.remove(port)
                
        if ports[0] >= port_start and (ports[0] - port_start) % ports_per_instance == 0:
            group_index = (ports[0] - port_start) // ports_per_instance
            if ports == list(range(ports[0], ports[0] + ports_per_instance)):
                available_group.append(group_index)
                condition.notify()
            else:
                raise ValueError("The group is not consequent")
        else:
            raise ValueError("Invalid port group")

def run_tasks(tasks, port_wait_timeout=None):
    """
    Run a function with a list of arguments concurrently with a specified concurrency level.
    """
    succeeded, failed = [], []
    pbar = tqdm(total=len(tasks), smoothing=0)
    effective_concurrency = min(concurrency, len(tasks))
    with ThreadPoolExecutor(max_workers=effective_concurrency) as executor:
        pending_tasks = list(tasks)
        running_futures = {}
        while pending_tasks and len(running_futures) < effective_concurrency:
            task = pending_tasks.pop(0)
            try:
                task_ports = get_ports(timeout=port_wait_timeout)
                future = executor.submit(task.run_ci, PortPool(task_ports))
                running_futures[future] = (task, task_ports)
            except RuntimeError as e:
                failed.append(task)
                pbar.update(1)
                print(f"Failed to get ports for task: {e}")
        
        while running_futures:
            done, _ = wait(
                running_futures.keys(),
                return_when=FIRST_COMPLETED
            )
            
            for future in done:
                task, task_ports = running_futures.pop(future)
                try:
                    [eval_result, previous_eval_result] = future.result()
                    succeeded.append(task)
                except Exception as e:
                    failed.append(task)
                    print(f"Task failed with exception: {e}")
                finally:
                    release_ports(task_ports)
                    pbar.update(1)
                
                if pending_tasks:
                    next_task = pending_tasks.pop(0)
                    try:
                        next_ports = get_ports(timeout=port_wait_timeout)
                        next_future = executor.submit(next_task.run_ci, PortPool(next_ports))
                        running_futures[next_future] = (next_task, next_ports)
                    except RuntimeError as e:
                        failed.append(next_task)
                        pbar.update(1)
                        print(f"Failed to get ports for task: {e}")

    pbar.close()
    return succeeded, failed


def load_swingbench_dataset_json(json_path: str) -> list[SwingbenchInstance]:
    instances = None
    with open(json_path, "r") as f:
        instances = [SwingbenchInstance(**json.loads(line)) for line in f]
    return instances


def load_swingbench_dataset(
    dataset_name: str,
    sub_dataset_identifier: str,
    split: str = None,
    with_ci: bool = False
) -> list[SwingbenchInstance]:
    multi_language_choice = False
    try:
        dataset = load_dataset(dataset_name, sub_dataset_identifier, split=split)
    except:
        # multi-language choice
        print(f'dataset_name: {dataset_name}, sub_dataset_identifier: {sub_dataset_identifier}, split: {split}')
        dataset = load_dataset(dataset_name, split=split)[sub_dataset_identifier]
        multi_language_choice = True
    instance_list = []
    if split is None:
        if multi_language_choice:
            for instance in dataset:    
                if with_ci and not instance['ci_name_list']:
                    continue
                instance_list.append(SwingbenchInstance(**instance))
        else:
            identifier = sub_dataset_identifier
            for instance in dataset[identifier]:    
                if with_ci and not instance['ci_name_list']:
                    continue
                instance_list.append(SwingbenchInstance(**instance))
    else:
        instance_list = [SwingbenchInstance(**instance) for instance in dataset]
    return instance_list


### MARK - Patch Correction
PATCH_PATTERN = re.compile(
    r"(?:diff[\w\_\.\ \/\-]+\n)?\-\-\-\s+a\/(?:.*?)\n\+\+\+\s+b\/(?:.*?)(?=diff\ |\-\-\-\ a\/|\Z)",
    re.DOTALL,
)
PATCH_FILE_PATTERN = re.compile(r"\-\-\-\s+a\/(?:.+)\n\+\+\+\s+b\/(?:.+)")
PATCH_HUNK_PATTERN = re.compile(
    r"\@\@\s+\-(\d+),(\d+)\s+\+(\d+),(\d+)\s+\@\@(.+?)(?=diff\ |\-\-\-\ a\/|\@\@\ \-|\Z)",
    re.DOTALL,
)


def get_first_idx(charlist):
    """Get index of first occurrence of "-" or "+" in charlist"""
    first_min = charlist.index("-") if "-" in charlist else len(charlist)
    first_plus = charlist.index("+") if "+" in charlist else len(charlist)
    return min(first_min, first_plus)


def get_last_idx(charlist):
    """Get index of last occurrence of "-" or "+" in charlist"""
    char_idx = get_first_idx(charlist[::-1])
    last_idx = len(charlist) - char_idx
    return last_idx + 1


def strip_content(hunk):
    """Remove trailing non +/- lines and trailing whitespace per line per hunk"""
    first_chars = list(map(lambda x: None if not len(x) else x[0], hunk.split("\n")))
    first_idx = get_first_idx(first_chars)
    last_idx = get_last_idx(first_chars)
    new_lines = list(map(lambda x: x.rstrip(), hunk.split("\n")[first_idx:last_idx]))
    # should leave one space for empty context lines
    new_lines = [line if line.strip() else " " for line in new_lines]
    new_hunk = "\n" + "\n".join(new_lines) + "\n"
    return new_hunk, first_idx - 1


def get_hunk_stats(pre_start, pre_len, post_start, post_len, hunk, total_delta):
    """Recalculate hunk start/end position and diff delta"""
    stats = {"context": 0, "added": 0, "subtracted": 0}
    hunk = hunk.split("\n", 1)[-1].strip("\n")
    for line in hunk.split("\n"):
        if line.startswith("-"):
            stats["subtracted"] += 1
        elif line.startswith("+"):
            stats["added"] += 1
        else:
            stats["context"] += 1
    context = stats["context"]
    added = stats["added"]
    subtracted = stats["subtracted"]
    pre_len = context + subtracted
    post_start = pre_start + total_delta
    post_len = context + added
    total_delta = total_delta + (post_len - pre_len)
    return pre_start, pre_len, post_start, post_len, total_delta


def extract_minimal_patch(model_patch):
    """
    Wrapper function that takes hunk and
    * Removes trailing non +/- lines and trailing whitespace per line per hunk
    * Recalculates hunk start/end position and diff delta
    * Returns new patch
    """
    model_patch = model_patch.lstrip("\n")
    new_patch = ""
    for patch in PATCH_PATTERN.findall(model_patch):
        total_delta = 0
        patch_header = PATCH_FILE_PATTERN.findall(patch)[0]
        if patch_header:
            new_patch += patch_header + "\n"
        for hunk in PATCH_HUNK_PATTERN.findall(patch):
            pre_start, pre_len, post_start, post_len, content = hunk
            pre_start, pre_len, post_start, post_len, content = list(
                map(lambda x: int(x) if x.isnumeric() else x, hunk)
            )
            content, adjust_pre_start = strip_content(content)
            pre_start += adjust_pre_start
            pre_start, pre_len, post_start, post_len, total_delta = get_hunk_stats(
                pre_start, pre_len, post_start, post_len, content, total_delta
            )
            new_patch += (
                f"@@ -{pre_start},{pre_len} +{post_start},{post_len} @@{content}"
            )
    return new_patch


def has_attribute_or_import_error(log_before):
    """
    Check to see if Attribute/Import-prefix is in log text

    Args:
        log_before (str): Validation log text before patch application
    """
    log_before = log_before.lower()

    if any([x in log_before for x in ["attribute", "import"]]):

        def get_lines_with_word(text, target_word):
            # Function to extract line(s) that contains target_word
            text, target_word = text.lower(), target_word.lower()
            lines, hits = text.split("\n")[::-1], []
            for line in lines:
                if target_word in line:
                    hits.append(line)
            return hits

        # Get line with Attribute/Import error
        lines_1 = get_lines_with_word(log_before, "attribute")
        lines_2 = get_lines_with_word(log_before, "import")
        lines_1 = " ".join(lines_1)
        lines_2 = " ".join(lines_2)

        if any([(x in lines_1 or x in lines_2) for x in ["error", "fail"]]):
            return True
    return False


def str2bool(v):
    """
    Minor helper function to convert string to boolean
    """
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise ArgumentTypeError("Boolean value expected.")


def get_repo_file(repo, commit, filepath):
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{filepath}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None
    except:
        return None


def get_modified_files(patch: str) -> list[str]:
    """
    Get the list of modified files in a patch
    """
    source_files = []
    for file in PatchSet(patch):
        if file.source_file != "/dev/null":
            source_files.append(file.source_file)
    source_files = [x[2:] for x in source_files if x.startswith("a/")]
    return source_files


def merge_two_diffs(diff1: str, diff2: str) -> str:
    if not diff1 and not diff2:
        return ""
    if not diff1:
        return diff2
    if not diff2:
        return diff1
    
    file_path1 = None
    file_path2 = None
    
    match1 = re.search(r'diff --git a/(.*?) b/', diff1)
    if match1:
        file_path1 = match1.group(1)
    
    match2 = re.search(r'diff --git a/(.*?) b/', diff2)
    if match2:
        file_path2 = match2.group(1)
    
    if file_path1 and file_path2 and file_path1 != file_path2:
        return diff1 + "\n" + diff2
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run("git init -b main -q", shell=True, cwd=tmp_dir)
        subprocess.run("git config user.name 'test'", shell=True, cwd=tmp_dir)
        subprocess.run("git config user.email 'test@example.com'", shell=True, cwd=tmp_dir)
        
        subprocess.run("git commit --allow-empty -m 'initial commit'", shell=True, cwd=tmp_dir)
        
        file_path = file_path1 or file_path2 or "unknown_file"
        
        file_dir = os.path.dirname(file_path)
        if file_dir:
            os.makedirs(os.path.join(tmp_dir, file_dir), exist_ok=True)
        
        file_path_in_tmp = os.path.join(tmp_dir, file_path)
        with open(file_path_in_tmp, "w") as f:
            f.write("")
        
        subprocess.run(f"git add {file_path}", shell=True, cwd=tmp_dir)
        subprocess.run("git commit -m 'add empty file'", shell=True, cwd=tmp_dir)
        
        with open(os.path.join(tmp_dir, "patch1.diff"), "w") as f:
            f.write(diff1)
        
        subprocess.run("git apply patch1.diff", shell=True, cwd=tmp_dir)
        subprocess.run(f"git add {file_path}", shell=True, cwd=tmp_dir)
        subprocess.run("git commit -m 'apply first diff'", shell=True, cwd=tmp_dir)
        
        with open(os.path.join(tmp_dir, "patch2.diff"), "w") as f:
            f.write(diff2)
        
        subprocess.run("git apply patch2.diff", shell=True, cwd=tmp_dir)
        subprocess.run(f"git add {file_path}", shell=True, cwd=tmp_dir)
        subprocess.run("git commit -m 'apply second diff'", shell=True, cwd=tmp_dir)
        
        result = subprocess.run(
            "git diff HEAD~2", 
            shell=True, 
            capture_output=True,
            cwd=tmp_dir
        )
        merged_diff = result.stdout.decode("utf-8")
        
        return merged_diff


def merge_diffs(lhs: dict, rhs: dict) -> str:
    result_patch = ''
    for key in lhs.keys():
        result_patch = merge_two_diffs(result_patch, lhs[key])
    for key in rhs.keys():
        result_patch = merge_two_diffs(result_patch, rhs[key])
    return result_patch


def extract_file_list_from_diff(diff_str: str) -> list[str]:
    """
    Extract the modified file from a diff string
    
    Args:
        diff_str (str): The diff string to extract modified files from
        
    Returns:
        list[str]: List of modified file paths
    """
    modified_files = []
    pattern = r'diff --git a/(.*?) b/'
    matches = re.findall(pattern, diff_str)
    
    for match in matches:
        if match not in modified_files:
            modified_files.append(match)
    
    return modified_files


if __name__ == "__main__":
    diff_1 = 'diff --git a/tests/tap_test.rs b/tests/tap_test.rs\nindex e69de29..a43a653 100644\n--- a/tests/tap_test.rs\n+++ b/tests/tap_test.rs\n@@ -0,0 +1,104 @@\n+use rustzx_core::zx::tape::tap::Tap;\n+use rustzx_core::host::LoadableAsset;\n+use std::io::Cursor;\n+\n+#[test]\n+fn test_empty_file() {\n+    let asset = Cursor::new(Vec::new());\n+    let tap = Tap::from_asset(asset).unwrap();\n+    assert!(tap.data.is_empty());\n+}\n+use rustzx_core::zx::tape::tap::Tap;\n+use rustzx_core::host::LoadableAsset;\n+use std::io::Cursor;\n+\n+#[test]\n+fn test_single_chunk_file() {\n+    let data = vec![0x01, 0x02, 0x03];\n+    let asset = Cursor::new(data.clone());\n+    let tap = Tap::from_asset(asset).unwrap();\n+    assert_eq!(tap.data, data);\n+}\n+use rustzx_core::zx::tape::tap::Tap;\n+use rustzx_core::host::LoadableAsset;\n+use std::io::Cursor;\n+\n+#[test]\n+fn test_multiple_chunks_file() {\n+    let data = vec![0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08];\n+    let asset = Cursor::new(data.clone());\n+    let tap = Tap::from_asset(asset).unwrap();\n+    assert_eq!(tap.data, data);\n+}\n+use rustzx_core::zx::tape::tap::Tap;\n+use rustzx_core::host::LoadableAsset;\n+use std::io::{Cursor, Error, ErrorKind};\n+\n+struct ErrorAsset;\n+impl LoadableAsset for ErrorAsset {\n+    fn read(&mut self, _buf: &mut [u8]) -> std::io::Result<usize> {\n+        Err(Error::new(ErrorKind::Other, "Read error"))\n+    }\n+}\n+\n+#[test]\n+fn test_read_error() {\n+    let asset = ErrorAsset;\n+    let result = Tap::from_asset(asset);\n+    assert!(result.is_err());\n+}\n+use rustzx_core::zx::tape::tap::Tap;\n+use rustzx_core::host::LoadableAsset;\n+use std::io::Cursor;\n+\n+#[test]\n+fn test_large_file() {\n+    let data = vec![0x01; 1024 * 1024];\n+    let asset = Cursor::new(data.clone());\n+    let tap = Tap::from_asset(asset).unwrap();\n+    assert_eq!(tap.data, data);\n+}\n+use rustzx_core::zx::tape::tap::Tap;\n+use rustzx_core::host::LoadableAsset;\n+use std::io::Cursor;\n+\n+#[test]\n+fn test_file_with_zero_length_chunk() {\n+    let data = vec![0x01, 0x00, 0x02];\n+    let asset = Cursor::new(data.clone());\n+    let tap = Tap::from_asset(asset).unwrap();\n+    assert_eq!(tap.data, vec![0x01, 0x02]);\n+}\n+use rustzx_core::zx::tape::tap::Tap;\n+use rustzx_core::host::LoadableAsset;\n+use std::io::Cursor;\n+\n+#[test]\n+fn test_file_with_multiple_zero_length_chunks() {\n+    let data = vec![0x01, 0x00, 0x00, 0x02];\n+    let asset = Cursor::new(data.clone());\n+    let tap = Tap::from_asset(asset).unwrap();\n+    assert_eq!(tap.data, vec![0x01, 0x02]);\n+}\n+use rustzx_core::zx::tape::tap::Tap;\n+use rustzx_core::host::LoadableAsset;\n+use std::io::Cursor;\n+\n+#[test]\n+fn test_file_with_large_zero_length_chunk() {\n+    let data = vec![0x01, 0x00; 1024 * 1024, 0x02];\n+    let asset = Cursor::new(data.clone());\n+    let tap = Tap::from_asset(asset).unwrap();\n+    assert_eq!(tap.data, vec![0x01, 0x02]);\n+}\n+use rustzx_core::zx::tape::tap::Tap;\n+use rustzx_core::host::LoadableAsset;\n+use std::io::Cursor;\n+\n+#[test]\n+fn test_file_with_large_zero_length_chunks() {\n+    let data = vec![0x01, 0x00; 1024 * 1024, 0x00, 0x00, 0x02];\n+    let asset = Cursor::new(data.clone());\n+    let tap = Tap::from_asset(asset).unwrap();\n+    assert_eq!(tap.data, vec![0x01, 0x02]);\n+}\n\\ No newline at end of file\n'
    
    diff_2 = 'diff --git a/rustzx-core/src/zx/tape/tap.rs b/rustzx-core/src/zx/tape/tap.rs\nindex feaa5e7..d03d2f2 100644\n--- a/rustzx-core/src/zx/tape/tap.rs\n+++ b/rustzx-core/src/zx/tape/tap.rs\n@@ -84,11 +84,13 @@ impl Tap {\n \n         let mut tap = Self::default();\n \n-        let mut buffer = [0u8; 1024];\n-        let mut read_bytes = asset.read(&mut buffer)?;\n-        while read_bytes != 0 {\n-            tap.data.extend_from_slice(&buffer[0..read_bytes]);\n+        let mut read_bytes;\n+        loop {\n             read_bytes = asset.read(&mut buffer)?;\n+            if read_bytes == 0 {\n+                break;\n+            }\n+            tap.data.extend_from_slice(&buffer[0..read_bytes]);\n         }\n \n         tap.block_info.clear();\n'
    
    # print(merge_two_diffs(diff_1, diff_2))
    # print(extract_file_list_from_diff(diff_1))
    
    # print(len(load_swingbench_dataset('/mnt/Data/wdxu/github/Swing-Bench/tmpdata/SwingBench', 'Rust', True)))
