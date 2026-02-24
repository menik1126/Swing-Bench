import os
import json
import argparse
import shutil
from datasets import load_dataset


def clarity_rule(instance):
    """
    Filter out instances with clarity score 0 or 1
    """
    if instance["clarity"] == 0 or instance["clarity"] == 1:
        return False
    return True


def image_rule(instance):
    """
    Filter out instances with problem statement containing images
    """
    if "![image](" in instance["problem_statement"]:
        return False
    
    if "snapshot" in instance["problem_statement"]:
        return False
    
    if "![Image]" in instance["problem_statement"]:
        return False

    return True


def make_pair_ci_list(ci_name_list):
    """
    Make a pair of CI names from the list of CI names.
    TODO(wdxu): Remove once the dataset is fixed.
    """
    new_ci_name_list = []
    for i in range(0, len(ci_name_list) // 2, 2):
        new_ci_name_list.append([ci_name_list[i], ci_name_list[i+1]])
    return new_ci_name_list


def main(**kwargs):
    if not os.path.exists(kwargs["output_dir"]):
        os.makedirs(kwargs["output_dir"])

    instance_list = []
    key_set = set()
    file_name = kwargs["jsonl_path"].split("/")[-1]

    with open(kwargs["jsonl_path"], "r") as f:
        total_instance = 0
        for line in f:
            total_instance += 1
            instance = json.loads(line)
            if not clarity_rule(instance):
                continue
            if not image_rule(instance):
                continue
            instance_list.append(instance)
            key_set.add(instance["instance_id"])
    output_path = os.path.join(kwargs["output_dir"], file_name.split(".")[0] + "_filtered.jsonl")
    with open(output_path, "w") as f:
        for instance in instance_list:
            f.write(json.dumps(instance) + "\n")

    print(f"jsonl_path: {kwargs['jsonl_path']}")
    print(f"output_path: {output_path}")
    print(f"Total instances: {total_instance}")
    print(f"Filtered instances: {len(instance_list)}")

    language = kwargs["jsonl_path"].split("/")[-1].split(".")[0].split("_")[0]
    ori_instance_list = load_dataset(kwargs["instance_dir"], split=None)[language]
    new_instances_list = []

    for instance in ori_instance_list:
        if instance["instance_id"] not in key_set:
            continue

        # TODO(wdxu): Remove once the dataset is fixed.
        instance["ci_name_list"] = make_pair_ci_list(instance["ci_name_list"])

        new_instances_list.append(instance)

    output_filename = f"filtered_{language}_instance_list.jsonl"
    with open(os.path.join(kwargs["output_dir"], output_filename), "w") as f:
        for instance in new_instances_list:
            f.write(json.dumps(instance) + "\n")

    print(f"ori_instance_list: {len(ori_instance_list)}")
    print(f"new_instances_list: {len(new_instances_list)}")
    print(f"saved to {os.path.join(kwargs['output_dir'], output_filename)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl_path", type=str, default="/mnt/Data/wdxu/dataset/swing-bench-annotated-jsonl/python.jsonl")
    parser.add_argument("--instance_dir", type=str, default="/mnt/Data/wdxu/github/SwingBench-data/")
    parser.add_argument("--output_dir", type=str, default="./temp")
    args = parser.parse_args()

    main(**vars(args))
