#!/usr/bin/env bash
set -euo pipefail

PI_USER="${PI_USER:-puranlai}"
PI_HOST="${PI_HOST:-192.168.31.120}"
PI_DIR="${PI_DIR:-/home/puranlai/Code/duckbot}"
IMAGE="duckbot:latest"
TARBALL="duckbot.tar"

echo "==> 1/4 安装 QEMU 多架构支持（如已安装则跳过）"
docker run --privileged --rm tonistiigi/binfmt --install all

echo "==> 2/4 构建 linux/arm64 镜像: ${IMAGE}"
docker buildx build --platform linux/arm64 -t "${IMAGE}" --load .

echo "==> 3/4 导出镜像并传输到树莓派"
docker save "${IMAGE}" -o "${TARBALL}"
scp "${TARBALL}" "${PI_USER}@${PI_HOST}:${PI_DIR}/"
rm -f "${TARBALL}"

echo "==> 4/4 在树莓派上加载镜像并重启服务"
ssh "${PI_USER}@${PI_HOST}" "cd ${PI_DIR} && docker load -i ${TARBALL} && docker compose up -d && rm -f ${TARBALL}"

echo "==> 完成"
