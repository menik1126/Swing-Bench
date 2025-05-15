import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import tiktoken
from scipy.interpolate import interp1d
import re


def count_diff_lines(patch):
    added = 0
    deleted = 0
    for line in patch.split('\n'):
        if line.startswith('+') and not line.startswith('+++'):
            added += 1
        elif line.startswith('-') and not line.startswith('---'):
            deleted += 1
    return added, deleted


languages = ['go', 'python', 'cpp', 'rust']
dfs = []
problem_statement_lengths = []
patch_lengths = []
p_lengths = []

for lang in languages:
    df = pd.read_json(f'{lang}.jsonl', lines=True)
    df['language'] = lang

    df['statement_length'] = df['problem_statement'].apply(lambda x: len(x.split()))
    problem_statement_lengths.append(df['statement_length'].mean())
    p_lengths.append(df['statement_length'])

    df['total_lines_changed'] = df['patch'].apply(lambda x: len(x.split()))
    patch_lengths.append(df['total_lines_changed'].mean())

    dfs.append(df)

languages = ['Go', 'Python', 'Cpp', 'Rust']

x = np.arange(len(languages)) * 0.4  
width = 0.15  
fig, ax = plt.subplots(figsize=(8, 6)) 

rects1 = ax.bar(x - width*0.55, problem_statement_lengths, width,
                label='Problem Statement Length', color='#5B8DB8')
rects2 = ax.bar(x + width*0.55, patch_lengths, width,
                label='Patch Length', color='#AED6F1')

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_ylabel('Average Length', fontsize=16)
ax.set_xticks(x)
ax.set_xticklabels(languages, fontsize=16)
ax.legend(fontsize=14)

def add_labels(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.1f}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=14)

add_labels(rects1)
add_labels(rects2)

plt.tight_layout()
plt.savefig('problem_statement_patch_line_change.pdf', dpi=300, bbox_inches='tight')
plt.show()

###################################################################

fig, axes = plt.subplots(2, len(dfs), figsize=(20, 10))

for ax, df in zip(axes[0], dfs):
    clarity_counts = df['clarity'].value_counts()
    ax.pie(clarity_counts, labels=clarity_counts.index, autopct='%1.1f%%', startangle=90,
           textprops={'fontsize': 17})
    ax.set_title(f'{df["language"].iloc[0].capitalize()} clarity distribution', fontsize=20)

for ax, df in zip(axes[1], dfs):
    df['difficulty'] = df['difficulty'].round(2)
    difficulty_counts = df['difficulty'].value_counts()

    total_count = difficulty_counts.sum()

    small_categories = difficulty_counts[difficulty_counts / total_count < 0.068].index

    if not small_categories.empty:
        difficulty_counts['other'] = difficulty_counts[small_categories].sum()
        difficulty_counts = difficulty_counts.drop(small_categories)

    ax.pie(difficulty_counts, labels=difficulty_counts.index, autopct='%1.1f%%', startangle=90,
           textprops={'fontsize': 17})
    ax.set_title(f'{df["language"].iloc[0].capitalize()} difficulty distribution', fontsize=20)

plt.tight_layout()
plt.savefig('clarity_difficulty_distribution_filtered_pie.pdf', dpi=300, bbox_inches='tight')
plt.show()

###################################################################

fig, axes = plt.subplots(1, len(languages), figsize=(5 * len(languages), 5))

if len(languages) == 1:
    axes = [axes]

buckets = [100, 100, 100, 100]

t = p_lengths[0]
t = t[t <= 1350]
p_lengths[0] = t

t = p_lengths[1]
t = t[t <= 2625]
p_lengths[1] = t

t = p_lengths[3]
t = t[t <= 1500]
p_lengths[3] = t

for i, lang in enumerate(languages):
    lang_df = p_lengths[i]

    bins = range(0, lang_df.max() + buckets[i], buckets[i])
    labels = [f"{bins[j]}-{bins[j+1]}" for j in range(len(bins) - 1)]
    bin_counts = pd.cut(lang_df, bins=bins, labels=labels, right=False).value_counts().sort_index()
    axes[i].bar(bin_counts.index.astype(str), bin_counts.values, color='skyblue')
    axes[i].set_title(f'{lang} Statement Length Distribution')
    axes[i].set_ylabel('Count')
    axes[i].set_xticks(range(len(labels)))
    axes[i].set_xticklabels(labels, rotation=45, ha='right')

plt.tight_layout()
plt.savefig('problem_statement_distribution_filtered_bar.pdf', dpi=300, bbox_inches='tight')
plt.show()

exit(0)
