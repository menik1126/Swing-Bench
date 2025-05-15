import json
import os
from pathlib import Path
from utils import annotated_jsonl_dir


def load_jsonl_to_dict(jsonl_path):
    results = {}

    if os.path.exists(jsonl_path):
        with open(jsonl_path, "r") as f:
            for line_num, line in enumerate(f):
                try:
                    data = json.loads(line.strip())
                    instance_id = data.get("instance_id")
                    if instance_id:
                        results[instance_id] = data
                    else:
                        print(f"{line_num+1} line miss instance_id")
                except json.JSONDecodeError:
                    print(f"{line_num+1} line error")

    else:
        print(f"no file: {jsonl_path}")

    return results


jsonl_path = annotated_jsonl_dir / "rust.jsonl"
data_dict = load_jsonl_to_dict(jsonl_path)

for idx, instance_id in enumerate(list(data_dict.keys())[:5]):
    print(f"{idx+1}. {instance_id}")
    item = data_dict[instance_id]
    print(f"   - clarity: {item.get('clarity')}")
    print(f"   - clarity explanation: {item.get('clarity_explanation')}")
    print(f"   - difficulty: {item.get('difficulty')}")
    print(f"   - difficulty explanation: {item.get('difficulty_explanation')}")

missing_fields = {
    field: 0
    for field in [
        "instance_id",
        "clarity",
        "difficulty",
        "clarity_explanation",
        "difficulty_explanation",
    ]
}
for instance_id, data in data_dict.items():
    for field in missing_fields:
        if field not in data or data[field] is None:
            missing_fields[field] += 1

for field, count in missing_fields.items():
    if count > 0:
        print(f"- {field}: miss {count} items")
