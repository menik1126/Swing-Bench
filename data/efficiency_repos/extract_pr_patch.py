import pandas as pd
import os
import requests
from github import Github
from urllib.parse import urlparse
from tqdm import tqdm
import logging
import sys
import re
import base64

token = "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"  # 替换为你的 GitHub 访问令牌
g = Github(token)

# 定义存储所有数据的列表
all_data = []

# 遍历文件夹下的所有 CSV 文件
folder_path = 'source_data'
for file_name in os.listdir(folder_path):
    if file_name.endswith('.csv'):
        file_path = os.path.join(folder_path, file_name)
        
        # 读取 CSV 文件并追加到列表中
        df = pd.read_csv(file_path)
        all_data.append(df)

def extract_patch(pr):
        """
        从 GitHub PR 中提取每个文件的 patch 数据。

        参数:
            pr: github.PullRequest.PullRequest 对象
        
        返回:
            一个字典，包含文件名及其对应的 patch 数据
        """
        patches = {}
    #try:
        # 获取 PR 的文件变更列表
        files = pr.get_files()
        #print("len(files):{}".format(len(list(files))))
        for file in files:
            file_name = file.filename
            patch = file.patch  # 获取该文件的 patch 数据

            if patch:
                patches[file_name] = patch
            else:
                patches[file_name] = "No patch data available (possibly binary file)"

        return patches
    # except Exception as e:
    #     print(f"提取 PR patch 数据失败：{e}")
    #     return None





env_files = ["Dockerfile", "requirements.txt", "package.json"]




def analyze_and_reconstruct_patch(patches):
    """
    分析 patch 数据，同时生成修改后的代码。

    参数:
        patches: 一个字典，键是文件名，值是对应的 patch 数据（从 extract_patch 提取）

    返回:
        一个包含以下内容的字典：
        - 每个文件的原始行、新增行、删除行分类
        - 每个文件的修改后代码
        - 总的新增行数和删除行数统计
    """
    result = {}
    total_added = 0
    total_removed = 0
    

    for file_name, patch in patches.items():
        if patch == "No patch data available (possibly binary file)":
            # 处理二进制文件
            print("patch:{}".format(patch))
            result[file_name] = {
                "original_lines": [],
                "added_lines": [],
                "removed_lines": [],
                "modified_code": "Binary file, no code available",
                "added_count": 0,
                "removed_count": 0,
            }
            continue

        original_lines = []
        added_lines = []
        removed_lines = []
        modified_code = []
        
        #print("patch:{}".format(patch))
        # 按行解析 patch 数据
        lines = patch.split("\n")
        for line in lines:
            if line.startswith("-") and not line.startswith("---"):
                # 删除的行
                removed_lines.append(line[1:].strip())
                total_removed += 1
            elif line == "\ No newline at end of file":
                continue
            elif line.startswith("+") and not line.startswith("+++"):
                # 新增的行
                added_lines.append(line[1:].strip())
                modified_code.append(line[1:].strip())  # 添加到修改后代码
                total_added += 1
            elif not line.startswith("@") and not line.startswith("---") and not line.startswith("+++"):
                # 上下文行（原始行）
                original_lines.append(line.strip())
                modified_code.append(line.strip())  # 添加到修改后代码
        original_code  =  "\n".join(original_lines)
        modified_code = "\n".join(modified_code)
        if file_name in env_files:
            print(f"检测到环境配置文件 {file_name} 被修改")
            print(f"原始行: \n{original_code}")
            print(f"修改行: \n{modified_code}")
            #assert 1==0

            #assert 1==0
        # 保存每个文件的结果
        result[file_name] = {
            "original_lines": original_code,
            "added_lines": added_lines,
            "removed_lines": removed_lines,
            "modified_code": modified_code,
            "added_count": len(added_lines),
            "removed_count": len(removed_lines),
        }

    # 添加总的统计信息
    result["summary"] = {
        "total_added": total_added,
        "total_removed": total_removed,
    }
    #print("len(patches.items()):{}".format(len(patches.items())))
    return result


# 定义获取 Pull Request 和处理的函数
def get_pull_request(repo, pull_number):
    try:
        return repo.get_pull(int(pull_number))
    except Exception as e:
        logging.error(f"获取 PR {pull_number} 失败：{e}")
        return None




def extract_pr_changes(repo, pull_number):
    """
    提取 PR 的文件变更内容，包括变更前的内容和变更后的内容。

    参数:
        repo_name: 仓库名 (如 "owner/repo")
        pr_number: PR 编号

    返回:
        一个字典，包含每个文件的原始内容（before）和当前内容（after）
    """
    pr = repo.get_pull(int(pull_number))
    changes = {}

    for file in pr.get_files():
        file_name = file.filename
        if file_name in ["Dockerfile", "requirements.txt", "package.json"]:
            changes[file_name] = {
                "before": file.raw_url,  # 获取变更前的版本
                "after": file.contents_url,  # 获取变更后的版本
            }
            before_content = fetch_file_content(file.raw_url)
            after_content = fetch_and_decode_content(file.contents_url) #fetch_file_content(file.contents_url)
            print(f"{file_name} - 变更前内容:\n{before_content}")
            print(f"{file_name} - 变更后内容:\n{after_content}")

    return changes




