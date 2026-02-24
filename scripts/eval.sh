#!/bin/bash

# conda activate parallel_new_version

# cd ../

echo "----------------Start evaluation!----------------"

python -m swingarena.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Lite \
    --predictions_path ./outputs/princeton-nlp__SWE-bench_oracle__test__princeton-nlp__SWE-Llama-7b__temp-0.0__top-p-1.0.jsonl \
    --max_workers 1 \
    --run_id test