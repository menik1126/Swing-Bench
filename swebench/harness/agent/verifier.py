import os
import sys

# 设置临时目录 - 在最开始设置
temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "temp")
os.makedirs(temp_dir, exist_ok=True)
os.environ['TMPDIR'] = temp_dir
os.environ['TEMP'] = temp_dir
os.environ['TMP'] = temp_dir

import copy
from abc import abstractmethod
from datetime import datetime
import subprocess
from uuid import uuid4
from swebench.harness.constants.swing_constants import SwingbenchInstance
from swebench.harness.router import CIToolBase
from swebench.harness.router import EVAL_HANDLER
from swebench.harness.agent.model import AgentProxy
from swebench.harness.agent.utils import TempDirectoryManager
import shutil
import tempfile
# 强制设置临时目录
tempfile.tempdir = temp_dir

from swebench.harness.agent.editor import generate_git_diff_batch
from swebench.harness.agent.retriever import Retriever
from swebench.harness.agent.editor import CodeEditorBase
from swebench.harness.utils import get_available_port_pool
from swebench.harness.swing_utils import merge_diffs

from swebench.harness.agent.swing_chunker import CodeChunker, CodeReranker

class Verifier:
    @abstractmethod
    def __init__(self, ci_tool: CIToolBase):
        raise NotImplementedError

    @abstractmethod
    def _extract_code(self, input: str):
        raise NotImplementedError

    @abstractmethod
    def verify(self, data: SwingbenchInstance, input: str):
        raise NotImplementedError


class Generator:
    @abstractmethod
    def __init__(self):
        raise NotImplementedError

    @abstractmethod
    def generate(self, data: SwingbenchInstance):
        raise NotImplementedError


