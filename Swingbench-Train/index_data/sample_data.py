import json
import os
import random
from collections import defaultdict

def load_json_file(file_path):
    """Load a JSON file and return its contents"""
    if not os.path.exists(file_path):
        print(f"Warning: File not found: {file_path}")
        return []
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return []

def main():
    # Base directory containing language-specific folders
    base_dir = "/home/xiongjing/Swing-Bench/Swingbench-Train/index_data"
    
    # Languages to combine
    languages = ["go", "python", "rust", "cpp"]
    
    # To store data from each language
    language_data = defaultdict(list)
    
    # Load data from each language
    for lang in languages:
        file_path = os.path.join(base_dir, lang, "index_dataset.json")
        data = load_json_file(file_path)
        # print("lang: ", lang)
        # print("file_path: ", file_path)
        # print("data[0]: ", data[0])
        if data:
            print(f"Loaded {len(data)} records from {lang}")
            language_data[lang] = data
        else:
            print(f"No data found for {lang}")
    
    # Find language with minimum number of samples
    languages_with_data = [lang for lang in languages if language_data[lang]]
    print("len of language_data[python]: ", len(language_data["python"]))
    if not languages_with_data:
        print("No data found for any language")
        return
        
    min_lang = min(languages_with_data, key=lambda x: len(language_data[x]))
    print("min_lang: ", min_lang)
    #assert 1==0
    min_count = len(language_data[min_lang])
    print("min_count: ", min_count)
    print(f"\nLanguage with fewest records: {min_lang} with {min_count} records")
    
    # Sample equal number of records from each language
    balanced_data = []
    lang_counts = {}
    
    for lang, data in language_data.items():
        if not data:
            continue
            
        # Sample min_count records from this language
        lang_samples = random.sample(data, min(min_count, len(data)))
        balanced_data.extend(lang_samples)
        lang_counts[lang] = len(lang_samples)
    
    print(f"\nBalanced dataset created with {len(balanced_data)} total records")
    print("\nSamples per language:")
    for lang, count in lang_counts.items():
        print(f"{lang}: {count} records")
    
    # Save balanced dataset
    output_dir = "/home/xiongjing/Swing-Bench/Swingbench-Train/index_data/combined"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "index_dataset.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(balanced_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved balanced dataset to {output_path}")

if __name__ == "__main__":
    main() 