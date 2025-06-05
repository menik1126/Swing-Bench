import argparse
import os
import subprocess

from datasets import load_dataset


def clone_repos(repos: list, repo_root_dir: str) -> list:
    """
    Clone the repositories and return the list of repository paths
    """
    repo_paths = []
    for repo in repos:
        repo_owner, repo_name = repo.split("/")
        repo_url = f"https://github.com/{repo}"
        repo_path = os.path.join(repo_root_dir, f"{repo_owner}__{repo_name}")
        subprocess.run(["git", "clone", repo_url, repo_path, "--recursive"])
        repo_paths.append(repo_path)
    return repo_paths


def read_parquet(dataset_path: str) -> list:
    """
    Read the parquet file and return the list of repository paths
    """
    dataset = load_dataset(dataset_path)
    repo_path_list = []
    for split in dataset.keys():
        for repo in dataset[split]["repo"]:
            repo_path_list.append(repo)
    return repo_path_list


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_path", type=str, help="Path to the dataset")
    parser.add_argument("--repo_root_dir", type=str, help="Root directory for the repositories")
    args = parser.parse_args()
    repo_path_list = read_parquet(args.dataset_path)
    clone_repos(repo_path_list, args.repo_root_dir)


if __name__ == "__main__":
    """
    python swebench/prepare/swing_clone_repos.py \
        --dataset_path /home/mnt/wdxu/github/Swing-Dataset/Swing-Rust \
        --repo_root_dir ./testbed
    """
    main()
