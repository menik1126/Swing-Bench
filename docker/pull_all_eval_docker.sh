#!/bin/bash
set -e

LEVEL=$1
# three levels:
# - base, keyword "sweb.base"
# - env, keyword "sweb.env"
# - instance, keyword "sweb.eval"
SET=$2

if [ -z "$LEVEL" ]; then
    echo "Usage: $0 <cache_level> <set>"
    echo "cache_level: base, env, or instance"
    echo "set: lite, full"
    exit 1
fi

if [ -z "$SET" ]; then
    echo "Usage: $0 <cache_level> <set>"
    echo "cache_level: base, env, or instance"
    echo "set: lite, full, default is lite"
    SET="lite"
fi

# Check if namespace is provided via argument $3, otherwise default to 'xingyaoww'
NAMESPACE=${3:-swebench}

echo "Using namespace: $NAMESPACE"

if [ "$SET" == "rest" ]; then
    IMAGE_FILE="$(dirname "$0")/rest.txt"
else
    IMAGE_FILE="$(dirname "$0")/all-swebench-verified-instance-images.txt"
fi

# Define a pattern based on the level
case $LEVEL in
    base)
        PATTERN="sweb.base"
        ;;
    env)
        PATTERN="sweb.base\|sweb.env"
        ;;
    instance)
        PATTERN="sweb.base\|sweb.env\|sweb.eval"
        ;;
    *)
        echo "Invalid cache level: $LEVEL"
        echo "Valid levels are: base, env, instance"
        exit 1
        ;;
esac

echo "Pulling docker images for [$LEVEL] level"

echo "Pattern: $PATTERN"
echo "Image file: $IMAGE_FILE"

# Read each line from the file, filter by pattern, and pull the docker image
export NAMESPACE  # 确保环境变量可以被子进程访问
grep "$PATTERN" "$IMAGE_FILE" | xargs -P 64 -I {} bash -c '
    image="{}"

    echo "Processing image: $image"

    image=$(echo "$image" | sed 's/_s_/_1776_/g')

    # 检查镜像是否已存在
    # image_name=$(echo "$image" | sed 's/_s_/__/g')
    image_name=$image
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$image_name$"; then
        echo "Image $image_name already exists, skipping pull."
    else
        echo "Pulling docker-0.unsee.tech/$NAMESPACE/$image into $image"
	docker pull docker-0.unsee.tech/$NAMESPACE/$image
    fi
'

        # docker pull docker-0.unsee.tech/$NAMESPACE/$image

        # # Retag镜像
        # renamed_image=$(echo "$image" | sed "s/_s_/__/g")
        # echo "Retagging $NAMESPACE/$image to $renamed_image"
        # docker tag $NAMESPACE/$image $renamed_image 2>&1

    # echo "Processing image: $image"
