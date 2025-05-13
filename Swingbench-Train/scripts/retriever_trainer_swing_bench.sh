#!/bin/bash

echo "==== 环境变量设置 ===="

export NCCL_P2P_DISABLE=1
export CUDA_VISIBLE_DEVICES=1,2
gpu=2
port=5324



task_name=combined
model_name=llama3-8b #llama2-7b-chat


echo "==== 输入参数 ===="
echo "task_name: $task_name"
echo "model_name: $model_name"

if [ "${model_name}" = "llama2-7b-base" ]; then
  model_path=YOUR_PATH
elif [ "${model_name}" = "llama2-7b-chat" ]; then
  model_path=meta-llama/Llama-2-7b-chat-hf
elif [ "${model_name}" = "vicuna-7b" ]; then
  model_path=YOUR_PATH
elif [ "${model_name}" = "llama3-8b" ]; then 
  model_path=meta-llama/Llama-3.1-8B-Instruct #YOUR_PATH
fi

n_tokens=800
scr_batch_size=4


for task_name in ${task_name} # selection from asdiv gsm8k svamp aqua   rust
do
  echo "==== 当前任务: ${task_name} ===="
  export WANDB_TAGS="${method},${task_name},${model_name}"
  run_dir=output/${task_name}/${task_name}/${model_name}
  index_data=index_data/${task_name}/index_dataset.json   # If you wish to use a local dataset, please change this path to "index_data=index_data/${task_name}/${task_name}/train.json"
  mkdir -p ${run_dir}

  echo "==== 检查索引数据文件是否存在: ${index_data} ===="
  if [ ! -f "${index_data}" ]; then
    echo "索引数据文件不存在: ${index_data}"
    exit 1
  fi

  retrieve_file=${run_dir}/retrieved.json
  echo "==== 运行BM25检索 ===="
  python bm25_retriever.py \
      hydra.run.dir=${run_dir}/bm25_retriever \
      output_file=${retrieve_file} \
      num_candidates=50 \
      num_ice=1 \
      task_name=${task_name} \
      index_reader.dataset_path=${index_data} \
      dataset_split=train \
      ds_size=44000 \
      query_field=a \
      index_reader.field=a

  echo "==== 检查检索结果文件是否存在: ${retrieve_file} ===="
  if [ ! -f "${retrieve_file}" ]; then
    echo "检索结果文件不存在: ${retrieve_file}"
    exit 1
  fi

  scored_file=${run_dir}/scored.json
  echo "==== 运行评分模型 ===="
  accelerate launch --num_processes ${gpu} --main_process_port ${port} scorer.py \
      hydra.run.dir=${run_dir}/scorer \
      model_name=${model_path} \
      task_name=${task_name} \
      output_file=${scored_file} \
      batch_size=${scr_batch_size} \
      dataset_reader.dataset_path=${retrieve_file} \
      dataset_reader.n_tokens=${n_tokens} \
      index_reader.dataset_path=${index_data}

  echo "==== 检查评分结果文件是否存在: ${scored_file} ===="
  if [ ! -f "${scored_file}" ]; then
    echo "评分结果文件不存在: ${scored_file}"
    exit 1
  fi

  run_name=bert-fix_ctx-shared-bs64_1
  run_dir=${run_dir}/${run_name}
  pretrained_model=${run_dir}/qa_model
  echo "==== 运行QA训练 ===="
  accelerate launch --main_process_port ${port} qa_retriever_trainer.py \
      hydra.run.dir=${run_dir}/trainer \
      task_name=${task_name} \
      qa_dataset_reader.dataset_path=${scored_file} \
      index_reader.dataset_path=${index_data} \
      training_args.output_dir=${run_dir} \
      training_args.run_name=${run_name} \
      model_config.ctx_model_name=null \
      pretrained_model=${pretrained_model}
# share ctx model with q model 
  echo "==== 任务 ${task_name} 完成 ===="
done

echo "==== 所有任务完成 ===="