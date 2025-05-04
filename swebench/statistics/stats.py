from datasets import load_dataset, load_from_disk, DatasetDict
from transformers import AutoTokenizer
from tqdm import tqdm

import argparse
import os
import json

fields = ["patch", "test_patch", "problem_statement", "hints_text"]


bins = [
    "01. 0-100",
    "02. 100-250",
    "03. 250-500",
    "04. 500-750",
    "05. 750-1000",
    "06. 1000-1500",
    "07. 1500-2000",
    "08. 2000-2500",
    "09. 2500-3000",
    "10. 3000-3500",
    "11. 3500-5000",
    "12. 5000-7500",
    "13. 7500-10000",
    "14. 10000-15000",
    "15. 15000-20000",
    "16. 20000-25000",
    "17. 25000-30000",
    "18. 30000-35000",
    "19. 35000-50000",
    "20. 50000+",
]


def get_length_bins(length):
    if length < 100:
        return bins[0]
    if length < 250:
        return bins[1]
    if length < 500:
        return bins[2]
    if length < 750:
        return bins[3]
    if length < 1000:
        return bins[4]
    if length < 1500:
        return bins[5]
    if length < 2000:
        return bins[6]
    if length < 2500:
        return bins[7]
    if length < 3000:
        return bins[8]
    if length < 3500:
        return bins[9]
    if length < 5000:
        return bins[10]
    if length < 7500:
        return bins[11]
    if length < 10000:
        return bins[12]
    if length < 15000:
        return bins[13]
    if length < 20000:
        return bins[14]
    if length < 25000:
        return bins[15]
    if length < 30000:
        return bins[16]
    if length < 35000:
        return bins[17]
    if length < 50000:
        return bins[18]
    return bins[19]


def get_length_stats(language, dataset, tokenizer_path, output_dir):
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)

    print("-" * 80)
    print(f"Language: {language}")
    print(f"Number of unsampled examples: {len(dataset)}")
    stats = {
        "language": language,
        "patch": {},
        "test_patch": {},
        "problem_statement": {},
        "hints_text": {},
    }

    dump_field_token_length_path = os.path.join(
        output_dir, f"{language}_field_token_length.data"
    )
    # Initialize all bins
    for field in fields:
        for bin_name in bins:
            stats[field][bin_name] = 0

    if os.path.exists(dump_field_token_length_path):
        with open(dump_field_token_length_path, "r") as f:
            for line in f:
                _, _, field, token_length = line.strip().split()
                bin_name = get_length_bins(int(token_length))
                stats[field][bin_name] += 1
    else:
        with open(dump_field_token_length_path, "w") as f:
            for instance in tqdm(dataset, desc="Processing instances"):
                for field in fields:
                    if field in instance and instance[field]:
                        token_length = len(tokenizer.encode(instance[field]))
                        bin_name = get_length_bins(token_length)
                        f.write(
                            f"{instance['repo']} {instance['instance_id']} {field} {token_length}\n"
                        )
                        stats[field][bin_name] += 1

    with open(os.path.join(output_dir, f"{language}_summary.json"), "w") as f:
        json.dump(stats, f)


def main(**kwargs):
    output_dir = kwargs["output_dir"]
    data_path = kwargs["data_path"]
    tokenizer_path = kwargs["tokenizer_path"]
    language_list = kwargs["language_list"].split(",")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print("Number of unsampled examples: ", end="")
    for language in language_list:
        dataset = load_dataset(data_path)[language]
        get_length_stats(language, dataset, tokenizer_path, output_dir)


def analyze_difficulty_distribution(results):
    difficulties = [r["difficulty"] for r in results]
    avg_difficulty = sum(difficulties) / len(difficulties)

    print(f"\nDifficulty Analysis Results:")
    print(f"Total instances: {len(results)}")
    print(f"Average difficulty: {avg_difficulty:.3f}")

    bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    for i in range(len(bins) - 1):
        count = sum(1 for d in difficulties if bins[i] <= d < bins[i + 1])
        percentage = (count / len(difficulties)) * 100
        print(f"Difficulty {bins[i]:.1f}-{bins[i+1]:.1f}: {count} ({percentage:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data_path", type=str, default="/home/mnt/wdxu/github/SwingBench-data"
    )
    parser.add_argument("--language_list", type=str, default="rust,cpp,python,go")
    parser.add_argument(
        "--tokenizer_path",
        type=str,
        default="/home/mnt/wdxu/models/Qwen2.5-Coder-7B-Instruct",
    )
    parser.add_argument("--output_dir", type=str, default="./length_stats")
    args = parser.parse_args()

    main(**vars(args))
