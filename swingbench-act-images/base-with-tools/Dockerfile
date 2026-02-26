ARG BASE_IMAGE=node:16-bullseye-slim
FROM ${BASE_IMAGE}

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        curl \
        wget \
        git \
        ca-certificates \
        build-essential \
    && rm -rf /var/lib/apt/lists/*