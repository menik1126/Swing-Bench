# 数据清洗

## 数据标注

非常简单，直接运行 `python difficulty_estimate.py` 即可，逻辑非常好改动。

## 数据标注

注意，在 `/dataset/` 目录下，只有标注好的 jsonl 会传到 github，其他都会重新下载。目前用的是 grok-3-beta 做的标注。

## 数据检查

运行 `python sampling_checking.py` 即可。