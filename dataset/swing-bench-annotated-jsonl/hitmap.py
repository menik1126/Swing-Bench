import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from matplotlib import cm
from matplotlib.colors import LogNorm
from matplotlib.colors import LinearSegmentedColormap
# Data (unchanged)
data = [
    {"Submitter": "Gemini", "Reviewer": "Gemini", "Language": "C++", "Request Token": 59187, "Response Token": 2357},
    {"Submitter": "Gemini", "Reviewer": "Gemini", "Language": "Python", "Request Token": 57843, "Response Token": 1949},
    {"Submitter": "Gemini", "Reviewer": "Gemini", "Language": "Rust", "Request Token": 45043, "Response Token": 2328},
    {"Submitter": "Gemini", "Reviewer": "Gemini", "Language": "Go", "Request Token": 220270, "Response Token": 2040},
    {"Submitter": "DeepSeek", "Reviewer": "DeepSeek", "Language": "C++", "Request Token": 57799, "Response Token": 3060},
    {"Submitter": "DeepSeek", "Reviewer": "DeepSeek", "Language": "Python", "Request Token": 40478, "Response Token": 2689},
    {"Submitter": "DeepSeek", "Reviewer": "DeepSeek", "Language": "Rust", "Request Token": 43460, "Response Token": 2631},
    {"Submitter": "DeepSeek", "Reviewer": "DeepSeek", "Language": "Go", "Request Token": 36949, "Response Token": 2701},
    {"Submitter": "ChatGPT", "Reviewer": "ChatGPT", "Language": "C++", "Request Token": 72522, "Response Token": 3402},
    {"Submitter": "ChatGPT", "Reviewer": "ChatGPT", "Language": "Python", "Request Token": 53209, "Response Token": 3166},
    {"Submitter": "ChatGPT", "Reviewer": "ChatGPT", "Language": "Rust", "Request Token": 72783, "Response Token": 3402},
    {"Submitter": "ChatGPT", "Reviewer": "ChatGPT", "Language": "Go", "Request Token": 55300, "Response Token": 3386},
    {"Submitter": "Claude", "Reviewer": "Claude", "Language": "C++", "Request Token": 39879, "Response Token": 9188},
    {"Submitter": "Claude", "Reviewer": "Claude", "Language": "Python", "Request Token": 33125, "Response Token": 5259},
    {"Submitter": "Claude", "Reviewer": "Claude", "Language": "Rust", "Request Token": 79865, "Response Token": 7094},
    {"Submitter": "Claude", "Reviewer": "Claude", "Language": "Go", "Request Token": 41422, "Response Token": 9592},
    {"Submitter": "Gemini", "Reviewer": "ChatGPT", "Language": "C++", "Request Token": 81161, "Response Token": 3016},
    {"Submitter": "Gemini", "Reviewer": "ChatGPT", "Language": "Python", "Request Token": 87862, "Response Token": 2853},
    {"Submitter": "Gemini", "Reviewer": "ChatGPT", "Language": "Rust", "Request Token": 72657, "Response Token": 2922},
    {"Submitter": "Gemini", "Reviewer": "ChatGPT", "Language": "Go", "Request Token": 93550, "Response Token": 2986},
    {"Submitter": "Gemini", "Reviewer": "DeepSeek", "Language": "C++", "Request Token": 55745, "Response Token": 2358},
    {"Submitter": "Gemini", "Reviewer": "DeepSeek", "Language": "Python", "Request Token": 110166, "Response Token": 1760},
    {"Submitter": "Gemini", "Reviewer": "DeepSeek", "Language": "Rust", "Request Token": 55182, "Response Token": 2443},
    {"Submitter": "Gemini", "Reviewer": "DeepSeek", "Language": "Go", "Request Token": 211644, "Response Token": 1947},
    {"Submitter": "Gemini", "Reviewer": "Claude", "Language": "C++", "Request Token": 114032, "Response Token": 2860},
    {"Submitter": "Gemini", "Reviewer": "Claude", "Language": "Python", "Request Token": 74302, "Response Token": 2658},
    {"Submitter": "Gemini", "Reviewer": "Claude", "Language": "Rust", "Request Token": 72663, "Response Token": 2995},
    {"Submitter": "Gemini", "Reviewer": "Claude", "Language": "Go", "Request Token": 271945, "Response Token": 2462},
    {"Submitter": "DeepSeek", "Reviewer": "Claude", "Language": "C++", "Request Token": 53478, "Response Token": 2963},
    {"Submitter": "DeepSeek", "Reviewer": "Claude", "Language": "Python", "Request Token": 49021, "Response Token": 2921},
    {"Submitter": "DeepSeek", "Reviewer": "Claude", "Language": "Rust", "Request Token": 71495, "Response Token": 3223},
    {"Submitter": "DeepSeek", "Reviewer": "Claude", "Language": "Go", "Request Token": 37667, "Response Token": 2803},
    {"Submitter": "DeepSeek", "Reviewer": "ChatGPT", "Language": "C++", "Request Token": 62938, "Response Token": 3171},
    {"Submitter": "DeepSeek", "Reviewer": "ChatGPT", "Language": "Python", "Request Token": 45919, "Response Token": 3211},
    {"Submitter": "DeepSeek", "Reviewer": "ChatGPT", "Language": "Rust", "Request Token": 51089, "Response Token": 3289},
    {"Submitter": "DeepSeek", "Reviewer": "ChatGPT", "Language": "Go", "Request Token": 23351, "Response Token": 2893},
    {"Submitter": "DeepSeek", "Reviewer": "Gemini", "Language": "C++", "Request Token": 76409, "Response Token": 2555},
    {"Submitter": "DeepSeek", "Reviewer": "Gemini", "Language": "Python", "Request Token": 54764, "Response Token": 2441},
    {"Submitter": "DeepSeek", "Reviewer": "Gemini", "Language": "Rust", "Request Token": 55280, "Response Token": 2653},
    {"Submitter": "DeepSeek", "Reviewer": "Gemini", "Language": "Go", "Request Token": 31081, "Response Token": 2580},
    {"Submitter": "ChatGPT", "Reviewer": "Claude", "Language": "C++", "Request Token": 76789, "Response Token": 2773},
    {"Submitter": "DeepSeek", "Reviewer": "Claude", "Language": "Python", "Request Token": 49021, "Response Token": 2921},
    {"Submitter": "ChatGPT", "Reviewer": "Claude", "Language": "Rust", "Request Token": 44821, "Response Token": 2783},
    {"Submitter": "ChatGPT", "Reviewer": "Claude", "Language": "Go", "Request Token": 60875, "Response Token": 2681},
    {"Submitter": "ChatGPT", "Reviewer": "DeepSeek", "Language": "C++", "Request Token": 62436, "Response Token": 2648},
    {"Submitter": "ChatGPT", "Reviewer": "DeepSeek", "Language": "Python", "Request Token": 62265, "Response Token": 2385},
    {"Submitter": "ChatGPT", "Reviewer": "DeepSeek", "Language": "Rust", "Request Token": 46789, "Response Token": 2626},
    {"Submitter": "ChatGPT", "Reviewer": "DeepSeek", "Language": "Go", "Request Token": 35550, "Response Token": 2563},
    {"Submitter": "ChatGPT", "Reviewer": "Gemini", "Language": "C++", "Request Token": 67790, "Response Token": 2427},
    {"Submitter": "ChatGPT", "Reviewer": "Gemini", "Language": "Python", "Request Token": 46966, "Response Token": 2264},
    {"Submitter": "ChatGPT", "Reviewer": "Gemini", "Language": "Rust", "Request Token": 50890, "Response Token": 2332},
    {"Submitter": "ChatGPT", "Reviewer": "Gemini", "Language": "Go", "Request Token": 40515, "Response Token": 2637},
    {"Submitter": "Claude", "Reviewer": "DeepSeek", "Language": "C++", "Request Token": 66457, "Response Token": 3398},
    {"Submitter": "Claude", "Reviewer": "DeepSeek", "Language": "Python", "Request Token": 52576, "Response Token": 3147},
    {"Submitter": "Claude", "Reviewer": "DeepSeek", "Language": "Rust", "Request Token": 48364, "Response Token": 3616},
    {"Submitter": "Claude", "Reviewer": "DeepSeek", "Language": "Go", "Request Token": 36424, "Response Token": 3263},
    {"Submitter": "Claude", "Reviewer": "ChatGPT", "Language": "C++", "Request Token": 50399, "Response Token": 3043},
    {"Submitter": "Claude", "Reviewer": "ChatGPT", "Language": "Python", "Request Token": 38252, "Response Token": 3401},
    {"Submitter": "Claude", "Reviewer": "ChatGPT", "Language": "Rust", "Request Token": 58291, "Response Token": 3628},
    {"Submitter": "Claude", "Reviewer": "ChatGPT", "Language": "Go", "Request Token": 34459, "Response Token": 3517},
    {"Submitter": "Claude", "Reviewer": "Gemini", "Language": "C++", "Request Token": 85504, "Response Token": 3021},
    {"Submitter": "Claude", "Reviewer": "Gemini", "Language": "Python", "Request Token": 62164, "Response Token": 3212},
    {"Submitter": "Claude", "Reviewer": "Gemini", "Language": "Rust", "Request Token": 103077, "Response Token": 3311},
    {"Submitter": "Claude", "Reviewer": "Gemini", "Language": "Go", "Request Token": 90416, "Response Token": 2888},
]

