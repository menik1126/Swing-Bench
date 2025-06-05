import json
import argparse

from swebench.harness.constants import (
    FAIL_TO_FAIL,
    FAIL_TO_PASS,
    PASS_TO_FAIL,
    PASS_TO_PASS,
)

JUDGE_SUCCESS = 'success'
JUDGE_FAILURE = 'failure'


def process_report_results(report_results):
    job_step_result = {}
    for result in report_results:
        if (result["job"] is not None and 
            result["step"] != '' and 
            result["stepResult"] is not None):
            
            if result["job"] not in job_step_result:
                job_step_result[result["job"]] = {}
            job_step_result[result["job"]][result["step"]] = result["stepResult"]
    return job_step_result


def get_step_transition(base_state, merged_state):
    if base_state == JUDGE_SUCCESS:
        return PASS_TO_PASS if merged_state == JUDGE_SUCCESS else PASS_TO_FAIL
    else:
        return FAIL_TO_PASS if merged_state == JUDGE_SUCCESS else FAIL_TO_FAIL


def main(based_report, merged_report, debug_tag=False):
    based_report = json.load(open(based_report))
    merged_report = json.load(open(merged_report))

    based_job_step_result = process_report_results(based_report["processed_output"])
    merged_job_step_result = process_report_results(merged_report["processed_output"])

    job_step_result_judgement = {}

    for job in based_job_step_result:
        job_step_result_judgement[job] = {}
        for step in based_job_step_result[job]:
            if step not in merged_job_step_result.get(job, {}):
                base_state = based_job_step_result[job][step]
                job_step_result_judgement[job][step] = get_step_transition(base_state, JUDGE_FAILURE)
            else:
                base_state = based_job_step_result[job][step]
                merged_state = merged_job_step_result[job][step]
                job_step_result_judgement[job][step] = get_step_transition(base_state, merged_state)

    for job in merged_job_step_result:
        if job not in job_step_result_judgement:
            job_step_result_judgement[job] = {}
        for step in merged_job_step_result[job]:
            if step not in based_job_step_result.get(job, {}):
                base_state = merged_job_step_result[job][step]
                job_step_result_judgement[job][step] = get_step_transition(base_state, JUDGE_SUCCESS)
            else:
                base_state = based_job_step_result[job][step]
                merged_state = merged_job_step_result[job][step]
                job_step_result_judgement[job][step] = get_step_transition(base_state, merged_state)
    if debug_tag:
        for job in job_step_result_judgement:
            print(job)
            for step in job_step_result_judgement[job]:
                print(step, job_step_result_judgement[job][step])

    return job_step_result_judgement


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--based-report", type=str, required=True)
    parser.add_argument("--merged-report", type=str, required=True)
    args = parser.parse_args()

    main(args.based_report, args.merged_report, debug_tag=True)
