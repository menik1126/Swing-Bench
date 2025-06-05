#!/bin/bash
python swingarena/prepare/swing_build_index.py \
    --dataset_path SwingBench/SwingBench \
    --repo_root_dir /raid/SwingBench/tmpdata/testbed \
    --output_dir /raid/SwingBench/tmpdata/indexes \
    --split Rust 