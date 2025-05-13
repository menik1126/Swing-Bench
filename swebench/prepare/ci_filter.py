import argparse
import os

from swebench.harness.swing_utils import load_swingbench_dataset_json
from swebench.harness.agent.verifier import PatchVerifier


json_name_path = "filtered_{}_instance_list.jsonl"


def process_ci_emit(instance, verifier):
    result = verifier.verify(instance, "")
    print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json_dir", type=str, default="/mnt/Data/wdxu/github/Swing-Bench/temp/")
    parser.add_argument("--languages", type=str, default="python,cpp,go,rust")
    parser.add_argument("--output_dir", type=str, default="/mnt/Data/wdxu/github/Swing-Bench/temp/")
    args = parser.parse_args()

    verifier = PatchVerifier(ci_tool_name="act",
                             workdir="./temp/",
                             src_folder="./temp/repos")

    for language in args.languages.split(","):
        json_path = os.path.join(args.json_dir, json_name_path.format(language))
        instances = load_swingbench_dataset_json(json_path)

        print(f"load {len(instances)} instances from {json_path}")

        for instance in instances:
            process_ci_emit(instance, verifier)
            break

