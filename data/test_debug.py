import json

# 定义文件路径
file_path = 'code_debug.jsonl'

all_data = []
with open(file_path, 'r', encoding='utf-8') as file:
    for line_number, line in enumerate(file, start=1):

            # 将每一行解析为 JSON 对象
            data = json.loads(line)
            all_data.append(data)

print("len of all_data[0]:{}".format(len(all_data[0])))

# print("all_data[0]:{}".format(all_data[0]))
# print("all_data[0].keys():{}".format(all_data[0].keys()))   # ['id', 'context', 'input', 'answer', 'options']
print("all_data[0][options]:{}".format(all_data[0]["options"]))
print("all_data[0][input]:{}".format(all_data[0]["input"]))