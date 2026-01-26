from huggingface_hub import login, HfApi, create_repo
import os
import shutil
import tempfile

login(token=os.environ["HF_TOKEN"])

api = HfApi()
repo_id = "SwingBench/SwingBench"

api.create_repo(
    repo_id=repo_id,
    repo_type="dataset",
    private=True,
    exist_ok=True 
)

with tempfile.TemporaryDirectory() as tmp_dir:
    rust_dir = os.path.join(tmp_dir, "Rust")
    os.makedirs(rust_dir, exist_ok=True)
    
    shutil.copy("tasks_with_ci.jsonl", os.path.join(rust_dir, "rust.json"))
    
    api.upload_folder(
        folder_path=tmp_dir,
        repo_id=repo_id,
        repo_type="dataset",
        commit_message="Add Rust split"
    )

api.update_repo_visibility(
    repo_id=repo_id,
    repo_type="dataset",
    private=True
)
