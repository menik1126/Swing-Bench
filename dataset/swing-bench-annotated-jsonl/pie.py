import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import tiktoken
from scipy.interpolate import interp1d
import re

# # 设置中文字体
# plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'Microsoft YaHei']  # 优先使用这些字体
# plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


def count_diff_lines(patch):
    added = 0
    deleted = 0
    for line in patch.split('\n'):
        if line.startswith('+') and not line.startswith('+++'):
            added += 1
        elif line.startswith('-') and not line.startswith('---'):
            deleted += 1
    return added, deleted

# # 设置绘图风格 - 修复样式设置
# plt.style.use('seaborn-v0_8')  # 使用正确的样式名称
# sns.set_theme()  # 使用seaborn的默认主题

# 读取数据
languages = ['go', 'python', 'cpp', 'rust']
dfs = []
problem_statement_lengths = []
patch_lengths = []

p_lengths = []
patch_p_lengths = []

for lang in languages:
    df = pd.read_json(f'{lang}.jsonl', lines=True)
    df['language'] = lang

    df['statement_length'] = df['problem_statement'].apply(lambda x: len(x.split()))
    problem_statement_lengths.append(df['statement_length'].mean())
    p_lengths.append(df['statement_length'])

    df['total_lines_changed'] = df['patch'].apply(lambda x: len(x.split()))
    patch_lengths.append(df['total_lines_changed'].mean())
    patch_p_lengths.append(df['total_lines_changed'])
    dfs.append(df)

languages = ['Go', 'Python', 'Cpp', 'Rust']
# x = np.arange(len(languages)) * 0.4  # 将间隔设置为 0.8
# width = 0.15  # 条形的宽度变窄
# fig, ax = plt.subplots(figsize=(8, 6))  # 调整图形大小

# # 绘制两组条形图
# rects1 = ax.bar(x - width*0.55, problem_statement_lengths, width,
#                 label='Problem Statement Length', color='#5B8DB8')
# rects2 = ax.bar(x + width*0.55, patch_lengths, width,
#                 label='Patch Length', color='#AED6F1')

# ax.spines['top'].set_visible(False)
# ax.spines['right'].set_visible(False)
# ax.set_ylabel('Average Length', fontsize=16)
# ax.set_xticks(x)
# ax.set_xticklabels(languages, fontsize=16)
# ax.legend(fontsize=14)

# # 添加数值标签
# def add_labels(rects):
#     for rect in rects:
#         height = rect.get_height()
#         ax.annotate(f'{height:.1f}',  # 保留一位小数
#                     xy=(rect.get_x() + rect.get_width() / 2, height),
#                     xytext=(0, 5),  # 垂直偏移稍大
#                     textcoords="offset points",
#                     ha='center', va='bottom', fontsize=14)

# add_labels(rects1)
# add_labels(rects2)

# plt.tight_layout()
# plt.savefig('problem_statement_patch_line_change.pdf', dpi=300, bbox_inches='tight')
# plt.show()
# exit(0)

all_data = pd.concat(dfs, ignore_index=True)

# # 创建子图，2行4列
# fig, axes = plt.subplots(2, len(dfs), figsize=(20, 10))  # 2行，每行4个子图

# # 绘制第一行：clarity 分布
# for ax, df in zip(axes[0], dfs):
#     clarity_counts = df['clarity'].value_counts()
#     ax.pie(clarity_counts, labels=clarity_counts.index, autopct='%1.1f%%', startangle=90,
#            textprops={'fontsize': 17})  # 设置标签和百分比的字体大小
#     ax.set_title(f'{df["language"].iloc[0].capitalize()} clarity distribution', fontsize=20)  # 设置标题字体大小

# # 绘制第二行：difficulty 分布
# for ax, df in zip(axes[1], dfs):
#     df['difficulty'] = df['difficulty'].round(2)
#     difficulty_counts = df['difficulty'].value_counts()

#     # 计算总数量
#     total_count = difficulty_counts.sum()

#     # 找出小于3%的类别
#     small_categories = difficulty_counts[difficulty_counts / total_count < 0.068].index

#     # 将小于3%的类别合并为 "Other"
#     if not small_categories.empty:
#         difficulty_counts['other'] = difficulty_counts[small_categories].sum()
#         difficulty_counts = difficulty_counts.drop(small_categories)

