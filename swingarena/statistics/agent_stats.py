import argparse
import os

from swebench.harness.agent.retriever import BM25DiskRetriever
from swebench.harness.swing_utils import load_swingbench_dataset
from swebench.harness.agent.verifier import PatchGenerator, TestGenerator
from swebench.harness.agent.editor import RawDataCodeEditor

DEBUG_ONE_SHOT = True


def main(**kwargs):
    print('------------ processing dataset ------------')
    print(f'kwargs: {kwargs}')

    dataset = load_swingbench_dataset(kwargs["dataset_name"], kwargs["language"], split=None, with_ci=False)

    print(f'dataset size: {len(dataset)}')

    retriever = BM25DiskRetriever(index_dir=kwargs["retriever_index_dir"])
    print(f'retriever: {retriever}')
    
    code_editor = RawDataCodeEditor(
        api_key=kwargs["api_key"],
        base_url=kwargs["base_url"],
        model=kwargs["model"],
        tok_model=kwargs["tok_model"],
    )

    patch_generator = PatchGenerator(
        workdir=kwargs["workdir"],
        src_folder=kwargs["src_folder"],
        code_editor=code_editor,
        retriever=retriever,
        retrieve_file_num=kwargs["retrieve_file_num"],
    )

    test_generator = TestGenerator(
        workdir=kwargs["workdir"],
        src_folder=kwargs["src_folder"],
        code_editor=code_editor,
        retriever=retriever,
        retrieve_file_num=kwargs["retrieve_file_num"],
    )

    for instance in dataset:
        print(f'process instance: {instance}')
        patch_result = patch_generator.generate(instance)
        _ = test_generator.generate(instance, patch_result)

        if DEBUG_ONE_SHOT:
            break


if __name__ == "__main__":
    """
    Redirect stdout and parse the output of all information.
    """
    parser = argparse.ArgumentParser()

    base_url = "http://localhost:8000/v1"
    api_key = "no-api-key"
    model = "/home/mnt/wdxu/models/Qwen2.5-Coder-7B-Instruct"
    tok_model = "/home/mnt/wdxu/models/Qwen2.5-Coder-7B-Instruct"

    parser.add_argument(
        "--dataset_name",
        default="/home/mnt/wdxu/github/SwingBench-data",
        type=str,
        help="Name of dataset or path to JSON file.",
    )
    parser.add_argument(
        "--language", type=str, default="rust", help="Language of the dataset"
    )
    parser.add_argument(
        "--api_key", type=str, default=api_key, help="API key"
    )
    parser.add_argument(
        "--base_url", type=str, default=base_url, help="Base URL"
    )
    parser.add_argument(
        "--model", type=str, default=model, help="Model"
    )
    parser.add_argument(
        "--retriever_index_dir", type=str, default=os.environ["SWING_INDEXES_PATH"], help="Retriever index directory"
    )
    parser.add_argument(
        "--workdir", type=str, default=os.environ["SWING_TESTBED_PATH"], help="Work directory"
    )
    parser.add_argument(
        "--src_folder", type=str, default=os.environ["SWING_REPOS_DIR_PATH"], help="Source code folder"
    )
    parser.add_argument(
        "--retrieve_file_num", type=int, default=5, help="Retrieve file number"
    )
    parser.add_argument(
        "--tok_model", type=str, default=tok_model, help="Token model"
    )
    args = parser.parse_args()

    main(**vars(args))
