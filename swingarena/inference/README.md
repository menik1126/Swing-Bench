# SwingBench Inference Framework

The SwingBench inference framework provides a comprehensive suite of tools for running inference on software engineering benchmarks. This module supports multiple model types, inference patterns, and deployment scenarios, from API-based models to local Llama deployments and real-time GitHub issue solving.

## 🚀 Quick Start



### Basic Usage Examples

**API Model Inference:**
```bash
export OPENAI_API_KEY=<your_key>
python -m swingarena.inference.run_api \
    --dataset_name_or_path princeton-nlp/SWE-bench_oracle \
    --model_name_or_path gpt-4-0125-preview \
    --output_dir ./outputs
```

**Local Llama Model Inference:**
```bash
python -m swingarena.inference.run_llama \
    --dataset_path princeton-nlp/SWE-bench_oracle \
    --model_name_or_path princeton-nlp/SWE-Llama-13b \
    --output_dir ./outputs
```

**Live GitHub Issue Solving:**
```bash
export OPENAI_API_KEY=<your_key>
python -m swingarena.inference.run_live \
    --model_name gpt-3.5-turbo-1106 \
    --issue_url https://github.com/owner/repo/issues/123
```

## 📁 Module Architecture

### Core Components

#### 1. **API Inference Engine** (`run_api.py`)
A production-ready inference engine supporting OpenAI and Anthropic APIs with advanced features:

**Supported Models:**
- **OpenAI**: GPT-3.5 Turbo variants, GPT-4 series (including 32k and 128k context models)
- **Anthropic**: Claude Instant, Claude 2, Claude 3 (Opus, Sonnet, Haiku)
- **Azure OpenAI**: Full compatibility with Azure deployments

**Key Features:**
- **Automatic Cost Tracking**: Real-time monitoring of API costs with configurable limits
- **Token Management**: Context length validation and automatic filtering
- **Retry Logic**: Exponential backoff with configurable retry attempts
- **Progress Persistence**: Resumable inference with automatic checkpoint saving
- **Parallel Processing**: Multi-shard support for large-scale inference

**Advanced Configuration:**
```bash
python -m swingarena.inference.run_api \
    --dataset_name_or_path princeton-nlp/SWE-bench_oracle \
    --model_name_or_path claude-3-opus-20240229 \
    --model_args "temperature=0.2,top_p=0.95,max_tokens=4096" \
    --max_cost 100.0 \
    --shard_id 0 --num_shards 4 \
    --output_dir ./outputs
```

#### 2. **Llama Inference Engine** (`run_llama.py`)
Optimized local inference for Llama-family models with GPU memory management:

**Model Support:**
- **SWE-Llama**: Specialized models fine-tuned for software engineering tasks
- **Code Llama**: Base and instruction-tuned variants (7B, 13B, 34B)
- **PEFT Integration**: Support for LoRA and other parameter-efficient fine-tuning

**Memory Optimization:**
- **Multi-GPU Support**: Automatic device mapping based on available hardware
- **Flash Attention**: Optimized attention computation for improved throughput
- **Dynamic Memory Management**: Automatic GPU memory allocation with fallback to CPU

**Generation Control:**
- **Stopping Criteria**: Advanced stopping conditions to prevent repetitive outputs
- **Temperature/Top-p Sampling**: Configurable generation parameters
- **Length Constraints**: Minimum and maximum output length controls

**Example with PEFT:**
```bash
python -m swingarena.inference.run_llama \
    --dataset_path princeton-nlp/SWE-bench_oracle \
    --model_name_or_path princeton-nlp/SWE-Llama-13b \
    --peft_path ./fine-tuned-adapters \
    --temperature 0.1 --top_p 0.95 \
    --output_dir ./outputs
```

#### 3. **Live Issue Solver** (`run_live.py`)
Real-time GitHub issue processing with intelligent code retrieval:

**Workflow:**
1. **Issue Parsing**: Automatic extraction of problem statements from GitHub issues
2. **Repository Cloning**: Secure repository access with token authentication
3. **Index Building**: BM25-based code retrieval index construction
4. **Context Assembly**: Intelligent file selection based on relevance and token limits
5. **Model Inference**: Prompt generation and model interaction
6. **Result Formatting**: Structured output with diff extraction

