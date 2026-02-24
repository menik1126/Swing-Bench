#!/bin/bash
export SWING_TESTBED_PATH=/raid/SwingBench/tmpdata/testbed
export SWING_REPOS_DIR_PATH=/raid/rust-repos
export SWING_INDEXES_PATH=/raid/SwingBench/tmpdata/indexes #~/swing_indexes
export CI_TOOL_NAME=act

python swingarena/harness/agent_battle.py \
    --workdir $SWING_TESTBED_PATH \
    --src_folder $SWING_REPOS_DIR_PATH \
    --retriever_index_dir $SWING_INDEXES_PATH \
    --ci_tool_name $CI_TOOL_NAME \
    --dataset_name SwingBench/SwingBench \
    --split Rust \
    --tok_model_lhs Qwen/Qwen2.5-Coder-7B-Instruct \
    --tok_model_rhs Qwen/Qwen2.5-Coder-7B-Instruct