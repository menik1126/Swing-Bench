import logging
import sys
import os
import platform
import subprocess

from copy import deepcopy
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from typing import List, Tuple
from swebench.harness.constants.swing_constants import SwingbenchInstance
from swebench.harness.swing_utils import (
    load_swingbench_dataset,
    load_swingbench_dataset_json,
)

from swebench.harness.agent.verifier import PatchVerifier, TestVerifier, PatchGenerator, TestGenerator
from swebench.harness.agent.editor import CodeEditorBase, RawDataCodeEditor
from swebench.harness.agent.retriever import BM25DiskRetriever, Retriever

from swebench.harness.swing_utils import merge_diffs

DEBUG_ONE_SHOT = False

if platform.system() == "Linux":
    import resource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_battle.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("agent_battle")


def check_repo_exists(repo: str, src_folder: str) -> None:
    print(f'Checking repo existence: {repo}')
    if src_folder == '':
        return

    # check if the original repo is exists
    if not os.path.exists(repo):
        print(f'repo {repo} does not exist. Cloning...')
        repo_owner, repo_name = repo.split("/")
        repo_url = f"https://github.com/{repo}"
        repo_path = os.path.join(src_folder, f"{repo_owner}__{repo_name}")
        subprocess.run(["git", "clone", repo_url, repo_path, "--recursive"])


def construct_base_instance(data: SwingbenchInstance) -> SwingbenchInstance:

    base_instance = deepcopy(data)
    base_instance.patch = ''
    base_instance.test_patch = ''
    base_instance.merge_commit_sha = base_instance.base_commit

    return base_instance


def check_generated_patch(original_patch_result: dict, golden_patch_result: dict, generated_patch_result: dict) -> bool:

    # [result format]
    # "result" = {
    #     "ci_1": {
    #       "returncode": number,
    #       "test_results": {
    #         "passed": passed_tests,
    #         "failed": failed_tests,
    #         "skipped": skipped_tests,
    #       },
    #       "unit_test": [passed, failed, skipped]
    #     },
    # }

    failed_rules = set(["FPF", "PPF"])

    result = {}
    if not (original_patch_result['result'].keys() == \
            golden_patch_result['result'].keys() == \
            generated_patch_result['result'].keys()):
        print('##############################')
        print('check_generated_patch failed')
        print(f'original_patch_result: {original_patch_result["result"].keys()}')
        print(f'golden_patch_result: {golden_patch_result["result"].keys()}')
        print(f'generated_patch_result: {generated_patch_result["result"].keys()}')
        print('##############################')
        return None
    ci_name_list = original_patch_result['result'].keys()

    for ci_name in ci_name_list:
        result_str = ''
        if original_patch_result['result'][ci_name]['returncode'] != 0:
            result_str += 'F'
        else:
            result_str += 'P'

        if golden_patch_result['result'][ci_name]['returncode'] != 0:
            result_str += 'F'
        else:
            result_str += 'P'

        if generated_patch_result['result'][ci_name]['returncode'] != 0:
            result_str += 'F'
        else:
            result_str += 'P'

        if result_str in failed_rules:
            result[ci_name] = False
        else:
            result[ci_name] = True
        print(f'ci_name: {ci_name}, result_str: {result_str}')

        # Collect step results
        step_name_list = sorted(generated_patch_result['result'][ci_name]['test_results']["success"] + \
                                generated_patch_result['result'][ci_name]['test_results']["failure"] + \
                                generated_patch_result['result'][ci_name]['test_results']["skipped"])
        for step_name in step_name_list:
            result_str = ''
            if step_name in original_patch_result['result'][ci_name]['test_results']["success"]:
                result_str += 'P'
            else:
                result_str += 'F'

            if step_name in golden_patch_result['result'][ci_name]['test_results']["success"]:
                result_str += 'P'
            elif step_name in golden_patch_result['result'][ci_name]['test_results']["failure"]:
                result_str += 'F'
            else:
                result_str += 'P'

            if step_name in generated_patch_result['result'][ci_name]['test_results']["success"]:
                result_str += 'P'
            elif step_name in generated_patch_result['result'][ci_name]['test_results']["failure"]:
                result_str += 'F'
            else:
                result_str += 'P'

            if result_str in failed_rules:
                result[step_name] = False
            else:
                result[step_name] = True

            print(f'step_name: {step_name}, result_str: {result_str}')
    return result


