#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -z "$JAVA_HOME" ]; then
    if command -v java &>/dev/null; then
        _java_bin="$(command -v java)"
        _java_real="$(readlink -f "$_java_bin" 2>/dev/null || echo "$_java_bin")"
        export JAVA_HOME="${_java_real%/bin/java}"
    fi
fi

if [ -n "$JAVA_HOME" ]; then
    export PATH="$JAVA_HOME/bin:$PATH"
    _jvm_so="$JAVA_HOME/lib/server/libjvm.so"
    [ -f "$_jvm_so" ] && export JVM_PATH="$_jvm_so"
    [ -d "$JAVA_HOME/lib/server" ] && \
        export LD_LIBRARY_PATH="$JAVA_HOME/lib/server:${LD_LIBRARY_PATH:-}"
fi

export SWING_TESTBED_PATH="${SWING_TESTBED_PATH:-$PROJECT_ROOT/data/testbed}"
export SWING_REPOS_DIR_PATH="${SWING_REPOS_DIR_PATH:-$PROJECT_ROOT/data/repos}"
export SWING_INDEXES_PATH="${SWING_INDEXES_PATH:-$PROJECT_ROOT/data/indexes}"
export CI_TOOL_NAME="${CI_TOOL_NAME:-act}"

mkdir -p "$SWING_TESTBED_PATH" "$SWING_REPOS_DIR_PATH" "$SWING_INDEXES_PATH"

echo "SwingArena environment loaded."
echo "  JAVA_HOME            = ${JAVA_HOME:-<not set>}"
echo "  SWING_TESTBED_PATH   = $SWING_TESTBED_PATH"
echo "  SWING_REPOS_DIR_PATH = $SWING_REPOS_DIR_PATH"
echo "  SWING_INDEXES_PATH   = $SWING_INDEXES_PATH"
