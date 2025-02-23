#!/bin/bash

# 指定镜像前缀
prefix="docker-0.unsee.tech"

# 获取所有以 $prefix 开头的镜像
images_to_delete=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "^${prefix}")

# 检查是否有匹配的镜像
if [ -z "$images_to_delete" ]; then
    echo "No images found with prefix: $prefix"
    exit 0
fi

# 删除匹配的镜像
echo "Deleting the following images:"
echo "$images_to_delete"

# 遍历并删除每个镜像
while IFS= read -r image; do
    docker rmi "$image"
done <<< "$images_to_delete"