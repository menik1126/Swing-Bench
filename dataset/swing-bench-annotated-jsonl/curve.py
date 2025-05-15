import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib as mpl

# Set Seaborn style for better aesthetics
sns.set(style="whitegrid", font_scale=1.2)

# Set global font to Times New Roman
mpl.rcParams['font.family'] = 'Times New Roman'

# Data
retries = [1, 2, 4, 6, 8, 10, 12, 14, 16]
submitter_win_rate = [0.43, 0.45, 0.49, 0.52, 0.55, 0.57, 0.59, 0.61, 0.64]
reviewer_win_rate =  [0.57, 0.59, 0.61, 0.62, 0.64, 0.64, 0.66, 0.67, 0.69]

# Create the plot
plt.figure(figsize=(10, 5), facecolor='white')
# 绘制submitter_win_rate
plt.plot(retries, submitter_win_rate, marker='o', linestyle='-', color='#5a8af3', linewidth=2, markersize=11, label='Submitter Best@k')
plt.fill_between(retries, submitter_win_rate, alpha=0.1, color='#5a8af3')
# 绘制reviewer_win_rate
plt.plot(retries, reviewer_win_rate, marker='s', linestyle='-', color='#557fae', linewidth=2, markersize=11, label='Reviewer Best@k')
plt.fill_between(retries, reviewer_win_rate, alpha=0.1, color='#557fae')

# Customize plot
# plt.title('Win Rate of Submitter and Reviewer', fontsize=16, pad=15)
plt.xlabel('Number of Retries (k)', fontsize=25, fontname='Times New Roman', fontweight='bold')
plt.ylabel('Win Rate', fontsize=25, fontname='Times New Roman', fontweight='bold')

# Customize grid and spines
plt.grid(True, linestyle='--', alpha=0.7)
plt.gca().spines['top'].set_visible(False)
plt.gca().spines['right'].set_visible(False)

# Add legend
plt.legend(loc='lower right', fontsize=25, prop={'family': 'Times New Roman', 'weight': 'bold'})

# Adjust layout to prevent label cutoff
plt.tight_layout()

# 在每个数据点上显示数字
for x, y in zip(retries, submitter_win_rate):
    plt.text(x, y - 0.012, f'{y}', fontsize=20, color='#5a8af3', ha='center', va='top', fontname='Times New Roman', fontweight='bold')
for x, y in zip(retries, reviewer_win_rate):
    plt.text(x, y + 0.012, f'{y}', fontsize=20, color='#557fae', ha='center', va='bottom', fontname='Times New Roman', fontweight='bold')
plt.ylim(0.4, 0.7)
plt.xticks(fontsize=25, fontname='Times New Roman', fontweight='bold')
plt.yticks([0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70], fontsize=25, fontname='Times New Roman', fontweight='bold')
# Show and save the plot
plt.savefig('win_rate_curve_best_k.pdf', dpi=300, bbox_inches='tight')
plt.show()

