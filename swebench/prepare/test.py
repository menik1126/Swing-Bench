import re
import os

from swebench.harness.swing_utils import load_swingbench_dataset_json, load_swingbench_dataset

def _get_ci_job_name_id_dict(target_dir, act_list_path):
    def _extract_jobs(filename):
        jobs = {}
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("Stage"):
                    continue
                columns = re.split(r'\s{2,}', line)
                if len(columns) >= 3:
                    job_id = columns[1]
                    job_name = columns[2]
                    jobs[job_name] = job_id
        return jobs

    script = ["#!/bin/bash"]
    script.extend(["cd " + target_dir])
    script.extend([f"act --list > {act_list_path}"])
    os.system("\n".join(script))
    # only absolute path? 
    act_list_path = os.path.join(target_dir, act_list_path)
    ci_dict = _extract_jobs(os.path.expanduser(act_list_path))
    os.system("rm " + act_list_path)

    return ci_dict


if __name__ == "__main__":
    target_dir = '/mnt/Data/wdxu/github/Swing-Bench/testbed/lightningnetwork__lnd'
    act_list_path = './act_list.txt'
    ci_dict = _get_ci_job_name_id_dict(target_dir, act_list_path)
    print(ci_dict)

    # origin_path = "/home/mnt/wdxu/github/SwingBench-data"
    # origin_dataset = load_swingbench_dataset(origin_path, sub_dataset_identifier="python", split=None)
    
    # filtered_path = "/mnt/Data/wdxu/github/filtered_swingbench/filtered_python_instance_list.jsonl"
    # filtered_dataset = load_swingbench_dataset_json(filtered_path)
    
    # print(origin_dataset[0])
    # print('')

    # print(filtered_dataset[0])
    

    # print(origin_dataset[0].ci_name_list, type(origin_dataset[0].ci_name_list))
    # print(filtered_dataset[0].ci_name_list, type(filtered_dataset[0].ci_name_list))
    