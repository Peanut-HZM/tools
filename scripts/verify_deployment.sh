#!/bin/bash
# 部署验证脚本
# 从 deploy.env 读取服务器配置

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

# 安全加载 deploy.env
if [ -f "${PROJECT_ROOT}/deploy.env" ]; then
    while IFS='=' read -r key value; do
        [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        value="${value%\"}"; value="${value#\"}"
        value="${value%\'}"; value="${value#\'}"
        if [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
            export "$key=$value"
        fi
    done < "${PROJECT_ROOT}/deploy.env"
else
    echo "错误: 未找到 deploy.env"
    exit 1
fi

SERVER_HOST="${SERVER_HOST:-}"
SERVER_USER="${SERVER_USER:-root}"
SERVER_PORT="${SERVER_PORT:-22}"
DOMAIN="${DOMAIN:-localhost}"
FRONTEND_DEPLOY_PATH="${FRONTEND_DEPLOY_PATH:-/data/www/tools}"
BACKEND_SERVICE="${BACKEND_SERVICE:-tools-backend.service}"

if [ -z "${SERVER_HOST}" ]; then
    echo "错误: SERVER_HOST 未配置"
    exit 1
fi

echo "=========================================="
echo "验证部署状态"
echo "=========================================="

echo ""
echo "1. 检查前端文件..."
ssh -p "${SERVER_PORT}" "${SERVER_USER}@${SERVER_HOST}" "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && ls -lh ${FRONTEND_DEPLOY_PATH}/index.html"

echo ""
echo "2. 检查后端服务..."
ssh -p "${SERVER_PORT}" "${SERVER_USER}@${SERVER_HOST}" "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && systemctl is-active ${BACKEND_SERVICE}"

echo ""
echo "3. 检查Nginx配置..."
ssh -p "${SERVER_PORT}" "${SERVER_USER}@${SERVER_HOST}" "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && nginx -t"

echo ""
echo "4. 测试前端访问..."
curl -s -I "https://${DOMAIN}/" -k | head -5

echo ""
echo "5. 测试API访问..."
curl -s "https://${DOMAIN}/api/tools" -k | head -c 200
echo "..."

echo ""
echo "=========================================="
echo "验证完成"
echo "=========================================="