class PatchGenerator(Generator):
    def __init__(self, workdir: str = "testbed", 
                 src_folder: str = "repos",
                 code_editor: CodeEditorBase = None,
                 retriever: Retriever = None,
                 retrieve_file_num: int = 20,
                 agent_retry_times: int = 3,
                 max_chunk_num: int = 3,
                 language = "rust",
                 chunk_type = "function"
                 ):
        self.workdir = workdir
        self.src_folder = src_folder
        self.code_editor = code_editor
        self.retriever = retriever
        self.retrieve_file_num = retrieve_file_num
        self.agent_retry_times = agent_retry_times
        self.chunker = CodeChunker(language=language, chunk_type=chunk_type)
        self.max_chunk_num = max_chunk_num
        self.reranker = CodeReranker()
    def model_name(self):
        return self.code_editor.model

    def generate(self, data: SwingbenchInstance):
        """
        Generate a patch for the given Swingbench instance.
        """
        print("Retrieving data files from retriever to data:{}".format(data))
        code_snippet = self.retriever.retrieve(data, self.src_folder, k=self.retrieve_file_num)
        print(f"self.retrieve_file_num: {self.retrieve_file_num}")
        if code_snippet is not None:
            print(f"len of code_snippet: {len(code_snippet)}")
            print(f"len(code_snippet['hits']): {len(code_snippet['hits'])}")
            print(f"code_snippet.keys: {code_snippet.keys()}")
        else:
            print('Warning: code_snippet is None')
            return None
        # print(f"code_snippet[hits].keys: {code_snippet['hits'][0].keys()}")
        # print(f"code_snippet[hits][0]: {code_snippet['hits'][0]}")
        # print(f"code_snippet[hits][0]['docid']: {code_snippet['hits'][0]['docid']}")
        
        all_chunks = []
        # Chunk the code snippet for each hit
        for hit in code_snippet['hits']:
            # Use self.chunker to chunk the code
            chunks = self.chunker.chunk(code_snippet=hit['contents'])
            # Add the chunk results to the hit and associate the original file path
            for chunk in chunks:
                chunk['file_path'] = hit['docid']
            hit['chunks'] = chunks
            all_chunks.extend(chunks)
            # Print the chunking information 
            print(f"File {hit['docid']} has {len(chunks)} code chunks")
 
        # Rerank the all code chunks
        print(f"Total chunks before reranking: {len(all_chunks)}")
        top_chunks = []
        total_tokens = self.code_editor.default_prompt_token_length
        if all_chunks and self.reranker.initialized:
            top_chunks = self.reranker.rerank(all_chunks, data.problem_statement, top_k=self.max_chunk_num)
            print(f"After reranking, selected top {len(top_chunks)} chunks:")
            for i, chunk in enumerate(top_chunks):
                total_tokens += len(self.code_editor.tokenizer.encode(chunk['code']))
                print(f'total_tokens: {total_tokens} in collected of max tokens: {self.code_editor.max_model_len}')
                if total_tokens > self.code_editor.max_model_len:
                    print(f"Total tokens: {total_tokens} > max tokens: {self.code_editor.max_model_len}, break")
                    top_chunks = top_chunks[:i - 1]
                    break
                print(f"  Top Chunk {i}: {chunk['type']} - {chunk['name']} (score: {chunk.get('similarity_score', 'N/A')})")
                print(f"    From file: {chunk['file_path']}")
                print(f"    Chunk length: {len(chunk['code'])}")
        
        # Build the new input based on the reranked code chunks
        chunk_file_path_list = [chunk['file_path'] for chunk in top_chunks]
        chunk_code_list = [chunk['code'] for chunk in top_chunks]
        
        # Build the metadata information related to the code chunks to help the model understand the context
        context_info = []
        for chunk in top_chunks:
            context_info.append(f"File: {chunk['file_path']}\n"
                              f"Type: {chunk['type']}\n"
                              f"Name: {chunk['name']}\n"
                              f"Lines: {chunk['start_line']}-{chunk['end_line']}\n"
                              f"Code:\n{chunk['code']}\n")
        
        # Add the context information to the problem statement
        # enhanced_problem = data.problem_statement + "\n\n" + "RELEVANT CODE BLOCKS:\n" + "\n".join(context_info)
        enhanced_problem = data.problem_statement
        # Use the original file list as a backup, and provide the code chunks
        file_path_list = [hit["docid"] for hit in code_snippet["hits"]]
        code_snippet_list = [hit["contents"] for hit in code_snippet["hits"]]
        
        # Call the editor with the enhanced problem description, and provide the original file and the code chunks
        response = self.code_editor.edit_code_batch(
            enhanced_problem,
            code_snippet_list,  # Original complete code
            file_path_list,     # Original file path
            role="patch",
            retry=self.agent_retry_times,
            chunks={ # Add the code chunks information as additional context
                "file_paths": chunk_file_path_list,
                "code_blocks": chunk_code_list,
                "metadata": top_chunks
            }
        )
        if response is None:
            print(f'patch generator response is None: {response}')
            return None

        base_path = f"{self.workdir}/{data.instance_id}_{str(uuid4())}"
        with TempDirectoryManager(base_path) as base_path:
            # convert repo path from x/y to x__y
            repo_path = f"{self.src_folder}/{data.repo.replace('/', '__')}"

            if os.path.exists(base_path):
                try:
                    # remove existing repo
                    shutil.rmtree(base_path)
                except Exception as e:
                    print(f"Error removing existing repo {base_path}: {e}. Skipping...")

            try:
                shutil.copytree(repo_path, base_path)
                subprocess.run(["git", "checkout", data.base_commit], cwd=base_path)
            except Exception as e:
                print(f"Error copying repo {repo_path} to {base_path}: {e}. Skipping...")
                return None

            patch = generate_git_diff_batch(response["code_edits"], base_path)
            if patch is None:
                print(f'generate_git_diff_batch merged failed. patch is None. code_edits: {response["code_edits"]}. base_path: {base_path}')
                return None

            return patch


