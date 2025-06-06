# Data Collection

This folder contains the code for collecting and processing GitHub repository data. The pipeline follows a six-step process to gather, process, and filter data from GitHub repositories.

## Pipeline Steps

### Step 1: Repository Collection 🔍

Fetches repositories from GitHub based on specified languages and criteria.

```bash
python crawl/fetch_all.py \
    --output github_repos \
    --max-repos 100 \
    --concurrency 10 \
    --languages "python,java,javascript,go,rust,c++,php" \
    --parallel \
    --timeout 30 \
    --retry 3
```

**Parameters:**
- `--output`: Output directory for repositories
- `--max-repos`: Maximum repositories per language
- `--concurrency`: Number of concurrent requests
- `--languages`: Target programming languages
- `--parallel`: Enable parallel crawling
- `--timeout`: HTTP request timeout in seconds
- `--retry`: Number of retry attempts

### Step 2: Instance Extraction ⚙️

Extracts task instances from the collected repositories.

```bash
python get_tasks_pipeline.py \
    --repos swing_data/tasks/all_tasks.jsonl \
    --path_prs swing_data/tasks/prs \
    --path_tasks swing_data/tasks/tasks \
    --max_pulls 100 \
    --cutoff_date 20220101
```

**Parameters:**
- `--repos`: Path to repository list file
- `--path_prs`: Output directory for pull requests
- `--path_tasks`: Output directory for task instances
- `--max_pulls`: Maximum number of PRs to process
- `--cutoff_date`: Cut-off date for PRs (YYYYMMDD)

### Step 3: Result Combination 🔄

Merges extracted instances into a single dataset.

```bash
python crawl/merge_instances.py \
    --input swing_data/tasks/all_tasks.jsonl \
    --output swing_data/tasks/merged_tasks.jsonl
```

**Parameters:**
- `--input`: Path to task instances file
- `--output`: Path for merged output file

### Step 4: Initial Filtering 🔍

First round of data filtering to ensure quality.

```bash
python filter.py \
    --input swing_data/tasks/all_tasks.jsonl \
    --output swing_data/tasks/filtered_tasks.jsonl \
    --api-key <your-api-key> \
    --base-url <your-base-url> \
    --workers 10
```

**Parameters:**
- `--input`: Input file to filter
- `--output`: Output file for filtered data
- `--api-key`: API key for filtering service
- `--base-url`: Base URL for filtering service
- `--workers`: Number of worker threads

### Step 5: Dataset Building 📊

Constructs the dataset from filtered instances.

```bash
python build_dataset.py \
    swing_data/tasks/filtered_tasks.jsonl \
    --output swing_data/tasks/dataset.jsonl \
    --token <your-github-token>
```

**Parameters:**
- First argument: Input file path
- `--output`: Output dataset path
- `--token`: GitHub API token

### Step 6: Final Filtering ✨

Final quality assurance filtering of the dataset.

```bash
python filter.py \
    --input swing_data/tasks/dataset.jsonl \
    --output swing_data/tasks/filtered_dataset.jsonl \
    --api-key <your-api-key> \
    --base-url <your-base-url> \
    --workers 10
```

**Parameters:**
- Same as Step 4, but operates on the built dataset

## Directory Structure

```
collect/
├── crawl/
│   ├── fetch_all.py        # Step 1: Repository collection
│   ├── merge_instances.py  # Step 3: Result combination
│   └── filter.py          # Steps 4 & 6: Filtering
├── get_tasks_pipeline.py   # Step 2: Instance extraction
└── build_dataset.py       # Step 5: Dataset building
```

## Output Structure

```
swing_data/
├── tasks/
│   ├── all_tasks.jsonl         # Step 1 output
│   ├── prs/                    # Step 2 PR data
│   ├── tasks/                  # Step 2 task data
│   ├── merged_tasks.jsonl      # Step 3 output
│   ├── filtered_tasks.jsonl    # Step 4 output
│   ├── dataset.jsonl           # Step 5 output
│   └── filtered_dataset.jsonl  # Step 6 output
└── logs/
    └── *.log                   # Process logs
```

## Environment Setup

1. Required environment variables:
```bash
# GitHub API tokens (required)
export GITHUB_TOKENS='token1,token2,token3'

# API key and base URL for filtering service
export API_KEY='your-api-key'
export BASE_URL='your-base-url'
```

2. Required Python packages:
```bash
pip install aiohttp aiofiles tqdm
```

## Supported Languages

Currently supported programming languages:
- Python
- Java
- JavaScript
- Go
- Rust
- C++
- PHP

## Resource Requirements

- **Disk Space**: Varies based on repository count and size
- **Memory**: Depends on concurrency settings
- **Network**: Stable internet connection required
- **API Usage**: 
  - GitHub API tokens for repository access
  - Filtering service API key
  - Rate limiting handled automatically

## Error Handling

- Each step includes error handling and logging
- Failed operations are logged for investigation
- Progress is saved between steps
- Automatic retries for transient failures

## Quick Start

1. Set up environment variables:
```bash
export GITHUB_TOKENS='your-tokens-here'
export API_KEY='your-api-key'
export BASE_URL='your-base-url'
```

2. Run the complete pipeline:
```bash
./run_pipeline.sh
```

Or run individual steps as needed using the commands shown in each step section.
