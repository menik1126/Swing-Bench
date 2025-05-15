import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import tiktoken
from scipy.interpolate import interp1d

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'Microsoft YaHei']  # 优先使用这些字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


def count_diff_lines(patch):
    added = 0
    deleted = 0
    for line in patch.split('\n'):
        if line.startswith('+') and not line.startswith('+++'):
            added += 1
        elif line.startswith('-') and not line.startswith('---'):
            deleted += 1
    return added, deleted

# 设置绘图风格 - 修复样式设置
plt.style.use('seaborn-v0_8')  # 使用正确的样式名称
sns.set_theme()  # 使用seaborn的默认主题

# 读取数据
languages = ['go', 'python', 'cpp', 'rust']
dfs = []
for lang in languages:
    df = pd.read_json(f'{lang}.jsonl', lines=True)
    df['language'] = lang
    dfs.append(df)

all_data = pd.concat(dfs, ignore_index=True)
print("Available columns in the dataset:")
print(all_data.columns.tolist())

print("\nDifficulty column statistics:")
print(all_data['difficulty'].describe())
print("\nDifficulty value counts:")
print(all_data['difficulty'].value_counts())

# 按语言分组的难度统计
print("\nDifficulty statistics by language:")
print(all_data.groupby('language')['difficulty'].describe())





all_data['statement_length'] = all_data['problem_statement'].apply(lambda x: len(x.split()))
all_data[['added_lines', 'deleted_lines']] = all_data['patch'].apply(lambda x: pd.Series(count_diff_lines(x)))
all_data['total_lines_changed'] = all_data['added_lines'] + all_data['deleted_lines']
all_data['repository'] = all_data['instance_id'].apply(lambda x: '/'.join(x.split('/')[:2]))

assert all_data['clarity'].isin([2, 3]).all(), "Clarity scores should be 2 or 3"
assert ((0 <= all_data['difficulty']) & (all_data['difficulty'] <= 1)).all(), "Difficulty should be between 0 and 1"
assert all_data['instance_id'].duplicated().sum() == 0, "There are duplicate instance_ids"

# 1. 语言分布统计和可视化
print("Total problems per language:")
lang_counts = all_data['language'].value_counts()
print(lang_counts)

plt.figure(figsize=(10, 6))
plt.pie(lang_counts, labels=lang_counts.index, autopct='%1.1f%%', 
        colors=sns.color_palette("husl", len(lang_counts)))
