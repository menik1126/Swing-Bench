from dataclasses import asdict
from datasets import Dataset, DatasetDict
from swebench.harness.constants.swing_constants import SwingbenchInstance

def upload_dataclass_list_to_huggingface(
    dataclass_list: list[SwingbenchInstance],
    repo_id: str,
    private: bool = False,
    split_name: str = "rust",
) -> None:
    if not dataclass_list or not isinstance(dataclass_list, list):
        raise ValueError("dataclass_list must be a non-empty list")
    
    if not hasattr(dataclass_list[0], "__dataclass_fields__"):
        raise ValueError("Items in dataclass_list must be dataclass instances")
    data_dicts = [
        {k: v for k, v in asdict(item).items() if k not in ["retrieved_files", "issue_numbers", "pull_number"]}
        for item in dataclass_list
    ]
    dataset = Dataset.from_list(data_dicts)
    dataset_dict = DatasetDict({split_name: dataset})
    try:
        dataset_dict.push_to_hub(
            repo_id=repo_id,
            private=private,
        )
        print(f"Dataset successfully uploaded to https://huggingface.co/datasets/{repo_id}")
    except Exception as e:
        raise Exception(f"Failed to upload dataset: {str(e)}")

def upload(data):
    upload_dataclass_list_to_huggingface(
        dataclass_list=data,
        repo_id="SwingBench/Full-data",
        private=True,
        split_name="rust",
    )