#     # 绘制饼图
#     ax.pie(difficulty_counts, labels=difficulty_counts.index, autopct='%1.1f%%', startangle=90,
#            textprops={'fontsize': 17})  # 设置标签和百分比的字体大小
#     ax.set_title(f'{df["language"].iloc[0].capitalize()} difficulty distribution', fontsize=20)  # 设置标题字体大小

# plt.tight_layout()
# plt.savefig('clarity_difficulty_distribution_filtered_pie.pdf', dpi=300, bbox_inches='tight')
# plt.show()
# exit(0)

c_lengths = []
c_lengths[0] = [7279, 4081, 3984, 4858, 5409, 7581, 5249, 10778, 18555, 7871, 8715, 9871, 7052, 7359, 375645, 382034, 382345, 375645, 214112, 14845, 5587, 20534, 4587, 40969, 17604, 3692, 2575, 26261, 20447, 25395, 11964, 7862, 13587, 17526, 10833, 9288, 6864, 10759, 4956, 8233, 11518, 15138, 14150, 24039, 3285, 2562, 6739, 6114, 4580, 4488, 12833, 4428, 4449, 3847, 5394, 14800, 14913, 11567, 23613, 26543, 21377, 17775, 12880, 11899, 16732, 17759, 72589, 832359, 125415, 132075, 128261, 1590, 51819, 5883, 51046, 10027, 48440, 9662, 48898, 8976, 47366, 3394, 6440, 4048, 12548, 11741, 16332, 14033, 23643, 20242, 17142, 22722, 18318, 18934, 17578, 17290, 15858, 14708, 18762, 7349, 9419, 4347, 17294, 6828, 18883, 6195, 4623, 11648, 7062, 22076, 9502, 20243, 5844, 4261, 12942, 6477, 7855, 15041, 20891, 16765, 392626, 7991, 134792, 17771, 131170, 8114, 395569, 101223, 95571, 7882, 92944, 7621, 9943, 80368, 9801, 7585, 95978, 94100, 7882, 80246, 393949, 90104, 8660, 8226, 395930, 50294, 84821, 7871, 393193, 393931, 175700, 89282, 399385, 9050, 232448, 9283, 262222, 279980, 205171, 8511, 161844, 395335, 398341, 402247, 392410, 137520, 330466, 12091, 2391, 5933, 14019, 13950, 13148, 8872, 16676, 8301, 8137, 13900, 7416, 8830, 14367, 10071, 6999, 15588, 8725, 16127, 15094, 7577, 6414, 12802, 19088, 12533, 13473, 14389, 48330, 48330, 38618, 38618, 48330, 23948, 320543, 48330, 48715, 48330, 43508, 57060, 13975, 185173, 1758, 48404, 331118, 331118, 48629, 14612, 3605, 1440, 10351, 2645, 1878, 5284, 3066, 15140, 5061, 17557, 7052, 3815, 9868, 29357, 10479, 12386, 29666, 7615, 1657, 5571, 1313, 2002, 2081, 12979, 10892, 4911, 16291, 12665, 12904, 12406, 16281, 8070, 7436, 7784, 15891, 16262, 13255, 8690, 11434, 3853, 4001, 14085, 13474, 14850, 9897, 10185, 9138, 10556, 10984, 7103, 8975, 10977, 6932, 9810, 10279, 11103, 8997, 8615, 10135, 6261, 6597, 12882, 6908, 7934, 9487, 7419, 5678, 12475, 12952, 9952, 7939, 13091, 7618, 9926, 1644, 3090, 22495, 2244, 5216, 2470, 2147, 2019, 9975, 4466, 4194, 3461, 1825, 3334, 4610, 4543, 4228, 5029, 4493, 4062, 10631, 6335, 4920, 9916, 9891, 8550, 4048, 17160, 14423, 11053, 10869, 2675, 14098, 16691, 11100, 3651, 5424, 1734, 2289, 1697, 5052, 4632, 2237, 4622, 1253, 1576, 2363, 1959, 10490, 7023, 9227, 7820, 2717, 13672, 5621, 2070, 12028, 15918, 4576, 3272, 4005, 3973, 14417, 7446, 4236, 21783, 20424, 9113, 20536, 8667, 11044, 22552, 9060, 8468, 7594, 9212, 10087, 6065, 6838, 5259, 6788, 7516, 5357, 4359, 19111, 14567, 9512, 1733, 8731, 5496, 15710, 18954, 2806, 8948, 16363, 24350, 11692, 12409, 15464, 11348, 5532, 13988, 2537, 10899, 3159, 13953, 16494, 7460, 2190, 5926, 12521, 6215, 4805, 7435, 12444, 14936, 8690, 6811, 18589, 6786, 8990, 30237, 30433, 22713, 30782, 30441, 21423, 25922, 30971, 32995, 7008]
c_lengths[1] = 
c_lengths[2] = [18650, 15714, 30740, 15216, 4711, 127554, 42532, 80385, 25131, 9121, 2666, 23516, 7661, 4008, 11091, 15714, 14076, 6604, 58579, 9008, 3578, 18312, 100469, 13873, 5299, 98730, 8015, 65977, 26528, 4878, 9216, 7129, 25561, 21722, 4956, 6564, 8468, 4939, 18682, 8505, 8075, 22005, 1100, 7206, 2987, 12129, 9262, 32222, 3409, 41540, 47503, 12600, 9436, 3488, 29039, 6329, 91212, 33015, 21134, 9561, 20252, 431, 14742, 25392, 11833, 6990, 7342, 4771, 14650, 14043, 29515, 15445, 8435, 14697, 50316, 17737, 28482, 7129, 22476, 1937, 3046, 5884, 8041, 7610, 5358, 4290, 8249, 14660, 31769, 12282, 2571, 10527, 5206, 5937, 88849, 40787, 3388, 4757, 14814, 115166, 78259, 5107, 2781, 6920, 12839, 31978, 4369, 5259, 7863, 3885, 15382, 8939, 7237, 7956, 3971, 14093, 2381, 4047, 13112, 5749, 8652, 11135, 6365, 13585, 9298, 5668, 10621, 10015, 37457, 21343, 9101, 20048, 9109, 155220, 32698, 101947, 5000, 3537, 18279, 8924, 14648, 25483, 10190, 18273, 27768, 11049, 10460, 36950, 14109, 7833, 28566, 43461, 31, 12866, 9149, 28632, 14309, 23711, 13816, 6827, 10358, 2923, 33143, 84758, 16782, 7813, 23462, 5781, 4262, 3138, 2934, 23969, 10085, 7275, 2934, 10757, 6704, 30041, 3019, 3099, 6387, 8924, 5926, 6844, 6248, 2912, 7920, 8195, 33242, 13867, 6981, 11910, 7526, 4534, 2912, 4540, 4633, 2912, 7140, 11505, 28020, 10289, 11705, 34287, 38868, 24707, 2650, 36403, 5994, 32558, 32353, 6889, 6913, 32343, 3417, 30931, 8024, 13598, 9410, 2946, 12686, 10020, 36379, 14533, 8909, 6938, 7455, 6099, 11025, 13205, 17183, 5737, 11039, 17518, 6271, 12376, 8075, 19960, 19675, 7950, 22833, 11648, 2848, 5852, 3924, 3256, 4066, 34141, 5305, 15596, 3290, 1953, 8028, 6263, 50829, 55944, 4446, 8505, 4664, 35353, 4698, 6224, 6635, 38075, 5240, 13667, 82497, 35704, 15476, 9763, 6681, 3076, 8012, 27621, 24362, 1937, 12060, 30319, 6427, 58946, 56112, 43163, 23536, 5412, 10024, 28633, 56392, 68935, 68775, 15714, 4468, 31737, 4316, 11128, 28563, 15659, 41387, 25099, 15082, 8972, 0, 6336, 10543, 10722, 74497, 6750, 38085, 19609, 8895, 149213, 11339, 0, 18738, 4213, 20788, 44458, 14288, 0, 24351, 3195, 60091, 14730, 18608, 2180, 3426, 4522, 11671, 8792, 5175, 6409, 3859, 16001, 4334, 12543, 4163, 20253, 14341, 7296, 8860, 3243, 3948, 20271, 4192, 25009, 9398, 17530, 9751, 4611, 4104, 10722, 4784, 9978, 23411, 29688, 20696, 8435, 22450, 13040, 10460, 32920, 4540, 15395, 9766, 41715, 27719, 20726, 18949, 26878, 25064, 49025, 65228, 49634, 18295, 6678, 26702, 31370, 11363, 7422, 4540, 6397, 7994, 7900, 9342, 6661, 11190, 60132, 7825, 8465, 5591, 1846, 3391, 10540, 6674, 59970, 103592, 55979, 40359, 37685, 12091, 2987, 3727, 21881, 8141, 7212, 26556, 6093, 94469, 3568, 14184, 5003, 30566, 7408, 2102, 13494, 5916, 9029, 14785, 6213, 19488, 8937, 6167, 30312, 6645, 17380, 3417, 4096, 30628, 10413, 8817, 52058, 32463, 12491, 4596, 11611, 6757, 7408, 605, 263559, 18388, 4735, 3294, 4931, 59945, 7645, 56580, 29507, 90705, 26556, 11767, 30787, 112993, 82428, 9025, 79503, 76905, 95226, 55942, 10542, 11671, 21298, 125134, 20253, 89052, 4583, 7471, 7506, 4310, 26828, 10264, 24838, 3460, 5482, 14036, 3336, 8877, 3140, 28082, 7831, 10203, 42946, 11762, 11702, 10305, 9367, 8740, 10482, 16208, 12658, 7732, 4858, 6417, 3175, 6133, 16624, 40524, 39526, 3288, 22736, 59970, 14119, 6047, 49047, 26663, 34915, 3362, 12254, 10763, 14088, 7057, 35723, 4268, 37278, 2729, 3819, 8839, 33148, 13142, 4255, 18709, 13183, 61217, 7210, 12547, 3882, 5654, 238165, 48360, 5961, 29825, 27650, 5022, 2634, 4538, 5185, 9354, 7949, 6621, 5048, 9181, 16930, 4481, 13269, 28254, 122683, 157730, 120389, 106881, 27802, 138239, 9708, 58574, 6598, 32889, 6698, 8704, 8527, 13698, 6665, 5078, 5290, 4476, 12890, 10922, 2418, 15760, 9868, 6088, 9399, 23572, 3512, 3441, 88928, 88061, 3024, 1812, 3447, 29515, 9561, 15445, 20252, 41715, 68641, 49025, 4538, 62179, 25846, 14650, 8327, 7106, 9874, 9295, 32257, 19941, 2604, 43595, 9008, 11669, 8608, 10028, 2280, 17474, 46540, 9220, 37334, 22654, 16037, 3703, 10803, 16468, 65635, 5227, 10423, 7282, 67325, 5292, 11189, 33924, 13361, 88035, 74085, 67703, 67483, 10633, 53411, 3495, 7316, 10271, 95543, 9214, 2591, 7344, 52686, 3761, 6684, 13999, 32463, 8662, 14836, 34106, 11101, 16608, 2280, 4966, 10533, 5010, 67483, 3019, 26384, 17700, 5227, 2604, 23493, 15374, 74085, 4789, 9436, 3168, 14036, 4603, 8509, 6519, 8183, 22429, 4291, 6627, 6496, 13795, 5564, 2320, 14562, 7027, 5531, 7722, 4525, 6232, 6444, 3667, 7466, 82428, 23979, 55942, 125134, 5141, 30836, 95226, 11939, 112993, 26923, 4684, 9938, 7553, 6084, 8943, 18986, 6287, 7711, 4953, 12018, 5232, 49634, 2338, 4146, 11142, 31, 6080, 11049, 29155, 5255, 33143, 13232, 2443, 10395, 8964, 4578, 14309, 36950, 23711, 9704, 25362, 23613, 4110, 43461, 17904, 23462, 28566, 5352, 16275, 8238, 10256, 3079, 6648, 6440, 41986, 15345, 10546, 23578, 100469, 5590, 7338, 7380, 9263, 11525, 4904, 8522, 10661, 2951, 88928, 2895, 20042, 2196, 24591, 6695, 3464, 3518, 3441, 11181, 23572, 88061, 8179, 26037, 4561, 3442, 15545, 14390, 11351, 3138, 23969, 3019, 2912, 18603, 6122, 8035, 17765, 11887, 28254, 10281, 11611, 25078, 4414, 10542, 7573, 30787, 15545, 17737, 38211, 33661, 77959, 4273, 10493, 7237, 11202, 10475, 23433, 58574, 35178, 26528, 98730, 36291, 5675, 5825, 49453, 25901, 22598, 31665, 29257, 2644, 6647, 3356, 18009, 17997, 2137, 3815, 8674, 3774, 5397, 3866, 3991, 6896, 5779, 8142, 3786, 5774, 6142, 13585, 7247, 4898, 13912, 10858, 9142, 6558, 43163, 12096, 9327, 35570, 30508, 12133, 7298, 5807, 49453, 7998, 3453, 13809, 3478, 15953, 9900, 39757, 14836, 3695, 5683, 2386, 4106, 50829, 6839, 10450, 7089, 12892, 28482, 4549, 3512, 2874, 11997, 15588, 12476, 60132, 6472, 5704, 101218, 20561, 14324, 13563, 8202, 52153, 7673, 7910, 7716, 5616, 7737, 6531, 18640, 7960, 4339, 7726, 27790, 4937, 23446, 40836, 22292, 26503, 15520, 31248, 6675, 17992, 2989, 37281, 6651, 27466, 52686, 14305, 18490, 9246, 9561, 15670, 7818, 20120, 7744, 10101, 31665, 17265, 25901, 29257, 12425, 8737, 3255, 31063, 8552, 12279, 42192, 11288, 7667, 5016, 3137, 43412, 31898, 27187, 7742, 8744, 11008, 7336, 15505, 6093, 5878, 13373, 516050, 3104, 13459, 10358, 64110, 12814, 20788, 2791, 13140, 42946, 7730, 8569, 6819, 5060, 6815, 6735, 8575, 7965, 10748, 15089, 11301, 8139, 10763, 13661, 12178, 9730, 10234, 42192, 5886, 4693, 18679, 13756, 90705, 4005, 2011, 3448, 2677, 27131, 23209, 18312, 5222, 46328, 8907, 35723, 10844, 4290, 4099, 10960, 20348, 15215, 9863, 104239, 3932, 36024, 8581, 16727, 6218, 44829, 6192, 11032, 41491, 30740, 15734, 9288, 6919, 51945, 7146, 7429, 7270, 35138, 7011, 11798, 2926, 4931, 263559, 2987, 5008, 5215, 80385, 12129, 42532, 127554, 9812, 14036, 21933, 34733, 4206, 13375, 54456]
c_lengths[3] = [24982, 0, 15217, 5018, 6470, 2844, 27137, 14208, 22905, 0, 10742, 9919, 11818, 34420, 15402, 7844, 3729, 1380, 6739, 4670, 122769, 5164, 55764, 4682, 14189, 7769, 386, 386, 1086, 605, 100643, 83942, 120902, 122713, 113602, 120902, 75760, 2971, 476, 5837, 5376, 9090, 57899, 6642, 5969, 5322, 33177, 19652, 27073, 17784, 15160, 3686, 840, 2229, 1607, 6420, 1120, 3441, 5017, 2415, 2126, 11881, 3276, 1744, 7536, 16640, 13368, 25853, 3624, 6553, 614, 2510, 0, 3482, 656, 4190, 69932, 9925, 5404, 0, 9163, 59084, 1626, 31096, 386, 6877, 0, 8177, 386, 35505, 1454, 15557, 4855, 5421, 9539, 1056, 17161, 9252, 3214, 2336, 124835, 6705, 8344, 10776, 17309, 0, 97201, 263, 1769, 12177, 41420, 19236, 32494, 595, 13107, 195, 118, 9604, 5525, 7487, 46362, 557, 7256, 24463, 21060, 320, 8015, 6704, 5256, 3578, 19994, 12602, 25127, 37545, 41122, 21052, 28480, 21768, 49425, 14988, 46104, 19334, 17130, 16864, 17078, 818, 44606, 6422, 44737, 20201, 25091, 11722, 1430, 2947, 22569, 20132, 0, 17202, 1182, 524, 5078, 0, 1213, 5616, 5217, 2030, 68256, 7255, 18849, 6673, 3174, 617, 7833, 3117, 699, 6423, 14447, 3135, 3138, 12048, 16747, 17369, 15578, 1676, 1639, 4975, 4975, 5136, 605, 330, 10020, 966, 8414, 1828, 10035, 17707, 16111, 9149, 897, 0, 0, 0, 9544, 11977, 33532, 5205, 0, 1456, 728, 342, 342, 728, 1456, 342, 728, 342, 1456, 342, 1456, 342, 342, 342, 728, 342, 342, 692, 306, 306, 692, 692, 306, 306, 306, 306, 692, 8165, 605, 27225, 386, 1020, 0, 0, 11150, 574, 11024, 6290, 0, 7147, 27959, 22574, 0, 3803, 11430, 7006, 9014, 44785, 44785, 17448, 2953, 8232, 4391, 30882, 12761, 21167, 20384, 29594, 10346, 6839, 5921, 3798, 59909, 4619, 4504, 8331, 8805, 10236, 25966, 13097, 6831, 12610, 3236, 1401, 386, 49105, 0, 0, 876, 386, 3247, 11360, 28447, 28274, 17979, 7035, 1452, 605, 57288, 41618, 4328, 4478, 3938, 255352, 32220, 7424, 0, 9607, 23191, 16421, 96633, 9003, 25538, 14736, 5027, 31495, 5721, 11853, 6755, 4378, 15471, 386, 1664, 7995, 17782, 19969, 3840, 15488, 18764, 22165, 22165, 31356, 3748, 0, 0, 16273, 6664, 10621, 4231, 4993, 5275, 3614, 0, 386, 17937, 0, 11495, 8759, 5065, 8369, 4191, 40069, 12925, 34841, 18544, 13464, 36266, 29087, 3655, 14647, 20439, 14755, 19745, 15001, 386, 0, 27158, 14786, 4154, 386, 0, 1505, 9243, 8192, 497, 0, 11177, 17944, 8576, 7730, 2515, 9740, 8418, 2948, 2948, 4951, 1701, 5553, 2959, 7292, 2844, 2376, 31422, 4740, 12121, 14751, 18172, 23162, 1789, 30726, 39318, 32566, 75536, 29680, 30500, 44475, 43174, 33880, 39521, 7300, 26826, 3062, 215660, 286199, 778, 12772, 14509, 33253, 22369, 6439, 8632, 5604, 20689, 82718, 3581, 6005, 386, 3356, 3275, 42349, 2108, 1265, 11835, 2416, 37204, 17558, 16659, 15670, 11645, 32826, 41104, 7386, 8118, 19564, 408579, 31968, 2107, 20293, 2497, 23795, 159987, 59729, 4903, 605, 222591, 18137, 1705, 38846, 5395, 28702, 13346, 1899, 178331, 9266, 20196, 4613, 4401, 21142, 6914, 23942, 2668, 95364, 3250, 1491, 3510, 26589, 4389, 7326, 3026, 28036, 27946, 2111, 7319, 34450, 10523, 605, 605, 3340, 18554, 8646, 74083, 4668, 10845, 605, 4812, 12082, 17559, 10379, 13841, 16207, 43561, 20715, 5336, 16811, 1662, 386, 2712, 653, 28409, 386, 7867, 2375, 10776, 741, 577, 4219, 38483, 54976, 41187, 886, 88645, 193014, 8056, 4140, 214876, 14903, 879, 7982, 63724, 2040, 719, 88668, 1860, 1256, 603, 908, 856, 88612, 1595, 88752, 1604, 1091, 7986, 569, 172, 4137, 37049, 13542, 19266, 6366, 32068, 89492, 35089, 0, 23379, 34447, 34611, 43634, 30376, 286560, 36313, 271289, 60256, 4783, 4174, 12369, 15237, 690, 62134, 32910, 16375, 20168, 127980, 19884, 127980]
# 设置子图数量
fig, axes = plt.subplots(1, len(languages), figsize=(5 * len(languages), 5))