def check_generated_test(golden_patch_result: dict, generated_test_result: dict) -> bool:

    # [result format]
    # test_results = {
    #     "ci_1": {
    #         "passed": passed_tests,
    #         "failed": failed_tests,
    #         "skipped": skipped_tests,
    #         "failure_details": {}
    #     }, ...
    # }

    failed_rules = set(["FP", "PF"])

    result = {}

    ci_name_list = generated_test_result['result'].keys()
    for ci_name in ci_name_list:
        result_str = ''
        if ci_name in golden_patch_result and golden_patch_result['result'][ci_name]['returncode'] != 0:
            result_str += 'F'
        else:
            result_str += 'P'

        if ci_name in generated_test_result and generated_test_result['result'][ci_name]['returncode'] != 0:
            result_str += 'F'
        else:
            result_str += 'P'

        if result_str in failed_rules:
            result[ci_name] = False
        else:
            result[ci_name] = True
        print(f'ci_name: {ci_name}, result_str: {result_str}')

        # Collect step results
        step_name_list = sorted(generated_test_result['result'][ci_name]['test_results']["success"] + \
                                generated_test_result['result'][ci_name]['test_results']["failure"] + \
                                generated_test_result['result'][ci_name]['test_results']["skipped"])
        for step_name in step_name_list:
            result_str = ''
            if step_name in golden_patch_result['result'][ci_name]['test_results']["success"]:
                result_str += 'P'
            else:
                result_str += 'F'
            if step_name in generated_test_result['result'][ci_name]['test_results']["success"]:
                result_str += 'P'
            elif step_name in generated_test_result['result'][ci_name]['test_results']["failure"]:
                result_str += 'F'
            else:
                result_str += 'P'

            if result_str in failed_rules:
                result[step_name] = False
            else:
                result[step_name] = True
            print(f'step_name: {step_name}, result_str: {result_str}')

    return result


def is_valid_result(result: dict) -> bool:
    if result == None:
        return False
    for each in result:
        if not each:
            return False
    return True


def check_patches(golden_patch_result: dict, patch_with_test_verify_result: dict) -> bool:
    if not golden_patch_result['result'].keys() == patch_with_test_verify_result['result'].keys():
        print('##############################')
        print('check_patches failed')
        print(f'golden_patch_result: {golden_patch_result["result"].keys()}')
        print(f'patch_with_test_verify_result: {patch_with_test_verify_result["result"].keys()}')
        print('##############################')
        return [False]
    ci_name_list = golden_patch_result['result'].keys()
    for ci_name in ci_name_list:
        if golden_patch_result['result'][ci_name]['returncode'] != patch_with_test_verify_result['result'][ci_name]['returncode']:
            return [False]
    return [True]


