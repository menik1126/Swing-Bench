# import json

# languages = ['python', 'go', 'rust', 'cpp']

# for lang in languages:
#     input_file = f"{lang}.jsonl"
#     output_file = input_file
    
#     print(f"\nhandle {lang} file...")
    
#     filtered_data = []
#     with open(input_file, 'r', encoding='utf-8') as f:
#         for line in f:
#             try:
#                 data = json.loads(line.strip())
#                 if 'clarity' in data:
#                     filtered_data.append(data)
#             except json.JSONDecodeError:
#                 print(f"Warning: Skipping invalid JSON line: {line[:100]}...")

#     with open(output_file, 'w', encoding='utf-8') as f:
#         for data in filtered_data:
#             f.write(json.dumps(data, ensure_ascii=False) + '\n')

#     print(f"{lang} original data number: {len(filtered_data) + sum(1 for line in open(input_file)) - len(filtered_data)}")
#     print(f"{lang} data number: {len(filtered_data)}")

# import pandas as pd

# languages = ['go', 'python', 'cpp', 'rust']
# dfs = []
# for lang in languages:
#     df = pd.read_json(f'{lang}.jsonl', lines=True)
#     df['language'] = lang
#     dfs.append(df)

# all_data = pd.concat(dfs, ignore_index=True)

# duplicates = all_data[all_data['instance_id'].duplicated(keep=False)].sort_values('instance_id')
# print(duplicates[['instance_id', 'language']].to_string())

# for lang in languages:
#     df = pd.read_json(f'{lang}.jsonl', lines=True)
#     lang_duplicates = duplicates[duplicates['language'] == lang]['instance_id'].unique()
#     df = df[~df['instance_id'].isin(lang_duplicates)]
#     df.to_json(f'{lang}.jsonl', orient='records', lines=True)


import json
import tiktoken
import pandas as pd

def normalize_difficulty(group):
    if group.isnull().any():
        print(f"Warning: Found NaN values in difficulty")
        raise ValueError("Found NaN values in difficulty")

    min_val = group.min()
    max_val = group.max()
    if max_val == min_val:
        return group
    normalized = (group - min_val) / (max_val - min_val)
    return normalized

enc = tiktoken.encoding_for_model("gpt-4o")

languages = ['python', 'go', 'rust', 'cpp']

for lang in languages:
    input_file = f"{lang}.jsonl"
    output_file = input_file
    
    processed_data = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                if 'problem_statement' in data:
                    tokens = enc.encode(data['problem_statement'])
                    data['token_count'] = len(tokens)
                data['language'] = lang
                processed_data.append(data)
            except json.JSONDecodeError:
                print(f"Warning: Skipping invalid JSON line: {line[:100]}...")

    df = pd.DataFrame(processed_data)
    if 'difficulty' in df.columns:
        df['normalized_difficulty'] = df.groupby('language')['difficulty'].transform(normalize_difficulty)
        processed_data = df.to_dict('records')

    with open(output_file, 'w', encoding='utf-8') as f:
        for data in processed_data:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')

    if 'difficulty' in df.columns:
        print(f"normalized difficulty range：{df['normalized_difficulty'].min():.2f} - {df['normalized_difficulty'].max():.2f}")


