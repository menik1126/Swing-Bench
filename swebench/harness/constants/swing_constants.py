from enum import Enum, auto
from pathlib import Path
from dataclasses import dataclass, field

# Constants - Evaluation Log Directories
BASE_IMAGE_BUILD_DIR = Path("logs/build_images/base")
ENV_IMAGE_BUILD_DIR = Path("logs/build_images/env")
INSTANCE_IMAGE_BUILD_DIR = Path("logs/build_images/instances")
RUN_EVALUATION_LOG_DIR = Path("logs/run_evaluation")
RUN_VALIDATION_LOG_DIR = Path("logs/run_validation")


# Constants - Task Instance Class
@dataclass
class SwingbenchInstance:
    repo: str = ""
    instance_id: str = ""
    base_commit: str = ""
    patch: str = ""
    test_patch: str = ""
    problem_statement: str = ""
    hints_text: str = ""
    created_at: str = ""
    pull_number: int = 0
    issue_numbers: int = 0
    merge_commit_sha: str = ""
    ci_name_list: list[str] = field(default_factory=list)
    retrieved_files: dict[str, str] = field(default_factory=dict)
    environment_setup_commit: str = ""
    version: str = ""
    FAIL_TO_PASS: str = ""
    PASS_TO_PASS: str = ""
    enhanced_problem: str = ""
    original_code: str = ""
    file_paths: list[str] = field(default_factory=list)
    total_tokens: int = 0

    def __str__(self):
        return f"SwingbenchInstance( " \
               f"repo={self.repo}, " \
               f"instance_id={self.instance_id}, " \
               f"base_commit={self.base_commit}, " \
               f"patch={self.patch[:15]}...), " \
               f"test_patch={self.test_patch[:15]}...), " \
               f"problem_statement={self.problem_statement[:15]}...), " \
               f"hints_text={self.hints_text[:15]}...), " \
               f"ci_name_list={self.ci_name_list}, " \
               f"retrieved_files={self.retrieved_files}, " \
               f"environment_setup_commit={self.environment_setup_commit}, " \
               f"version={self.version}, " \
               f"FAIL_TO_PASS={self.FAIL_TO_PASS}, " \
               f"PASS_TO_PASS={self.PASS_TO_PASS}, " \
               f"enhanced_problem={self.enhanced_problem}, " \
               f"original_code={self.original_code}, " \
               f"file_paths={self.file_paths}, " \
               f"total_tokens={self.total_tokens})"

    def __repr__(self):
        return self.__str__()


# Constants - Test Types, Statuses, Commands
FAIL_TO_PASS = "FAIL_TO_PASS"
FAIL_TO_FAIL = "FAIL_TO_FAIL"
PASS_TO_PASS = "PASS_TO_PASS"
PASS_TO_FAIL = "PASS_TO_FAIL"

class AgentState(Enum):
    PATCH = auto()
    TEST = auto()

class ResolvedStatus(Enum):
    NO = "RESOLVED_NO"
    PARTIAL = "RESOLVED_PARTIAL"
    FULL = "RESOLVED_FULL"


class TestStatus(Enum):
    FAILED = "FAILED"
    PASSED = "PASSED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"
    XFAIL = "XFAIL"


class EvalType(Enum):
    PASS_AND_FAIL = "pass_and_fail"
    FAIL_ONLY = "fail_only"


# Constants - Evaluation Keys
KEY_INSTANCE_ID = "instance_id"
KEY_MODEL = "model_name_or_path"
KEY_PREDICTION = "model_patch"

# Constants - Harness
DOCKER_PATCH = "/tmp/patch.diff"
DOCKER_USER = "root"
DOCKER_WORKDIR = "/testbed"
LOG_REPORT = "report.json"
LOG_INSTANCE = "run_instance.log"
LOG_TEST_OUTPUT = "test_output.txt"
UTF8 = "utf-8"

# Constants - Logging
APPLY_PATCH_FAIL = ">>>>> Patch Apply Failed"
APPLY_PATCH_PASS = ">>>>> Applied Patch"
INSTALL_FAIL = ">>>>> Init Failed"
INSTALL_PASS = ">>>>> Init Succeeded"
INSTALL_TIMEOUT = ">>>>> Init Timed Out"
RESET_FAILED = ">>>>> Reset Failed"
TESTS_ERROR = ">>>>> Tests Errored"
TESTS_FAILED = ">>>>> Some Tests Failed"
TESTS_PASSED = ">>>>> All Tests Passed"
TESTS_TIMEOUT = ">>>>> Tests Timed Out"
START_TEST_OUTPUT = ">>>>> Start Test Output"
END_TEST_OUTPUT = ">>>>> End Test Output"
