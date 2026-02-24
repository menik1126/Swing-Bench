import json
import sys

def extract_keys(data, prefix=""):
    keys = []
    for key, value in data.items():
        full_key = f"{prefix}{key}"
        keys.append(full_key)
        if isinstance(value, dict):  # If value is a map, extract its keys
            keys.extend(extract_keys(value, prefix=full_key + "."))
    return keys

def show_jsonl_keys(input_file):
    with open(input_file, "r", encoding="utf-8") as infile:
        for line in infile:
            data = json.loads(line)
            keys = extract_keys(data)
            print(json.dumps(keys, indent=4, ensure_ascii=False))
            print("-" * 80)  # Separator for readability

if __name__ == "__main__":
    input_path = "../outputs/output.jsonl"   
    show_jsonl_keys(input_path)