# Convert to DataFrame
df = pd.DataFrame(data)

# Unique languages, submitters, and reviewers
languages = ["C++", "Python", "Rust", "Go"]
submitters = sorted(df["Submitter"].unique())
reviewers = sorted(df["Reviewer"].unique())

# Set up the 2x2 subplot grid
fig = plt.figure(figsize=(20, 15))
axes = [fig.add_subplot(2, 2, i+1, projection='3d') for i in range(4)]

# Colormap for Request Token (matching the heatmap)
# Create a custom darker OrRd colormap
or_rd_colors = cm.OrRd(np.linspace(0, 1, 256))  # Get the original OrRd colors
# Darken the colors by reducing brightness (multiply RGB values by a factor < 1)
darkening_factor = 0.96  # Adjust this factor to control darkness (lower = darker)
or_rd_colors_darkened = np.clip(or_rd_colors[:, :3] * darkening_factor, 0, 1)  # Darken RGB, clip to valid range
or_rd_colors_darkened = np.hstack((or_rd_colors_darkened, or_rd_colors[:, 3:4]))  # Reattach alpha channel
cmap = LinearSegmentedColormap.from_list("DarkenedOrRd", or_rd_colors_darkened)

# Create a 3D bar plot for each language
for idx, lang in enumerate(languages):
    # Filter data for the current language
    lang_df = df[df["Language"] == lang]
    
    # Create pivot tables for Request and Response Tokens
    pivot_request = lang_df.pivot_table(values="Request Token", index="Submitter", columns="Reviewer", fill_value=0)
    pivot_response = lang_df.pivot_table(values="Response Token", index="Submitter", columns="Reviewer", fill_value=0)
    
    # Reindex to ensure all submitters and reviewers are included
    pivot_request = pivot_request.reindex(index=submitters, columns=reviewers, fill_value=0)
    pivot_response = pivot_response.reindex(index=submitters, columns=reviewers, fill_value=0)
    
    # Get the data as arrays
    request_data = pivot_request.values
    response_data = pivot_response.values
    
    # Create grid for bar positions
    x = np.arange(len(reviewers))
    y = np.arange(len(submitters))
    x, y = np.meshgrid(x, y)
    x = x.ravel()
    y = y.ravel()
    z = np.zeros_like(x, dtype=float)
    dx = dy = 0.4  # Bar width
    dz = response_data.ravel()  # Bar height (Response Token)
    
    # Log-normalize Request Token for colormap, with adjusted vmin/vmax to match heatmap
    norm = LogNorm(vmin=df["Request Token"].min(), vmax=df["Request Token"].max())
    colors = cmap(norm(request_data.ravel()))
    
    # Plot 3D bars without shading to avoid darkening
    bars = axes[idx].bar3d(x, y, z, dx, dy, dz, color=colors, shade=False)
    
    # 在循环内的标注部分
    for i in range(len(x)):
        if dz[i] > 0:  # Only annotate non-zero bars
            # Combined annotation: I: Request Token, O: Response Token
            annotation = f"I: {int(request_data.ravel()[i])}\nO: {int(dz[i])}"
            axes[idx].text(
                x[i] + dx/2, y[i] + dy/2, dz[i],  # Position at top of bar
                annotation,
                color='black',
                fontsize=9, ha='center', va='bottom'  # 字体大小改为 8
            )

    # 设置 Y 轴标签并旋转
    axes[idx].set_xticks(np.arange(len(reviewers)))
    axes[idx].set_yticks(np.arange(len(submitters)))
    axes[idx].set_xticklabels(reviewers, rotation=25, ha='left', va='bottom', rotation_mode='anchor')
    axes[idx].set_yticklabels(submitters, rotation=0, ha='right')
    axes[idx].set_xlabel("Reviewer", fontsize=15, labelpad=10)
    axes[idx].set_ylabel("Submitter", fontsize=15, labelpad=10)  # 增加 labelpad
    axes[idx].set_zlabel("Response Token", fontsize=15)
    axes[idx].set_title(f"Language: {lang}", fontsize=15)
    
    # Adjust view angle for better visibility
    axes[idx].view_init(elev=25, azim=22)
    
    # Add colorbar for Request Token with log scale, matching the heatmap
    cbar = fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes[idx], shrink=0.5, aspect=10)
    cbar.set_label("Request Token (log scale)", fontsize=8)

# Adjust layout
plt.tight_layout(pad=3.0, rect=[0.1, 0, 0.95, 1])  # 修正 rect 参数，增加左侧边距

# Save the figure
plt.savefig("3d_bar_token_usage_matching_or_rd_annotated.png", dpi=300, bbox_inches='tight', pad_inches=0.5)

# Show plot
plt.show()