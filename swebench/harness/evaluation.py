from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from router import tasks, HANDLER, Task
import subprocess
import tempfile
import os
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

def run_script(script_content):

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".sh") as temp_script:
        temp_script.write(script_content)
        temp_script.flush()
        temp_path = temp_script.name

    try:
        subprocess.run(["bash", temp_path], check=True)
    finally:
        subprocess.run(["rm", "-f", temp_path])


def run_instance(task: Task):

    run_script("\n".join(task.env_script))
    run_script("\n".join(task.eval_script))
    
    with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.patch') as patch_file:
        patch_file.write(task.patch)
        patch_path = patch_file.name

        log_file = os.path.join(task.output_dir, "output_"+ str(task.id) +".log")
        subprocess.run(["git", "apply", patch_path], cwd=task.target_dir, text=True, check=True)
        try:
            with open(log_file, "w") as f:
                result = subprocess.run(["cargo", "test"], cwd=task.target_dir, stdout=f, stderr=f, text=True)

            if result.returncode != 0:
                print(f"[ERROR] Task {task.id} cargo test failed with return code {result.returncode}")
                return False

            return True
        except Exception as e:
            print(f"[ERROR] Task {task.id} encountered an error: {e}")
            traceback.print_exc()
            return False 
        finally:
            if os.path.exists(patch_path):
                os.remove(patch_path)
            subprocess.run(["rm", "-rf", task.target_dir], check=False)


def run_threadpool(func, payloads, workers):
    succeeded, failed = [], []
    with tqdm(total=len(payloads), smoothing=0) as pbar:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(func, payload): payload for payload in payloads}
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        succeeded.append(futures[future])
                    else:
                        failed.append(futures[future])
                except Exception as e:
                    print(f"{type(e)}: {e}")
                    traceback.print_exc()
                    failed.append(futures[future])
                    continue
                pbar.update(1)
                pbar.set_description(
                    f"{len(succeeded)} ran successfully, {len(failed)} failed"
                )
    return succeeded, failed


def main(
    max_workers: int,
    workdir: str,
    output_dir: str
):
    """
    Run evaluation harness for the given dataset and predictions.
    """

    # load dataset

    # check parameters

    # handle data
    with open("./swebench/harness/patch/patch.diff", "r", encoding="utf-8") as f:
        patch_content = f.read()
    
    config = {
        "repo": "vectordotdev/vector",
        "base_commit": "d49c542930267cc69d577e8d3b86a6c119fcf331",
        "patch": patch_content,
        "workdir": workdir,
        "output_dir": output_dir
    }

    # router to different handler
    HANDLER["cargo"](config)

    run_threadpool(run_instance, tasks, max_workers)



if __name__ == "__main__":
    parser = ArgumentParser(
        description="Run evaluation for the given dataset.",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )

    # Local execution args
    parser.add_argument(
        "--max_workers",
        type=int,
        default=1,
        help="Maximum number of workers (should be <= 75%% of CPU cores)",
    )

    parser.add_argument(
        "--workdir",
        type=str,
        default="/home",
        help="The location where the repo is stored",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="./swebench/harness/patch/",
        help="The location where the output is stored",
    )

    args = parser.parse_args()
    main(**vars(args))
