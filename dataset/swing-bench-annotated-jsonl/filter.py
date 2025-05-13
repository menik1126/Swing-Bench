# import json

# # 处理所有语言文件
# languages = ['python', 'go', 'rust', 'cpp']

# for lang in languages:
#     input_file = f"{lang}.jsonl"
#     output_file = input_file  # 就地写入
    
#     print(f"\n处理 {lang} 文件...")
    
#     # 读取并过滤数据
#     filtered_data = []
#     with open(input_file, 'r', encoding='utf-8') as f:
#         for line in f:
#             try:
#                 data = json.loads(line.strip())
#                 # 检查 clarity 字段是否存在
#                 if 'clarity' in data:  # 只保留有 clarity 字段的数据
#                     filtered_data.append(data)
#             except json.JSONDecodeError:
#                 print(f"Warning: Skipping invalid JSON line: {line[:100]}...")

#     # 写回文件
#     with open(output_file, 'w', encoding='utf-8') as f:
#         for data in filtered_data:
#             f.write(json.dumps(data, ensure_ascii=False) + '\n')

#     print(f"{lang} 处理完成！原始数据条数：{len(filtered_data) + sum(1 for line in open(input_file)) - len(filtered_data)}")
#     print(f"{lang} 过滤后数据条数：{len(filtered_data)}")

# import pandas as pd

# # 读取所有语言的数据
# languages = ['go', 'python', 'cpp', 'rust']
# dfs = []
# for lang in languages:
#     df = pd.read_json(f'{lang}.jsonl', lines=True)
#     df['language'] = lang  # 添加语言列
#     dfs.append(df)

# all_data = pd.concat(dfs, ignore_index=True)

# # 找出重复的 instance_ids
# duplicates = all_data[all_data['instance_id'].duplicated(keep=False)].sort_values('instance_id')
# print("重复的 instance_ids:")
# print(duplicates[['instance_id', 'language']].to_string())

# # 对每个语言文件进行处理
# for lang in languages:
#     # 读取原始数据
#     df = pd.read_json(f'{lang}.jsonl', lines=True)
    
#     # 获取该语言中重复的 instance_ids
#     lang_duplicates = duplicates[duplicates['language'] == lang]['instance_id'].unique()
    
#     # 移除重复项
#     df = df[~df['instance_id'].isin(lang_duplicates)]
    
#     # 写回文件
#     df.to_json(f'{lang}.jsonl', orient='records', lines=True)
#     print(f"\n已从 {lang}.jsonl 中移除 {len(lang_duplicates)} 个重复项")


import json
import tiktoken
import pandas as pd

def normalize_difficulty(group):
    # 检查 difficulty 是否为空
    if group.isnull().any():
        print(f"Warning: Found NaN values in difficulty")
        raise ValueError("Found NaN values in difficulty")

    min_val = group.min()
    max_val = group.max()
    if max_val == min_val:  # 处理所有值都相同的情况
        return group
    normalized = (group - min_val) / (max_val - min_val)
    return normalized

# 初始化 tokenizer
enc = tiktoken.encoding_for_model("gpt-4o")

# 处理所有语言文件
languages = ['python', 'go', 'rust', 'cpp']

for lang in languages:
    input_file = f"{lang}.jsonl"
    output_file = input_file  # 就地写入
    
    print(f"\n处理 {lang} 文件...")
    
    # 读取并处理数据
    processed_data = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                # 计算 problem_statement 的 token 数量
                if 'problem_statement' in data:
                    tokens = enc.encode(data['problem_statement'])
                    data['token_count'] = len(tokens)
                data['language'] = lang  # 添加语言字段
                processed_data.append(data)
            except json.JSONDecodeError:
                print(f"Warning: Skipping invalid JSON line: {line[:100]}...")

    # 转换为 DataFrame 进行难度归一化
    df = pd.DataFrame(processed_data)
    if 'difficulty' in df.columns:
        # 按语言分组进行归一化
        df['normalized_difficulty'] = df.groupby('language')['difficulty'].transform(normalize_difficulty)
        processed_data = df.to_dict('records')

    # 写回文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for data in processed_data:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')

    print(f"{lang} 处理完成！总数据条数：{len(processed_data)}")
    if 'difficulty' in df.columns:
        print(f"难度归一化范围：{df['normalized_difficulty'].min():.2f} - {df['normalized_difficulty'].max():.2f}")


