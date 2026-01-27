import argparse
import json
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


def read_dataset(dataset_path: str) -> list:
    """
    Read the dataset file (JSON, JSONL, or HuggingFace dataset) and return the list of repositories
    """
    repo_path_list = []

    # Check if it's a local JSON/JSONL file
    if os.path.isfile(dataset_path):
        with open(dataset_path, 'r') as f:
            # Try to load as single JSON first
            try:
                data = json.load(f)
                # If it's a list of instances
                if isinstance(data, list):
                    for instance in data:
                        if 'repo' in instance:
                            repo_path_list.append(instance['repo'])
                # If it's a single instance
                elif isinstance(data, dict) and 'repo' in data:
                    repo_path_list.append(data['repo'])
            except json.JSONDecodeError:
                # If not valid JSON, try as JSONL (one JSON per line)
                f.seek(0)
                for line in f:
                    line = line.strip()
                    if line:
                        instance = json.loads(line)
                        if 'repo' in instance:
                            repo_path_list.append(instance['repo'])
    else:
        # Assume it's a HuggingFace dataset path
        dataset = load_dataset(dataset_path)
        for split in dataset.keys():
            for repo in dataset[split]["repo"]:
                repo_path_list.append(repo)

    # Remove duplicates while preserving order
    seen = set()
    unique_repos = []
    for repo in repo_path_list:
        if repo not in seen:
            seen.add(repo)
            unique_repos.append(repo)

    return unique_repos


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_path", type=str, help="Path to the dataset (JSON/JSONL file or HuggingFace dataset)")
    parser.add_argument("--repo_root_dir", type=str, help="Root directory for the repositories")
    args = parser.parse_args()
    repo_path_list = read_dataset(args.dataset_path)
    print(f"Found {len(repo_path_list)} unique repositories to clone")
    clone_repos(repo_path_list, args.repo_root_dir)


if __name__ == "__main__":
    """
    python swingarena/prepare/swing_clone_repos.py \
        --dataset_path ./data/SwingBench/Cpp/cpp.json \
        --repo_root_dir ./testbed

    or for HuggingFace datasets:

    python swingarena/prepare/swing_clone_repos.py \
        --dataset_path SwingBench/SwingBench \
        --repo_root_dir ./testbed
    """
    main()