class TestGenerator(Generator):
    def __init__(self, workdir: str = "testbed", 
                 src_folder: str = "repos",
                 code_editor: CodeEditorBase = None,
                 retriever: Retriever = None,
                 retrieve_file_num: int = 20,
                 agent_retry_times: int = 3,
                 max_chunk_num: int = 3,
                 language = "rust",
                 chunk_type = "function"
                 ):
        self.workdir = workdir
        self.src_folder = src_folder
        self.code_editor = code_editor
        self.retriever = retriever
        self.retrieve_file_num = retrieve_file_num
        self.agent_retry_times = agent_retry_times
        self.chunker = CodeChunker(language=language, chunk_type=chunk_type)
        self.max_chunk_num = max_chunk_num
        self.reranker = CodeReranker()
    
    def model_name(self):
        return self.code_editor.model

    def generate(self, data: SwingbenchInstance, generated_patch: str = None):
        # TODO(wdxu): remove this hack.
        data.hints_text += "test, testcase, unittest."
        code_snippet = self.retriever.retrieve(data, self.src_folder, k=self.retrieve_file_num)
        if code_snippet is not None:
            print(f"len of code_snippet: {len(code_snippet)}")
            print(f"len(code_snippet['hits']): {len(code_snippet['hits'])}")
            print(f"code_snippet.keys: {code_snippet.keys()}")
        else:
            print('Warning: code_snippet is None')
            return None

        # print(f"code_snippet[hits].keys: {code_snippet['hits'][0].keys()}")
        # print(f"code_snippet[hits][0]: {code_snippet['hits'][0]}")
        
        all_chunks = []
        # Chunk the code snippet for each hit
        for hit in code_snippet['hits']:
            # Use self.chunker to chunk the code
            chunks = self.chunker.chunk(code_snippet=hit['contents'])
            # Add the chunk results to the hit and associate the original file path
            for chunk in chunks:
                chunk['file_path'] = hit['docid']
            hit['chunks'] = chunks
            all_chunks.extend(chunks)
            # Print the chunking information 
            print(f"File {hit['docid']} has {len(chunks)} code chunks")
        
        # Rerank the all code chunks
        print(f"Total chunks before reranking: {len(all_chunks)}")
        top_chunks = []
        total_tokens = self.code_editor.default_prompt_token_length
        if all_chunks and self.reranker.initialized:
            top_chunks = self.reranker.rerank(all_chunks, data.problem_statement, top_k=self.max_chunk_num)
            print(f"After reranking, selected top {len(top_chunks)} chunks:")
            for i, chunk in enumerate(top_chunks):
                total_tokens += len(self.code_editor.tokenizer.encode(chunk['code']))
                print(f'total_tokens: {total_tokens} in collected of max tokens: {self.code_editor.max_model_len}')
                if total_tokens > self.code_editor.max_model_len:
                    print(f"Total tokens: {total_tokens} > max tokens: {self.code_editor.max_model_len}, break")
                    top_chunks = top_chunks[:i - 1]
                    break
                print(f"  Top Chunk {i}: {chunk['type']} - {chunk['name']} (score: {chunk.get('similarity_score', 'N/A')})")
                print(f"    From file: {chunk['file_path']}")
                print(f"    Chunk length: {len(chunk['code'])}")
        
        # Build the new input based on the reranked code chunks
        chunk_file_path_list = [chunk['file_path'] for chunk in top_chunks]
        chunk_code_list = [chunk['code'] for chunk in top_chunks]
        
        # Build the metadata information related to the code chunks to help the model understand the context
        context_info = []
        for chunk in top_chunks:
            context_info.append(f"File: {chunk['file_path']}\n"
                              f"Type: {chunk['type']}\n"
                              f"Name: {chunk['name']}\n"
                              f"Lines: {chunk['start_line']}-{chunk['end_line']}\n"
                              f"Code:\n{chunk['code']}\n")
        
        # Add the context information and patch to the problem statement
        enhanced_problem = data.problem_statement + "\n\n" + "RELEVANT CODE BLOCKS:\n" + "\n".join(context_info)
        # print(f"generated_patch: {generated_patch}")
        # if generated_patch:
        #     enhanced_problem += "\n\nGENERATED PATCH:\n" + generated_patch
        
        # Use the original file list as a backup, and provide the code chunks
        file_path_list = [hit["docid"] for hit in code_snippet["hits"]]
        code_snippet_list = [hit["contents"] for hit in code_snippet["hits"]]
        
        # Call the editor with the enhanced problem description
        response = self.code_editor.edit_code_batch(
            enhanced_problem,
            code_snippet_list,  # Original complete code
            file_path_list,     # Original file path
            role="test",
            retry=self.agent_retry_times,
            generated_patch=generated_patch,
            chunks={ # Add the code chunks information as additional context
                "file_paths": chunk_file_path_list,
                "code_blocks": chunk_code_list,
                "metadata": top_chunks
            }
        )
        if response is None:
            print(f'test generator response is None: {response}')
            return None

        base_path = f"{self.workdir}/{data.instance_id}_{str(uuid4())}"
        with TempDirectoryManager(base_path) as base_path:
            # convert repo path from x/y to x__y
            repo_path = f"{self.src_folder}/{data.repo.replace('/', '__')}"

            if os.path.exists(base_path):
                try:
                    # remove existing repo
                    shutil.rmtree(base_path)
                except Exception as e:
                    print(f"Error removing existing repo {base_path}: {e}. Skipping...")

            try:
                shutil.copytree(repo_path, base_path)
                subprocess.run(["git", "checkout", data.base_commit], cwd=base_path)
            except Exception as e:
                print(f"Error copying repo {repo_path} to {base_path}: {e}. Skipping...")
                return None

            patch = generate_git_diff_batch(response["test_cases"], base_path)
            if patch is None:
                print(f'generate_git_diff_batch merged failed. patch is None. test_cases: {response["test_cases"]}. base_path: {base_path}')
                return None

            return patch


