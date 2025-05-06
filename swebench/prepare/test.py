from swebench.harness.swing_utils import load_swingbench_dataset_json, load_swingbench_dataset

if __name__ == "__main__":
    origin_path = "/home/mnt/wdxu/github/SwingBench-data"
    origin_dataset = load_swingbench_dataset(origin_path, sub_dataset_identifier="python", split=None)
    
    filtered_path = "/mnt/Data/wdxu/github/filtered_swingbench/filtered_python_instance_list.jsonl"
    filtered_dataset = load_swingbench_dataset_json(filtered_path)
    
    print(origin_dataset[0])
    print('')

    print(filtered_dataset[0])
    

    print(origin_dataset[0].ci_name_list, type(origin_dataset[0].ci_name_list))
    print(filtered_dataset[0].ci_name_list, type(filtered_dataset[0].ci_name_list))