#!/usr/bin/env bash
set -euo pipefail

# PVE 一键部署脚本（Debian/Proxmox 环境）
# 用法：
#   bash deploy/pve-deploy.sh
#   REPO_URL=... BRANCH=main APP_DIR=/opt/yield-ledger bash deploy/pve-deploy.sh

REPO_URL="${REPO_URL:-https://github.com/remember20240711/Yield-Ledger.git}"
BRANCH="${BRANCH:-main}"
APP_DIR="${APP_DIR:-/opt/yield-ledger}"
SERVICE_PORT="${SERVICE_PORT:-8000}"

echo "[1/6] 检查基础命令..."
for cmd in git curl; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    apt-get update -y
    apt-get install -y git curl ca-certificates
    break
  fi
done

echo "[2/6] 检查 Docker..."
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

if ! docker compose version >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y docker-compose-plugin || true
fi

echo "[3/6] 拉取项目代码..."
if [[ -d "${APP_DIR}/.git" ]]; then
  git -C "${APP_DIR}" fetch --all --prune
  git -C "${APP_DIR}" checkout "${BRANCH}"
  git -C "${APP_DIR}" pull --ff-only origin "${BRANCH}"
else
  mkdir -p "$(dirname "${APP_DIR}")"
  git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
fi

cd "${APP_DIR}"

echo "[4/6] 准备配置文件..."
if [[ ! -f .env ]]; then
  cp .env.example .env
fi
mkdir -p data

echo "[5/6] 启动服务..."
docker compose up -d --build

echo "[6/6] 完成"
HOST_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
if [[ -n "${HOST_IP}" ]]; then
  echo "访问地址: http://${HOST_IP}:${SERVICE_PORT}"
else
  echo "访问地址: http://<你的PVE-IP>:${SERVICE_PORT}"
fi
echo "查看状态: docker compose ps"
echo "查看日志: docker compose logs -f --tail=200"
