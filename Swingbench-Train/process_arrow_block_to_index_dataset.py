from datasets import load_from_disk, concatenate_datasets, Dataset
import pandas as pd
import numpy as np
import json
import os
from tqdm import tqdm
import re
from swing_chunker import CodeChunker

# 提取代码功能函数
def extract_added_code_from_patch(patch: str) -> str:
    """
    从diff patch字符串中提取应用补丁后的完整代码块，包含原有代码和新增代码，但不包含被删除的代码行。
    """
    result_lines = []
    for line in patch.splitlines():
        # 跳过diff元信息和文件头
        if line.startswith('+++') or line.startswith('---') or line.startswith('diff --git') or line.startswith('@@'):
            continue
        # 添加不以-开头的内容行（上下文行和新增行）
        if not line.startswith('-'):
            # 如果是新增行，去掉开头的+号
            if line.startswith('+'):
                result_lines.append(line[1:])
            else:
                result_lines.append(line)
    result =    '\n'.join(result_lines)
    # print("result: ", result)
    # assert 1 == 2
    # 合并为一个代码字符串
    return result

# 备选的代码切分方法
def fallback_chunk_code(code, language):
    """
    当TreeSitter失败时的备选代码切分方法，通过简单的规则切分代码
    """
    # 基于空行切分代码
    chunks = []
    current_chunk = []
    
    # 针对不同语言的函数识别模式
    patterns = {
        "python": r"(^|\n)def\s+\w+\s*\(",
        "cpp": r"(^|\n)(\w+\s+)+\w+\s*\([^)]*\)\s*(\{|\n\{)",
        "rust": r"(^|\n)fn\s+\w+\s*\(",
        "go": r"(^|\n)func\s+\w+\s*\("
    }
    
    pattern = patterns.get(language, r"(^|\n)(\w+\s+)+\w+\s*\(")  # 默认模式
    
    # 找到所有可能的函数起始位置
    matches = list(re.finditer(pattern, code, re.MULTILINE))
    
    if not matches:
        # 如果没有找到函数匹配，返回整个代码块
        return [{"code": code, "type": "fallback"}]
    
    # 根据匹配位置分割代码
    chunks = []
    for i in range(len(matches)):
        start = matches[i].start()
        end = matches[i+1].start() if i < len(matches) - 1 else len(code)
        
        # 提取函数块
        func_code = code[start:end].strip()
        if func_code:
            chunks.append({"code": func_code, "type": "function"})
    
    # 如果没有成功切分，返回原始代码
    if not chunks:
        chunks = [{"code": code, "type": "fallback"}]
    
    return chunks

def find_json_files(base_dir):
    """Find all json files in the directory structure that match all_tasks.json pattern"""
    json_files = {}
    
    # Check each language directory
    language_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    
    for lang in language_dirs:
        # Skip hidden directories
        if lang.startswith('.'):
            continue
            
        lang_path = os.path.join(base_dir, lang)
        
        # Look for all_tasks.json directly in language directory
        if os.path.exists(os.path.join(lang_path, "all_tasks.json")):
            json_files[lang] = os.path.join(lang_path, "all_tasks.json")
            continue
            
        # Look for instances directory
        instances_dir = os.path.join(lang_path, f"{lang}_instances")
        if os.path.exists(instances_dir):
            if os.path.exists(os.path.join(instances_dir, "all_tasks.json")):
                json_files[lang] = os.path.join(instances_dir, "all_tasks.json")
                
    return json_files

def process_language_data(input_path, language):
    """Process data for a specific language and create index dataset."""
    # Initialize chunker for the specific language
    # chunker = CodeChunker(language=language, chunk_type="function")
    chunker_block = CodeChunker(language=language, chunk_type="block")
    
    # Load data
    print(f"正在加载JSON数据: {input_path}")
    with open(input_path, "r") as f:
        data = json.load(f)
    
    result_data = []
    
    # 统计成功和失败的处理数量
    total_processed = 0
    successful_chunks = 0
    fallback_chunks = 0

    
    for item in tqdm(data, desc=f"处理 {language} 数据"):
        total_processed += 1
        problem = item.get("problem_statement", "")
        patch = item.get("patch", "")
        
        # Extract added code
        code = extract_added_code_from_patch(patch)
        print("================================================START================================================\n")
        print("code: \n\n", code)
        print("================================================END================================================\n")
        # 尝试使用TreeSitter进行切分

        #chunks = chunker.chunk(code)
        chunks = chunker_block.chunk(code)

        if not chunks:  # 如果TreeSitter没有返回任何块
            # 尝试使用block切分作为备选方法
            
            

                fallback_chunks += 1
              
                # 使用完整代码作为最后的备选方法
                chunks = [{
                    "type": "function",
                    "name": "",
                    "code": code,
                    "start_line": 1,
                    "end_line": len(code.split('\n')),
                    "metadata": {
                        "source": "fallback_method"
                    }
                }]
                print(f"警告: TreeSitter未返回任何切分结果，使用完整代码作为最后的备选方法")

        else:
            successful_chunks += 1
            print(f"信息: 函数切分成功，获取了{len(chunks)}个函数块")
        
        # 添加结果
        for chunk in chunks:
            chunk_code = chunk.get("code", "") if isinstance(chunk, dict) else chunk
            if isinstance(chunk_code, str) and chunk_code.strip():
                result_data.append({
                    "question": problem,
                    "answer": chunk_code
                })
                
                # 打印每个添加的代码块信息
                chunk_type = chunk.get("type", "unknown") if isinstance(chunk, dict) else "raw_string"
                chunk_lines = len(chunk_code.split('\n'))
                print(f"添加代码块 - 类型: {chunk_type}, 行数: {chunk_lines}, 代码示例: {chunk_code[:50]}{'...' if len(chunk_code) > 50 else ''}")
    
    # 打印详细的统计信息
    print("\n" + "="*50)
    print(f"【{language.upper()} 语言处理统计】")
    print(f"总处理条目: {total_processed}")
    print(f"成功切分: {successful_chunks} ({successful_chunks/total_processed*100:.2f}%)")
   
    print("="*50 + "\n")
    
    return result_data

