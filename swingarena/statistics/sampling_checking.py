import json
import os
from pathlib import Path
from utils import annotated_jsonl_dir


def load_jsonl_to_dict(jsonl_path):
    results = {}

    if os.path.exists(jsonl_path):
        with open(jsonl_path, "r") as f:
            for line_num, line in enumerate(f):
                try:
                    data = json.loads(line.strip())
                    instance_id = data.get("instance_id")
                    if instance_id:
                        results[instance_id] = data
                    else:
                        print(f"警告：第 {line_num+1} 行缺少 instance_id")
                except json.JSONDecodeError:
                    print(f"警告：第 {line_num+1} 行解析 JSON 失败")

        print(f"共加载了 {len(results)} 条记录")
    else:
        print(f"文件不存在：{jsonl_path}")

    return results


# 加载数据
jsonl_path = annotated_jsonl_dir / "rust.jsonl"
data_dict = load_jsonl_to_dict(jsonl_path)

# 打印前5个记录的统计信息
print("\n前5个记录的ID:")
for idx, instance_id in enumerate(list(data_dict.keys())[:5]):
    print(f"{idx+1}. {instance_id}")
    item = data_dict[instance_id]
    print(f"   - 清晰度: {item.get('clarity')}")
    print(f"   - 清晰度解释: {item.get('clarity_explanation')}")
    print(f"   - 难度: {item.get('difficulty')}")
    print(f"   - 难度解释: {item.get('difficulty_explanation')}")

# 检查是否有字段缺失
missing_fields = {
    field: 0
    for field in [
        "instance_id",
        "clarity",
        "difficulty",
        "clarity_explanation",
        "difficulty_explanation",
    ]
}
for instance_id, data in data_dict.items():
    for field in missing_fields:
        if field not in data or data[field] is None:
            missing_fields[field] += 1

print("\n字段缺失统计:")
for field, count in missing_fields.items():
    if count > 0:
        print(f"- {field}: 缺失 {count} 条记录")
