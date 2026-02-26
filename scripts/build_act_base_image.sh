#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR%/scripts}"

# Default base image; can be overridden via BASE_IMAGE env var or first arg.
BASE_IMAGE="${BASE_IMAGE:-${1:-node:16-bullseye-slim}}"
TARGET_TAG="${TARGET_TAG:-swingbench/base-with-tools}"

echo "Building SwingBench act base image..."
echo "  Base image : ${BASE_IMAGE}"
echo "  Target tag : ${TARGET_TAG}"
echo

DOCKERFILE_DIR="${REPO_ROOT}/swingbench-act-images/base-with-tools"

if [[ ! -d "${DOCKERFILE_DIR}" ]]; then
  echo "ERROR: Dockerfile directory not found: ${DOCKERFILE_DIR}" >&2
  echo "Make sure you have cloned the repository with the swingbench-act-images folder." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker command not found. Please install Docker first." >&2
  exit 1
fi

cd "${DOCKERFILE_DIR}"

echo "Running docker build..."
echo "  docker build --build-arg BASE_IMAGE=${BASE_IMAGE} -t ${TARGET_TAG} ."
docker build \
  --build-arg "BASE_IMAGE=${BASE_IMAGE}" \
  -t "${TARGET_TAG}" .

echo
echo "Successfully built image: ${TARGET_TAG}"
echo "You can now set ACT_PLATFORM_OVERRIDES in your .env, for example:"
echo "  ACT_PLATFORM_OVERRIDES=${BASE_IMAGE}=${TARGET_TAG}"

