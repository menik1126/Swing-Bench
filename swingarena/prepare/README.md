# SwingBench Data Preparation Framework

The `prepare` module provides a comprehensive suite of tools for preparing, filtering, and indexing SwingBench datasets. This framework handles the entire data pipeline from raw repository cloning to final dataset preparation with quality filtering and search index construction.

## 🚀 Overview

The preparation framework consists of several specialized components that work together to create high-quality, searchable datasets for software engineering benchmarks:

- **Repository Management**: Automated cloning and management of source repositories
- **Search Index Construction**: BM25-based indexing for efficient code retrieval
- **Multi-stage Filtering**: Quality assurance through CI, annotation, and content-based filters
- **Dataset Processing**: Comprehensive testing and validation utilities

## 📁 Module Components

### 1. **Repository Cloning** (`swing_clone_repos.py`)

Automated repository cloning from SwingBench datasets with support for recursive submodule initialization.

**Features:**
- **Batch Processing**: Clone multiple repositories from dataset configurations
- **Submodule Support**: Recursive cloning with `--recursive` flag
- **Path Management**: Organized directory structure with standardized naming

**Usage:**
```bash
python swingarena/prepare/swing_clone_repos.py \
    --dataset_path /path/to/swing-dataset \
    --repo_root_dir ./repositories
```

**Functionality:**
- Reads repository lists from parquet/dataset files
- Creates sanitized directory names (replacing `/` with `__`)
- Handles authentication via GitHub tokens (if available)
- Supports multiple dataset splits (train/test/validation)

### 2. **Search Index Builder** (`swing_build_index.py`)

Advanced indexing system for building BM25-based search indexes across multiple repository commits.

**Key Features:**
- **Multi-commit Indexing**: Build separate indexes for different commit states
- **Document Encoding**: Multiple strategies for code representation
- **Parallel Processing**: Multi-threaded index construction
- **Incremental Updates**: Skip existing indexes to resume interrupted builds

**Document Encoding Strategies:**
- **file_name_and_contents**: Complete file content with path information
- **file_name_and_documentation**: AST-based extraction of docstrings and comments

**Advanced Configuration:**
```bash
python swing_build_index.py \
    --dataset_path /path/to/swingbench \
    --language rust \
    --split test \
    --root_dir ./indexes \
    --repo_root_dir ./repositories \
    --document_encoding_style file_name_and_contents \
    --python $(which python)
```

**Index Structure:**
```
indexes/
├── repo__owner__name/
│   └── file_name_and_contents/
│       ├── commit_hash_1/
│       │   └── index/
│       └── commit_hash_2/
│           └── index/
```

**Technical Details:**
- Uses Pyserini for Lucene-based indexing
- Filters out documentation files (.md, .txt, .rst, .pdf)
- Git operations for commit checkout and cleanup
- Error handling for malformed files
- Automatic cleanup of temporary document files

### 3. **CI-based Filtering** (`ci_filter.py`)

Continuous Integration verification for dataset quality assurance.

**Purpose:**
- Validate that patches can be successfully applied
- Ensure CI workflows execute properly
- Filter out instances that fail basic integration tests

**Components:**
- **PatchVerifier Integration**: Uses SwingBench's built-in verification system
- **ACT Support**: Local CI execution using GitHub Actions compatible runner
- **Batch Processing**: Efficient filtering of large instance collections

**Usage:**
```bash
python ci_filter.py \
    --json_dir ./filtered_data \
    --languages python,cpp,go,rust \
    --output_dir ./verified_data
```

### 4. **Annotation-based Filtering** (`annotated_filter.py`)

Quality filtering based on human annotations and difficulty/clarity assessments.

**Filtering Workflow:**
1. **Annotation Collection**: Gather human-annotated quality scores
2. **Instance Matching**: Map annotations to original dataset instances
3. **Quality Thresholds**: Apply minimum quality criteria
4. **Data Merging**: Combine annotations with instance metadata

