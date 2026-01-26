from __future__ import annotations

import platform
import shutil
import os
import logging
import time
import sys
from datetime import datetime
import json
import concurrent.futures
from typing import Optional, List, Dict, Any

if platform.system() == "Linux":
    import resource

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from pathlib import Path

from swingarena.harness.constants import (
    KEY_INSTANCE_ID,
)

from swingarena.harness.router import ActCITool, CargoCITool
from swingarena.harness.utils import (
    load_swebench_dataset,
    get_predictions_from_file,
    PortPool,
    run_tasks
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("evaluation.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("evaluation")

GIT_APPLY_CMDS = [
    "git apply --verbose",
    "git apply --verbose --reject",
    "patch --batch --fuzz=5 -p1 -i",
]

def run_instance(
    instance: Dict[str, Any],
    timeout: int,
    target_dir: str,
    logs_dir: str,
    apply_patch: bool,
    src_folder: str = "/raid/rust-repos",
    ci_tool: str = "act",
    log_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run a single instance.

    Args:
        instance: Instance data
        timeout: Timeout in seconds
        target_dir: Directory to clone/copy repo to
        logs_dir: Directory to write logs to
        apply_patch: Whether to apply patch during evaluation
        src_folder: Source folder for Rust repositories
        ci_tool: CI tool to use ("act" or "cargo")
        log_file: Path to log file (if None, one will be created)

    Returns:
        Dictionary containing test results
    """
    instance_id = instance["instance_id"]
    repo = instance["repo"]
    logger.info(f"Processing instance {instance_id} for repo {repo}")
    
    # Create log file path if not provided
    if log_file is None:
        log_file = os.path.join(logs_dir, f"{instance_id}.log")
    
    try:
        start_time = time.time()
        
        if ci_tool == "cargo":
            logger.info(f"Using CargoCITool for instance {instance_id}")
            # Use CargoCITool for Cargo projects
            cargo = CargoCITool({
                "instance_id": instance_id,
                "repo": repo,
                "base_commit": instance.get("base_commit"),
                "merge_commit": instance.get("merge_commit_sha"),
                "patch": instance.get("patch"),
                "workdir": f"{target_dir}/{instance_id}",  # Use instance-specific directory
                "output_dir": logs_dir,
                "apply_patch": apply_patch,
                "src_folder": src_folder
            })
            # Pass log_file as argument to run_ci
            result = cargo.run_ci(log_file)
        else:
            logger.info(f"Using ActCITool for instance {instance_id}")
            # Find act executable
            act_path = shutil.which("act")
            if act_path is None:
                raise FileNotFoundError("'act' not found in system PATH")
                
            # Create PortPool object for ActCITool
            port_pool = PortPool(3000, 4000)
            # Use ActCITool by default
            act = ActCITool({
                "act_path": act_path,
                "instance_id": instance_id,
                "repo": repo,
                "base_commit": instance.get("base_commit"),
                "merge_commit": instance.get("merge_commit_sha"),
                "patch": instance.get("patch"),
                "ci_name_list": instance.get("ci_name_list", []),
                "workdir": f"{target_dir}/{instance_id}",  # Use instance-specific directory
                "output_dir": logs_dir,
                "apply_patch": apply_patch,
                "src_folder":src_folder
            })
            # Pass port_pool object to ActCITool's run_ci method
            result = act.run_ci(port_pool)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Instance {instance_id} completed in {elapsed_time:.2f}s")
        
        # Add metadata to result
        result["instance_id"] = instance_id
        result["repo"] = repo
        result["elapsed_time"] = elapsed_time
        result["log_file"] = os.path.relpath(log_file, os.path.dirname(logs_dir))
        result["timestamp"] = datetime.now().isoformat()
        
        return result
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Failed to process instance {instance_id}: {str(e)}")
        
        # Record error to log file
        with open(log_file, "w") as f:
            f.write(f"Failed to process instance {instance_id}: {str(e)}")
        
        return {
            "instance_id": instance_id,
            "repo": repo,
            "returncode": 1,
            "error": str(e),
            "elapsed_time": elapsed_time,
            "log_file": os.path.relpath(log_file, os.path.dirname(logs_dir)),
            "timestamp": datetime.now().isoformat(),
            "test_results": {"passed": [], "failed": [], "ignored": [], "failure_details": {}}
        }

def run_instances(
    instances: List[Dict[str, Any]],
    timeout: int,
    target_dir: str,
    report_dir: str,
    apply_patch: bool,
    src_folder: str = "/raid/rust-repos",
    ci_tool: str = "act",
    concurrent_workers: int = 1,
    start_index: int = 0,
    max_instances: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Run multiple instances with optional concurrency.

    Args:
        instances: List of instances
        timeout: Timeout in seconds
        target_dir: Directory to clone/copy repo to
        report_dir: Directory to write reports to
        apply_patch: Whether to apply patch during evaluation
        src_folder: Source folder for Rust repositories
        ci_tool: CI tool to use ("act" or "cargo")
        concurrent_workers: Number of concurrent workers
        start_index: Index of first instance to process
        max_instances: Maximum number of instances to process

    Returns:
        List of dictionaries containing test results
    """
    # Create timestamp directory to organize results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(report_dir, timestamp)
    logs_dir = os.path.join(run_dir, "logs")
    
    # Create output directories
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(target_dir, exist_ok=True)
    
    # Path for unified evaluation results
    evaluation_jsonl = os.path.join(run_dir, "evaluation.jsonl")
    
    logger.info(f"Saving results to {run_dir}")
    logger.info(f"Logs will be stored in {logs_dir}")
    
    # Select instances to process
    if start_index >= len(instances):
        logger.warning(f"Start index {start_index} exceeds number of instances {len(instances)}")
        return []
    
    end_index = len(instances)
    if max_instances is not None:
        end_index = min(start_index + max_instances, len(instances))
    
    selected_instances = instances[start_index:end_index]
    logger.info(f"Processing {len(selected_instances)} instances (from index {start_index} to {end_index-1})")
    
    # Function to run instance and write result to evaluation.jsonl
    def process_instance(instance):
        instance_id = instance["instance_id"]
        log_file = os.path.join(logs_dir, f"{instance_id}.log")
        
        result = run_instance(
            instance,
            timeout,
            target_dir,
            logs_dir,
            apply_patch,
            src_folder,
            ci_tool,
            log_file
        )
        
        # Write result to the evaluation.jsonl file (with lock to prevent concurrent writes)
        with open(evaluation_jsonl, 'a') as f:
            f.write(json.dumps(result) + '\n')
            
        return result
    
    results = []
    
    # Use sequential execution if concurrent_workers is 1
    if concurrent_workers <= 1:
        logger.info("Running instances sequentially")
        for instance in selected_instances:
            results.append(process_instance(instance))
    else:
        # Use concurrent execution with ThreadPoolExecutor
        logger.info(f"Running instances concurrently with {concurrent_workers} workers")
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
            future_to_instance = {
                executor.submit(process_instance, instance): instance 
                for instance in selected_instances
            }
            
            for future in concurrent.futures.as_completed(future_to_instance):
                instance = future_to_instance[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    instance_id = instance["instance_id"]
                    logger.error(f"Instance {instance_id} generated an exception: {exc}")
    
    logger.info(f"Processed {len(results)} instances. Results saved to {evaluation_jsonl}")
    return results

def get_dataset_from_preds(
    dataset_name: str,
    split: str,
    instance_ids: list,
    predictions: dict,
    exclude_completed: bool = True,
):
    """
    Return only instances that have predictions and are in the dataset.
    If instance_ids is provided, only return instances with those IDs.
    If exclude_completed is True, only return instances that have not been run yet.
    """
    # load dataset
    logger.info(f"Loading dataset {dataset_name} ({split} split)")
    dataset = load_swebench_dataset(dataset_name, split)
    dataset_ids = {i[KEY_INSTANCE_ID] for i in dataset}
    logger.info(f"Dataset contains {len(dataset)} instances")

    if instance_ids:
        # check that all instance IDs have predictions
        missing_preds = set(instance_ids) - set(predictions.keys())
        if missing_preds:
            logger.warning(f"Missing predictions for {len(missing_preds)} instance IDs")

    # check that all prediction IDs are in the dataset
    prediction_ids = set(predictions.keys())
    overlap_ids = prediction_ids.intersection(dataset_ids)
    logger.info(f"Found predictions for {len(overlap_ids)} instances in the dataset")
    
    if instance_ids:
        dataset = [i for i in dataset if i[KEY_INSTANCE_ID] in instance_ids]
        logger.info(f"Filtered to {len(dataset)} instances based on provided instance IDs")

    # TODO: check which instance IDs have already been run
    completed_ids = set()
    
    if completed_ids and exclude_completed:
        # filter dataset to only instances that have not been run
        logger.info(f"{len(completed_ids)} instances already run, skipping...")
        dataset = [i for i in dataset if i[KEY_INSTANCE_ID] not in completed_ids]

    empty_patch_ids = {
        k
        for k, v in predictions.items()
        if v.get("test_patch") == "" or v.get("test_patch") is None
    }
    logger.info(f"Found {len(empty_patch_ids)} instances with empty test patches")

    # filter dataset to only instances with predictions
    dataset = [
        i
        for i in dataset
        if i[KEY_INSTANCE_ID] in prediction_ids
        and i["test_patch"] not in empty_patch_ids
    ]
    
    # filter out dataset with test cases
    dataset = [d for d in dataset if d['test_patch']]
    logger.info(f'Final dataset contains {len(dataset)} instances with test patches')
    return dataset


def main(
    dataset_name: str,
    split: str,
    instance_ids: list,
    predictions_path: str,
    open_file_limit: int,
    timeout: int,
    target_dir: str = "./testbed",
    report_dir: str = "./report",
    apply_patch: bool = False,
    src_folder: str = "/raid/rust-repos",
    ci_tool: str = "act",
    concurrent_workers: int = 1,
    start_index: int = 0,
    max_instances: Optional[int] = None,
):
    """
    Run evaluation harness for the given dataset and predictions.
    """
    logger.info(f"Starting evaluation with ci_tool={ci_tool}, src_folder={src_folder}, concurrent_workers={concurrent_workers}")
    logger.info(f"Processing {dataset_name} ({split} split)")

    if dataset_name == "princeton-nlp/SWE-bench_Multimodal" and split == "test":
        logger.warning(
            "⚠️ Local evaluation for the test split of SWE-bench Multimodal is not supported. "
            "Please check out sb-cli (https://github.com/swe-bench/sb-cli/) for instructions on how to submit predictions."
        )
        return
    
    # Create target directory if it doesn't exist
    expanded_path = os.path.expanduser(target_dir)
    Path(expanded_path).mkdir(parents=True, exist_ok=True)
    
    # Create base report directory if it doesn't exist
    expanded_path = os.path.expanduser(report_dir)
    Path(expanded_path).mkdir(parents=True, exist_ok=True)

    # Load predictions
    logger.info(f"Loading predictions from {predictions_path}")
    predictions = get_predictions_from_file(predictions_path, dataset_name, split)
    predictions = {pred[KEY_INSTANCE_ID]: pred for pred in predictions}
    logger.info(f"Loaded {len(predictions)} predictions")
    
    # Get dataset
    dataset = get_dataset_from_preds(
        dataset_name, split, instance_ids, predictions,
    )

    if platform.system() == "Linux":
        logger.info(f"Setting open file limit to {open_file_limit}")
        resource.setrlimit(resource.RLIMIT_NOFILE, (open_file_limit, open_file_limit))

    if not dataset:
        logger.warning("No instances to run.")
    else:
        run_instances(
            dataset,
            timeout,
            target_dir,
            report_dir,
            apply_patch,
            src_folder,
            ci_tool,
            concurrent_workers,
            start_index,
            max_instances
        )

if __name__ == "__main__":
    parser = ArgumentParser(
        description="Run evaluation harness for the given dataset and predictions.",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    
    parser.add_argument(
        "--apply_patch",
        help="Whether to apply patch during evaluation",
        action="store_true",
    )

    # Common args
    parser.add_argument(
        "--dataset_name",
        default="results/scikit-learn-task-instances.jsonl",
        type=str,
        help="Name of dataset or path to JSON file.",
    )
    parser.add_argument(
        "--split", type=str, default="test", help="Split of the dataset"
    )
    parser.add_argument(
        "--instance_ids",
        nargs="+",
        type=str,
        help="Instance IDs to run (space separated)",
    )
    parser.add_argument(
        "--predictions_path",
        default="results/scikit-learn-task-instances.jsonl",
        type=str,
        help="Path to predictions file - if 'gold', uses gold predictions",
    )

    # Local execution args
    parser.add_argument(
        "--open_file_limit", type=int, default=4096, help="Open file limit"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout (in seconds) for running tests for each instance",
    )
    parser.add_argument(
        "--report_dir", type=str, default="./report", help="Directory to write reports to"
    )
    parser.add_argument(
        "--target_dir", type=str, default="./testbed", help="Directory to clone repo to"
    )
    parser.add_argument(
        "--src_folder", 
        type=str, 
        default="/raid/rust-repos", 
        help="Source folder containing Rust repositories"
    )
    parser.add_argument(
        "--ci_tool",
        type=str,
        choices=["act", "cargo"],
        default="act",
        help="CI tool to use for testing (act or cargo)"
    )
    parser.add_argument(
        "--concurrent_workers",
        type=int,
        default=1,
        help="Number of concurrent workers (1 means sequential execution)"
    )
    parser.add_argument(
        "--start_index",
        type=int,
        default=0,
        help="Index of first instance to process"
    )
    parser.add_argument(
        "--max_instances",
        type=int,
        default=None,
        help="Maximum number of instances to process"
    )

    args = parser.parse_args()
    main(**vars(args))

# Example usage:
# python -m swebench.harness.run_evaluation \
#     --dataset_name SwingBench/SWE-Rust \
#     --split train \
#     --src_folder /home/hrwang/rust-repos \
#     --predictions_path swe-rust.json \
#     --ci_tool cargo \
#     --start_index 0 \
#     --max_instances 5 \
#     --concurrent_workers 3


# from __future__ import annotations

# import platform
# import shutil
# import os
# import logging
# import time
# import sys
# from datetime import datetime
# import json

# if platform.system() == "Linux":
#     import resource

# from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
# from pathlib import Path
# from typing import Optional, List, Dict, Any



# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("evaluation.log"),
#         logging.StreamHandler(sys.stdout)
#     ]
# )
# logger = logging.getLogger("evaluation")

# GIT_APPLY_CMDS = [
#     "git apply --verbose",
#     "git apply --verbose --reject",
#     "patch --batch --fuzz=5 -p1 -i",
# ]

# def run_instance(
#     instance: Dict[str, Any],
#     timeout: int,
#     target_dir: str,
#     logs_dir: str,
#     apply_patch: bool,
#     src_folder: str = "/raid/rust-repos",
#     ci_tool: str = "act",
#     log_file: Optional[str] = None
# ) -> Dict[str, Any]:
#     """
#     Run a single instance.

#     Args:
#         instance: Instance data
#         timeout: Timeout in seconds
#         target_dir: Directory to clone/copy repo to
#         logs_dir: Directory to write logs to
#         apply_patch: Whether to apply patch during evaluation
#         src_folder: Source folder for Rust repositories
#         ci_tool: CI tool to use ("act" or "cargo")
#         log_file: Path to log file (if None, one will be created)

#     Returns:
#         Dictionary containing test results
#     """
#     instance_id = instance["instance_id"]
#     repo = instance["repo"]
#     logger.info(f"Processing instance {instance_id} for repo {repo}")
    
#     # Create log file path if not provided
#     if log_file is None:
#         log_file = os.path.join(logs_dir, f"{instance_id}.log")
    
#     try:
#         start_time = time.time()
        
#         if ci_tool == "cargo":
#             logger.info(f"Using CargoCITool for instance {instance_id}")
#             # Use CargoCITool for Cargo projects
#             cargo = CargoCITool({
#                 "id": instance_id,
#                 "repo": repo,
#                 "base_commit": instance.get("base_commit"),
#                 "merge_commit": instance.get("merge_commit_sha"),
#                 "patch": instance.get("patch"),
#                 "workdir": target_dir,
#                 "output_dir": logs_dir,
#                 "apply_patch": apply_patch,
#                 "src_folder": src_folder
#             })
#             # Pass log_file as argument to run_ci
#             result = cargo.run_ci(log_file)
#         else:
#             logger.info(f"Using ActCITool for instance {instance_id}")
#             # Find act executable
#             act_path = shutil.which("act")
#             if act_path is None:
#                 raise FileNotFoundError("'act' not found in system PATH")
                
#             # Create PortPool object for ActCITool
#             port_pool = PortPool(3000, 4000)
#             # Use ActCITool by default
#             act = ActCITool({
#                 "act_path": act_path,
#                 "id": instance_id,
#                 "repo": repo,
#                 "base_commit": instance.get("base_commit"),
#                 "merge_commit": instance.get("merge_commit_sha"),
#                 "patch": instance.get("patch"),
#                 "ci_name_list": instance.get("ci_name_list", []),
#                 "workdir": target_dir,
#                 "output_dir": logs_dir,
#                 "apply_patch": apply_patch
#             })
#             # Pass port_pool object to ActCITool's run_ci method
#             result = act.run_ci(port_pool)
        
#         elapsed_time = time.time() - start_time
#         logger.info(f"Instance {instance_id} completed in {elapsed_time:.2f}s")
        
#         # Add metadata to result
#         result["instance_id"] = instance_id
#         result["repo"] = repo
#         result["elapsed_time"] = elapsed_time
#         result["log_file"] = os.path.relpath(log_file, os.path.dirname(logs_dir))
#         result["timestamp"] = datetime.now().isoformat()
        
#         return result
#     except Exception as e:
#         elapsed_time = time.time() - start_time
#         logger.error(f"Failed to process instance {instance_id}: {str(e)}")
        
#         # Record error to log file
#         with open(log_file, "w") as f:
#             f.write(f"Failed to process instance {instance_id}: {str(e)}")
        
#         return {
#             "instance_id": instance_id,
#             "repo": repo,
#             "returncode": 1,
#             "error": str(e),
#             "elapsed_time": elapsed_time,
#             "log_file": os.path.relpath(log_file, os.path.dirname(logs_dir)),
#             "timestamp": datetime.now().isoformat(),
#             "test_results": {"passed": [], "failed": [], "ignored": [], "failure_details": {}}
#         }

# def run_instances(
#     instances: List[Dict[str, Any]],
#     timeout: int,
#     target_dir: str,
#     report_dir: str,
#     apply_patch: bool,
#     src_folder: str = "/raid/rust-repos",
#     ci_tool: str = "act",
#     batch_size: Optional[int] = None,
#     start_index: int = 0,
#     max_instances: Optional[int] = None
# ) -> List[Dict[str, Any]]:
#     """
#     Run multiple instances.

#     Args:
#         instances: List of instances
#         timeout: Timeout in seconds
#         target_dir: Directory to clone/copy repo to
#         report_dir: Directory to write reports to
#         apply_patch: Whether to apply patch during evaluation
#         src_folder: Source folder for Rust repositories
#         ci_tool: CI tool to use ("act" or "cargo")
#         batch_size: Number of instances to process in each batch
#         start_index: Index of first instance to process
#         max_instances: Maximum number of instances to process

#     Returns:
#         List of dictionaries containing test results
#     """
#     # Create timestamp directory to organize results
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     run_dir = os.path.join(report_dir, timestamp)
#     logs_dir = os.path.join(run_dir, "logs")
    
#     # Create output directories
#     os.makedirs(run_dir, exist_ok=True)
#     os.makedirs(logs_dir, exist_ok=True)
    
#     # Path for unified evaluation results
#     evaluation_jsonl = os.path.join(run_dir, "evaluation.jsonl")
    
#     logger.info(f"Saving results to {run_dir}")
#     logger.info(f"Logs will be stored in {logs_dir}")
    
#     # Select instances to process
#     if start_index >= len(instances):
#         logger.warning(f"Start index {start_index} exceeds number of instances {len(instances)}")
#         return []
    
#     end_index = len(instances)
#     if max_instances is not None:
#         end_index = min(start_index + max_instances, len(instances))
    
#     selected_instances = instances[start_index:end_index]
#     logger.info(f"Processing {len(selected_instances)} instances (from index {start_index} to {end_index-1})")
    
#     results = []
    
#     # Process instances in batches if batch_size is specified
#     if batch_size is not None and batch_size > 0:
#         batch_count = (len(selected_instances) + batch_size - 1) // batch_size
#         logger.info(f"Processing in {batch_count} batches of size {batch_size}")
        
#         for batch_index in range(batch_count):
#             batch_start = batch_index * batch_size
#             batch_end = min(batch_start + batch_size, len(selected_instances))
#             batch = selected_instances[batch_start:batch_end]
            
#             logger.info(f"Processing batch {batch_index+1}/{batch_count} with {len(batch)} instances")
            
#             for instance in batch:
#                 # Create log file path in the logs directory
#                 instance_id = instance["instance_id"]
#                 log_file = os.path.join(logs_dir, f"{instance_id}.log")
                
#                 result = run_instance(
#                     instance,
#                     timeout,
#                     target_dir,
#                     logs_dir,  # Pass logs_dir instead of report_dir
#                     apply_patch,
#                     src_folder,
#                     ci_tool,
#                     log_file  # Pass explicit log_file path
#                 )
#                 results.append(result)
                
#                 # Append result to the evaluation.jsonl file
#                 with open(evaluation_jsonl, 'a') as f:
#                     f.write(json.dumps(result) + '\n')
#     else:
#         # Process all selected instances sequentially
#         for instance in selected_instances:
#             # Create log file path in the logs directory
#             instance_id = instance["instance_id"]
#             log_file = os.path.join(logs_dir, f"{instance_id}.log")
            
#             result = run_instance(
#                 instance,
#                 timeout,
#                 target_dir,
#                 logs_dir,  # Pass logs_dir instead of report_dir
#                 apply_patch,
#                 src_folder,
#                 ci_tool,
#                 log_file  # Pass explicit log_file path
#             )
#             results.append(result)
            
#             # Append result to the evaluation.jsonl file
#             with open(evaluation_jsonl, 'a') as f:
#                 f.write(json.dumps(result) + '\n')
    
#     logger.info(f"Processed {len(results)} instances. Results saved to {evaluation_jsonl}")
#     return results

# def get_dataset_from_preds(
#     dataset_name: str,
#     split: str,
#     instance_ids: list,
#     predictions: dict,
#     exclude_completed: bool = True,
# ):
#     """
#     Return only instances that have predictions and are in the dataset.
#     If instance_ids is provided, only return instances with those IDs.
#     If exclude_completed is True, only return instances that have not been run yet.
#     """
#     # load dataset
#     logger.info(f"Loading dataset {dataset_name} ({split} split)")
#     dataset = load_swebench_dataset(dataset_name, split)
#     dataset = [i for i in dataset if os.path.exists(f'/home/hrwang/rust-repos/{i["repo"].replace("/", "__")}')]
#     dataset_ids = {i[KEY_INSTANCE_ID] for i in dataset}
#     logger.info(f"Dataset contains {len(dataset)} instances")

#     if instance_ids:
#         # check that all instance IDs have predictions
#         missing_preds = set(instance_ids) - set(predictions.keys())
#         if missing_preds:
#             logger.warning(f"Missing predictions for {len(missing_preds)} instance IDs")

#     # check that all prediction IDs are in the dataset
#     prediction_ids = set(predictions.keys())
#     overlap_ids = prediction_ids.intersection(dataset_ids)
#     logger.info(f"Found predictions for {len(overlap_ids)} instances in the dataset")
    
#     if instance_ids:
#         dataset = [i for i in dataset if i[KEY_INSTANCE_ID] in instance_ids]
#         logger.info(f"Filtered to {len(dataset)} instances based on provided instance IDs")

#     # TODO: check which instance IDs have already been run
#     completed_ids = set()
    
#     if completed_ids and exclude_completed:
#         # filter dataset to only instances that have not been run
#         logger.info(f"{len(completed_ids)} instances already run, skipping...")
#         dataset = [i for i in dataset if i[KEY_INSTANCE_ID] not in completed_ids]

#     empty_patch_ids = {
#         k
#         for k, v in predictions.items()
#         if v["test_patch"] == "" or v["test_patch"] is None
#     }
#     logger.info(f"Found {len(empty_patch_ids)} instances with empty test patches")

#     # filter dataset to only instances with predictions
#     dataset = [
#         i
#         for i in dataset
#         if i[KEY_INSTANCE_ID] in prediction_ids
#         and i["test_patch"] not in empty_patch_ids
#     ]
    
#     # filter out dataset with test cases
#     dataset = [d for d in dataset if d['test_patch']]
#     logger.info(f'Final dataset contains {len(dataset)} instances with test patches')
#     return dataset


# def main(
#     dataset_name: str,
#     split: str,
#     instance_ids: list,
#     predictions_path: str,
#     open_file_limit: int,
#     timeout: int,
#     target_dir: str = "./testbed",
#     report_dir: str = "./report",
#     apply_patch: bool = False,
#     src_folder: str = "/raid/rust-repos",
#     ci_tool: str = "act",
#     batch_size: Optional[int] = None,
#     start_index: int = 0,
#     max_instances: Optional[int] = None,
# ):
#     """
#     Run evaluation harness for the given dataset and predictions.
#     """
#     logger.info(f"Starting evaluation with ci_tool={ci_tool}, src_folder={src_folder}")
#     logger.info(f"Processing {dataset_name} ({split} split)")

#     if dataset_name == "princeton-nlp/SWE-bench_Multimodal" and split == "test":
#         logger.warning(
#             "⚠️ Local evaluation for the test split of SWE-bench Multimodal is not supported. "
#             "Please check out sb-cli (https://github.com/swe-bench/sb-cli/) for instructions on how to submit predictions."
#         )
#         return
    
#     # Create target directory if it doesn't exist
#     expanded_path = os.path.expanduser(target_dir)
#     Path(expanded_path).mkdir(parents=True, exist_ok=True)
    
#     # Create base report directory if it doesn't exist
#     expanded_path = os.path.expanduser(report_dir)
#     Path(expanded_path).mkdir(parents=True, exist_ok=True)

#     # Load predictions
#     logger.info(f"Loading predictions from {predictions_path}")
#     predictions = get_predictions_from_file(predictions_path, dataset_name, split)
#     predictions = {pred[KEY_INSTANCE_ID]: pred for pred in predictions}
#     logger.info(f"Loaded {len(predictions)} predictions")
    
#     # Get dataset
#     dataset = get_dataset_from_preds(
#         dataset_name, split, instance_ids, predictions,
#     )

#     if platform.system() == "Linux":
#         logger.info(f"Setting open file limit to {open_file_limit}")
#         resource.setrlimit(resource.RLIMIT_NOFILE, (open_file_limit, open_file_limit))

#     if not dataset:
#         logger.warning("No instances to run.")
#     else:
#         run_instances(
#             dataset,
#             timeout,
#             target_dir,
#             report_dir,
#             apply_patch,
#             src_folder,
#             ci_tool,
#             batch_size,
#             start_index,
#             max_instances
#         )

# if __name__ == "__main__":
#     parser = ArgumentParser(
#         description="Run evaluation harness for the given dataset and predictions.",
#         formatter_class=ArgumentDefaultsHelpFormatter,
#     )
    
#     parser.add_argument(
#         "--apply_patch",
#         help="Whether to apply patch during evaluation",
#         action="store_true",
#     )

#     # Common args
#     parser.add_argument(
#         "--dataset_name",
#         default="results/scikit-learn-task-instances.jsonl",
#         type=str,
#         help="Name of dataset or path to JSON file.",
#     )
#     parser.add_argument(
#         "--split", type=str, default="test", help="Split of the dataset"
#     )
#     parser.add_argument(
#         "--instance_ids",
#         nargs="+",
#         type=str,
#         help="Instance IDs to run (space separated)",
#     )
#     parser.add_argument(
#         "--predictions_path",
#         default="results/scikit-learn-task-instances.jsonl",
#         type=str,
#         help="Path to predictions file - if 'gold', uses gold predictions",
#     )

#     # Local execution args
#     parser.add_argument(
#         "--open_file_limit", type=int, default=4096, help="Open file limit"
#     )
#     parser.add_argument(
#         "--timeout",
#         type=int,
#         default=600,
#         help="Timeout (in seconds) for running tests for each instance",
#     )
#     parser.add_argument(
#         "--report_dir", type=str, default="./report", help="Directory to write reports to"
#     )
#     parser.add_argument(
#         "--target_dir", type=str, default="./testbed", help="Directory to clone repo to"
#     )
#     parser.add_argument(
#         "--src_folder", 
#         type=str, 
#         default="/raid/rust-repos", 
#         help="Source folder containing Rust repositories"
#     )
#     parser.add_argument(
#         "--ci_tool",
#         type=str,
#         choices=["act", "cargo"],
#         default="act",
#         help="CI tool to use for testing (act or cargo)"
#     )
#     parser.add_argument(
#         "--batch_size",
#         type=int,
#         default=None,
#         help="Number of instances to process in each batch"
#     )
#     parser.add_argument(
#         "--start_index",
#         type=int,
#         default=0,
#         help="Index of first instance to process"
#     )
#     parser.add_argument(
#         "--max_instances",
#         type=int,
#         default=None,
#         help="Maximum number of instances to process"
#     )

#     args = parser.parse_args()
#     main(**vars(args))

# # Example usage:
# # python -m swebench.harness.run_evaluation \
# #     --dataset_name SwingBench/SWE-Rust \
# #     --split train \
# #     --src_folder /home/hrwang/rust-repos \
# #     --predictions_path swe-rust.json \
# #     --ci_tool cargo \
# #     --start_index 0 \
# #     --max_instances 5 \
# #     --batch_size 2