# TODO(haoran): concurrent execution
def battle_one_turn(
    dataset: List[SwingbenchInstance],
    patch_generator: PatchGenerator,
    test_generator: TestGenerator,
    patch_verifier: PatchVerifier,
    test_verifier: TestVerifier,
    turns: int = 1,
    workdir: str = '',
    src_folder: str = '',
) -> List[int]:
    """
    The logic of model battle.

    Args:
        dataset (List[SwingbenchInstance]): a list containing multiple instances of SwingbenchInstance
        patch_generator (PatchGenerator): an instance of PatchGenerator
        test_generator (TestGenerator): an instance of TestGenerator
        patch_verifier (PatchVerifier): an instance of PatchVerifier
        test_verifier (TestVerifier): an instance of TestVerifier
        turns (int): the number of turns in the battle
    """
    patch_agent_score = 0
    test_agent_score = 0
    verified_patch_agent_score = 0
    verified_test_agent_score = 0

    for data in dataset:
        # -- Prepare Stage:
        # 0. original patch CI: checkout base_commit  -> apply original (base_commit) patch -> run CI -> results_0.

        check_repo_exists(data.repo, os.path.join(workdir, src_folder))

        base_instance = construct_base_instance(data)
        # clear all patch information, only need to keep the base_commit
        original_patch_result = patch_verifier.verify(base_instance, '') # results_0
        print(f'original_patch_result: {original_patch_result["result"]}')

        # 1. golden patch CI: checkout base_commit -> apply golden (merged_commit) patch -> run CI -> results_1.
        golden_patch_result = patch_verifier.verify(data, '') # results_1
        print(f'golden_patch_result: {golden_patch_result["result"]}')

        for _ in range(turns):
            # -- Stage 1: patch, test individually generation and verification.
            # Case 1: patch generation and verification.
            patch = patch_generator.generate(data)
            if patch is None:
                print('patch is None')
            else:
                print(f"patch is {patch}")
            generated_patch_result = patch_verifier.verify(data, patch) # results_2
            print(f'generated_patch_result: {generated_patch_result["result"]}')

            # Check if generated patch is valid.
            patch_verify_result = check_generated_patch(original_patch_result,
                                                        golden_patch_result,
                                                        generated_patch_result)
            print(f'patch_verify_result: {patch_verify_result}')

            if not is_valid_result(patch_verify_result):
                patch_agent_score -= 1
                continue

            # Case 2: test generation and verification.
            test = test_generator.generate(data, patch)
            if test is None:
                print('test is None')
            else:
                print(f"test is {test}")
            generated_test_result = test_verifier.verify(data, test) # results_3
            print(f'generated_test_result: {generated_test_result["result"]}')

            # Check if generated test is valid.
            test_verify_result = check_generated_test(golden_patch_result,
                                                      generated_test_result)
            print(f'test_verify_result: {test_verify_result}')

            if not is_valid_result(test_verify_result):
                test_agent_score -= 1
                continue

            # -- Stage 2: patch and test generation and verification.

            # Case 3: with new patch, with new generated tests (Verifying)
            try:
                patch_with_test = merge_diffs(patch, test)
                patch_with_test_verify_result = test_verifier.verify(data, patch_with_test) # results_4
                print(f'patch_with_test_verify_result: {patch_with_test_verify_result["result"]}')
            except Exception as e:
                print(f"Error merging diffs: {e}")
                print(f"Patch: {patch}")
                print(f"Test: {test}")
                continue
            
            # Check if patch_with_test is valid.
            patch_with_test_verify_result = check_patches(golden_patch_result,
                                                          patch_with_test_verify_result)
            print(f'patch_with_test_verify_result: {patch_with_test_verify_result}')
            if not is_valid_result(patch_with_test_verify_result):
                verified_test_agent_score += 1
            else:
                verified_patch_agent_score += 1
            
            if DEBUG_ONE_SHOT:
                break
        print(f'patch generator: {patch_generator.model_name()}')
        print(f'test generator: {test_generator.model_name()}')
        print(f'patch_agent_score: {patch_agent_score}')
        print(f'test_agent_score: {test_agent_score}')
        print(f'verified_patch_agent_score: {verified_patch_agent_score}')
        print(f'verified_test_agent_score: {verified_test_agent_score}')
        print('-----------------------------------')
        if DEBUG_ONE_SHOT:
            break

    print('-----------------------------------------------------')
    return [patch_agent_score, test_agent_score]