def save_to_json_index_format(dataset, output_path):
    """将数据集保存为索引格式的JSON文件"""
    # 创建输出目录
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 准备JSON数据
    data = []
    for i in range(len(dataset)):
        item = dataset[i]
        data.append({
            "question": item["question"],
            "answer": item["answer"]
        })
    
    # 保存为JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"已保存 {len(data)} 条数据到 {output_path}")
    return len(data)

def process_arrow_datasets(dataset_path, output_base_dir):
    """处理Arrow格式的数据集并转换为索引格式"""
    print("正在加载Arrow数据集...")
    dataset = load_from_disk(dataset_path)
    
    # 查看可用的子数据集
    print(f"\n可用的子数据集: {list(dataset.keys())}")
    
    # 处理每个语言数据集
    languages = ["cpp", "python", "go", "rust"]
    language_datasets = {}
    language_counts = {}
    # 创建语言对应的代码切分器
    
    # 总体统计
    total_all_langs = 0
    success_all_langs = 0
    fallback_all_langs = 0
    complete_fallback_all_langs = 0
    #assert 1 == 0
    for lang in languages:
        if lang not in dataset:
            print(f"警告: {lang}数据集不存在，跳过")
            continue
        
        # if lang != "go":
        #     continue
        
        print(f"\n\n===== {lang.upper()} 数据集 =====")
        lang_dataset = dataset[lang]
        chunker = CodeChunker(language=lang, chunk_type="function")
        chunker_block = CodeChunker(language=lang, chunk_type="block")
        # 将Arrow数据集转换为索引格式（question, answer）
        print(f"转换 {lang} 数据集为索引格式...")
        
        # 检查数据集结构，确定字段映射
        features = list(lang_dataset.features.keys())
        print(f"数据集特征: {features}")
        
        # 找出问题和答案字段
        question_field = None
        
        # 猜测字段映射
        if "problem_statement" in features:
            question_field = "problem_statement"
        elif "prompt" in features:
            question_field = "prompt"
        elif "instruction" in features:
            question_field = "instruction"
        elif "question" in features:
            question_field = "question"
            
 
        answer_field = "patch"
            
        print(f"使用字段映射 - 问题: {question_field}, 答案: {answer_field}")
        
        if not question_field or not answer_field:
            print(f"警告: 无法确定 {lang} 数据集的问题/答案字段，跳过")
            continue
        
        # 处理并切分代码
        result_data = []
        
        # 统计成功和失败的处理数量
        total_processed = 0
        successful_chunks = 0
        fallback_chunks = 0
        complete_fallback_chunks = 0
        
        for item in tqdm(lang_dataset, desc=f"处理 {lang} 数据"):
            total_processed += 1
            question = item[question_field]
            patch = item[answer_field]
            
            # 提取代码
            code = extract_added_code_from_patch(patch)
            
            # 尝试使用TreeSitter进行切分
            
            
            chunks = chunker.chunk(code)
            #print("patch: \n\n", patch)
            if not chunks:  # 如果TreeSitter没有返回任何块
                # 尝试使用block切分作为备选方法
                chunks = chunker_block.chunk(code)
                
                if not chunks:  # 如果block切分也没有返回任何块
                    #fallback_chunks += 1
                    complete_fallback_chunks += 1
                    # 使用完整代码作为最后的备选方法
                    chunks = [{
                        "type": "function",
                        "name": "",
                        "code": code,
                        "start_line": 1,
                        "end_line": len(code.split('\n')),
                        "metadata": {
                            "source": "fallback_method"
                        }
                    }]
                    print(f"警告: TreeSitter block未返回任何切分结果，使用完整代码作为最后的备选方法")
                else:
                    print(f"信息: 函数切分失败，使用block切分成功，获取了{len(chunks)}个代码块")
                    fallback_chunks += 1
                    # 为block切分的结果添加信息
                    for i, chunk in enumerate(chunks):
                        chunk["metadata"] = chunk.get("metadata", {})
                        chunk["metadata"]["source"] = "block_chunking"
                        # 如果没有名称，添加一个基于类型的名称
                        if not chunk.get("name"):
                            chunk["name"] = f"{chunk.get('type', 'block')}_{i+1}"
            else:
                successful_chunks += 1
                print(f"信息: 函数切分成功，获取了{len(chunks)}个函数块")

            
            # 添加结果
            for chunk in chunks:
                chunk_code = chunk.get("code", "") if isinstance(chunk, dict) else chunk
                if isinstance(chunk_code, str) and chunk_code.strip():
                    result_data.append({
                        "question": question,
                        "answer": chunk_code
                    })
        
        # 保存为JSON索引格式
        lang_dir = os.path.join(output_base_dir, lang)
        os.makedirs(lang_dir, exist_ok=True)
        output_path = os.path.join(lang_dir, "index_dataset.json")
        
        print("=========save_path:{}".format(output_path))
        # 直接保存JSON数据
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        count = len(result_data)
        
        # 创建Dataset对象用于后续处理
        if count > 0:
            index_dataset = Dataset.from_dict({
                "question": [item["question"] for item in result_data],
                "answer": [item["answer"] for item in result_data]
            })
            language_datasets[lang] = index_dataset
        else:
            language_datasets[lang] = None
            
        language_counts[lang] = count
        
        # 更新总体统计
        total_all_langs += total_processed
        success_all_langs += successful_chunks
        fallback_all_langs += fallback_chunks
        complete_fallback_all_langs += complete_fallback_chunks
        
        print(f"已将 {count} 条 {lang} 数据转换为索引格式并保存到 {output_path}")
        print("\n" + "="*50)
        print(f"【{lang.upper()} 语言处理统计】")
        print(f"总处理条目: {total_processed}")
        print(f"成功切分: {successful_chunks} ({successful_chunks/total_processed*100:.2f}%)")
        print(f"使用备选block切分: {fallback_chunks-complete_fallback_chunks} ({(fallback_chunks-complete_fallback_chunks)/total_processed*100:.2f}%)")
        print(f"完全失败使用原始代码: {complete_fallback_chunks} ({complete_fallback_chunks/total_processed*100:.2f}%)")
        print("="*50 + "\n")
        
        # 显示示例数据
        if result_data:
            print("\n示例数据 (第一条):")
            example = result_data[0]
            for key, value in example.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"  {key}: {value[:100]}...")
                else:
                    print(f"  {key}: {value}")
    
    # 打印总体统计信息
    print("\n" + "="*60)
    print("【所有语言处理统计信息汇总】")
    print(f"总处理条目: {total_all_langs}")
    print(f"成功切分: {success_all_langs} ({success_all_langs/total_all_langs*100:.2f}% 成功率)")
    print(f"使用block备选切分: {fallback_all_langs-complete_fallback_all_langs} ({(fallback_all_langs-complete_fallback_all_langs)/total_all_langs*100:.2f}%)")
    print(f"完全失败使用原始代码: {complete_fallback_all_langs} ({complete_fallback_all_langs/total_all_langs*100:.2f}%)")
    print("="*60 + "\n")
    
    return language_datasets, language_counts

