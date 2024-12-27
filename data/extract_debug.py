import json

# 定义文件路径
file_path = 'code_debug.jsonl'
new_file_path = 'code_debug_top10.jsonl'

all_data = []
with open(file_path, 'r', encoding='utf-8') as file:
    for line_number, line in enumerate(file, start=1):
        # 将每一行解析为 JSON 对象
        data = json.loads(line)
        all_data.append(data)
        # 只保留前10条数据
        if len(all_data) >= 10:
            break

# 将前10条数据写入新的 JSONL 文件
with open(new_file_path, 'w', encoding='utf-8') as new_file:
    for item in all_data:
        new_file.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"前10条数据已保存到 {new_file_path}")
