from datasets import load_dataset
import json
ds = load_dataset("SwingBench/SWE-Rust")["train"]
ds = list(ds)
ds = [d for d in ds if d["ci_name_list"]]
for i in range(len(ds)):
    ds[i]['created_at'] = str(ds[i]['created_at'])
print(len(ds))
with open("tasks_with_ci.json", "w") as f:
    json.dump(ds, f, indent=4)