def process_json_datasets(base_data_dir, output_base_dir):
    """处理JSON格式的原始代码数据集"""
    # 查找所有要处理的JSON文件
    json_files = find_json_files(base_data_dir)
    
    print(f"找到 {len(json_files)} 个语言数据集:")
    for lang, file_path in json_files.items():
        print(f"  - {lang}: {file_path}")
    
    # 处理每种语言
    language_datasets = {}
    language_counts = {}
    
    for lang, input_path in json_files.items():
     
            # 处理数据
            data = process_language_data(input_path, lang)
            
            # 创建Dataset对象
            index_dataset = Dataset.from_dict({
                "question": [item["question"] for item in data],
                "answer": [item["answer"] for item in data]
            })
            
            # 保存为JSON索引格式
            lang_dir = os.path.join(output_base_dir, lang)
            os.makedirs(lang_dir, exist_ok=True)
            output_path = os.path.join(lang_dir, "index_dataset.json")
            
            # 直接保存JSON数据
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            count = len(data)
            language_datasets[lang] = index_dataset
            language_counts[lang] = count
            
            print(f"{lang.upper()}: 成功处理 - 生成并保存了 {count} 个Q&A对到 {output_path}")


    
    return language_datasets, language_counts

def main():
    # 数据集路径
    arrow_dataset_path = "/home/xiongjing/Swing-Bench/Swingbench-Train/SwingBench_Data_"
    output_base_dir = "/home/xiongjing/Swing-Bench/Swingbench-Train/index_data"
    
    print("正在处理Arrow格式数据并转换为可训练的索引格式...")
    language_datasets, language_counts = process_arrow_datasets(arrow_dataset_path, output_base_dir)
    
    print("\n所有语言处理完成。结果如下：")
    for lang, count in language_counts.items():
        print(f"{lang}: {count} 条数据")
    
    print(f"\n已将所有数据保存到 {output_base_dir} 目录")

if __name__ == "__main__":
    main()