def battle(
    dataset: List[SwingbenchInstance],
    workdir: str,
    src_folder: str,
    code_editor_lhs: CodeEditorBase,
    code_editor_rhs: CodeEditorBase,
    retriever: Retriever,
    ci_tool_name: str,
    retrieve_file_num: int = 5,
    agent_retry_times: int = 3,
    turns: int = 1,
    port_range: str = '10000-11000'
) -> Tuple[List[int], List[int]]:
    
    begin_port, end_port = map(int, port_range.split('-'))
    
    def get_roles(code_editor_lhs, code_editor_rhs):
        patch_verifier = PatchVerifier(ci_tool_name=ci_tool_name, 
            workdir=workdir, 
            src_folder=src_folder, 
            begin_port=begin_port,
            end_port=end_port
        )
        test_verifier = TestVerifier(ci_tool_name=ci_tool_name, 
            workdir=workdir, 
            src_folder=src_folder, 
            begin_port=begin_port,
            end_port=end_port
        )
        patch_generator = PatchGenerator(workdir=workdir, 
            src_folder=src_folder, 
            code_editor=code_editor_lhs,
            retriever=retriever,
            retrieve_file_num=retrieve_file_num,
            agent_retry_times=agent_retry_times,
            max_chunk_num=16,
            chunk_type='block'
        )
        test_generator = TestGenerator(workdir=workdir, 
            src_folder=src_folder, 
            code_editor=code_editor_rhs,
            retriever=retriever,
            retrieve_file_num=retrieve_file_num,
            agent_retry_times=agent_retry_times,
            max_chunk_num=16,
            chunk_type='block'
        )
        return patch_generator, test_generator, patch_verifier, test_verifier

    patch_generator, test_generator, patch_verifier, test_verifier = \
        get_roles(code_editor_lhs, code_editor_rhs)
    result = battle_one_turn(dataset,
                             patch_generator,
                             test_generator,
                             patch_verifier,
                             test_verifier,
                             turns=turns,
                             workdir=workdir,
                             src_folder=src_folder)

    if DEBUG_ONE_SHOT:
        return result, result

    patch_generator, test_generator, patch_verifier, test_verifier = \
        get_roles(code_editor_rhs, code_editor_lhs)
    result_rev = battle_one_turn(dataset,
                                 patch_generator,
                                 test_generator,
                                 patch_verifier,
                                 test_verifier,
                                 turns=turns,
                                 workdir=workdir,
                                 src_folder=src_folder)
    
    return result, result_rev


