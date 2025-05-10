import os
import json
from collections import defaultdict

def merge_jsonl_files():
    # 获取所有语言类型
    languages = set()
    for file in os.listdir('.'):
        if file.endswith('.jsonl'):
            lang = file.split('_')[0]
            languages.add(lang)
    
    # 统计每种语言的数据量
    stats = defaultdict(int)
    
    # 处理每种语言
    for lang in languages:
        # 获取所有同种语言的 jsonl 文件
        files = [f for f in os.listdir('.') if f.endswith('.jsonl') and f.startswith(f'{lang}_')]
        
        # 合并数据
        merged_data = []
        for file in files:
            with open(file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():  # 跳过空行
                        data = json.loads(line)
                        merged_data.append(data)
                        stats[lang] += 1
        
        # 保存合并后的文件
        output_file = f'{lang}.jsonl'
        with open(output_file, 'w', encoding='utf-8') as f:
            for data in merged_data:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        
        print(f'已合并 {lang} 文件，共 {stats[lang]} 条数据')
    
    # 打印统计信息
    print('\n数据统计:')
    for lang, count in stats.items():
        print(f'{lang}: {count} 条数据')

if __name__ == '__main__':
    merge_jsonl_files()