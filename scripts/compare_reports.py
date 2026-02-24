# python compare_reports.py --golden "/home/hrwang/Swing-Bench/report/" --dummy "/home/hrwang/Swing-Bench/dummy_report/"
import os
import json
import argparse
import sys
import re
from datetime import datetime

def parse_arguments():
    parser = argparse.ArgumentParser(description='Compare JSON files between two directories.')
    parser.add_argument('--report_dir', type=str, required=True, help='Path to report directory')
    parser.add_argument('--output', type=str, default='diff_report.jsonl', help='Output file path')
    return parser.parse_args()

def load_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def group_files_by_order(report_dir):
    all_files = os.listdir(report_dir)
    grouped_files = {}

    for file in all_files:
        parts = re.split(r'(?<!_)_(?!_)', file)
        if len(parts) < 4 or not file.endswith("_output.json"):
            continue
        task_id, order, value = parts[0], parts[1], parts[2]
        key = f"{task_id}_{value}"

        if key not in grouped_files:
            grouped_files[key] = {"based": None, "merged": None}

        if order in grouped_files[key]:
            grouped_files[key][order] = file

    file_pairs = []

    for key, orders in grouped_files.items():
        if orders["based"] and orders["merged"]:
            file_pairs.append((orders["based"], orders["merged"]))

    return file_pairs

def compare_reports(report_dir):
    file_pairs = group_files_by_order(report_dir)
    differences = []
    for (dummy_file, golden_file) in file_pairs:
        golden_path = os.path.join(report_dir, golden_file)
        dummy_path = os.path.join(report_dir, dummy_file)
        golden_data = load_json_file(golden_path)
        dummy_data = load_json_file(dummy_path)

        if not golden_data or not dummy_data:
            continue

        golden_jobs = {item.get('job'): item for item in golden_data.get('processed_output', [])}
        dummy_jobs = {item.get('job'): item for item in dummy_data.get('processed_output', [])}

        common_jobs = set(golden_jobs.keys()) & set(dummy_jobs.keys())

        for job in common_jobs:
            golden_job = golden_jobs[job]
            dummy_job = dummy_jobs[job]

            level_diff = golden_job.get('level') != dummy_job.get('level')
            result_diff = golden_job.get('stepResult') != dummy_job.get('stepResult')

            if level_diff or result_diff:
                diff_record = {
                    'golden_name': golden_file,
                    'dummy_name': dummy_file,
                    'job': job,
                    'has_level_diff': level_diff,
                    'has_result_diff': result_diff,
                    'golden_level': golden_job.get('level'),
                    'dummy_level': dummy_job.get('level'),
                    'golden_result': golden_job.get('stepResult'),
                    'dummy_result': dummy_job.get('stepResult'),
                    'golden_job_data': golden_job,
                    'dummy_job_data': dummy_job,
                    'comparison_time': datetime.now().isoformat()
                }
                differences.append(diff_record)

    return differences

# def compare_reports(report_dir):
#     all_files = os.listdir(report_dir)
    
#     common_files = set(golden_files) & set(dummy_files)
#     differences = []
    
#     for filename in common_files:
#         golden_path = os.path.join(report_dir, filename)
#         dummy_path = os.path.join(report_dir, filename)
        
#         golden_data = load_json_file(golden_path)
#         dummy_data = load_json_file(dummy_path)
        
#         if not golden_data or not dummy_data:
#             continue
            
#         golden_jobs = {item.get('job'): item for item in golden_data.get('processed_output', [])}
#         dummy_jobs = {item.get('job'): item for item in dummy_data.get('processed_output', [])}
        
#         common_jobs = set(golden_jobs.keys()) & set(dummy_jobs.keys())
        
#         for job in common_jobs:
#             golden_job = golden_jobs[job]
#             dummy_job = dummy_jobs[job]
            
#             level_diff = golden_job.get('level') != dummy_job.get('level')
#             result_diff = golden_job.get('stepResult') != dummy_job.get('stepResult')
            
#             if level_diff or result_diff:
#                 diff_record = {
#                     'filename': filename,
#                     'job': job,
#                     'has_level_diff': level_diff,
#                     'has_result_diff': result_diff,
#                     'golden_level': golden_job.get('level'),
#                     'dummy_level': dummy_job.get('level'),
#                     'golden_result': golden_job.get('stepResult'),
#                     'dummy_result': dummy_job.get('stepResult'),
#                     'golden_job_data': golden_job,
#                     'dummy_job_data': dummy_job,
#                     'comparison_time': datetime.now().isoformat()
#                 }
#                 differences.append(diff_record)
    
#     return differences

def save_differences(differences, output_path):
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for diff in differences:
                f.write(json.dumps(diff, ensure_ascii=False) + '\n')
        print(f"Successfully saved {len(differences)} differences to {output_path}")
    except Exception as e:
        print(f"Error saving differences to {output_path}: {e}")

def main():
    args = parse_arguments()
    
    if not os.path.isdir(args.report_dir):
        print(f"Error: Directory '{args.golden}' does not exist")
        sys.exit(1)
        
    differences = compare_reports(args.report_dir)
    
    if differences:
        save_differences(differences, args.output)
        print(f"Found {len(differences)} differences")
        
        level_diffs = sum(1 for d in differences if d['has_level_diff'])
        result_diffs = sum(1 for d in differences if d['has_result_diff'])
        print(f"  - Level differences: {level_diffs}")
        print(f"  - Result differences: {result_diffs}")
    else:
        print("No differences found")

if __name__ == "__main__":
    main()