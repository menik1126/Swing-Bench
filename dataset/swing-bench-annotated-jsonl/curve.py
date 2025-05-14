import matplotlib.pyplot as plt
import seaborn as sns

# Set Seaborn style for better aesthetics
sns.set(style="whitegrid", font_scale=1.2)

# Data
retries = [1, 2, 4, 6, 8, 10, 12, 14, 16]
win_rate = [0.43, 0.45, 0.49, 0.52, 0.55, 0.57, 0.59, 0.61, 0.64]

# Create the plot
plt.figure(figsize=(10, 6), facecolor='white')
plt.plot(retries, win_rate, marker='o', linestyle='-', color='#1f77b4', linewidth=2, markersize=8, label='Win Rate')
plt.fill_between(retries, win_rate, alpha=0.1, color='#1f77b4')

# Customize plot
plt.title('Win Rate vs Number of Retries', fontsize=16, pad=15)
plt.xlabel('Number of Retries', fontsize=12)
plt.ylabel('Win Rate', fontsize=12)

# Add annotations for key points directly on the points
plt.annotate(f'{win_rate[0]}', xy=(retries[0], win_rate[0]), xytext=(0, -10),
             textcoords='offset points', fontsize=10, color='#1f77b4', ha='center', va='top')
plt.annotate(f'{win_rate[-1]}', xy=(retries[-1], win_rate[-1]), xytext=(0, 10),
             textcoords='offset points', fontsize=10, color='#1f77b4', ha='center', va='bottom')

# Customize grid and spines
plt.grid(True, linestyle='--', alpha=0.7)
plt.gca().spines['top'].set_visible(False)
plt.gca().spines['right'].set_visible(False)

# Add legend
plt.legend(loc='lower right', fontsize=10)

# Adjust layout to prevent label cutoff
plt.tight_layout()

# Show and save the plot
plt.savefig('curve.pdf', dpi=300, bbox_inches='tight')
plt.show()