# 确保 axes 是可迭代的（当只有一个语言时，axes 是单个对象）
if len(languages) == 1:
    axes = [axes]

buckets = [100, 200, 100, 100]

t = c_lengths[0]
t = t[t <= 1350]
c_lengths[0] = t

t = c_lengths[1]
t = t[t <= 2625]
c_lengths[1] = t

t = c_lengths[3]
t = t[t <= 1500]
c_lengths[3] = t

# 为每种语言绘制柱状图
for i, lang in enumerate(languages):
    lang_df = c_lengths[i]
    lang_df = pd.DataFrame(lang_df)
    bins = range(0, lang_df.max() + buckets[i], buckets[i])
    labels = [f"{bins[j]}-{bins[j+1]}" for j in range(len(bins) - 1)]

    # 计算每个桶的数量
    bin_counts = pd.cut(lang_df, bins=bins, labels=labels, right=False).value_counts().sort_index()

    # 绘制柱状图
    axes[i].bar(bin_counts.index.astype(str), bin_counts.values, color='#5B8DB8')
    axes[i].set_title(f'{lang} problem statement length distribution', fontsize=16)
    axes[i].set_ylabel('Count', fontsize=20)
    axes[i].set_xticks(range(len(labels)))
    axes[i].set_xticklabels(labels, rotation=45, ha='right', fontsize=15)
    axes[i].tick_params(axis='y', labelsize=15)

