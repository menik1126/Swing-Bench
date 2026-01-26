from huggingface_hub import login, HfApi
import os

login(token=os.environ["HF_TOKEN"])

api = HfApi()
repo_id = "SwingBench/SwingBench"

api.delete_file(
    path_in_repo="rust.json",
    repo_id=repo_id,
    repo_type="dataset",
    commit_message="Remove root rust.json file"
)