**File Organization:**
- Supports multiple annotation files per language
- Pattern-based file matching (`{language}_.+.jsonl`)
- Automatic merging of split annotation files

**Usage:**
```python
# Automatically processes all annotation files in directory
python annotated_filter.py
```

### 5. **Post-processing Filter** (`post_filter.py`)

Final quality assurance with rule-based filtering and dataset finalization.

**Filtering Rules:**

#### **Clarity Rules**
```python
def clarity_rule(instance):
    """Filter out instances with clarity score 0 or 1"""
    return instance["clarity"] not in [0, 1]
```

#### **Content Rules**
```python
def image_rule(instance):
    """Filter out instances containing images or snapshots"""
    problem_text = instance["problem_statement"]
    return not any(keyword in problem_text for keyword in [
        "![image](", "snapshot", "![Image]"
    ])
```

**CI Processing:**
- Automatically pairs CI names for proper formatting
- Handles legacy data format conversions
- Maintains consistency across dataset versions

**Complete Workflow:**
```bash
python post_filter.py \
    --jsonl_path ./annotated/python.jsonl \
    --instance_dir ./original_data \
    --output_dir ./final_filtered
```

### 6. **Comprehensive Testing Suite** (`test.py`)

Extensive testing and validation utilities for dataset quality assurance.

**Testing Components:**
- **Instance Validation**: Verify data integrity and completeness
- **CI Workflow Testing**: Validate GitHub Actions compatibility
- **Format Verification**: Ensure consistent data schemas
- **Performance Benchmarking**: Measure processing efficiency

**Quality Metrics:**
- Patch application success rates
- CI execution compatibility
- Data completeness analysis
- Performance profiling

## 🔧 Configuration and Setup

### Environment Requirements
```bash
# Required dependencies
pip install datasets pyserini git-python tqdm

# For CI testing
sudo apt-get install act  # GitHub Actions runner

# For advanced Git operations
git config --global user.name "SwingBench Processor"
git config --global user.email "processor@swingbench.dev"
```

### Directory Structure
```
prepare_workspace/
├── repositories/           # Cloned source repositories
├── indexes/               # Search indexes by repo/commit
├── filtered_data/         # Intermediate filtered datasets
├── annotations/           # Human annotation files
├── final_datasets/        # Production-ready datasets
└── logs/                 # Processing logs and metrics
```

### Environment Variables
```bash
# GitHub authentication
export GITHUB_TOKEN=<your_github_token>

# Processing configuration
export SWING_PREPARE_WORKERS=8
export SWING_INDEX_THREADS=4
export SWING_MEMORY_LIMIT=32G
```

## 📊 Processing Pipeline

### Full Dataset Preparation Workflow

#### **Stage 1: Repository Setup**
```bash
# Clone all repositories from dataset
python swing_clone_repos.py \
    --dataset_path princeton-nlp/SwingBench \
    --repo_root_dir ./repositories
```

#### **Stage 2: Index Construction**
```bash
# Build search indexes for all commits
python swing_build_index.py \
    --dataset_path princeton-nlp/SwingBench \
    --language python \
    --root_dir ./indexes \
    --repo_root_dir ./repositories
```

#### **Stage 3: Quality Filtering**
```bash
# Apply CI-based filtering
python ci_filter.py \
    --json_dir ./raw_instances \
    --languages python,cpp,go,rust

# Process human annotations
python annotated_filter.py

# Apply final post-processing rules
python post_filter.py \
    --jsonl_path ./annotated/python.jsonl \
    --instance_dir ./original_data \
    --output_dir ./final_datasets
```

#### **Stage 4: Validation and Testing**
```bash
# Run comprehensive validation
python test.py --validate_all
```

## 🚨 Error Handling and Recovery

### Common Issues and Solutions

**Repository Cloning Failures:**
- **Authentication**: Ensure GITHUB_TOKEN is set for private repositories
- **Network Issues**: Implement retry logic with exponential backoff
- **Disk Space**: Monitor available storage during large repository clones

