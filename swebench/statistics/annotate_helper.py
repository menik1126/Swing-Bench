import json
import os


if __name__ == "__main__":
    jsonl_file_list = [
        "/home/mnt/wdxu/dataset/swing-bench-annotated-jsonl/cpp.jsonl",
        "/home/mnt/wdxu/dataset/swing-bench-annotated-jsonl/go.jsonl",
        "/home/mnt/wdxu/dataset/swing-bench-annotated-jsonl/python.jsonl",
        "/home/mnt/wdxu/dataset/swing-bench-annotated-jsonl/rust.jsonl",
    ]
    output_dir = "/home/mnt/wdxu/dataset/swing-bench-annotated-jsonl-part"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    part_num = 20

    for each_file in jsonl_file_list:
        new_data = []
        with open(each_file, "r") as f:
            for line in f:
                data = json.loads(line)
                data["clarity_label"] = -1
                data["difficulty_label"] = -1
                data["human_clarity"] = -1
                data["human_difficulty"] = -1
                new_data.append(data)

            for i in range(part_num):
                with open(os.path.join(output_dir, f"{each_file}.{i}.jsonl"), "w") as f:
                    for data in new_data[i::part_num]:
                        f.write(json.dumps(data) + "\n")
