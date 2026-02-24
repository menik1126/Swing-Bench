# Statistical Analysis Tools

This folder contains statistical analysis and data processing tools for the SwingBench dataset, primarily used for data cleaning, difficulty annotation, result analysis, and other functions.

## Core Functional Modules

### 1. Dataset Construction and Processing (`utils.py`)
- **Dataset Loading**: Load SwingBench dataset from HuggingFace, supporting four languages: rust, cpp, python, go
- **CI Filtering**: Filter data instances that contain CI test information
- **Code Chunking**: Use CodeChunker and CodeReranker for code chunking and reranking
- **API Calls**: Encapsulate OpenAI-compatible API calls, supporting difficulty and clarity assessment

### 2. Difficulty and Clarity Assessment

#### Automated Annotation (`difficulty_estimate.py`)
- **Purpose**: Use large language models (such as grok-3-beta) to automatically assess problem difficulty and clarity
- **Usage**: `python difficulty_estimate.py`
- **Assessment Dimensions**:
  - Clarity Score (0-3): The clarity level of problem descriptions
  - Difficulty Score (0.0-1.0): The technical complexity required to solve the problem
- **Supported Features**: Parallel processing, code chunking, error retry

#### Annotation Result Checking (`sampling_checking.py`)
- **Purpose**: Check the completeness and quality of annotation results
- **Usage**: `python sampling_checking.py`
- **Check Content**: Missing field statistics, data integrity validation

#### Distribution Statistics (`difficulty_clarity_stats.py`)
- **Purpose**: Analyze the distribution of difficulty and clarity
- **Function**: Statistics on data volume distribution across different score ranges

### 3. Data Statistical Analysis

#### Basic Statistics (`stats.py`)
- **Token Length Analysis**: Calculate token length distribution for various fields using specified tokenizer
- **Supported Fields**: patch, test_patch, problem_statement, hints_text
- **Length Binning**: Classify token lengths into predefined interval statistics
- **Output Format**: JSON format statistical summary files

#### Arena Evaluation Statistics (`arena_stats.py`)
- **Purpose**: Analyze SwingArena battle evaluation results
- **Statistical Content**:
  - Battle result analysis (win rate statistics)
  - API call token consumption statistics
  - CI test pass rate statistics
  - Fix attempt count analysis
- **Supported Format**: Parse battle log files, generate detailed statistical reports

### 4. Agent Evaluation Tools

#### Agent Performance Testing (`agent_stats.py`)
- **Purpose**: Test the performance of patch generators and test generators
- **Testing Process**:
  - Load dataset and retriever
  - Create code editor
  - Generate patches and tests
  - Record performance metrics
- **Configuration Parameters**: API keys, model paths, retrieval file count, etc.

#### Batch Evaluation Script (`agent_stats.sh`)
- **Purpose**: Batch run agent performance tests for multiple languages
- **Supported Languages**: rust, python, go, cpp
- **Output**: Performance log files for each language

### 5. Utility Tools

#### Annotation Task Assignment (`annotate_helper.py`)
- **Purpose**: Assign large-scale annotation tasks to multiple annotators
- **Function**: Automatically split data files, evenly distribute workload
- **Annotator Management**: Support configuring annotator lists and work assignments

#### Result Aggregation (`accumulate_agent_stats.py`)
- **Purpose**: Aggregate evaluation results from multiple agents
- **Status**: Currently a placeholder file, functionality to be improved

## Usage Guide

### Basic Data Statistics
```bash
# Generate token length statistics
python stats.py --data_path /path/to/dataset --language_list rust,cpp,python,go

# Analyze difficulty and clarity distribution  
python difficulty_clarity_stats.py
```

### Difficulty Annotation Workflow
```bash
# 1. Run automated difficulty annotation
python difficulty_estimate.py

# 2. Check annotation results
python sampling_checking.py

# 3. View distribution statistics
python difficulty_clarity_stats.py
```

### Agent Performance Evaluation
```bash
# Single language testing
python agent_stats.py --language rust

# Batch test all languages
bash agent_stats.sh

# Analyze Arena battle results
python arena_stats.py --arena_log_dir ./evaluations/
```

## Data Path Configuration

Default data paths (configured in `utils.py`):
- Raw data: `../../dataset/swing-bench/`
- HuggingFace format: `../../dataset/swing-bench-hf-row`
- Filtered data: `../../dataset/swing-bench-hf-filtered`
- Annotation results: `../../dataset/swing-bench-annotated-jsonl`

## Notes

1. **API Configuration**: Need to configure corresponding API keys and base_url for LLM calls
2. **Environment Variables**: Some scripts require setting environment variables (such as `SWING_INDEXES_PATH`, etc.)
3. **Data Synchronization**: Only annotated jsonl files will be synced to GitHub, other data needs to be re-downloaded
4. **Parallel Processing**: Most statistical scripts support parallel processing to improve efficiency