**Index Building Problems:**
- **Pyserini Installation**: Verify Java dependencies and CLASSPATH
- **Memory Constraints**: Adjust thread count and batch sizes
- **Corrupted Repositories**: Implement git repair and re-clone logic

**Filtering Pipeline Issues:**
- **Missing Annotations**: Handle incomplete annotation coverage gracefully
- **Schema Mismatches**: Validate data formats before processing
- **CI Environment**: Ensure ACT and Docker are properly configured

### Recovery Strategies
```bash
# Resume interrupted index building
python swing_build_index.py --resume \
    --checkpoint_dir ./checkpoints

# Repair corrupted repositories
python swing_clone_repos.py --repair \
    --verify_integrity

# Validate and fix data consistency
python test.py --repair_mode \
    --fix_schema_errors
```

## 📈 Performance Optimization

### Memory Management
- **Streaming Processing**: Process large datasets without loading everything into memory
- **Batch Operations**: Optimize disk I/O with configurable batch sizes
- **Index Caching**: Reuse existing indexes to reduce computational overhead

### Parallel Processing
- **Multi-threading**: Concurrent index building and repository operations
- **Process Pools**: Distribute filtering operations across CPU cores
- **GPU Acceleration**: Optional CUDA support for large-scale text processing

### Storage Optimization
- **Compression**: Automatic compression of intermediate results
- **Deduplication**: Remove redundant data across dataset versions
- **Incremental Updates**: Only process changed repositories and commits

## 🔍 Monitoring and Metrics

### Progress Tracking
- Real-time progress bars with ETA estimation
- Detailed logging with configurable verbosity levels
- Resource usage monitoring (CPU, memory, disk)

### Quality Metrics
- **Filtering Statistics**: Success rates at each pipeline stage
- **Index Quality**: Search relevance and coverage metrics
- **Data Integrity**: Consistency checks and validation results

### Output Formats
```json
{
    "processing_summary": {
        "total_repositories": 150,
        "successful_clones": 148,
        "failed_clones": 2,
        "total_commits": 892,
        "indexed_commits": 890,
        "total_instances": 5234,
        "filtered_instances": 4567,
        "final_dataset_size": 4321
    }
}
```

## 🤝 Contributing and Extension

### Adding New Filters
```python
def custom_filter_rule(instance):
    """
    Custom filtering logic for specific requirements
    """
    # Implement your filtering criteria
    return meets_criteria(instance)

# Register in post_filter.py
FILTER_RULES = [
    clarity_rule,
    image_rule,
    custom_filter_rule,  # Add your filter here
]
```

### Custom Document Encoding
```python
def custom_encoding_function(filename: Path, relative_path: str) -> str:
    """
    Custom document encoding strategy
    """
    # Implement custom text extraction and formatting
    return formatted_text

# Register in swing_build_index.py
DOCUMENT_ENCODING_FUNCTIONS = {
    "custom_encoding": custom_encoding_function,
}
```

### Extension Guidelines
1. **Maintain Compatibility**: Ensure new features work with existing pipeline stages
2. **Add Tests**: Include comprehensive tests for new functionality
3. **Document Changes**: Update README and inline documentation
4. **Performance Considerations**: Optimize for large-scale dataset processing
5. **Error Handling**: Implement robust error recovery and reporting

## 📚 Research Applications

This preparation framework supports various research scenarios:

- **Benchmark Construction**: Create custom software engineering benchmarks
- **Code Retrieval Studies**: Build and evaluate code search systems
- **Dataset Quality Analysis**: Systematic evaluation of dataset characteristics
- **Multi-language Evaluation**: Comparative studies across programming languages
- **Longitudinal Analysis**: Track repository evolution over time

The modular design allows researchers to customize each stage of the preparation pipeline while maintaining reproducibility and quality standards.
