# Note that the dataset is not included in the repository. We add it to the gitignore file.

import os
import re
import time
import json
import re
import concurrent.futures

from datasets import load_dataset, load_from_disk
from pathlib import Path
from openai import OpenAI
from typing import Optional
from tqdm import tqdm

from swingarena.harness.agent.swing_chunker import CodeChunker, CodeReranker


parquet_dir = Path("../../dataset/swing-bench/")
hf_dir = Path("../../dataset/swing-bench-hf-row")
filtered_hf_dir = Path("../../dataset/swing-bench-hf-filtered")
annotated_jsonl_dir = Path("../../dataset/swing-bench-annotated-jsonl")


def build_dataset():

    if not filtered_hf_dir.exists():
        os.environ["HF_TOKEN"] = os.environ["SWINGBENCH_HF_TOKEN"]

        if not parquet_dir.exists():
            os.system(
                f"huggingface-cli download --repo-type dataset SwingBench/SwingBench-data --local-dir {parquet_dir}"
            )

        if not hf_dir.exists():
            dataset = load_dataset(
                "parquet",
                data_files={
                    "rust": str(parquet_dir / "data" / "rust-*.parquet"),
                    "cpp": str(parquet_dir / "data" / "cpp-*.parquet"),
                    "python": str(parquet_dir / "data" / "python-*.parquet"),
                    "go": str(parquet_dir / "data" / "go-*.parquet"),
                },
            )

            dataset.save_to_disk(hf_dir)
        else:
            dataset = load_from_disk(hf_dir)

        filtered_dataset = dataset.filter(lambda example: example["ci_name_list"] != [])

        filtered_dataset.save_to_disk(filtered_hf_dir)
    else:
        dataset = load_from_disk(filtered_hf_dir)

    print(dataset)
    return dataset


def call_api(
    prompt: str, api_key: str, base_url: str, model: str = ""
) -> Optional[str]:
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.0,
        )

        return response.choices[0].message.content
    except Exception as e:
        print(f"API call failed: {str(e)}")
        return None


def create_difficulty_prompt(instance):
    prompt = f"""
    You are a senior software engineer with over 10 years of solid experience in rust, cpp, python, and go. You possess a deep understanding of these languages and their standard libraries, along with a strong sense of problem difficulty.

    Your task is to evaluate the difficulty and clarity of a coding problem from a GitHub repository, given its "Problem Statement" and "Code Changes". You need to consider the following factors:

    1. **Clarity and complexity of the problem description:** Is the problem goal, input, output, and constraints clearly defined? Are there any ambiguities or missing critical details? Is the problem's logic inherently complex?
    2. **Scope and depth of code changes required to the whole codebase:** Does the modification involve a single file/function or multiple modules? Does it require understanding interactions between different parts of the codebase? What is the overall amount of code change? Does it impact the system's architecture?
    3. **Number of technical concepts that need to be understood:** What specific programming language features, libraries, algorithms, design patterns, or domain-specific knowledge are required to solve this problem? How complex are these concepts?
    4. **Potential edge cases and error handling requirements:** Does the problem statement mention any specific edge cases or error conditions to consider? Does the code change require adding or modifying error handling logic? How complex are these edge cases?

    Based on these factors, you will provide a Clarity Score and a Difficulty Score with detailed explanations.

    Here is the problem statement and code changes, delimited by '&&&':

    Problem Statement:
    &&&
    {instance["problem_statement"]}
    &&&

    Code Changes:
    &&&
    {instance["patch"]}
    &&&

    First, provide your judgment of the Clarity Scoring (0, 1, 2, 3) of the problem, along with your explanation:

    - 0 (Invalid): Statement is incomprehensible or code changes are unrelated.
    - 1 (Significant Ambiguities): Valid but lacks critical details (e.g., no input/output format).
    - 2 (Mostly Clear): Valid, clear, but minor details missing (e.g., edge cases not specified).
    - 3 (Comprehensive): Valid, clear, with detailed requirements and examples.

    Then, provide a difficulty score between 0.0 and 1.0, along with your explanation:

    - 0.0-0.2: Very easy, requires only basic code modifications (e.g., fixing a typo, changing a constant).
    - 0.2-0.4: Easy, requires understanding some code logic and making simple function or statement modifications (e.g., fixing a simple bug, adding a basic feature).
    - 0.4-0.6: Medium, requires understanding multiple concepts and making complex modifications across several files, potentially involving some edge case handling (e.g., implementing a new module with moderate complexity).
    - 0.6-0.8: Hard, requires deep understanding of the codebase architecture and complex modifications with significant impact, involving handling numerous edge cases and potential performance considerations (e.g., refactoring a core component, implementing a complex algorithm).
    - 0.8-1.0: Very hard, requires advanced technical knowledge, extensive experience, and tackling highly challenging problems with intricate logic, potentially involving system-level considerations or complex domain-specific knowledge (e.g., implementing a new distributed consensus protocol).

    Please return your response in the following structured format:
    <clarity_score>integer between 0 and 3</clarity_score>
    <clarity_explanation>Your explanation for the clarity score.</clarity_explanation>
    <difficulty>float between 0.00 and 1.00</difficulty>
    <difficulty_explanation>Your explanation for the difficulty score.</difficulty_explanation>
    """
    return prompt


def extract_code_snippet_from_patch(patch: str):
    result_lines = []
    for line in patch.splitlines():
        if line.startswith('+++') or line.startswith('---') or line.startswith('diff --git') or line.startswith('@@'):
            continue
        if not line.startswith('-'):
            if line.startswith('+'):
                result_lines.append(line[1:])
            else:
                result_lines.append(line)
        if not line.startswith('+'):
            if line.startswith('-'):
                result_lines.append(line[1:])
            else:
                result_lines.append(line)
        
    result =    '\n'.join(result_lines)
    return result


