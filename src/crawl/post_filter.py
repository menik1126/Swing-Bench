import os
import json
import argparse


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
    return True


def main(**kwargs):
    if not os.path.exists(kwargs["output_dir"]):
        os.makedirs(kwargs["output_dir"])

    instance_list = []
    
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

    output_path = os.path.join(kwargs["output_dir"], file_name.split(".")[0] + "_filtered.jsonl")
    with open(output_path, "w") as f:
        for instance in instance_list:
            f.write(json.dumps(instance) + "\n")

    print(f"jsonl_path: {kwargs['jsonl_path']}")
    print(f"output_path: {output_path}")
    print(f"Total instances: {total_instance}")
    print(f"Filtered instances: {len(instance_list)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl_path", type=str, default="/mnt/Data/wdxu/dataset/swing-bench-annotated-jsonl/cpp.jsonl")
    parser.add_argument("--output_dir", type=str, default="./temp")
    args = parser.parse_args()

    main(**vars(args))
