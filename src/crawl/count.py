from collections import Counter
import jsonlines
with jsonlines.open("issues/all_tasks.jsonl", "r") as f:
    ds = list(f)
print("Instance count:", len(ds))
print("Instance with testcase:", sum([1 for d in ds if d['test_patch']]))
print("Repo count:", len(list(set([d['repo'] for d in ds]))))
repos = [item["repo"] for item in ds]
repo_count = Counter(repos)
count_distribution = Counter(repo_count.values())
count_distribution = dict(sorted(count_distribution.items()))
print("Repo distribution:", count_distribution)