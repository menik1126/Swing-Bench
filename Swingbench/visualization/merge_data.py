import os
import json
from collections import defaultdict

def merge_jsonl_files():
    languages = set()
    for file in os.listdir('.'):
        if file.endswith('.jsonl'):
            lang = file.split('_')[0]
            languages.add(lang)
    
    stats = defaultdict(int)
    
    for lang in languages:
        files = [f for f in os.listdir('.') if f.endswith('.jsonl') and f.startswith(f'{lang}_')]
        
        merged_data = []
        for file in files:
            with open(file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        merged_data.append(data)
                        stats[lang] += 1
        
        output_file = f'{lang}.jsonl'
        with open(output_file, 'w', encoding='utf-8') as f:
            for data in merged_data:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        
    for lang, count in stats.items():
        print(f'{lang}: {count} data')

if __name__ == '__main__':
    merge_jsonl_files()