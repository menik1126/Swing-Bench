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

    annotator = [
        "Xiong Jing",
        "Shen Hui",
        "Wan Zhongwei",
        "Xu Wendong",
        "Xiao He",
        "Zhao Chenyang",
        "Chen Qiujiang",
        "Wang Haoran",
        "Guo Zhijiang",
        "Dai Jianbo",
        "Tao Chaofan",
        "Wu Taiqiang",
    ]

    workload = {name: [] for name in annotator}

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

        total_parts = part_num
        annotator_count = len(annotator)
        base_parts = total_parts // annotator_count
        remainder = total_parts % annotator_count

        start_idx = 1
        for i, name in enumerate(annotator):
            current_parts = base_parts + (1 if i < remainder else 0)
            end_idx = start_idx + current_parts
            
            file_numbers = list(range(start_idx, end_idx))
            file_names = [os.path.join(output_dir, f"{os.path.basename(each_file)}.{num}.jsonl") for num in file_numbers]
            
            workload[name].extend(file_names)
            start_idx = end_idx

    for name in annotator:
        print(f"{name}:")
        for file_name in workload[name]:
            print(f"  {file_name}")
        print()
