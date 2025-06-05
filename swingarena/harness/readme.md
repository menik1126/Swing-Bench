# Agent Battle - SwingArena Evaluation Framework

## Overview

`agent_battle.py` is a comprehensive evaluation framework for conducting competitive programming battles between AI agents on the SwingArena dataset. This framework evaluates agents' capabilities in both patch generation and test generation for GitHub issue solving scenarios.

## Features

- **Dual Agent Battle**: Compares two AI agents in both patch generation and test generation tasks
- **Multi-turn Evaluation**: Supports multiple battle rounds for comprehensive assessment  
- **Patch & Test Verification**: Validates generated patches and tests against golden standards
- **CI Integration**: Supports various CI tools (like GitHub Actions via `act`)
- **Flexible Model Support**: Compatible with various LLM APIs and local models
- **Retrieval-Augmented Generation**: Uses BM25 retriever for context-aware code generation

## Architecture

The battle system consists of four main components:

1. **PatchGenerator**: Generates code patches to fix issues
2. **TestGenerator**: Creates test cases for validation
3. **PatchVerifier**: Validates patch correctness via CI execution
4. **TestVerifier**: Verifies test case validity and effectiveness

## Requirements

- Python 3.8+
- SwingArena dataset
- Git repositories for testing
- CI tool (e.g., `act` for GitHub Actions simulation)
- LLM API access or local model serving

## Environment Variables

Set these environment variables before running:

```bash
export SWING_TESTBED_PATH="/path/to/workdir"
export SWING_REPOS_DIR_PATH="/path/to/source/repos" 
export SWING_INDEXES_PATH="/path/to/retriever/indexes"
```

## Usage

### Basic Usage

```bash
python agent_battle.py \
    --dataset_name "SwingArena/SwingArena" \
    --language "rust" \
    --model_lhs "gpt-4" \
    --model_rhs "claude-3" \
    --api_key_lhs "your-api-key-1" \
    --api_key_rhs "your-api-key-2"
```

### Local Model Usage

```bash
python agent_battle.py \
    --base_url_lhs "http://localhost:8000/v1" \
    --base_url_rhs "http://localhost:8001/v1" \
    --model_lhs "/path/to/local/model1" \
    --model_rhs "/path/to/local/model2" \
    --api_key_lhs "no-api-key" \
    --api_key_rhs "no-api-key"
```

### Advanced Configuration

```bash
python agent_battle.py \
    --dataset_name "custom_dataset.jsonl" \
    --language "python" \
    --turns 3 \
    --ci_tool_name "act" \
    --port_range "10000-11000" \
    --open_file_limit 8192
```

## Command Line Arguments

### Dataset Configuration
- `--dataset_name`: Dataset name or path to JSON file (default: "SwingArena/SwingArena")
- `--language`: Programming language (default: "rust")
- `--split`: Dataset split to use (default: None)

### Model Configuration (LHS Agent)
- `--api_key_lhs`: API key for left-hand side agent
- `--base_url_lhs`: Base URL for LHS model API
- `--model_lhs`: Model identifier for LHS agent
- `--tok_model_lhs`: Tokenizer model for LHS (optional)

### Model Configuration (RHS Agent)  
- `--api_key_rhs`: API key for right-hand side agent
- `--base_url_rhs`: Base URL for RHS model API
- `--model_rhs`: Model identifier for RHS agent
- `--tok_model_rhs`: Tokenizer model for RHS (optional)

### Execution Configuration
- `--workdir`: Working directory for execution
- `--src_folder`: Source code repository folder
- `--retriever_index_dir`: Directory containing retriever indexes
- `--ci_tool_name`: CI tool to use (default: "act")
- `--turns`: Number of battle turns (default: 1)
- `--port_range`: Port range for CI execution (default: "10000-11000")
- `--open_file_limit`: System open file limit (default: 4096)

## Battle Logic

The evaluation follows this sequence:

1. **Preparation Stage**:
   - Clone required repositories
   - Run baseline CI on original code
   - Run CI on golden patch for reference

2. **Generation Stage** (per turn):
   - Agent A generates a patch
   - Agent B generates tests for the patch
   - Verify patch correctness against golden standard
   - Verify test effectiveness

3. **Cross-Validation Stage**:
   - Merge patch and tests
   - Execute combined solution
   - Score based on CI results

4. **Role Reversal**:
   - Repeat with agents swapped (A generates tests, B generates patches)

## Scoring System

- **Patch Agent Score**: Points for generating valid patches
- **Test Agent Score**: Points for generating effective tests  
- **Verified Scores**: Points for patches/tests that pass combined validation

The framework uses rule-based validation:
- **FPF/PPF rules**: Fail-Pass-Fail and Pass-Pass-Fail patterns indicate invalid solutions
- **FP/PF rules**: Used for test validation

## Output

The script provides detailed logging including:
- Individual CI execution results
- Patch and test validation outcomes
- Final scores for both agents
- Detailed failure analysis
