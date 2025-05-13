import os
import json

data_path_list = [
    # "/mnt/Data/wdxu/dataset/swing-bench-annotated-jsonl/cpp.jsonl",
    # "/mnt/Data/wdxu/dataset/swing-bench-annotated-jsonl/go.jsonl",
    # "/mnt/Data/wdxu/dataset/swing-bench-annotated-jsonl/python.jsonl",
    # "/mnt/Data/wdxu/dataset/swing-bench-annotated-jsonl/rust.jsonl",
    "/mnt/Data/wdxu/github/Swing-Bench/temp/cpp_filtered.jsonl",
    "/mnt/Data/wdxu/github/Swing-Bench/temp/go_filtered.jsonl",
    "/mnt/Data/wdxu/github/Swing-Bench/temp/python_filtered.jsonl",
    "/mnt/Data/wdxu/github/Swing-Bench/temp/rust_filtered.jsonl",
]

if __name__ == '__main__':
    for data_path in data_path_list:
        difficulty_dict = {}
        clarity_dict = {}
        languge = os.path.basename(data_path).split('.')[0]
        with open(data_path, 'r') as f:
            for line in f:
                data = json.loads(line)
                difficulty = data['difficulty']
                clarity = data['clarity']
                if difficulty not in difficulty_dict:
                    difficulty_dict[difficulty] = 0
                if clarity not in clarity_dict:
                    clarity_dict[clarity] = 0
                difficulty_dict[difficulty] += 1
                clarity_dict[clarity] += 1
        print(f"{languge}\tdifficulty:")
        for difficulty, count in sorted(difficulty_dict.items()):
            print(f"{difficulty}\t{count}")
        print(f"{languge}\tclarity:")
        for clarity, count in sorted(clarity_dict.items()):
            print(f"{clarity}\t{count}")
