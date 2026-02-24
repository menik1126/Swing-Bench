from swingarena.harness.log_parsers.javascript import MAP_REPO_TO_PARSER_JS
from swingarena.harness.log_parsers.python import MAP_REPO_TO_PARSER_PY
from swingarena.harness.log_parsers.utils import get_eval_type

MAP_REPO_TO_PARSER = {
    **MAP_REPO_TO_PARSER_JS,
    **MAP_REPO_TO_PARSER_PY,
}
