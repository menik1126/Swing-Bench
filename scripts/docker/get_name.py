import json
from datasets import load_dataset

ds = load_dataset('princeton-nlp/SWE-bench_Verified')['test']
for d in ds:
    iid = d['instance_id']
    iid = f'sweb.eval.x86_64.{iid.replace("__", "_s_")}:latest'
    with open("all-swebench-verified-instance-images.txt", "a") as f:
        f.write(f'{iid}\n')
