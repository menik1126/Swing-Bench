import os
import uuid
import subprocess

def lint_code(repo_playground, temp_name, code, prev_code=""):
    repo_playground = os.path.join(repo_playground, str(uuid.uuid4()))
    if os.path.exists(repo_playground):
        os.removedirs(repo_playground)
    os.makedirs(repo_playground)

    with open(f"{repo_playground}/{temp_name}", "w") as f:
        f.write(prev_code)

    fatal = "E9,F821,F823,F831,F406,F407,F701,F702,F704,F706"
    o = subprocess.run(
        f"flake8 --select={fatal} --isolated {repo_playground}/{temp_name}",
        shell=True,
        capture_output=True,
    )
    s = o.stdout.decode("utf-8")

    prev_errors = set()
    if s != "":
        for error in s.split(f"{repo_playground}/{temp_name}:")[1:]:
            num_free_error = ":".join(error.split(":")[2:]).strip()
            prev_errors.add(num_free_error)

    with open(f"{repo_playground}/{temp_name}", "w") as f:
        f.write(code)

    o = subprocess.run(
        f"flake8 --select={fatal} --isolated {repo_playground}/{temp_name}",
        shell=True,
        capture_output=True,
    )
    s = o.stdout.decode("utf-8")

    subprocess.run(f"rm -rf {repo_playground}", shell=True)

    errors = set()
    if s != "":
        for error in s.split(f"{repo_playground}/{temp_name}:")[1:]:
            num_free_error = ":".join(error.split(":")[2:]).strip()
            errors.add(num_free_error)

    if len(errors - prev_errors) > 0:
        return False, prev_errors, errors

    return True, set(), set()

repo_playground = "/tmp/repo"
temp_name = "example.py"

prev_code = """
def add(a, b):
    return a + b
"""

code = """
def add(a, b):
return a + b  # 缩进错误
"""

result = lint_code(repo_playground, temp_name, code, prev_code)
print(result)