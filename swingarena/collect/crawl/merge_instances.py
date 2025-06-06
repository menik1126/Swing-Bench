import argparse
import os
import re
import jsonlines
import json
from tqdm import tqdm


def combine_results(output_folder: str,):
    # Combine all repos
    print("Start combining results...")
    all_tasks = []
    files = os.listdir(output_folder)
    for file in tqdm(files):
        repo_path = os.path.join(output_folder, file)
        if os.path.exists(repo_path) and os.path.isdir(repo_path):
            for inner_file in os.listdir(repo_path):
                task_instance_json_path = os.path.join(repo_path, inner_file, "{}-task-instances.jsonl.all".format(inner_file))
                if os.path.exists(task_instance_json_path):
                    with jsonlines.open(task_instance_json_path, "r") as f:
                        all_tasks.extend([d for d in f])
        else:
            print(f"Warning: {repo_path} does not exist, skipping...")
    print("Writing!")
    with open(os.path.join(output_folder, "all_tasks.json"), "w") as f:
        json.dump(all_tasks, f)
    print("Finished writing results.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Swing Merge Instances")
    parser.add_argument("--repo_root_dir", type=str, help="Root directory of the repository")
    args = parser.parse_args()
    
    combine_results(args.repo_root_dir)
