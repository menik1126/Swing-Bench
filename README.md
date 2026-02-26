<p align="center">
    <img src="docs/images/github_logo_pot.png" style="height: 10em" alt="SwingArena Logo" />
</p>

<div align="center">

 [English](https://github.com/menik1126/Swing-Bench/) 

</div>



<p align="center">
Code and data for our paper <a href="https://arxiv.org/abs/2505.23932">SwingArena: Competitive Programming Arena for Long-context GitHub Issue Solving</a>
    </br>
    </br>
    <a href="https://www.python.org/">
        <img alt="Build" src="https://img.shields.io/badge/Python-3.8+-1f425f.svg?color=purple">
    </a>
    <a href="https://copyright.princeton.edu/policy">
        <img alt="License" src="https://img.shields.io/badge/License-MIT-blue">
    </a>
</p>

Please refer our [website](https://swing-bench.github.io/) for the public leaderboard.

## 📰 News

* **[June. 5, 2024]**: We have released [SwingArena](https://arxiv.org/abs/2505.23932)! 

## 👋 Overview
SwingArena is a realistic, *CI-driven* evaluation framework for LLMs that simulates real-world software development by pairing models as patch *submitters* and *reviewers*, enhanced with *retrieval-augmented code generation* for multi-language support and long-context handling.

<img src="docs/images/main_pot.png">

## 🛠️ Technical Architecture & Environment Setup

SwingArena employs an advanced containerized evaluation architecture that ensures cross-platform reproducibility and consistency. The system core relies on **Docker** for isolated environment management, combined with **CI tools** (such as GitHub Actions simulated through `act`) to achieve real-world software development workflow evaluation.

### 🏗️ Architecture & Module Overview

SwingArena consists of five core modules that work together to create a complete software engineering benchmark pipeline:

#### 📊 Module Workflow

```mermaid
graph LR
    A[collect] --> B[prepare]
    B --> C[inference]
    C --> D[harness]
    D --> E[statistics]
    E --> A
    
    subgraph "Data Pipeline"
        A
        B
    end
    
    subgraph "Evaluation Pipeline"
        C
        D
        E
    end
```

#### 🔧 Core Modules

##### 📥 **collect** - Data Collection & Mining
- **Purpose**: Mine and filter high-quality GitHub repositories and pull requests
- **Key Functions**: Repository selection from top PyPI packages, PR collection with CI test validation, LLM-based quality filtering, expert rule-based validation
- **Outputs**: Task instances with issues, patches, and test cases

##### 🛠️ **prepare** - Data Preparation & Indexing  
- **Purpose**: Process and index collected data for efficient retrieval
- **Key Functions**: Repository cloning and management, BM25 search index construction, multi-stage quality filtering (CI, annotation, content), dataset validation and testing
- **Integration**: Builds indexes used by `inference` for context-aware generation

##### 🤖 **inference** - Model Inference Engine
- **Purpose**: Generate patches and solutions using various AI models
- **Key Functions**: API model support (OpenAI, Anthropic, Claude), local Llama model inference, live GitHub issue solving, retrieval-augmented code generation
- **Integration**: Uses prepared datasets and indexes from `prepare`

##### ⚔️ **harness** - Evaluation Framework
- **Purpose**: Evaluate model performance through CI-driven testing
- **Key Functions**: Dual-agent battle mode (patch submitter vs reviewer), CI workflow simulation, patch and test validation, Docker-based isolated execution
- **Integration**: Validates patches through real CI environments, similar to `collect` filtering

##### 📈 **statistics** - Analysis & Reporting
- **Purpose**: Analyze results and provide insights for dataset improvement
- **Key Functions**: Performance metric analysis, difficulty and clarity assessment, token usage and cost tracking, dataset quality reporting
- **Integration**: Provides feedback to improve `collect` filtering criteria (quality loop)

### 🔧 System Requirements
Before getting started, please ensure your system meets the following requirements:
- **Docker**: Follow the [Docker official installation guide](https://docs.docker.com/engine/install/) to install Docker Engine. Linux users are recommended to refer to the [post-installation steps](https://docs.docker.com/engine/install/linux-postinstall/) for optimal experience.
- **Hardware Configuration**: Recommended `x86_64` architecture machine with at least 120GB available storage, 16GB RAM, and 8 CPU cores (`arm64` support is still experimental)
- **Python Environment**: Python 3.8+ and related dependency packages

### 🏗️ Core Technology Stack
SwingArena integrates multiple cutting-edge technologies:

**AI Model Integration**: Supports various large language model APIs (OpenAI, Anthropic, Claude, etc.) and local model serving through a flexible model proxy system for seamless switching.

**Retrieval-Augmented Generation**: Built-in BM25 retriever provides precise relevant information retrieval for long-context code generation, supporting multi-language codebase indexing (Python, Rust, C++, Go, JavaScript, TypeScript, PHP, etc.).

**Distributed Evaluation**: Adopts multi-process parallel evaluation architecture with Modal cloud execution support, dynamically adjusting worker processes based on system resources (recommended not to exceed `min(0.75 * os.cpu_count(), 24)`).

**Arena Mechanism**: Pioneering dual-agent battle evaluation mode where one agent acts as a patch submitter and another as a code reviewer, simulating real collaborative development scenarios.

**Data Processing Pipeline**: Complete data collection, annotation, and evaluation pipeline with automated GitHub repository issue collection and PR analysis, multi-round annotation quality control, CI-driven validation, and detailed performance metrics analysis.

## 🚀 Quick Start

To build SwingArena from source, follow these steps:

### 🔧 Basic Installation
```bash
git clone https://github.com/menik1126/Swing-Bench.git
cd Swing-Bench
pip install -e .
```

### 🛠️ Full Installation with CI Tools (Recommended)

For complete SwingArena functionality including agent battles and CI simulation:

```bash
pip install -e ".[ci-tools]"
```

**This single command will:**
- ✅ Install all Python dependencies (including Docker SDK, YAML parser)
- 🐳 **Automatically install Docker** (on supported Linux distributions)
- 🔧 **Automatically install `act`** (GitHub Actions local runner)
- 🔗 Set up pre-commit hooks

> **💡 How it works**:
> - First installs Python packages
> - Then automatically detects the `[ci-tools]` extra and installs system tools
> - On macOS/Windows, uses Homebrew/Chocolatey when available

**To skip system tools installation:**
```bash
pip install -e ".[ci-tools]" --install-option="--skip-ci-tools"
# Then install manually later:
python install_ci_tools.py
```

> **⚠️ Note**: On macOS/Windows, you may need to install Docker Desktop manually if package managers (brew/choco) are not available.

### ☕ Java Requirements for BM25 Retrieval

If you plan to use BM25 retrieval for code search (used by the `prepare` and `inference` modules), you'll need Java 21+:

**Installation:**
```bash
# Using conda (recommended)
conda install openjdk=21

# Set environment variables (add to ~/.bashrc or ~/.zshrc)
export JVM_PATH=$CONDA_PREFIX/lib/jvm/lib/server/libjvm.so
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib/jvm/lib/server:$LD_LIBRARY_PATH
```

**Alternative installation methods:**
- **Ubuntu/Debian**: `sudo apt-get install openjdk-21-jdk`
- **macOS**: `brew install openjdk@21`
- **Windows**: Download from [Adoptium](https://adoptium.net/) or use `choco install openjdk21`

> **💡 Note**: Java is required for the `pyserini` library used in BM25 indexing and retrieval. Without it, you can still use other SwingArena features but won't be able to build search indexes or use retrieval-augmented generation.

### 🔧 CI Tools Installation Details

**Prerequisites:**
- **Git** (required for repository operations)
- **Docker** (required for act to run GitHub Actions and containerized environments)
- **sudo/admin privileges** (for system-level tool installation)

**Alternative Installation Methods:**

If the automatic installation doesn't work, use the dedicated installer:
```bash
python install_ci_tools.py
```

**Manual Installation (if automatic fails):**

*Docker Installation:*
- **Linux (Ubuntu/Debian)**:
  ```bash
  curl -fsSL https://get.docker.com -o get-docker.sh
  sudo sh get-docker.sh
  sudo usermod -aG docker $USER
  ```
- **Linux (CentOS/RHEL)**:
  ```bash
  sudo yum install -y yum-utils
  sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
  sudo yum install -y docker-ce docker-ce-cli containerd.io
  sudo systemctl start docker && sudo systemctl enable docker
  sudo usermod -aG docker $USER
  ```
- **macOS**: [Download Docker Desktop](https://docs.docker.com/desktop/mac/install/) or `brew install --cask docker`
- **Windows**: [Download Docker Desktop](https://docs.docker.com/desktop/windows/install/) or use Chocolatey/winget

*act Installation:*
- **Linux**: `curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash`
- **macOS**: `brew install act`
- **Windows**: `choco install act-cli` or `winget install nektos.act`

### ✅ Installation Verification

Verify CI tools installation:
```bash
python install_ci_tools.py --check
```

Expected output after successful CI tools installation:
```
🔍 Checking CI tools installation status...

act (GitHub Actions): ✅ Installed
Docker: ✅ Installed
Git: ✅ Installed
Python docker: ✅ Installed
Python yaml: ✅ Installed

📊 Overall status: ✅ All tools ready
```

## ⚙️ Environment Configuration

SwingArena uses environment variables for API keys, paths, and configuration. All variables can be set in a `.env` file, via shell `export`, or passed inline when running scripts.

### 1. Create .env File

```bash
cp .env.example .env
```

### 2. Configure LLM API

The core battle / inference features require an **OpenAI-compatible** LLM endpoint:

```bash
# LLM endpoint (any OpenAI-compatible API)
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=gpt-4

# Tokenizer for token counting (HuggingFace model name)
# Use "gpt2" for OpenAI models, or match the model family for others
LLM_TOK_MODEL=gpt2
```

Common provider examples:

| Provider | `LLM_BASE_URL` | `LLM_MODEL` example |
|----------|----------------|---------------------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4` |
| DashScope | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-max-latest` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Local vLLM | `http://localhost:8000/v1` | model path or name |

### 3. Configure Workspace Paths

```bash
# Temporary workspace for CI evaluation runs
SWING_TESTBED_PATH=/path/to/testbed

# Directory containing cloned repositories
SWING_REPOS_DIR_PATH=/path/to/repos

# Directory containing BM25 search indexes
SWING_INDEXES_PATH=/path/to/indexes

# CI tool: "act" (local GitHub Actions) or "cargo" (Rust only)
CI_TOOL_NAME=act
```

> **Path recommendations:**
> - Use absolute paths
> - Ensure sufficient disk space (~10 GB per language for repos)
> - Directories are auto-created by `scripts/setup_env.sh`, or create manually: `mkdir -p /path/to/{testbed,repos,indexes}`

### 4. Optional Configuration

```bash
# Java (required by pyserini for BM25 retrieval; auto-detected if on PATH)
# JAVA_HOME=/path/to/jdk-21

# Direct path to libjvm.so (overrides JAVA_HOME; used by pyjnius).
# Only needed when pyjnius cannot auto-detect the JVM, e.g. in conda envs.
# JVM_PATH=/usr/lib/jvm/java-21-openjdk-amd64/lib/server/libjvm.so

# API keys for inference / collect modules (not needed for agent_battle)
# OPENAI_API_KEY=sk-xxx
# ANTHROPIC_API_KEY=sk-ant-xxx
# GITHUB_TOKEN=ghp_xxx
# GITHUB_TOKENS=ghp_token1,ghp_token2,ghp_token3
```

### 5. Git Identity

Git author/committer identity used when applying patches to repositories during battle evaluation. If not set, `git commit` may fail in clean environments (e.g. fresh containers) where no global git config exists.

```bash
GIT_AUTHOR_NAME=SwingBench
GIT_AUTHOR_EMAIL=swingbench@local
GIT_COMMITTER_NAME=SwingBench
GIT_COMMITTER_EMAIL=swingbench@local
```

These are already set with default values in `.env.example`. Override them if you need commits attributed to a specific identity.

> **💡 Tip**: Run `source scripts/setup_env.sh` to load `.env` and auto-detect Java. The script only sets defaults for variables that are not already exported.

> **🔒 Security**: Never commit your `.env` file to version control. It contains sensitive API keys.

## 📊 Dataset Access

SwingArena automatically downloads datasets from Hugging Face when needed. You can also load them manually:

```python
from datasets import load_dataset

# Load the main SwingBench dataset
dataset = load_dataset('SwingBench/SwingBench', split='test')

# Or load language-specific datasets
languages = ['rust', 'cpp', 'python', 'go', 'java', 'javascript', 'php']
swingbench = {}
for lang in languages:
    swingbench[lang] = load_dataset('SwingBench/SwingBench-data', split=lang)
```

## 🎯 First Run: Verify Your Setup

Now let's run a simple evaluation to verify everything works. This requires two steps:

> **⚠️ Important Prerequisites:**
> - **Docker must be running** (check with `docker ps`)
> - This will **download dataset from HuggingFace** (~500MB) and **clone repositories from GitHub** (~100MB)
> - First run will **build Docker images** and may take 5-10 minutes

### Step 1: Prepare Repositories

First, clone the repositories needed for evaluation:

```bash
python swingarena/prepare/swing_clone_repos.py \
    --dataset_path SwingBench/SwingBench \
    --repo_root_dir ./repos
```

**What this does:**
- Downloads SwingBench dataset from HuggingFace
- Clones all repositories from the dataset to `./repos`
- Checks out the correct commits for each repository

> **Note:** This will clone all repositories in the dataset (~10GB total). The cloning process may take 10-30 minutes depending on network speed.

### Step 2: Run Evaluation

Now run the evaluation harness:

```bash
python -m swingarena.harness.run_evaluation \
    --dataset_name SwingBench/SwingBench \
    --split test \
    --predictions_path gold \
    --src_folder ./repos \
    --target_dir ./testbed \
    --report_dir ./report \
    --concurrent_workers 1 \
    --instance_ids pypa__pipenv-6240
```

**What this does:**
1. Loads `pypa__pipenv-6240` instance from SwingBench (Python project with 22 CI jobs)
2. Copies repository from `./repos` to isolated testbed
3. Applies the gold patch (correct fix) and test patch
4. Runs CI tests using GitHub Actions (via `act` tool)

**Expected output:**
```
Loading dataset...
Copying repository to testbed...
Running CI tests...
✅ Evaluation complete - results in ./report/
```

If successful, you're ready to use SwingArena! 🎉

> **💡 Note:** All 100 instances in SwingBench include both patches and test patches, with full CI configurations across 4 languages (Python, Rust, Go, C++).

## 💽 Basic Usage

### Running Evaluations

> **⚠️ Prerequisites:** You must first complete the [Data Preparation](#-data-preparation-prepare) step to clone repositories.

Evaluate model predictions on SwingArena using the evaluation harness:

```bash
python -m swingarena.harness.run_evaluation \
    --dataset_name SwingBench/SwingBench \
    --split test \
    --predictions_path <path_to_predictions> \
    --src_folder ./repos \
    --target_dir ./testbed \
    --report_dir ./report \
    --concurrent_workers <num_workers>
    # use --predictions_path 'gold' to verify the gold patches
```

**Key Parameters:**
- `--dataset_name`: Dataset to use (default: SwingBench/SwingBench)
- `--split`: Dataset split to use (test, train, etc.)
- `--predictions_path`: Path to predictions file, or 'gold' for gold patches
- `--src_folder`: Directory containing cloned repositories (from prepare step)
- `--target_dir`: Isolated testbed directory for running evaluations
- `--report_dir`: Directory for evaluation results and logs
- `--concurrent_workers`: Number of parallel workers (recommended: `min(0.75 * os.cpu_count(), 24)`)
- `--instance_ids`: Specific instance IDs to evaluate (space-separated)
- `--timeout`: Timeout in seconds for each instance (default: 600)

**Output:**
This command generates:
- Docker build logs in `logs/build_images/`
- Evaluation logs in `logs/run_evaluation/`
- Final results in `evaluation_results/`

To see all available options:
```bash
python -m swingarena.harness.run_evaluation --help
```

> [!WARNING]
> **Resource Requirements**
> - Recommended: `x86_64` machine with at least 120GB free storage, 16GB RAM, 8 CPU cores
> - For Docker Desktop: Increase virtual disk space to ~120GB
> - Adjust `--concurrent_workers` based on available resources
> - `arm64` support is experimental

### Using SwingArena for Model Development

The SwingArena repository can help you:
* Train your own models on our pre-processed datasets
* Run [inference](https://github.com/menik1126/Swing-Bench/blob/main/swingarena/inference/README.md) on existing models (local models like LLaMA, or API models like GPT-4)
* Run SwingArena's [data collection procedure](https://github.com/menik1126/Swing-Bench/blob/main/swingarena/collect/) on your own repositories

## 🗂️ Data Preparation (prepare) - **REQUIRED**

> **⚠️ IMPORTANT:** This step is **required** before running evaluations. The harness needs pre-cloned repositories to run CI tests.

The `prepare` module helps you clone repositories and build search indexes. This is required for:
- **All evaluation runs** (harness needs local repositories)
- Arena Battle mode (retrieval-augmented patch generation)
- Model inference with code search
- Working with custom datasets

### Prerequisites
- Java 21+ (for BM25 index building, see [installation guide](#-java-requirements-for-bm25-retrieval))
- Sufficient disk space (repos can be large, ~10GB per language)

### Clone Repositories

Clone repositories from the SwingBench dataset or your custom task instances:

```bash
cd swingarena/prepare

# Clone from SwingBench dataset
python swing_clone_repos.py \
    --dataset_path SwingBench/SwingBench \
    --repo_root_dir /path/to/repos

# Or from a local .jsonl file
python swing_clone_repos.py \
    --dataset_path /path/to/task-instances.jsonl \
    --repo_root_dir /path/to/repos
```

**What this does:**
- Downloads repositories from GitHub based on task instances
- Checks out the correct commit for each instance
- Organizes repos by `owner__repo` naming convention

### Build BM25 Search Indexes

Build search indexes for fast code retrieval:

```bash
cd swingarena/prepare

# Build indexes for SwingBench dataset
python swing_build_index.py \
    --dataset_path SwingBench/SwingBench \
    --repo_root_dir /path/to/repos \
    --output_dir /path/to/indexes

# Or specify a language/subset
python swing_build_index.py \
    --dataset_path /path/to/task-instances.jsonl \
    --repo_root_dir /path/to/repos \
    --output_dir /path/to/indexes \
    --sub_dataset_identifier Python
```

**Parameters:**
- `--dataset_path`: Path to dataset or HuggingFace dataset name
- `--repo_root_dir`: Directory containing cloned repositories
- `--output_dir`: Where to save the BM25 indexes
- `--sub_dataset_identifier`: Optional language filter (`python`, `rust`, `go`, `cpp` - case insensitive)

**What this does:**
- Parses source code files in each repository
- Builds BM25 indexes for fast text search
- Saves indexes to disk for use by inference/arena modules

**Index Structure:**
```
indexes/
├── python_index/
├── rust_index/
└── ...
```

> **💡 Note**: Index building can take 1-2 hours for the full SwingBench dataset. You can build indexes for specific languages to save time.

## 🤖 Model Inference (inference)

The `inference` module generates patches/solutions using AI models. This step comes after data preparation if you're using retrieval-augmented generation.

### Using API Models

Generate solutions with OpenAI, Anthropic, or other API providers:

```bash
cd swingarena/inference

python -m swingarena.inference.run_api \
    --dataset_name_or_path SwingBench/SwingBench \
    --split test \
    --model_name_or_path gpt-4 \
    --output_dir /path/to/output \
    --max_cost 1.0
```

**Key Parameters:**
- `--dataset_name_or_path`: Dataset to use (HuggingFace name or local .jsonl)
- `--model_name_or_path`: Model identifier (gpt-4, claude-3-opus, etc.)
- `--output_dir`: Where to save generated patches
- `--max_cost`: Maximum API cost in USD (stops when reached)
- `--instance_ids`: Specific instances to run (optional)

### Using Local Models

Run inference with local models like LLaMA:

```bash
python -m swingarena.inference.run_llama \
    --dataset_name_or_path SwingBench/SwingBench \
    --model_name_or_path /path/to/llama-model \
    --output_dir /path/to/output
```

### With Retrieval-Augmented Generation

To use code search for better context (requires prepared data):

> **Prerequisites:** Configure environment variables in your `.env` file (see [Environment Configuration](#%EF%B8%8F-environment-configuration))

```bash
# Run inference with retrieval
python -m swingarena.inference.run_api \
    --dataset_name_or_path SwingBench/SwingBench \
    --model_name_or_path gpt-4 \
    --output_dir /path/to/output \
    --use_retrieval
```

SwingArena will automatically use `SWING_REPOS_DIR_PATH` and `SWING_INDEXES_PATH` from your `.env` file.

For more details, see the [inference README](https://github.com/menik1126/Swing-Bench/blob/main/swingarena/inference/README.md).

## 🚀 Advanced Features

### 🥊 Arena Battle Mode

SwingArena's dual-agent battle evaluation mode allows you to compare two AI models in a competitive programming environment.

**Prerequisites:**
1. **Complete Data Preparation** (see [Data Preparation](#-data-preparation-prepare) section above)
2. **Configure `.env`** (see [Environment Configuration](#%EF%B8%8F-environment-configuration) section)

**Quick Start (recommended):**

```bash
# 1. Load environment (auto-detects Java, creates dirs)
source scripts/setup_env.sh

# 2. Run battle — all config comes from .env / env vars
bash scripts/run_battle.sh
```

Override any parameter via environment variables:

```bash
LLM_MODEL=gpt-4 LLM_BASE_URL=https://api.openai.com/v1 \
DATASET_NAME=SwingBench/SwingBench BATTLE_LANGUAGE=rust \
bash scripts/run_battle.sh
```

**Running directly (without script):**

```bash
python swingarena/harness/agent_battle.py \
    --dataset_name SwingBench/SwingBench \
    --split test \
    --src_folder $SWING_REPOS_DIR_PATH \
    --retriever_index_dir $SWING_INDEXES_PATH \
    --workdir $SWING_TESTBED_PATH \
    --ci_tool_name act \
    --base_url_lhs https://api.openai.com/v1 \
    --api_key_lhs $LLM_API_KEY \
    --model_lhs gpt-4 \
    --tok_model_lhs gpt2 \
    --base_url_rhs https://api.openai.com/v1 \
    --api_key_rhs $LLM_API_KEY \
    --model_rhs gpt-4 \
    --tok_model_rhs gpt2 \
    --turns 1
```

**Battle Parameters:**

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--dataset_name` | HuggingFace dataset name or local `.jsonl` path | `SwingBench/SwingBench` |
| `--language` | Language filter | `rust` |
| `--split` | Dataset split | `test` |
| `--src_folder` | Directory containing cloned repositories | `$SWING_REPOS_DIR_PATH` |
| `--retriever_index_dir` | Directory containing BM25 search indexes | `$SWING_INDEXES_PATH` |
| `--workdir` | Temporary workspace for CI runs | `$SWING_TESTBED_PATH` |
| `--ci_tool_name` | CI tool (`act` or `cargo`) | `act` |
| `--model_lhs/rhs` | LLM model names for the two agents | — |
| `--base_url_lhs/rhs` | OpenAI-compatible API endpoints | — |
| `--api_key_lhs/rhs` | API keys for the two agents | — |
| `--tok_model_lhs/rhs` | HuggingFace tokenizer names | — |
| `--turns` | Number of battle rounds | `1` |
| `--port_range` | Port range for `act` artifact server | `10000-11000` |
| `--retrieve_file_num` | Number of files retrieved via BM25 for context | `10` |
| `--agent_retry_times` | Max retry attempts when agent LLM call fails | `3` |
| `--max_chunk_num` | Max code chunks kept after reranking for LLM context | `16` |
| `--max_instances` | Max dataset instances to process (`0` = all) | `0` |

When using `run_battle.sh`, these parameters are configured via environment variables:

| Env Variable | Maps to | Default |
|---|---|---|
| `LLM_BASE_URL` | `--base_url_lhs/rhs` | `http://localhost:8000/v1` |
| `LLM_API_KEY` | `--api_key_lhs/rhs` | `no-api-key` |
| `LLM_MODEL` | `--model_lhs/rhs` | `Qwen/Qwen2.5-Coder-7B-Instruct` |
| `LLM_TOK_MODEL` | `--tok_model_lhs/rhs` | `Qwen/Qwen2.5-7B-Instruct` |
| `DATASET_NAME` | `--dataset_name` | `SwingBench/SwingBench` |
| `BATTLE_LANGUAGE` | `--language` | `python` |
| `SPLIT` | `--split` | `test` |
| `CI_TOOL` | `--ci_tool_name` | `act` |
| `TURNS` | `--turns` | `1` |
| `PORT_RANGE` | `--port_range` | `10000-11000` |
| `RETRIEVE_FILE_NUM` | `--retrieve_file_num` | `10` |
| `AGENT_RETRY_TIMES` | `--agent_retry_times` | `3` |
| `MAX_CHUNK_NUM` | `--max_chunk_num` | `16` |
| `MAX_INSTANCES` | `--max_instances` | `1` |
| `RERANKER_GPU` | GPU id for CodeBERT reranker | `0` |
| `ACT_TIMEOUT_SECONDS` | Timeout per act CI job (for matrix jobs) | `7200` (2h) |

### Matrix CI Jobs (Beginner-Friendly)

Many GitHub Actions workflows in SwingBench use **matrix jobs**. A matrix job means:

- You describe a **set of parameters** (for example different OS and Python versions)
- CI **automatically runs the same job once for each parameter combination**

For example, a `matrix` like this:

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: [3.8, 3.9, 3.10, 3.11, 3.12]
```

expands to many jobs like:

- Ubuntu + Python 3.8
- Ubuntu + Python 3.9
- ...
- Windows + Python 3.12

Each combination runs the **same CI steps**, but on a different environment. This is great for compatibility, but very slow to simulate locally with `act`.

To keep SwingBench runs practical, you can reduce the matrix size via the workflow (editing `strategy.matrix`) or via `act` filters (see `ACT_MATRIX_FILTER` in `.env.example` and `swingarena/harness/readme.md`):

- Set `ACT_MATRIX_FILTER` to a single representative combination, for example `os:ubuntu-latest,python-version:3.10`
- The framework converts this into `act --matrix os:ubuntu-latest --matrix python-version:3.10`, so only that one environment is executed

If you want full matrix coverage, simply leave `ACT_MATRIX_FILTER` empty or comment it out; CI will then run all combinations defined in the workflow.

### 🌩️ Cloud Evaluation with Modal

Run evaluations on the cloud using [Modal](https://modal.com/) to avoid local setup:

```bash
# Note: Modal evaluation requires using the modal_eval module
python -m swingarena.harness.modal_eval.run_evaluation_modal \
    --predictions_path gold \
    --instance_ids tokio-rs__tokio-6978
```

> [!NOTE]
> Modal for SwingArena is currently experimental and may not be fully supported.

### 🔄 Complete Workflow: Building Custom Datasets

This workflow shows how to use all five SwingArena modules to create and evaluate custom datasets. Follow these steps in order:

```mermaid
graph LR
    A[collect] --> B[prepare]
    B --> C[inference]
    C --> D[harness]
    D --> E[statistics]
    E -.feedback.-> A
```

#### 1. **Data Collection** (`collect`)

Mine GitHub repositories and create task instances:

```bash
# Set your GitHub token
export GITHUB_TOKEN=$(gh auth token)  # Or set it manually

python swingarena/collect/get_tasks_pipeline.py \
    --repos owner/repo-name \
    --path_prs ./collected_data/prs \
    --path_tasks ./collected_data/tasks \
    --max_pulls 100
```

**Key Parameters:**
- `--repos`: GitHub repository to collect from (format: `owner/repo-name`)
- `--path_prs`: Directory to save PR data
- `--path_tasks`: Directory to save task instances
- `--max_pulls`: Maximum number of PRs to process (optional)

**What this does:**
- Collects pull requests from specified GitHub repositories
- Filters PRs with passing CI tests
- Extracts problem statements, patches, and test cases
- Saves task instances to `.jsonl` format

**Output:** `task-instances.jsonl` containing collected issues

**Environment Variables:**
- `GITHUB_TOKEN`: Required for GitHub API access (get from `gh auth token` or [github.com/settings/tokens](https://github.com/settings/tokens))

For more details, see the [collect README](https://github.com/menik1126/Swing-Bench/blob/main/swingarena/collect/README.md).

---

#### 2. **Data Preparation** (`prepare`)

See the [Data Preparation](#-data-preparation-prepare) section above for detailed instructions.

**Quick commands:**
```bash
cd swingarena/prepare

# Clone repositories
python swing_clone_repos.py \
    --dataset_path /path/to/task-instances.jsonl \
    --repo_root_dir /path/to/repos

# Build BM25 indexes
python swing_build_index.py \
    --dataset_path /path/to/task-instances.jsonl \
    --repo_root_dir /path/to/repos \
    --output_dir /path/to/indexes
```

**Output:** Cloned repositories and BM25 search indexes

---

#### 3. **Model Inference** (`inference`)

See the [Model Inference](#-model-inference-inference) section above for detailed instructions.

**Quick commands:**
```bash
cd swingarena/inference

# Generate patches with API models
python -m swingarena.inference.run_api \
    --dataset_name_or_path /path/to/task-instances.jsonl \
    --model_name_or_path gpt-4 \
    --output_dir /path/to/predictions \
    --max_cost 1.0
```

**Output:** `predictions.jsonl` containing model-generated patches

---

#### 4. **Evaluation** (`harness`)

Evaluate the generated patches using CI-driven testing:

```bash
python -m swingarena.harness.run_evaluation \
    --dataset_name /path/to/task-instances.jsonl \
    --predictions_path /path/to/predictions.jsonl \
    --src_folder /path/to/repos \
    --target_dir /path/to/testbed \
    --report_dir /path/to/report \
    --concurrent_workers 4
```

**What this does:**
- Copies repositories from `src_folder` to isolated testbed
- Applies model-generated patches
- Runs CI tests (GitHub Actions via `act` or Cargo tests)
- Records pass/fail results

**Output:** Evaluation results in `report_dir`

See [Basic Usage](#-basic-usage) for more evaluation options.

---

#### 5. **Analysis** (`statistics`)

Generate performance metrics and insights:

```bash
cd swingarena/statistics

python arena_stats.py --arena_log_dir /path/to/evaluation_results
```

**What this does:**
- Calculates pass rates and success metrics
- Analyzes difficulty and clarity correlations
- Tracks token usage and API costs
- Generates reports for dataset quality assessment

**Output:** Statistical reports and visualizations

---

### 🔁 Iterative Improvement

Use insights from the analysis (step 5) to improve your data collection criteria (step 1):
- Adjust difficulty thresholds
- Filter by clarity scores
- Refine repository selection
- Update quality criteria

This creates a feedback loop for continuous dataset improvement.

## 🍎 Tutorials
We've also written the following blog posts on how to use different parts of SwingBench.
If you'd like to see a post about a particular topic, please let us know via an issue.
* [Nov 1. 2023] Collecting Evaluation Tasks for SwingArena ([🔗](https://github.com/menik1126/Swing-Bench/blob/main/swingarena/collect/README.md))


## 🚨 Troubleshooting

### Common CI Tool Issues

**1. "act: command not found"**
- Ensure `/usr/local/bin` is in your PATH
- Reinstall: `python install_ci_tools.py --force`

**2. "Docker daemon not running"**
- Start Docker service: `sudo systemctl start docker` (Linux)
- Start Docker Desktop (macOS/Windows)

**3. Permission denied errors**
- Add user to docker group: `sudo usermod -aG docker $USER`
- Log out and back in

For detailed troubleshooting, see [CI_TOOLS_SETUP.md](CI_TOOLS_SETUP.md).

## ✍️ Citation
If you find our work helpful, please use the following citations.
```
@article{xu2025swingarena,
  title={SwingArena: Competitive Programming Arena for Long-context GitHub Issue Solving},
  author={Xu, Wendong and Xiong, Jing and Zhao, Chenyang and Chen, Qiujiang and Wang, Haoran and Shen, Hui and Wan, Zhongwei and Dai, Jianbo and Wu, Taiqiang and Xiao, He and others},
  journal={arXiv preprint arXiv:2505.23932},
  year={2025}
}
```

## 🪪 License
MIT. Check `LICENSE.md`.