plt.title('Language Distribution')
plt.savefig('language_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

# 2. 清晰度分布统计和可视化
print("\nClarity distribution per language:")
clarity_dist = all_data.groupby('language')['clarity'].value_counts(normalize=True).unstack()
print(clarity_dist)

plt.figure(figsize=(12, 6))
clarity_dist.plot(kind='bar', stacked=True)
plt.title('Clarity Distribution by Language')
plt.xlabel('Programming Language')
plt.ylabel('Proportion')
plt.legend(title='Clarity')
plt.tight_layout()
plt.savefig('clarity_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

# 3. 难度统计和可视化
print("\nNormalized difficulty statistics per language:")
difficulty_stats = all_data.groupby('language')['normalized_difficulty'].describe()
print(difficulty_stats)

plt.figure(figsize=(12, 6))
sns.boxplot(x='language', y='normalized_difficulty', data=all_data)
plt.title('Normalized Difficulty Distribution by Language')
plt.xlabel('Programming Language')
plt.ylabel('Normalized Difficulty Score')
plt.tight_layout()
plt.savefig('normalized_difficulty_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

# 4. 问题描述长度统计和可视化 - 优化显示范围
plt.figure(figsize=(12, 6))
sns.boxplot(x='language', y='statement_length', data=all_data)
plt.title('Problem Statement Length Distribution')
plt.xlabel('Programming Language')
plt.ylabel('Word Count')
plt.ylim(0, 3000)  # 限制y轴范围到2000
plt.tight_layout()
plt.savefig('statement_length_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

# 5. 代码变更量统计和可视化
print("\nPatch size statistics per language:")
patch_stats = all_data.groupby('language')[['added_lines', 'deleted_lines', 'total_lines_changed']].mean()
print(patch_stats)

# 5.1 散点图
plt.figure(figsize=(12, 6))

# 对每种语言随机采样100个数据点
sampled_data = pd.DataFrame()
for lang in languages:
    lang_data = all_data[all_data['language'] == lang]
    if len(lang_data) > 100:
        sampled_data = pd.concat([sampled_data, lang_data.sample(n=100, random_state=42)])
    else:
        sampled_data = pd.concat([sampled_data, lang_data])

# 添加一些随机噪声来分散数据点
sampled_data['added_lines_jittered'] = sampled_data['added_lines'] + np.random.normal(0, 2, len(sampled_data))
sampled_data['deleted_lines_jittered'] = sampled_data['deleted_lines'] + np.random.normal(0, 1, len(sampled_data))

sns.scatterplot(data=sampled_data, x='added_lines_jittered', y='deleted_lines_jittered', 
                hue='language', alpha=0.4,  # 降低透明度
                s=50)  # 设置点的大小
plt.title('Code Changes Distribution (100 samples per language)')
plt.xlabel('Added Lines')
plt.ylabel('Deleted Lines')
plt.xlim(0, 500)
plt.ylim(0, 200)
plt.tight_layout()
plt.savefig('code_changes_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

# 5.2 新增：代码变更行数分布箱线图
plt.figure(figsize=(12, 6))
sns.boxplot(x='language', y='total_lines_changed', data=all_data)
plt.title('Total Lines Changed Distribution')
plt.xlabel('Programming Language')
plt.ylabel('Total Lines Changed')
plt.ylim(0, 500)  # 限制y轴范围到500
plt.tight_layout()
plt.savefig('total_lines_changed_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

# 5.3 新增：分别展示新增和删除行数的分布
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# 新增行数分布
sns.boxplot(x='language', y='added_lines', data=all_data, ax=ax1)
ax1.set_title('Added Lines Distribution')
ax1.set_xlabel('Programming Language')
ax1.set_ylabel('Added Lines')
ax1.set_ylim(0, 500)  # 限制y轴范围

# 删除行数分布
sns.boxplot(x='language', y='deleted_lines', data=all_data, ax=ax2)
ax2.set_title('Deleted Lines Distribution')
ax2.set_xlabel('Programming Language')
ax2.set_ylabel('Deleted Lines')
ax2.set_ylim(0, 200)  # 限制y轴范围

plt.tight_layout()
plt.savefig('lines_changed_breakdown.png', dpi=300, bbox_inches='tight')
plt.close()

# 提取仓库信息
all_data['repo'] = all_data['instance_id'].apply(lambda x: x.split('__')[1].split('-')[0])

# 统计每种语言的仓库分布
print("\nRepository distribution by language:")
repo_stats = all_data.groupby(['language', 'repo']).size().reset_index(name='count')
repo_stats = repo_stats.sort_values(['language', 'count'], ascending=[True, False])

# 打印每种语言的仓库统计
for lang in languages:
    print(f"\n{lang.upper()} repositories (top 20):")
    lang_repos = repo_stats[repo_stats['language'] == lang].head(20)
    print(lang_repos.to_string(index=False))

# 可视化仓库分布
plt.figure(figsize=(15, 8))
for i, lang in enumerate(languages):
    lang_repos = repo_stats[repo_stats['language'] == lang].head(20)
    plt.subplot(2, 2, i+1)
    plt.bar(lang_repos['repo'], lang_repos['count'])
    plt.title(f'{lang.upper()} Repositories (Top 20)')
    plt.xticks(rotation=45, ha='right')
    plt.ylabel('Number of Samples')
    plt.tight_layout()

plt.savefig('repo_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

# 统计每个语言 problem statement 的 token 数量分布
print("\nToken count statistics by language:")
token_stats = all_data.groupby('language')['token_count'].describe()
print(token_stats)

# 创建 token 数量分布的可视化
plt.figure(figsize=(12, 6))
sns.boxplot(x='language', y='token_count', data=all_data)
plt.title('Problem Statement Token Count Distribution')
plt.xlabel('Programming Language')
plt.ylabel('Token Count')
plt.ylim(0, 3000)  # 限制y轴范围到2000
plt.tight_layout()
plt.savefig('token_count_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

# 创建 token 数量的累计密度图
plt.figure(figsize=(12, 6))
for lang in languages:
    # 计算每个语言的数据
    lang_data = all_data[all_data['language'] == lang]['token_count']
    # 计算累计概率，处理重复值
    x = np.sort(lang_data)
    y = np.arange(1, len(x) + 1) / len(x)
    # 移除重复的x值，保留最后一个对应的y值
    unique_mask = np.r_[True, x[1:] != x[:-1]]
    x_unique = x[unique_mask]
    y_unique = y[unique_mask]
    # 使用插值使曲线更平滑
    f = interp1d(x_unique, y_unique, kind='cubic')
    x_smooth = np.linspace(x_unique.min(), x_unique.max(), 1000)
    y_smooth = f(x_smooth)
    
    plt.plot(x_smooth, y_smooth, label=lang, linewidth=2)

plt.title('Token Count Cumulative Distribution by Language')
plt.xlabel('Token Count')
plt.ylabel('Cumulative Probability')
plt.xlim(0, 3000)  # 限制x轴范围到2000
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig('token_count_cdf.png', dpi=300, bbox_inches='tight')
plt.close()

# 创建 token 数量的柱状图（四个子图）
plt.figure(figsize=(15, 10))
# 设置 bin 的数量和边界
bins = 50  # 0-3000 范围内的 bin 数量
bin_edges = np.linspace(0, 3000, bins+1)  # 创建 0-3000 的均匀分布的边界
bin_edges[-1] = 1e6  # 将最后一个边界设置为一个足够大的数，而不是无穷大

# 创建 2x2 的子图布局
for i, lang in enumerate(languages):
    plt.subplot(2, 2, i+1)
    lang_data = all_data[all_data['language'] == lang]['token_count']
    # 使用自定义的 bin 边界
    plt.hist(lang_data, bins=bin_edges, alpha=0.7, 
             color=sns.color_palette("husl", len(languages))[i])
    plt.title(f'{lang.upper()} Token Count Distribution')
    plt.xlabel('Token Count')
    plt.ylabel('Density')
    plt.xlim(0, 3000)  # 限制x轴范围到2000
    plt.grid(True, linestyle='--', alpha=0.7)

plt.tight_layout()
plt.savefig('token_count_distribution_subplots.png', dpi=300, bbox_inches='tight')
plt.close()