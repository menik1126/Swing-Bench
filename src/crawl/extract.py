import jsonlines
import re
import asyncio
import json
import os
from datetime import datetime
import aiohttp
import itertools

# awesome-rust

# input_file = "awesome-rust.md"
# output_file = "awesome-rust.json"
# with open(input_file, "r", encoding="utf-8", errors="replace") as f:
#     repo_list = f.readlines()
# GITHUB_REPO_PATTERN = re.compile(r"\[(.*?)\]\(https://github\.com/([\w\-_]+)/([\w\-_]+)\)")

# repos = []
# for line in repo_list:
#     match = GITHUB_REPO_PATTERN.search(line)
#     if match:
#         name, owner, repo = match.groups()
#         repos.append((name, owner, repo))

output_file = "crateio.jsonl"
pattern = r"https?://github\.com/([^/]+)/([^/\s]+)"
repos = []
with jsonlines.open("crates_data_20250302_170918.jsonl", "r") as f:
    for d in f:
        url = d["repository"]
        if url:
            match = re.match(pattern, url)
            if match:
                repo = match.group(2)
                owner = match.group(1)
                # print(f"Repository: {repo}")
                # print(f"Owner: {owner}")
                repos.append((repo, owner, repo))
repos = set(repos)
print(f'Length of repos: {len(repos)}')

# tokens = os.getenv("GH_TOKENS", "").split(",")
tokens = ["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"]
tokens = [t.strip() for t in tokens if t.strip()]
if not tokens:
    raise ValueError("GH_TOKENS environment variable is empty or not set.")
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

async def fetch_all_repos():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_repo_info(session, owner, repo) for _, owner, repo in repos]
        results = await asyncio.gather(*tasks)        
        valid_results = [r for r in results if r]
        with open(result_file, "w") as f:
            for item in valid_results:
                f.write(json.dumps(item) + "\n")
        return valid_results

if __name__ == "__main__":
    results = asyncio.run(fetch_all_repos())
    # print(json.dumps(results, indent=2))