class PatchVerifier(Verifier):
    def __init__(self, ci_tool_name: str, 
                 workdir: str = "testbed", 
                 src_folder: str = "repos",
                 ):
        self.ci_tool_name = ci_tool_name
        self.workdir = workdir
        self.src_folder = src_folder
        self.port_pool_size = 100

    def verify(self, data: SwingbenchInstance, patch: str) -> dict:
        data.patch = patch
        base_path = f"{self.workdir}/{data.instance_id}_{str(uuid4())}"
        with TempDirectoryManager(base_path) as base_path:
            if os.path.exists(base_path):
                shutil.rmtree(base_path)
            
            # CITool will handle the patch
            config = {
                "instance_id": data.instance_id,
                "repo": data.repo,
                "base_commit": data.base_commit,
                "merge_commit": data.merge_commit_sha,
                "patch": patch,
                "src_folder": self.src_folder,
                "output_dir": "logs",
                "workdir": base_path,
                "apply_patch": True,
                "ci_name_list": data.ci_name_list
            }
            ci_tool = EVAL_HANDLER.get(self.ci_tool_name)
            tool = ci_tool(config)

            # TODO(wdxu): remove the switch process for run_ci.
            if self.ci_tool_name == "act":
                pool = get_available_port_pool(self.port_pool_size)
                result = tool.run_ci(pool)
            else:
                result = tool.run_ci()

            # haoran: FOR CARGO
            # test_results = {
            #     "unit_test": {
            #         "passed": passed_tests,
            #         "failed": failed_tests,
            #         "ignored": ignored_tests,
            #         "failure_details": {}
            #     }
            # }
            # FOR ACT
            # test_results = {
            #     "ci_1": {
            #         "passed": passed_tests,
            #         "failed": failed_tests,
            #         "ignored": ignored_tests,
            #         "failure_details": {}
            #     }, ...
            # }

            return {
                "tool": self.ci_tool_name,
                "result": result,
                "patch": patch
            }


class TestVerifier(Verifier):
    def __init__(self, ci_tool_name: str, 
                 workdir: str = "testbed", 
                 src_folder: str = "repos",
                 proxy: AgentProxy = None,
                 ):
        self.ci_tool_name = ci_tool_name
        self.workdir = workdir
        self.src_folder = src_folder
        self.proxy = proxy
        self.port_pool_size = 100

    def verify(self, data: SwingbenchInstance, testcase: str) -> dict:
        # apply both test patch and original patch
        base_path = f"{self.workdir}/{data.instance_id}_{str(uuid4())}"
        with TempDirectoryManager(base_path) as base_path:
            if os.path.exists(base_path):
                shutil.rmtree(base_path)
            
            config = {
                "instance_id": data.instance_id,
                "repo": data.repo,
                "base_commit": data.base_commit,
                "merge_commit": data.merge_commit_sha,
                "patch": testcase,
                "src_folder": self.src_folder,
                "output_dir": "logs",
                "workdir": base_path,
                "apply_patch": True,
                "ci_name_list": data.ci_name_list
            }
            ci_tool = EVAL_HANDLER.get(self.ci_tool_name)
            tool = ci_tool(config)

            # TODO(wdxu): remove the switch process for run_ci.
            if self.ci_tool_name == "act":
                pool = get_available_port_pool(self.port_pool_size)
                result = tool.run_ci(pool)
            else:
                result = tool.run_ci()

            # haoran: FOR CARGO
            # test_results = {
            #     "unit_test": {
            #         "passed": passed_tests,
            #         "failed": failed_tests,
            #         "ignored": ignored_tests,
            #         "failure_details": {}
            #     }
            # }
            # FOR ACT
            # test_results = {
            #     "ci_1": {
            #         "passed": passed_tests,
            #         "failed": failed_tests,
            #         "ignored": ignored_tests,
            #         "failure_details": {}
            #     }, ...
            # }

            return {
                "tool": self.ci_tool_name,
                "result": result,
                "test_cases": testcase
            }


