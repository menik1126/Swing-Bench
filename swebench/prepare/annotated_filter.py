import re
import json
import os

annotated_root_dir = "/mnt/Data/wdxu/github/Swing-Bench/annotated/swing-bench annotated"
full_data_path = "/mnt/Data/wdxu/github/Swing-Bench/temp/filtered_instance_list_all.jsonl"

filter_json_listptn = {
    "cpp": r"cpp_.+.jsonl",
    "go": r"go_.+.jsonl",
    "python": r"python_.+.jsonl",
    "rust": r"rust_.+.jsonl"
}

output_dir = "/mnt/Data/wdxu/github/Swing-Bench/annotated/swing-bench annotated/merged"

def get_filtered_data_by_language(language: str, jsonl_path: str, filtered_instance_id_list: list[str]):
    with open(jsonl_path, "r") as f:
        filtered_data = [json.loads(line) for line in f]
    filtered_data = [instance for instance in filtered_data if dict(instance)["instance_id"] in filtered_instance_id_list]
    return filtered_data


if __name__ == '__main__':
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for root, dirs, files in os.walk(annotated_root_dir):
        for lang, ptn in filter_json_listptn.items():
            all_instance_list = []
            for file in files:
                if re.match(ptn, file):
                    instance_id_list = []
                    with open(os.path.join(root, file), "r") as f:
                        for line in f:
                            instance_id_list.append(json.loads(line)["instance_id"])
                    filtered_instance_list = get_filtered_data_by_language(lang, full_data_path, instance_id_list)
                    print(len(filtered_instance_list))
                    all_instance_list.extend(filtered_instance_list)

            with open(os.path.join(output_dir, f"{lang}_filtered_instance_list.jsonl"), "w") as f:
                for instance in all_instance_list:
                    f.write(json.dumps(instance) + "\n")