plt.tight_layout()
plt.savefig('code_chunk_distribution_filtered_bar.pdf', dpi=300, bbox_inches='tight')
plt.show()
exit(0)

# # 设置子图数量
# fig, axes = plt.subplots(1, len(languages), figsize=(5 * len(languages), 5))

# # 确保 axes 是可迭代的（当只有一个语言时，axes 是单个对象）
# if len(languages) == 1:
#     axes = [axes]

# buckets = [100, 200, 100, 100]

# t = p_lengths[0]
# t = t[t <= 1350]
# p_lengths[0] = t

# t = p_lengths[1]
# t = t[t <= 2625]
# p_lengths[1] = t

# t = p_lengths[3]
# t = t[t <= 1500]
# p_lengths[3] = t

# # 为每种语言绘制柱状图
# for i, lang in enumerate(languages):
#     lang_df = p_lengths[i]

#     bins = range(0, lang_df.max() + buckets[i], buckets[i])
#     labels = [f"{bins[j]}-{bins[j+1]}" for j in range(len(bins) - 1)]

#     # 计算每个桶的数量
#     bin_counts = pd.cut(lang_df, bins=bins, labels=labels, right=False).value_counts().sort_index()

#     # 绘制柱状图
#     axes[i].bar(bin_counts.index.astype(str), bin_counts.values, color='#5B8DB8')
#     axes[i].set_title(f'{lang} problem statement length distribution', fontsize=16)
#     axes[i].set_ylabel('Count', fontsize=20)
#     axes[i].set_xticks(range(len(labels)))
#     axes[i].set_xticklabels(labels, rotation=45, ha='right', fontsize=15)
#     axes[i].tick_params(axis='y', labelsize=15)

