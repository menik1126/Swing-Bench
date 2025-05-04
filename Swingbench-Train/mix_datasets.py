#!/usr/bin/env python3
import json
import os
import random
from pathlib import Path
from transformers import AutoTokenizer
from tqdm import tqdm
# Parameters
BASE_DIR = "/home/xiongjing/Swing-Bench/Swingbench-Train/index_data"
LANGUAGES = ["cpp", "go", "python", "rust"]
MAX_SAMPLES_PER_LANGUAGE = 100  # Set your desired maximum here
MAX_LENGTH = 4000  # Maximum token length threshold
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"
OUTPUT_FILE = "/home/xiongjing/Swing-Bench/Swingbench-Train/index_data/combined/index_dataset.json"

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def load_dataset(lang):
    """Load dataset for a specific language."""
    file_path = os.path.join(BASE_DIR, lang, "index_dataset.json")
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_length(item):
    """Get the token length of an item using Llama tokenizer."""
    # The dataset has "question" and "answer" fields
    if isinstance(item, dict):
        question = item.get("question", "")
        answer = item.get("answer", "")
        # Combine both fields for token counting
        content = question + " " + answer
    else:
        content = str(item)
    
    # Count tokens using the tokenizer
    tokens = tokenizer.encode(content)
    return len(tokens)

def main():
    mixed_dataset = []
    
    print(f"Using tokenizer from {MODEL_NAME}")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    # Load and sample from each language
    for lang in LANGUAGES:
        print(f"Processing {lang}...")
        dataset = load_dataset(lang)
        print(f"  - Found {len(dataset)} samples")
        
        # Filter by token length
        filtered_dataset = []
        filtered_count = 0
        
        for item in tqdm(dataset):
            token_length = get_length(item)
            if token_length <= MAX_LENGTH:
                filtered_dataset.append(item)
            else:
                filtered_count += 1
        
        print(f"  - {filtered_count} items filtered out (> {MAX_LENGTH} tokens)")
        print(f"  - {len(filtered_dataset)} items remain after token length filtering")
        
        # Sample up to the maximum (or use all if less than maximum)
        sampled = filtered_dataset
        if len(filtered_dataset) > MAX_SAMPLES_PER_LANGUAGE:
            sampled = random.sample(filtered_dataset, MAX_SAMPLES_PER_LANGUAGE)
        
        print(f"  - Using {len(sampled)} samples")
        mixed_dataset.extend(sampled)
    
    # Shuffle the combined dataset
    random.shuffle(mixed_dataset)
    
    # Save the mixed dataset
    print(f"Saving mixed dataset with {len(mixed_dataset)} total samples to {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(mixed_dataset, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main() 