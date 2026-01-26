__version__ = "3.0.13"

from swingarena.collect.build_dataset import main as build_dataset
from swingarena.collect.get_tasks_pipeline import main as get_tasks_pipeline

from swingarena.harness.constants import (
    KEY_INSTANCE_ID,
    KEY_MODEL,
    KEY_PREDICTION,
    MAP_REPO_VERSION_TO_SPECS,
)

from swingarena.harness.docker_build import (
    build_image,
    build_base_images,
    build_env_images,
    build_instance_images,
    build_instance_image,
    close_logger,
    setup_logger,
)

from swingarena.harness.docker_utils import (
    cleanup_container,
    remove_image,
    copy_to_container,
    exec_run_with_timeout,
    list_images,
)

from swingarena.harness.grading import (
    compute_fail_to_pass,
    compute_pass_to_pass,
    get_logs_eval,
    get_eval_report,
    get_resolution_status,
    ResolvedStatus,
    TestStatus,
)

from swingarena.harness.log_parsers import (
    MAP_REPO_TO_PARSER,
)

from swingarena.harness.run_evaluation import (
    main as run_evaluation,
)

from swingarena.harness.utils import (
    run_tasks,
)

# NOTE: versioning module not found in current codebase - commented out
# from swingarena.versioning.constants import (
#     MAP_REPO_TO_VERSION_PATHS,
#     MAP_REPO_TO_VERSION_PATTERNS,
# )
#
# from swingarena.versioning.get_versions import (
#     get_version,
#     get_versions_from_build,
#     get_versions_from_web,
#     map_version_to_task_instances,
# )
#
# from swingarena.versioning.utils import (
#     split_instances,
# )
