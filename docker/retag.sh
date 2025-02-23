#!/bin/bash

prefix="docker-0.unsee.tech/xingyaoww/"
images=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "^$prefix")

if [ -z "$images" ]; then
    echo "No such images"
    exit 0
fi

echo "找到以下镜像需要 retag 和删除："
echo "$images"

# 遍历每个镜像
for image in $images; do
    new_image=$(echo "$image" | sed "s|^${prefix}||")
    new_image="${new_image//_s_/__}"
    echo "Retagging $image -> $new_image"

    # 给镜像重新打标签
    docker tag "$image" "$new_image"

    # 删除原始镜像
    echo "Deleting original image: $image"
    docker rmi "$image"
done

echo "Retag 和删除操作完成。"
