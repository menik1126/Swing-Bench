import json
import pdb
import os
import subprocess
import tempfile

def run_script(script_content, cwd=None):
    with tempfile.NamedTemporaryFile(mode="w", delete=True, suffix=".sh") as temp_script:
        temp_script.write(script_content)
        temp_script.flush()
        temp_path = temp_script.name
        try:
            subprocess.run(["bash", temp_path], 
                           cwd=cwd,
                           check=True, 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
        except Exception as e:
            return e
    return None

def delete_act_containers():
    try:
        subprocess.run("docker rm -f $(docker ps -aq)", shell=True, check=False)
    except subprocess.CalledProcessError as e:
        print(f"error: {e}")


if __name__ == "__main__":
    with open('/mnt/Data/wdxu/github/Swing-Bench/repo.jsonl', 'r') as f:
        count = 0
        for line in f:
            data = json.loads(line.strip())
            repo_name = data["name"]
            
            log_path = f"/home/wdxu/testbed/log/{repo_name}"
            target_path = f"/home/wdxu/testbed/repo_ci/{repo_name}"
            if not os.path.exists(log_path):
                os.makedirs(log_path, exist_ok=True)

                print(f"run in repo {repo_name}")
                subprocess.run(f"git clone {data['url']}.git {target_path}", shell=True, check=True)
                script = ["#!/bin/bash"]
                script.append(f"cd {target_path}")
                script.append(f"act --list > {log_path}/act.txt")
                run_script("\n".join(script))

                job_ids = set()
                with open(f'{log_path}/act.txt', 'r') as f:
                    lines = f.readlines()
                    if len(lines) <= 1:
                        subprocess.run(f"rm -rf {log_path}/", shell=True, check=True)
                        continue
                    else:
                        for line in lines[1:]:
                            parts = line.strip().split()
                            if len(parts) > 1:
                                job_ids.add(parts[1])

                print(f"get {len(job_ids)} jobs from {repo_name}")
                while job_ids:
                    job_id = job_ids.pop()
                    print(f"doing job {job_id} of {repo_name}")
                    script = ["#!/bin/bash"]
                    script.append(f"cd {target_path}")
                    script.append(f"act -j {job_id} -P ubuntu-latest=catthehacker/ubuntu:full-latest --json > {log_path}/{job_id}.log")
                    run_script("\n".join(script))

                delete_act_containers()
                count += 1
                if count % 10 == 0:
                    subprocess.run(f"rm -rf .cache/act/*", shell=True, check=True)
