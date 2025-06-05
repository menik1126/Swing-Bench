
import argparse
import jsonlines
import os
import json
from tqdm import tqdm

from swingarena.collect.get_tasks_pipeline import main as get_tasks_pipeline

overall_info_json_path = "progress.json"


def process_repo(repo, repo_root_dir, output_dir, max_pulls, cutoff_date):
    repo_path = os.path.join(repo_root_dir, repo)
    metadata_path = os.path.join(repo_path, "metadata.json")
    metadata = None
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    
    if metadata is None:
        print(f"Metadata is None for {repo}")
        return
    
    repo_name = metadata["full_name"]
    output_path = os.path.join(output_dir, f"{repo_name}")
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    print(f"Processing {repo_name} with max_pulls={max_pulls} and cutoff_date={cutoff_date} at {output_path} ...")

    get_tasks_pipeline(
        repos=[repo_name],
        path_prs=output_path,
        path_tasks=output_path,
        max_pulls=max_pulls,
        cutoff_date=cutoff_date
    )


def main(repo_root_dir, output_dir, max_pulls, cutoff_date):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(os.path.join(repo_root_dir, overall_info_json_path), "r") as f:
        overall_info = json.load(f)
        for repo in overall_info["repos_cloned"]:
            process_repo(repo, repo_root_dir, output_dir, max_pulls, cutoff_date)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo_root_dir", type=str, required=True, help="Root directory of the repositories")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory")
    parser.add_argument("--max_pulls", type=int, required=False, help="Maximum number of pulls to log", default=None)
    parser.add_argument("--cutoff_date", type=str, required=False, help="Cutoff date for PRs to consider in format YYYYMMDD", default="20220101")
    args = parser.parse_args()

    main(**vars(args))