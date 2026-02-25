set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a; source "$PROJECT_ROOT/.env"; set +a
fi

source "$SCRIPT_DIR/setup_env.sh"

BASE_URL="${LLM_BASE_URL:-http://localhost:8000/v1}"
API_KEY="${LLM_API_KEY:-no-api-key}"
MODEL="${LLM_MODEL:-Qwen/Qwen2.5-Coder-7B-Instruct}"
TOK_MODEL="${LLM_TOK_MODEL:-Qwen/Qwen2.5-7B-Instruct}"

DATASET_NAME="${DATASET_NAME:-SwingBench/SwingBench}"
LANGUAGE="${LANGUAGE:-python}"
SPLIT="${SPLIT:-test}"
CI_TOOL="${CI_TOOL:-act}"
TURNS="${TURNS:-1}"
PORT_RANGE="${PORT_RANGE:-10000-11000}"

echo "============================================="
echo "  SwingArena Agent Battle"
echo "============================================="
echo "Dataset:      $DATASET_NAME"
echo "Language:     $LANGUAGE"
echo "Split:        $SPLIT"
echo "CI Tool:      $CI_TOOL"
echo "LLM Model:    $MODEL"
echo "LLM Base URL: $BASE_URL"
echo "Tokenizer:    $TOK_MODEL"
echo "Workdir:      $SWING_TESTBED_PATH"
echo "Repos dir:    $SWING_REPOS_DIR_PATH"
echo "Indexes dir:  $SWING_INDEXES_PATH"
echo "Turns:        $TURNS"
echo "============================================="
echo ""

echo "Checking prerequisites..."

if ! docker ps &>/dev/null; then
    echo "ERROR: Docker is not running. Please start Docker first."; exit 1
fi
echo "  Docker:  OK"

if ! command -v act &>/dev/null; then
    echo "ERROR: 'act' not found. Install: https://github.com/nektos/act"; exit 1
fi
echo "  act:     OK ($(act --version 2>/dev/null || echo 'unknown'))"

if ! command -v java &>/dev/null; then
    echo "  Java:    WARNING - not found; BM25 retrieval will fail"
else
    echo "  Java:    OK ($(java --version 2>&1 | head -1))"
fi
echo ""

exec python swingarena/harness/agent_battle.py \
    --dataset_name "$DATASET_NAME" \
    --language "$LANGUAGE" \
    --split "$SPLIT" \
    --workdir "$SWING_TESTBED_PATH" \
    --src_folder "$SWING_REPOS_DIR_PATH" \
    --retriever_index_dir "$SWING_INDEXES_PATH" \
    --ci_tool_name "$CI_TOOL" \
    --model_lhs "$MODEL" \
    --model_rhs "$MODEL" \
    --api_key_lhs "$API_KEY" \
    --api_key_rhs "$API_KEY" \
    --base_url_lhs "$BASE_URL" \
    --base_url_rhs "$BASE_URL" \
    --tok_model_lhs "$TOK_MODEL" \
    --tok_model_rhs "$TOK_MODEL" \
    --turns "$TURNS" \
    --port_range "$PORT_RANGE"
