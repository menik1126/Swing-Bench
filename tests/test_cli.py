import subprocess


def test_smoke_test():
    cmd = ["python", "-m", "swingarena.harness.run_evaluation", "--help"]
    result = subprocess.run(cmd, capture_output=True)
    print(result.stdout)
    print(result.stderr)
    assert result.returncode == 0


def test_one_instance():
    cmd = [
        "python",
        "-m",
        "swingarena.harness.run_evaluation",
        "--predictions_path",
        "gold",
        "--concurrent_workers",
        "1",
        "--instance_ids",
        "tokio-rs__tokio-6978",
    ]
    result = subprocess.run(cmd, capture_output=True)
    print(result.stdout)
    print(result.stderr)
    assert result.returncode == 0