def fetch_file_content(url):
    """
    获取文件内容。

    参数:
        url: 文件的原始或变更后的 URL

    返回:
        文件内容的字符串
    """
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"无法获取文件内容: {url}")

def fetch_and_decode_content(content_url):
    """
    从 GitHub API 提取文件内容并解码。
    
    参数:
        content_url: 文件内容的 API URL。
        
    返回:
        解码后的文件内容。
    """
    response = requests.get(content_url)
    if response.status_code == 200:
        # 获取 JSON 响应数据
        data = response.json()
        if 'content' in data and 'encoding' in data:
            if data['encoding'] == 'base64':
                # 解码 base64 内容
                decoded_content = base64.b64decode(data['content']).decode('utf-8')
                return decoded_content
        raise ValueError("内容未编码为 base64 或不包含 content 字段")
    else:
        raise Exception(f"请求失败，状态码: {response.status_code}, URL: {content_url}")




def process_pull_request(pr):   # 单个pr里面的所有的patch
    patches = extract_patch(pr)
       
    if patches:
        return analyze_and_reconstruct_patch(patches)
    else:
        logging.warning(f"PR {pr.number} 的 patch 数据为空")
        return None

# 遍历仓库文件
def find_config_files(repo):
    config_files = []  # 用于存储找到的配置文件
    contents = repo.get_contents("")  # 获取仓库根目录的内容

    while contents:
        file_content = contents.pop(0)
        if file_content.type == "dir":  # 如果是目录，继续递归
            print("file_content:{}".format(file_content))
            contents.extend(repo.get_contents(file_content.path))
        elif file_content.type == "file":  # 如果是文件，检查文件名
            print("file_content:{}".format(file_content))
            if (file_content.name in env_files)  or (file_content.name.endswith((".yaml", ".yml"))):
#                assert 1==0
                config_files.append(file_content)

    return config_files

# 将所有数据合并成一个 DataFrame
combined_df = pd.concat(all_data, ignore_index=True)


# 遍历每一行数据，处理并更新 DataFrame
for index, row in tqdm(combined_df.iterrows(), total=len(combined_df), desc="Processing Rows", leave=True, file=sys.stdout):
#    try:
        url = row['url']
        repo_name = row['repo_name']
        pull_number = urlparse(url).path.split('/')[-1]
        print("repo_name:{}".format(repo_name))
        repo = g.get_repo(repo_name)
        pr = get_pull_request(repo, pull_number)
        config_files = find_config_files(repo)
        print(f"config_files: {config_files}")
        assert 1==0
        if pr:
            results = process_pull_request(pr)
            if results:
                # 提取需要的结果并更新 DataFrame
                summary = results.get("summary", {})
                combined_df.at[index, 'added_count'] = summary.get('total_added', 0)
                combined_df.at[index, 'removed_count'] = summary.get('total_removed', 0)
                
                # 将修改后的代码保存到列中（可选）
                modified_code = "\n".join([
                    f"{file}: {data['modified_code']}" 
                    for file, data in results.items() 
                    if file != 'summary'
                ])
                combined_df.at[index, 'modified_code'] = modified_code


    # except Exception as e:
    #     logging.error(f"处理 URL {row['url']} 时出错：{e}")

# print(f"combined_df.head(5): {combined_df.head(5)}")
# for index, row in combined_df.iterrows():
#     url = row['url']
#     repo_name = row['repo_name']
#     path = urlparse(url).path  # 获取 URL 的路径部分
#     pull_number = path.split('/')[-1]  # 分割路径并取最后一部分


#     print("repo_name:{}".format(repo_name))
#     repo = g.get_repo(repo_name)
#     pulls = repo.get_pulls(state='open')
#     all_number = []
#     all_patch = []
#     for pr in pulls:
#         if pr.number == int(pull_number):
           
#            patch = extract_patch(pr)
#            print("code:{}".format(code))
#            print("patch:{}".format(patch))    
#            all_patch.append(patch)
#            assert 1==0
    
#     # results = analyze_patch(all_patch)
#     # origin_code = reconstruct_modified_code(all_patch)
#     results = analyze_and_reconstruct_patch(all_patch)






# 打印合并后的数据
print(combined_df.head(5))

# 保存合并后的数据到新的 CSV 文件
combined_df.to_csv('combined_data.csv', index=False)