**Features:**
- **BM25 Retrieval**: Semantic code search for relevant context
- **Token Budget Management**: Automatic context truncation within model limits
- **README Integration**: Optional inclusion of repository documentation
- **Multi-Issue Processing**: Batch processing of multiple issues

**Advanced Usage:**
```bash
python -m swingarena.inference.run_live \
    --model_name gpt-4-0125-preview \
    --issue_url https://github.com/owner/repo/issues/123 \
    --prompt_style style-3 \
    --max_context_length 15000 \
    --include_readmes \
    --output_dir ./live_results
```

### 4. **Dataset Generation Framework** (`make_datasets/`)

A comprehensive toolkit for creating custom SWE-bench datasets with flexible prompting and context strategies.

#### **Text Dataset Creation** (`create_text_dataset.py`)
Generate text datasets with customizable prompts and context sources:

**Prompt Styles:**
- **style-2**: Optimized for both API models and SWE-Llama
- **style-3**: Advanced prompting for API models with enhanced instructions
- **full_file_gen**: Complete file generation for ablation studies
- **style-2-edits-only**: Focused on edit generation for oracle-collapsed scenarios

**Context Sources:**
- **oracle**: Ground truth file contexts (for evaluation)
- **bm25**: BM25-retrieved relevant files
- **all**: Complete repository context (memory permitting)

**Example:**
```bash
export GITHUB_TOKEN=<your_token>
python -m swingarena.inference.make_datasets.create_text_dataset \
    --dataset_name_or_path princeton-nlp/SWE-bench \
    --output_dir ./custom_datasets \
    --prompt_style style-3 \
    --file_source oracle \
    --max_context_len 15000 \
    --splits test,validation \
    --push_to_hub_user your_username
```

#### **Dataset Tokenization** (`tokenize_dataset.py`)
Preprocess datasets with model-specific tokenizers:

**Supported Tokenizers:**
- **llama**: LlamaTokenizer for Llama-family models
- **cl100k**: OpenAI's tiktoken for GPT models
- **claude**: Anthropic's tokenizer for Claude models

**Features:**
- **Multiprocessing**: Parallel tokenization for large datasets
- **Hub Integration**: Direct push to Hugging Face Hub
- **Token Statistics**: Comprehensive length analysis

```bash
python -m swingarena.inference.make_datasets.tokenize_dataset \
    --dataset_name_or_path ./custom_datasets/DATASET_NAME \
    --tokenizer_name llama \
    --num_proc 20 \
    --push_to_hub_user your_username
```

#### **BM25 Retrieval System** (`bm25_retrieval.py`)
Build and query BM25 indexes for code retrieval:

**Capabilities:**
- **Repository Indexing**: Full codebase indexing with file-level granularity
- **Query Processing**: Natural language to code similarity search
- **Multi-language Support**: Language-agnostic code retrieval
- **Parallel Processing**: Distributed indexing for large repositories

