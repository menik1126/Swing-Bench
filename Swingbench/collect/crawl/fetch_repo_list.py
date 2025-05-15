import argparse
import jsonlines
import re
import asyncio
import json
import os
from datetime import datetime
import aiohttp
import itertools

tokens = os.getenv("GITHUB_TOKENS", "").split(",")
tokens = [t.strip() for t in tokens if t.strip()]
if not tokens:
    raise ValueError("GITHUB_TOKENS environment variable is empty or not set.")
token_cycle = itertools.cycle(tokens)
def get_token():
    return next(token_cycle)

os.makedirs('repos', exist_ok=True)
result_file = f"repos/{output_file}"

async def fetch_repo_info(session, owner, repo):
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {'Authorization': f'token {get_token()}'}
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    "name": repo,
                    "owner": owner,
                    "url": url.replace("api.github.com/repos", "github.com"),
                    "stars": data.get("stargazers_count", 0),
                    "forks": data.get("forks_count", 0),
                    "issues": data.get("open_issues_count", 0),
                }
            else:
                print(f"Failed to fetch {owner}/{repo}: {response.status}, {response.text}")
                return None
    except:
        return None

async def fetch_all_repos(repos):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_repo_info(session, owner, repo) for _, owner, repo in repos]
        results = await asyncio.gather(*tasks)        
        valid_results = [r for r in results if r]
        with open(result_file, "w") as f:
            for item in valid_results:
                f.write(json.dumps(item) + "\n")
        return valid_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True, help="Input file path")
    parser.add_argument("--output", type=str, required=True, help="Output file path")
    args = parser.parse_args()
    with jsonlines.open(args.input, "r") as f:
        repos = [d["repository"] for d in f]
    results = asyncio.run(fetch_all_repos(repos))