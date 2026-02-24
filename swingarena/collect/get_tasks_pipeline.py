#!/usr/bin/env python3

"""Script to collect pull requests and convert them to candidate task instances"""

import argparse
import os
import traceback

from dotenv import load_dotenv
from multiprocessing import Pool
from swingarena.collect.build_dataset import main as build_dataset
from swingarena.collect.utils import Repo
import json


load_dotenv()


def split_instances(input_list: list, n: int) -> list:
    """
    Split a list into n approximately equal length sublists

    Args:
        input_list (list): List to split
        n (int): Number of sublists to split into
    Returns:
        result (list): List of sublists
    """
    avg_length = len(input_list) // n
    remainder = len(input_list) % n
    result, start = [], 0

    for i in range(n):
        length = avg_length + 1 if i < remainder else avg_length
        sublist = input_list[start : start + length]
        result.append(sublist)
        start += length

    return result


def construct_data_files(data: dict):
    """
    Logic for combining multiple .all PR files into a single fine tuning dataset

    Args:
        data (dict): Dictionary containing the following keys:
            repos (list): List of repositories to retrieve instruction data for
            path_prs (str): Path to save PR data files to
            path_tasks (str): Path to save task instance data files to
            token (str): GitHub token to use for API requests
    """
    repos, path_prs, path_tasks, max_pulls, cutoff_date, token = (
        data["repos"],
        data["path_prs"],
        data["path_tasks"],
        data["max_pulls"],
        data["cutoff_date"],
        data["token"],
    )
    for repo in repos:
        repo = repo.strip(",").strip()
        repo_name = repo.split("/")[1]
        try:
            path_pr = os.path.join(path_prs, f"{repo_name}-prs.jsonl")
            if cutoff_date:
                path_pr = path_pr.replace(".jsonl", f"-{cutoff_date}.jsonl")
            if not os.path.exists(path_pr):
                print(f"Pull request data for {repo} not found, creating...")
                # Fetch PR data from GitHub
                repo_obj = Repo(repo.split("/")[0], repo.split("/")[1], token)
                pulls = repo_obj.get_all_pulls(per_page=100, num_pages=None)

                # Save PR data to file
                os.makedirs(path_prs, exist_ok=True)
                count = 0
                with open(path_pr, 'w') as f:
                    for pull in pulls:
                        if max_pulls and count >= max_pulls:
                            break
                        # Convert to dict if necessary (fastcore L objects)
                        pull_dict = dict(pull) if hasattr(pull, '__dict__') and not isinstance(pull, dict) else pull
                        # Extract resolved issues from PR body
                        pull_dict['resolved_issues'] = repo_obj.extract_resolved_issues(pull_dict)
                        f.write(json.dumps(pull_dict, default=str) + '\n')
                        count += 1
                print(f"Successfully saved {count} PR(s) for {repo} to {path_pr}")
            else:
                print(
                    f"Pull request data for {repo} already exists at {path_pr}, skipping..."
                )

            path_task = os.path.join(path_tasks, f"{repo_name}-task-instances.jsonl")
            if not os.path.exists(path_task):
                print(f"Task instance data for {repo} not found, creating...")
                build_dataset(path_pr, path_task, token)
                print(
                    f"✅ Successfully saved task instance data for {repo} to {path_task}"
                )
            else:
                print(
                    f"📁 Task instance data for {repo} already exists at {path_task}, skipping..."
                )
        except Exception as e:
            print("-" * 80)
            print(f"Something went wrong for {repo}, skipping: {e}")
            print("Here is the full traceback:")
            traceback.print_exc()
            print("-" * 80)


def main(
    repos: list,
    path_prs: str,
    path_tasks: str,
    max_pulls: int = None,
    cutoff_date: str = None,
):
    """
    Spawns multiple threads given multiple GitHub tokens for collecting fine tuning data

    Args:
        repos (list): List of repositories to retrieve instruction data for
        path_prs (str): Path to save PR data files to
        path_tasks (str): Path to save task instance data files to
        cutoff_date (str): Cutoff date for PRs to consider in format YYYYMMDD
    """
    path_prs, path_tasks = os.path.abspath(path_prs), os.path.abspath(path_tasks)
    print(f"Will save PR data to {path_prs}")
    print(f"Will save task instance data to {path_tasks}")
    print(f"Received following repos to create task instances for: {repos}")

    tokens = os.getenv("GITHUB_TOKENS")
    if not tokens:
        # Fallback to single GITHUB_TOKEN if GITHUB_TOKENS not set
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise Exception(
                "Missing GITHUB_TOKEN or GITHUB_TOKENS. Please set one of:\n"
                "  1. GITHUB_TOKEN in .env file (single token)\n"
                "  2. GITHUB_TOKENS in .env file (comma-separated for parallel processing)\n"
                "  3. Or run with: GITHUB_TOKENS=$(gh auth token)"
            )
        tokens = token
    tokens = tokens.split(",")
    data_task_lists = split_instances(repos, len(tokens))

    data_pooled = [
        {
            "repos": repos,
            "path_prs": path_prs,
            "path_tasks": path_tasks,
            "max_pulls": max_pulls,
            "cutoff_date": cutoff_date,
            "token": token,
        }
        for repos, token in zip(data_task_lists, tokens)
    ]

    with Pool(len(tokens)) as p:
        p.map(construct_data_files, data_pooled)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repos",
        nargs="+",
        help="List of repositories (e.g., `sqlfluff/sqlfluff`) to create task instances for",
    )
    parser.add_argument(
        "--path_prs", type=str, help="Path to folder to save PR data files to"
    )
    parser.add_argument(
        "--path_tasks",
        type=str,
        help="Path to folder to save task instance data files to",
    )
    parser.add_argument(
        "--max_pulls", type=int, help="Maximum number of pulls to log", default=None
    )
    parser.add_argument(
        "--cutoff_date",
        type=str,
        help="Cutoff date for PRs to consider in format YYYYMMDD",
        default=None,
    )
    args = parser.parse_args()
    main(**vars(args))
