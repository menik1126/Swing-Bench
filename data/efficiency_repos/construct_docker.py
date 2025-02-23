import pandas as pd
import os
import requests
from github import Github
from urllib.parse import urlparse
from tqdm import tqdm
import logging
import sys
import re

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

# 将所有数据合并成一个 DataFrame
combined_df = pd.concat(all_data, ignore_index=True)
# 遍历每一行数据，处理并更新 DataFrame
for index, row in tqdm(combined_df.iterrows(), total=len(combined_df), desc="Processing Rows", leave=True, file=sys.stdout):
    try:
        url = row['url']
        repo_name = row['repo_name']
        pull_number = urlparse(url).path.split('/')[-1]

        repo = g.get_repo(repo_name)
        pr = get_pull_request(repo, pull_number)