def chunk_instance(instance, chunk_type: str, language: str, max_chunk_num: int, chunker: CodeChunker = None, reranker: CodeReranker = None):
    code_snippet = extract_code_snippet_from_patch(instance["patch"])
    chunk_list = chunker.chunk(code_snippet=code_snippet)
    for chunk in chunk_list:
        chunk['file_path'] = instance["instance_id"]
    print(f"file_path: {instance['instance_id']} has {len(chunk_list)} code block(s).")
    top_chunks = []
    if chunk_list and reranker.initialized:
        top_chunks = reranker.rerank(chunk_list, instance["problem_statement"], top_k=max_chunk_num)

    context_info = []
    for chunk in top_chunks:
        context_info.append(f"File: {chunk['file_path']}\n"
                            f"Type: {chunk['type']}\n"
                            f"Name: {chunk['name']}\n"
                            f"Lines: {chunk['start_line']}-{chunk['end_line']}\n"
                            f"Code:\n{chunk['code']}\n")

    instance['patch'] = "\n".join(context_info)

    return instance


def estimate_clarity_and_difficulty(
    instance, api_key, base_url, model, max_attempts: int = 3, need_chunk: bool = False, chunk_type: str = "function", language: str = "rust", max_chunk_num: int = 3, chunker: CodeChunker = None, reranker: CodeReranker = None
):
    if need_chunk:
        instance = chunk_instance(instance, chunk_type, language, max_chunk_num, chunker, reranker)

    prompt = create_difficulty_prompt(instance)
    for attempt in range(max_attempts):
        response = call_api(prompt, api_key, base_url, model)

        if not response:
            continue

        try:
            clarity_match = re.search(
                r"<clarity_score>([0-3])</clarity_score>", response
            )
            clarity_score = int(clarity_match.group(1)) if clarity_match else None

            clarity_explanation_match = re.search(
                r"<clarity_explanation>(.*?)</clarity_explanation>", response, re.DOTALL
            )
            clarity_explanation = (
                clarity_explanation_match.group(1)
                if clarity_explanation_match
                else "No explanation provided"
            )
            difficulty_match = re.search(
                r"<difficulty>([0-9.]+)</difficulty>", response
            )
            difficulty_score = (
                float(difficulty_match.group(1)) if difficulty_match else None
            )
            difficulty_explanation_match = re.search(
                r"<difficulty_explanation>(.*?)</difficulty_explanation>",
                response,
                re.DOTALL,
            )
            difficulty_explanation = (
                difficulty_explanation_match.group(1)
                if difficulty_explanation_match
                else "No explanation provided"
            )
            return (
                clarity_score,
                clarity_explanation,
                difficulty_score,
                difficulty_explanation,
            )
        except Exception as e:
            print(f"Prompt: {prompt}")
            print(f"Response: {response}")
            print(f"Error {attempt+1}/{max_attempts} parsing response: {str(e)}")
            continue
    print(f"Failed to parse response after {max_attempts} attempts")
    return None, None, None, None


def process_instances_parallel(
    instances, output_file, api_key, base_url, model, num_workers=50, max_attempts: int = 3, need_chunk: bool = False, chunk_type: str = "function", language: str = "rust", max_chunk_num: int = 3
):
    results = []

    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"创建目录: {output_dir}")

    # 读取已处理过的实例ID
    processed_instance_ids = set()
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    processed_instance_ids.add(data.get("instance_id"))
                except json.JSONDecodeError:
                    continue

    # 过滤出未处理的实例
    instances_to_process = []
    for instance in instances:
        instance_id = instance.get("instance_id")
        if instance_id not in processed_instance_ids:
            instances_to_process.append(instance)

    if not instances_to_process:
        print("所有实例已处理完毕，无需再次运行。")
        return results

    print(f"总共 {len(instances)} 个实例，其中 {len(instances_to_process)} 个待处理。")

    chunker = None
    reranker = None

    if need_chunk:
        chunker = CodeChunker(language=language, chunk_type=chunk_type)
        reranker = CodeReranker()

    # 只打开文件一次用于追加结果
    with open(output_file, "a") as f:
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            # 创建future到实例的映射
            future_to_instance = {
                executor.submit(
                    estimate_clarity_and_difficulty, instance, api_key, base_url, model, max_attempts, need_chunk, chunk_type, language, max_chunk_num, chunker, reranker
                ): instance
                for instance in instances_to_process
            }

            with tqdm(
                total=len(future_to_instance), desc="Evaluating difficulty"
            ) as progress:
                for future in concurrent.futures.as_completed(
                    list(future_to_instance.keys())
                ):
                    instance = future_to_instance[future]
                    try:
                        (
                            clarity,
                            clarity_explanation,
                            difficulty,
                            difficulty_explanation,
                        ) = future.result()
                        if (
                            clarity is not None
                            and difficulty is not None
                            and clarity_explanation is not None
                            and difficulty_explanation is not None
                        ):
                            instance_id = instance.get("instance_id")

                            result = {
                                "problem_statement": instance.get("problem_statement"),
                                "patch": instance.get("patch"),
                                "instance_id": instance_id,
                                "clarity": clarity,
                                "difficulty": difficulty,
                                "clarity_explanation": clarity_explanation,
                                "difficulty_explanation": difficulty_explanation,
                            }
                            results.append(result)
                            f.write(json.dumps(result) + "\n")
                            f.flush()
                    except Exception as e:
                        print(
                            f"Error processing instance {instance.get('instance_id')}: {str(e)}"
                        )
                    progress.update(1)

    return results
