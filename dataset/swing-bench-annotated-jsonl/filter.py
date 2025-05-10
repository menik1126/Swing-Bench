import json

# 处理所有语言文件
languages = ['python', 'go', 'rust', 'cpp']

for lang in languages:
    input_file = f"{lang}.jsonl"
    output_file = input_file  # 就地写入
    
    print(f"\n处理 {lang} 文件...")
    
    # 读取并过滤数据
    filtered_data = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                # 检查 clarity 字段是否存在
                if 'clarity' in data:  # 只保留有 clarity 字段的数据
                    filtered_data.append(data)
            except json.JSONDecodeError:
                print(f"Warning: Skipping invalid JSON line: {line[:100]}...")

    # 写回文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for data in filtered_data:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')

    print(f"{lang} 处理完成！原始数据条数：{len(filtered_data) + sum(1 for line in open(input_file)) - len(filtered_data)}")
    print(f"{lang} 过滤后数据条数：{len(filtered_data)}")