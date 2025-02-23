#!/bin/bash

input_file="all-swebench-verified-instance-images.txt"

if [ ! -f "$input_file" ]; then
    echo "File $input_file not exists"
    exit 1
fi

count=0

# 获取本地所有镜像的完整名称（包括标签）
local_images=$(docker images --format "{{.Repository}}:{{.Tag}}")

# 遍历文件中的每一行
while IFS= read -r image_name || [ -n "$image_name" ]; do
    # 替换 _s_ 为 __
    image_name="${image_name//_s_/__}"
    
    # 检查是否存在本地镜像中
    if echo "$local_images" | grep -q "^${image_name}$"; then
        count=$((count+1))
        echo $count $image_name
    else
        echo "No such image: $image_name"
    fi
done < "$input_file"