**Requirements:** Install Pyserini following [these instructions](https://github.com/castorini/pyserini/blob/master/docs/installation.md)

```bash
python -m swingarena.inference.make_datasets.bm25_retrieval \
    --dataset_name_or_path princeton-nlp/SWE-bench \
    --output_dir ./retrieval_results \
    --splits test \
    --num_proc 8
```

#### **Retrieval Evaluation** (`eval_retrieval.py`)
Assess the quality of retrieval-based datasets:

```bash
python -m swingarena.inference.make_datasets.eval_retrieval \
    --dataset_name_or_path princeton-nlp/SWE-bench_bm25_13K \
    --split test
```

### 5. **Optimized Llama Implementation** (`llamao/`)

Custom Llama implementation with performance optimizations:

- **Flash Attention**: Memory-efficient attention computation
- **Distributed Processing**: Multi-device model parallelism
- **Memory Optimization**: Reduced memory footprint for large models

## 🔧 Configuration Management

### Device Mapping (`codellama_device_maps.json`)
Predefined GPU allocation strategies for different model sizes and hardware configurations:

- **7B Models**: Single GPU or 2/4-GPU configurations
- **13B Models**: 2/4-GPU optimized mappings
- **34B Models**: 4-GPU distributed setup

### Environment Variables
```bash
# API Keys
export OPENAI_API_KEY=<your_openai_key>
export ANTHROPIC_API_KEY=<your_anthropic_key>
export AZURE_OPENAI_API_KEY=<your_azure_key>

# GitHub Integration
export GITHUB_TOKEN=<your_github_token>

# Hugging Face Hub
export HUGGING_FACE_HUB_TOKEN=<your_hf_token>
```

## 📊 Advanced Features

### Cost Management
Automatic cost tracking and budget controls:
```bash
# Set maximum spending limit
python -m swingarena.inference.run_api \
    --max_cost 50.0 \
    --model_name_or_path gpt-4-0125-preview
```

### Parallel Processing
Distribute inference across multiple processes:
```bash
# Process data in shards
for i in {0..3}; do
    python -m swingarena.inference.run_api \
        --shard_id $i --num_shards 4 \
        --model_name_or_path gpt-3.5-turbo-1106 &
done
```

### Custom Model Arguments
Fine-tune model behavior with custom parameters:
```bash
python -m swingarena.inference.run_api \
    --model_args "temperature=0.1,top_p=0.9,max_tokens=2048,frequency_penalty=0.1"
```

### Memory Optimization for Llama Models
Configure memory usage for different hardware setups:
```bash
# For memory-constrained environments
python -m swingarena.inference.run_llama \
    --model_name_or_path princeton-nlp/SWE-Llama-7b \
    --max_len 1000  # Limit context length
```

## 🔍 Monitoring and Debugging

### Logging Configuration
All scripts include comprehensive logging:
- **Progress Tracking**: Real-time progress bars with ETA
- **Cost Monitoring**: Per-request cost calculation and running totals
- **Error Handling**: Detailed error messages with retry information
- **Performance Metrics**: Token throughput and processing times

### Output Format
Standardized JSONL output format:
```json
{
    "instance_id": "django__django-12345",
    "model_patch": "Generated code changes...",
    "model_name_or_path": "gpt-4-0125-preview",
    "text": "Full input prompt...",
    "full_output": "Complete model response...",
    "cost": 0.15
}
```

## 🚨 Troubleshooting

### Common Issues

**GPU Memory Errors:**
- Reduce batch size or use model sharding
- Check device mapping configuration
- Consider using smaller models

**API Rate Limits:**
- Implement exponential backoff (built-in)
- Use multiple API keys for higher throughput
- Adjust request frequency

**Context Length Exceeded:**
- Enable automatic context truncation
- Use models with larger context windows
- Implement intelligent context selection

**Installation Issues:**
- Ensure all dependencies are installed correctly
- Check CUDA compatibility for GPU inference
- Verify Pyserini installation for retrieval features

## 📈 Performance Optimization

### For API Models:
- Use appropriate context lengths to minimize costs
- Implement request batching for better throughput
- Monitor and optimize token usage

### For Local Models:
- Optimize device mapping for your hardware
- Use Flash Attention for memory efficiency
- Consider quantization for resource-constrained environments

### For Retrieval:
- Build indexes once and reuse across experiments
- Optimize query formulation for better relevance
- Use parallel processing for large-scale retrieval

## 📚 Research Applications

This framework supports various research directions:

- **Prompt Engineering**: Easy experimentation with different prompt styles
- **Context Selection**: Comparison of oracle vs. retrieved contexts
- **Model Comparison**: Systematic evaluation across different model families
- **Ablation Studies**: Fine-grained control over experimental conditions
- **Live Deployment**: Real-world application to GitHub issues

## 🤝 Contributing

When extending the framework:
1. Follow the existing code structure and naming conventions
2. Add comprehensive logging for new features
3. Include cost calculation for API-based additions
4. Test with both small and large-scale datasets
5. Update documentation for new parameters and features
