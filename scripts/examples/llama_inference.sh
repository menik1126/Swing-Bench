export NCCL_P2P_DISABLE=1
export CUDA_VISIBLE_DEVICES=0,1
python -m swingarena.inference.run_llama \
    --dataset_path princeton-nlp/SWE-bench_oracle \
    --model_name_or_path princeton-nlp/SWE-Llama-7b \
    --output_dir /home/xiongjing/resource_dir/SWE-bench-output \
    --temperature 1