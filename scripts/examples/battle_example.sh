#! /bin/bash
python swingarena/harness/agent_battle.py --dataset_name /mnt/Data/wdxu/github/Swing-Bench/annotated/swing-bench\ annotated/merged/python_filtered_instance_list.jsonl --language python --port_range 10001-11000 > qwen2.5_coder_7B_instruct_python_filtered_self.log

python swingarena/harness/agent_battle.py --dataset_name /mnt/Data/wdxu/github/Swing-Bench/annotated/swing-bench\ annotated/merged/rust_filtered_instance_list.jsonl --language rust --port_range 11001-12000 > qwen2.5_coder_7B_instruct_rust_filtered_self.log

python swingarena/harness/agent_battle.py --dataset_name /mnt/Data/wdxu/github/Swing-Bench/annotated/swing-bench\ annotated/merged/go_filtered_instance_list.jsonl --language go --port_range 12001-13000 > qwen2.5_coder_7B_instruct_go_filtered_self.log

python swingarena/harness/agent_battle.py --dataset_name /mnt/Data/wdxu/github/Swing-Bench/annotated/swing-bench\ annotated/merged/cpp_filtered_instance_list.jsonl --language cpp --port_range 13001-14000 > qwen2.5_coder_7B_instruct_cpp_filtered_self.log