if __name__ == "__main__":
    from swebench.harness.swing_utils import load_swingbench_dataset
    from swebench.harness.agent.retriever import BM25DiskRetriever
    from swebench.harness.agent.editor import RawDataCodeEditor
    from swebench.harness.agent.model import AgentProxy
    import json
    
    SWING_DEBUG_GENERATE_DRYRUN = False
    
    # base_url = "https://api.x.ai/v1/"
    # api_key = os.environ["XAI_API_KEY"]
    # model = "grok-2-latest"

    base_url = "http://147.8.181.248:8000/v1/"
    api_key = "no-api-key"
    model = "/home/mnt/wdxu/models/Qwen2.5-Coder-7B-Instruct"

    with open(os.environ["SWING_DEMO_DATASET_PATH"], "r") as f:
        dataset = json.load(f)
    with open(os.environ["SWING_DEMO_PATCH_PATH"], "r") as f:
        patch = f.read()

    retriever = BM25DiskRetriever(index_dir=os.environ["SWING_INDEXES_PATH"])

    code_editor = RawDataCodeEditor(
        api_key=api_key,
        base_url=base_url,
        model=model
    )
    data = SwingbenchInstance(**dataset[0])
    if not SWING_DEBUG_GENERATE_DRYRUN:
        print('----------- [BEGIN PATCH GENERATOR] -----------',)
        print('input data: ', data)
        patch_generator = PatchGenerator(workdir=os.environ["SWING_TESTBED_PATH"], 
            src_folder=os.environ["SWING_REPOS_DIR_PATH"], 
            code_editor=code_editor,
            retriever=retriever,
            retrieve_file_num=5,
            agent_retry_times=3
        )
        patch = patch_generator.generate(data)
        print('generated patch: ', patch)
        print('----------- [END PATCH GENERATOR] -----------',)

        print('----------- [BEGIN PATCH VERIFIER] -----------')

        patch_verifier = PatchVerifier(ci_tool_name="cargo", 
            workdir=os.environ["SWING_TESTBED_PATH"], 
            src_folder=os.environ["SWING_REPOS_DIR_PATH"], 
        )
        result = patch_verifier.verify(data, patch)
        print('verify result: ', result)
        print('----------- [END PATCH VERIFIER] -----------')

        print('----------- [BEGIN TEST GENERATOR] -----------')
        test_generator = TestGenerator(workdir=os.environ["SWING_TESTBED_PATH"], 
            src_folder=os.environ["SWING_REPOS_DIR_PATH"], 
            code_editor=code_editor,
            retriever=retriever,
            retrieve_file_num=5,
            agent_retry_times=3,
        )
        testcase = test_generator.generate(data, patch)
        print('generated testcase: ', testcase)
        print('----------- [END TEST GENERATOR] -----------')

        print('----------- [BEGIN TEST VERIFIER] -----------')
        test_verifier = TestVerifier(ci_tool_name="cargo", 
            workdir=os.environ["SWING_TESTBED_PATH"], 
            src_folder=os.environ["SWING_REPOS_DIR_PATH"], 
        )
        result = test_verifier.verify(data, testcase)
        print('test verify result: ', result)
        print('----------- [END TEST VERIFIER] -----------')

        print('patch generated instance: ', data)
        print('test generated instance: ', testcase)

        result_patch = merge_diffs(patch, testcase)
        print('patch with test: ', result_patch)

        result = test_verifier.verify(data, result_patch)
        print('patch with test verify result: ', result)

    else:
        import swebench.harness.agent.verifier_test_patch as test_patch
        patch = test_patch.patch
