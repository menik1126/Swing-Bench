import subprocess
import os
import re
import tempfile
import logging
import shutil

from pathlib import Path


OPENAI_LIST = ["gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4.5-preview",
               "/home/mnt/wdxu/models/DeepSeek-R1-Distill-Qwen-7B",
               "/home/mnt/wdxu/models/Qwen2.5-Coder-14B-Instruct",
               "/home/mnt/wdxu/models/Qwen2.5-Coder-32B-Instruct",
               "/app/wdxu/models/Qwen2.5-Coder-32B",
               "/app/wdxu/models/DeepSeek-R1-Distill-Qwen-32B",
               "glm-4-flash",
               "/app/wdxu/models/DeepSeek-R1-Distill-Qwen-7B"]

MODEL_LIMITS = {
    # "claude-instant-1": 100_000,
    # "claude-2": 100_000,
    # "claude-3-opus-20240229": 200_000,
    # "claude-3-sonnet-20240229": 200_000,
    # "claude-3-haiku-20240307": 200_000,
    "gpt-3.5-turbo": 16_385,
    "gpt-4": 8_192,
    "gpt-4o": 128_000,
    "gpt-4.5-preview": 128_000,
    "glm-4-flash": 32_768,
}

EVAL_TOOL_MAP = {
    "ci": "CargoCITool",
    "test": "CargoTestTool",
}

import re

def parse_testcase(response: str, language: str) -> str:
    """Parse the test case from the response.
    
    Extracts code between ```{language} and ``` or between ``` and ```
    
    Args:
        response: The response string containing code blocks
        language: The programming language to look for
        
    Returns:
        The extracted code content
    """
    pattern = r"```{}\s*([\s\S]*?)\s*```".format(language)
    match = re.search(pattern, response)
    if match:
        return match.group(1).strip()
    
    pattern = r"```\s*([\s\S]*?)\s*```"
    match = re.search(pattern, response)
    if match:
        return match.group(1).strip()
    
    return response.strip()

def apply_git_patch(patch: str, directory: str):
    """Apply a patch to files in the specified directory.
    
    Args:
        patch: String containing the patch content in unified diff format
        directory: Path to the directory where the patch should be applied
        commit: Optional commit hash to reset the repository to before applying the patch
    
    Returns:
        bool: True if patch was successfully applied, False otherwise
    
    Raises:
        ValueError: If the directory is not a valid git repository
        subprocess.CalledProcessError: If git commands fail
    """
    directory_path = Path(directory)
    
    if not (directory_path / ".git").exists():
        raise ValueError(f"The directory {directory} is not a git repository")
    
    current_dir = os.getcwd()
    os.chdir(directory)
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as temp_file:
            temp_file.write(patch)
            temp_path = temp_file.name
        
        try:
            result = subprocess.run(
                ["git", "apply", "--check", temp_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logging.error(f"Patch cannot be applied cleanly: {result.stderr}")
                return False
            
            logging.info("Applying patch...")
            subprocess.run(["git", "apply", temp_path], check=True)
            logging.info("Patch applied successfully")
            return True
            
        finally:
            os.unlink(temp_path)
    
    except subprocess.CalledProcessError as e:
        logging.error(f"Error applying patch: {str(e)}")
        logging.error(f"Command output: {e.stdout if hasattr(e, 'stdout') else ''}")
        logging.error(f"Command error: {e.stderr if hasattr(e, 'stderr') else ''}")
        return False
        
    finally:
        os.chdir(current_dir)

def files_to_str(files: dict[str, str]) -> str:
    """Convert a dictionary of file paths and their contents to a string.
    
    Args:
        files: A dictionary where keys are file paths and values are file contents
        
    Returns:
        A string containing the file contents
    """
    return "\n".join([f"{file_path}:\n{file_content}" for file_path, file_content in files.items()])


class TempDirectoryManager:
    def __init__(self, base_path: str):
        self.base_path = base_path

    def __enter__(self):
        return self.base_path

    def __exit__(self, exc_type, exc_val, exc_tb):
        if os.path.exists(self.base_path):
            try:
                print(f"Removing base_path {self.base_path}...")
                shutil.rmtree(self.base_path)
            except Exception as e:
                print(f"Error removing base_path {self.base_path}: {e}")


if __name__ == "__main__":
    response = """
    ```
    fn main() {
        println!("Hello, world!");
    }
    ```
    """
    print(parse_testcase(response, "rust"))