# plt.tight_layout()
# plt.savefig('problem_statement_distribution_filtered_bar.pdf', dpi=300, bbox_inches='tight')
# plt.show()
# exit(0)

# # 设置子图数量
# fig, axes = plt.subplots(1, len(languages), figsize=(5 * len(languages), 5))

# # 确保 axes 是可迭代的（当只有一个语言时，axes 是单个对象）
# if len(languages) == 1:
#     axes = [axes]

# buckets = [100, 200, 200, 100]

# t = patch_p_lengths[0]
# t = t[t <= 1350]
# patch_p_lengths[0] = t

# t = patch_p_lengths[1]
# t = t[t <= 2500]
# patch_p_lengths[1] = t

# t = patch_p_lengths[2]
# t = t[t <= 2500]
# patch_p_lengths[2] = t

# t = patch_p_lengths[3]
# t = t[t <= 1500]
# patch_p_lengths[3] = t

# # 为每种语言绘制柱状图
# for i, lang in enumerate(languages):
#     lang_df = patch_p_lengths[i]

#     bins = range(0, lang_df.max() + buckets[i], buckets[i])
#     labels = [f"{bins[j]}-{bins[j+1]}" for j in range(len(bins) - 1)]

#     # 计算每个桶的数量
#     bin_counts = pd.cut(lang_df, bins=bins, labels=labels, right=False).value_counts().sort_index()

#     # 绘制柱状图
#     axes[i].bar(bin_counts.index.astype(str), bin_counts.values, color='#5B8DB8')
#     axes[i].set_title(f'{lang} patch length distribution', fontsize=20)
#     axes[i].set_ylabel('Count', fontsize=20)
#     axes[i].set_xticks(range(len(labels)))
#     axes[i].set_xticklabels(labels, rotation=45, ha='right', fontsize=15)
#     axes[i].tick_params(axis='y', labelsize=15)

# plt.tight_layout()
# plt.savefig('patch_distribution_filtered_bar.pdf', dpi=300, bbox_inches='tight')
# plt.show()
# exit(0)

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