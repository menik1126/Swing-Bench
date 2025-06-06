# Step 1: Fetch all repositories
python crawl/fetch_all.py \
    --output github_repos \
    --max-repos 100 \
    --concurrency 10 \
    --languages "python,java,javascript,go,rust,c++,php" \
    --parallel \
    --timeout 30 \
    --retry 3

# Step 2: Extract instances
python get_tasks_pipeline.py \
    --repos swing_data/tasks/all_tasks.jsonl \
    --path_prs swing_data/tasks/prs \
    --path_tasks swing_data/tasks/tasks \
    --max_pulls 100 \
    --cutoff_date 20220101

# Step 3: Combine results
python crawl/merge_instances.py \
    --input swing_data/tasks/all_tasks.jsonl \
    --output swing_data/tasks/merged_tasks.jsonl

# Step 4: Filter
python filter.py \
    --input swing_data/tasks/all_tasks.jsonl \
    --output swing_data/tasks/filtered_tasks.jsonl \
    --api-key <your-api-key> \
    --base-url <your-base-url> \
    --workers 10

# Step 5: Build dataset
python build_dataset.py \
    swing_data/tasks/filtered_tasks.jsonl \
    --output swing_data/tasks/dataset.jsonl
    --token <your-github-token>

# Step 6: Filter
python filter.py \
    --input swing_data/tasks/dataset.jsonl \
    --output swing_data/tasks/filtered_dataset.jsonl \
    --api-key <your-api-key> \
    --base-url <your-base-url> \
    --workers 10