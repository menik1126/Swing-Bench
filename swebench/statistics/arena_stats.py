# -*- coding: utf-8 -*-

import os
import argparse
import re

def isdigit(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def dispatch_final_result_item(result_dict, final_result_str):
    result = final_result_str.split(': ')
    if len(result) == 2:
        key, value = result
        key = key.strip()[15:]
        value = value.strip()
        return key, value
    else:
        return None, None
        

def get_api_transmission(result_str: str):
    ret = re.findall(r"[CALL API].+#(\d+)#.+#(\d+)#", result_str)
    if len(ret) == 0:
        return None, None
    return float(ret[0][0]), float(ret[0][1])


def get_max_abs_value(values):
    ret = 0
    for each in values:
        if abs(each) > abs(ret):
            ret = each
    return ret


def compute_average_token_size(transmission_dict):
    avg_transmission_dict = {}
    for patch_generator in transmission_dict:
        for test_generator in transmission_dict[patch_generator]:
            for language in transmission_dict[patch_generator][test_generator]:
                for request, response in zip(transmission_dict[patch_generator][test_generator][language]["request"], transmission_dict[patch_generator][test_generator][language]["response"]):
                    if patch_generator not in avg_transmission_dict:
                        avg_transmission_dict[patch_generator] = {}
                    if test_generator not in avg_transmission_dict[patch_generator]:
                        avg_transmission_dict[patch_generator][test_generator] = {}
                    if language not in avg_transmission_dict[patch_generator][test_generator]:
                        avg_transmission_dict[patch_generator][test_generator][language] = {
                            "avg_request_token_size": .0,
                            "avg_response_token_size": .0,
                        }
                    avg_transmission_dict[patch_generator][test_generator][language]["avg_request_token_size"] += request
                    avg_transmission_dict[patch_generator][test_generator][language]["avg_response_token_size"] += response

    for patch_generator in avg_transmission_dict:
        for test_generator in avg_transmission_dict[patch_generator]:
            for language in avg_transmission_dict[patch_generator][test_generator]:
                avg_transmission_dict[patch_generator][test_generator][language]["avg_request_token_size"] /= len(transmission_dict[patch_generator][test_generator][language]["request"])
                avg_transmission_dict[patch_generator][test_generator][language]["avg_response_token_size"] /= len(transmission_dict[patch_generator][test_generator][language]["response"])
    return avg_transmission_dict


def get_ci_result_count(line: str):
    pass_count = 0
    fail_count = 0
    ret = re.findall(r"ci_name: (.+), result_str: (.+)", line)
    if len(ret) == 0:
        ret = re.findall(r"step_name: (.+), result_str: (.+)", line)
        if len(ret) == 0:
            return 0, 0
        ci_name, result_str = ret[0]
    else:
        ci_name, result_str = ret[0]
    for each in result_str:
        if each == 'P':
            pass_count += 1
        elif each == 'F':
            fail_count += 1
    return pass_count, fail_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--arena_log_dir", type=str, default="./evaluations/")
    args = parser.parse_args()

    arena_log_dir = args.arena_log_dir
    result_dict = {}
    percent_result_dict = {}
    transmission_dict = {}
    all_language_summary_dict = {}
    fix_attempt_dict = {}
    all_language_fix_attempt_dict = {}
    ci_result_dict = {}
    all_language_ci_result_dict = {}

 
    logname_pattern = r'(.+)_vs_(.+)_(.+).log'
    final_result_pattern = r'\[FINAL_RESULT\].*?(?=-----------------------------------)'
    
    for log_file in os.listdir(arena_log_dir):
        logname_match = re.match(logname_pattern, log_file)
        patch_generator, test_generator, language = logname_match.groups()
        print(patch_generator, test_generator, language)
        if patch_generator not in result_dict:
            transmission_dict[patch_generator] = {}
            result_dict[patch_generator] = {}
            percent_result_dict[patch_generator] = {}
            all_language_summary_dict[patch_generator] = {}
            fix_attempt_dict[patch_generator] = {}
            all_language_fix_attempt_dict[patch_generator] = {}
            ci_result_dict[patch_generator] = {}
            all_language_ci_result_dict[patch_generator] = {}
        if test_generator not in result_dict[patch_generator]:
            transmission_dict[patch_generator][test_generator] = {}
            result_dict[patch_generator][test_generator] = {}
            percent_result_dict[patch_generator][test_generator] = {}
            all_language_summary_dict[patch_generator][test_generator] = {}
            fix_attempt_dict[patch_generator][test_generator] = {}
            all_language_fix_attempt_dict[patch_generator][test_generator] = 0
            ci_result_dict[patch_generator][test_generator] = {}
            all_language_ci_result_dict[patch_generator][test_generator] = {
                "pass_count": 0,
                "fail_count": 0
            }
        if language not in result_dict[patch_generator][test_generator]:
            transmission_dict[patch_generator][test_generator][language] = {
                "request": [],
                "response": []
            }
            result_dict[patch_generator][test_generator][language] = {}
            percent_result_dict[patch_generator][test_generator][language] = {}
            fix_attempt_dict[patch_generator][test_generator][language] = {}
            ci_result_dict[patch_generator][test_generator][language] = {
                "pass_count": 0,
                "fail_count": 0
            }
        if log_file.endswith(".log"):
            print(os.path.join(arena_log_dir, log_file))
            with open(os.path.join(arena_log_dir, log_file), "r") as f:
                lines = f.readlines()
                for line in lines:
                    # battle result
                    if "[FINAL_RESULT]" in line:
                        key, value = dispatch_final_result_item(result_dict, line)
                        if key == None:
                            continue
                        if key not in result_dict[patch_generator][test_generator][language]:
                            result_dict[patch_generator][test_generator][language][key] = set()
                            result_dict[patch_generator][test_generator][language][key].add(0)
                        elif isdigit(value):
                            result_dict[patch_generator][test_generator][language][key].add(float(value))
                    # request/response token size
                    if "Sending request size" in line:
                        request, response = get_api_transmission(line)
                        if request is not None and response is not None:
                            transmission_dict[patch_generator][test_generator][language]["request"].append(request)
                            transmission_dict[patch_generator][test_generator][language]["response"].append(response)
                    # ci result
                    if ("ci_name:" in line or "step_name:" in line) and "result_str:" in line:
                        pass_count, fail_count = get_ci_result_count(line)
                        ci_result_dict[patch_generator][test_generator][language]["pass_count"] += pass_count
                        ci_result_dict[patch_generator][test_generator][language]["fail_count"] += fail_count

    for patch_generator in result_dict:
        for test_generator in result_dict[patch_generator]:
            for language in result_dict[patch_generator][test_generator]:
                for key in result_dict[patch_generator][test_generator][language]:
                    result_dict[patch_generator][test_generator][language][key] = get_max_abs_value(result_dict[patch_generator][test_generator][language][key])

    for patch_generator in result_dict:
        for test_generator in result_dict[patch_generator]:
            total_p = 0
            total_q = 0
            for language in result_dict[patch_generator][test_generator]:
                fix_attempt_dict[patch_generator][test_generator][language] = abs(result_dict[patch_generator][test_generator][language]['patch_agent_score'])
                all_language_fix_attempt_dict[patch_generator][test_generator] += fix_attempt_dict[patch_generator][test_generator][language]
                all_language_ci_result_dict[patch_generator][test_generator]['pass_count'] += ci_result_dict[patch_generator][test_generator][language]["pass_count"]
                all_language_ci_result_dict[patch_generator][test_generator]['fail_count'] += ci_result_dict[patch_generator][test_generator][language]["fail_count"]
                p = result_dict[patch_generator][test_generator][language]['verified_patch_agent_score']
                q = result_dict[patch_generator][test_generator][language]['verified_test_agent_score']
                total_p += p
                total_q += q
                if q != .0:
                    percent_result_dict[patch_generator][test_generator][language]['verified_patch_agent_score'] = p / (p + q)
                    percent_result_dict[patch_generator][test_generator][language]['verified_test_agent_score'] = q / (p + q)
                else:
                    percent_result_dict[patch_generator][test_generator][language]['verified_patch_agent_score'] = 1.0
                    percent_result_dict[patch_generator][test_generator][language]['verified_test_agent_score'] = 0.0
                if p != .0:
                    fix_attempt_dict[patch_generator][test_generator][language] /= p
                else:
                    fix_attempt_dict[patch_generator][test_generator][language] = 0.0
            all_language_fix_attempt_dict[patch_generator][test_generator] /= total_p
            if total_p + total_q != .0:
                all_language_summary_dict[patch_generator][test_generator]['verified_patch_agent_score'] = total_p / (total_p + total_q)
                all_language_summary_dict[patch_generator][test_generator]['verified_test_agent_score'] = total_q / (total_p + total_q)
            else:
                all_language_summary_dict[patch_generator][test_generator]['verified_patch_agent_score'] = 1.0
                all_language_summary_dict[patch_generator][test_generator]['verified_test_agent_score'] = 0.0
            all_language_ci_result_dict[patch_generator][test_generator]['pass_rate'] = all_language_ci_result_dict[patch_generator][test_generator]['pass_count'] / (all_language_ci_result_dict[patch_generator][test_generator]['pass_count'] + all_language_ci_result_dict[patch_generator][test_generator]['fail_count'])

    # print(result_dict)
    # print('')
    print(percent_result_dict)
    print('')
    avg_transmission_dict = compute_average_token_size(transmission_dict)
    print(avg_transmission_dict)
    print('')
    print(all_language_summary_dict)
    print('')
    print(fix_attempt_dict)
    print('')
    print(all_language_fix_attempt_dict)
    print('')
    print(all_language_ci_result_dict)
    print('')