def main(
    language: str,
    dataset_name: str,
    workdir: str,
    src_folder: str,
    open_file_limit: int,
    api_key_lhs: str,
    base_url_lhs: str,
    model_lhs: str,
    tok_model_lhs: str,
    api_key_rhs: str,
    base_url_rhs: str,
    model_rhs: str,
    tok_model_rhs: str,
    retriever_index_dir: str,
    ci_tool_name: str,
    turns: int = 1,
    split: str = "train",
    port_range: str = '10000-11000'
) -> Tuple[List[int], List[int]]:
    """
    Runs evaluation to battle two agents on a dataset.
    """

    if platform.system() == "Linux":
        print(f"Setting open file limit to {open_file_limit}")
        resource.setrlimit(resource.RLIMIT_NOFILE, (open_file_limit, open_file_limit))

    print('------------ processing dataset ------------')
    print(f'language: {language}')
    print(f'dataset_name: {dataset_name}')
    print(f'workdir: {workdir}')
    print(f'src_folder: {src_folder}')
    print(f'open_file_limit: {open_file_limit}')
    print(f'api_key_lhs: {api_key_lhs}')
    print(f'base_url_lhs: {base_url_lhs}')
    print(f'model_lhs: {model_lhs}')
    print(f'tok_model_lhs: {tok_model_lhs}')
    print(f'api_key_rhs: {api_key_rhs}')
    print(f'base_url_rhs: {base_url_rhs}')
    print(f'model_rhs: {model_rhs}')
    print(f'tok_model_rhs: {tok_model_rhs}')
    print(f'retriever_index_dir: {retriever_index_dir}')
    print(f'ci_tool_name: {ci_tool_name}')

    with_ci = 'act' == ci_tool_name

    if "jsonl" in dataset_name:
        dataset = load_swingbench_dataset_json(dataset_name)
    else:
        dataset = load_swingbench_dataset(dataset_name, language, split=split, with_ci=with_ci)
    print(f'dataset size: {len(dataset)}')

    retriever = BM25DiskRetriever(index_dir=retriever_index_dir)
    print(f'retriever: {retriever}')

    code_editor_lhs = RawDataCodeEditor(
        api_key=api_key_lhs,
        base_url=base_url_lhs,
        model=model_lhs,
        tok_model=tok_model_lhs
    )
    print(f'code_editor_lhs: {code_editor_lhs}')

    code_editor_rhs = RawDataCodeEditor(
        api_key=api_key_rhs,
        base_url=base_url_rhs,
        model=model_rhs,
        tok_model=tok_model_rhs
    )
    print(f'code_editor_rhs: {code_editor_rhs}')

    retrieve_file_num = 2
    agent_retry_times = 3

    result, result_rev = battle(dataset,
                                workdir,
                                src_folder,
                                code_editor_lhs,
                                code_editor_rhs,
                                retriever,
                                ci_tool_name,
                                retrieve_file_num,
                                agent_retry_times,
                                turns,
                                port_range)

    print('------------ result ------------')
    print(f'result: {result}')
    print(f'result_rev: {result_rev}')

    print('------------ end of processing dataset ------------')
    print('\n')
    exit(0)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Runs evaluation harness to compare two agents on a dataset",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    
    # Common args
    parser.add_argument(
        "--dataset_name",
        default="SwingBench/SwingBench",
        type=str,
        help="Name of dataset or path to JSON file.",
    )

    parser.add_argument(
        "--language", type=str, default="rust", help="Language of the dataset"
    )

    # default models
    # base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"#'https://dashscope.aliyuncs.com/compatible-mode/v1/'
    # api_key = "sk-826b874003eb4f309bd65c7a6f0f79b5"#'sk-826b874003eb4f309bd65c7a6f0f79b5'
    # model = "qwen-max-latest"#'qwq-plus'

    base_url = "http://localhost:8000/v1"
    api_key = "no-api-key"
    model = "/home/mnt/wdxu/models/Qwen2.5-Coder-7B-Instruct"
    # Local execution args
    parser.add_argument(
        "--workdir", type=str, default=os.environ["SWING_TESTBED_PATH"], help="Work directory"
    )
    parser.add_argument(
        "--src_folder", type=str, default=os.environ["SWING_REPOS_DIR_PATH"], help="Source code folder"
    )
    parser.add_argument(
        "--retriever_index_dir", type=str, default=os.environ["SWING_INDEXES_PATH"], help="Retriever index directory"
    )
    parser.add_argument(
        "--open_file_limit", type=int, default=4096, help="Open file limit"
    )
    parser.add_argument(
        "--api_key_lhs", type=str, default=api_key, help="API key for lhs"
    )
    parser.add_argument(
        "--base_url_lhs", type=str, default=base_url, help="Base URL for lhs"
    )
    parser.add_argument(
        "--model_lhs", type=str, default=model, help="Model for lhs"
    )
    parser.add_argument(
        "--api_key_rhs", type=str, default=api_key, help="API key for rhs"
    )
    parser.add_argument(
        "--base_url_rhs", type=str, default=base_url, help="Base URL for rhs"
    )
    parser.add_argument(
        "--model_rhs", type=str, default=model, help="Model for rhs"
    )

    parser.add_argument(
        "--ci_tool_name", type=str, default='act', help="CI tool name"
    )
    parser.add_argument(
        "--turns", type=int, default=1, help="Number of turns"
    )
    parser.add_argument(
        "--split", type=str, default=None, help="Split"
    )
    parser.add_argument(
        "--tok_model_lhs", type=str, default=None, help="Tokenizer model for lhs"
    )
    parser.add_argument(
        "--tok_model_rhs", type=str, default=None, help="Tokenizer model for rhs"
    )
    parser.add_argument(
        "--port_range", type=str, default='10000-11000', help="Port range"
    )
    args = parser.parse_args()

    
    main(**vars(args))