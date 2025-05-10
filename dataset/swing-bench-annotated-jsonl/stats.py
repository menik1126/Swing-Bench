import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib import font_manager

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
all_data['statement_length'] = all_data['problem_statement'].apply(lambda x: len(x.split()))
all_data[['added_lines', 'deleted_lines']] = all_data['patch'].apply(lambda x: pd.Series(count_diff_lines(x)))
all_data['total_lines_changed'] = all_data['added_lines'] + all_data['deleted_lines']
all_data['repository'] = all_data['instance_id'].apply(lambda x: '/'.join(x.split('/')[:2]))

# assert all_data['clarity'].isin([2, 3]).all(), "Clarity scores should be 2 or 3"
# assert ((0 <= all_data['difficulty']) & (all_data['difficulty'] <= 1)).all(), "Difficulty should be between 0 and 1"
# assert all_data['instance_id'].duplicated().sum() == 0, "There are duplicate instance_ids"

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
print("\nDifficulty statistics per language:")
difficulty_stats = all_data.groupby('language')['difficulty'].describe()
print(difficulty_stats)

plt.figure(figsize=(12, 6))
sns.boxplot(x='language', y='difficulty', data=all_data)
plt.title('Difficulty Distribution by Language')
plt.xlabel('Programming Language')
plt.ylabel('Difficulty Score')
plt.tight_layout()
plt.savefig('difficulty_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

# 4. 问题描述长度统计和可视化 - 优化显示范围
plt.figure(figsize=(12, 6))
sns.boxplot(x='language', y='statement_length', data=all_data)
plt.title('Problem Statement Length Distribution')
plt.xlabel('Programming Language')
plt.ylabel('Word Count')
plt.ylim(0, 2000)  # 限制y轴范围到2000
plt.tight_layout()
plt.savefig('statement_length_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

# 5. 代码变更量统计和可视化
print("\nPatch size statistics per language:")
patch_stats = all_data.groupby('language')[['added_lines', 'deleted_lines', 'total_lines_changed']].mean()
print(patch_stats)

# 5.1 散点图
plt.figure(figsize=(12, 6))
sns.scatterplot(data=all_data, x='added_lines', y='deleted_lines', 
                hue='language', alpha=0.6)
plt.title('Code Changes Distribution')
plt.xlabel('Added Lines')
plt.ylabel('Deleted Lines')
plt.xlim(0, 500)  # 限制x轴范围
plt.ylim(0, 200)  # 限制y轴范围
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
