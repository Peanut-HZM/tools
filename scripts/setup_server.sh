#!/bin/bash
# 服务器初始化脚本
# 在服务器上执行此脚本来配置环境

set -e

echo "=========================================="
echo "服务器初始化脚本"
echo "=========================================="

# 创建必要的目录
echo "创建部署目录..."
mkdir -p /data/www/tools
mkdir -p /data/programs/tools
mkdir -p /data/programs/tools/data/users
mkdir -p /data/programs/tools/data/history
mkdir -p /data/programs/tools/temp

# 安装Python和依赖
echo "检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "安装Python3..."
    apt-get update
    apt-get install -y python3 python3-pip python3-venv
fi

# 安装PostgreSQL客户端库
echo "安装PostgreSQL依赖..."
apt-get install -y libpq-dev postgresql-client

# 安装Nginx
if ! command -v nginx &> /dev/null; then
    echo "安装Nginx..."
    apt-get update
    apt-get install -y nginx
fi

# 安装certbot
if ! command -v certbot &> /dev/null; then
    echo "安装certbot..."
    apt-get install -y certbot python3-certbot-nginx
fi

# 配置systemd服务
echo "配置systemd服务..."
cat > /etc/systemd/system/tools-backend.service <<'EOF'
[Unit]
Description=Tools Backend Service
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/data/programs/tools
Environment="PATH=/data/programs/tools/venv/bin"
ExecStart=/data/programs/tools/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 19092
Restart=always
RestartSec=10

# 环境变量（需要根据实际情况修改）
Environment="JWT_SECRET_KEY=your-secret-key-change-in-production"
Environment="JWT_EXPIRE_MINUTES=1440"
Environment="USERS_DATA_PATH=/data/programs/tools/data/users"
Environment="DATABASE_URL=postgresql://tools_user:YOUR_PASSWORD@localhost:5432/tools_db"

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=tools-backend

[Install]
WantedBy=multi-user.target
EOF

# 重新加载systemd
systemctl daemon-reload

echo "=========================================="
echo "服务器初始化完成"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 修改 /etc/systemd/system/tools-backend.service 中的数据库密码"
echo "2. 配置Nginx（参考 scripts/nginx_config.conf）"
echo "3. 运行 scripts/setup_ssl.sh 配置SSL证书"
echo "4. 使用 deploy.py 部署项目"
