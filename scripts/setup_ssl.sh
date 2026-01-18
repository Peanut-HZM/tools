#!/bin/bash
# SSL证书配置脚本

DOMAIN="tools.peanuthzm.com.cn"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"
CONFIG_FILE="${NGINX_SITES_AVAILABLE}/${DOMAIN}"

echo "=========================================="
echo "配置SSL证书: ${DOMAIN}"
echo "=========================================="

# 检查certbot是否安装
if ! command -v certbot &> /dev/null; then
    echo "安装certbot..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

# 创建nginx配置文件（临时，用于获取证书）
echo "创建临时nginx配置..."
cat > "${CONFIG_FILE}" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        return 301 https://\$server_name\$request_uri;
    }
}
EOF

# 启用配置
ln -sf "${CONFIG_FILE}" "${NGINX_SITES_ENABLED}/${DOMAIN}"

# 测试nginx配置
nginx -t
if [ $? -ne 0 ]; then
    echo "Nginx配置测试失败"
    exit 1
fi

# 重载nginx
systemctl reload nginx

# 获取SSL证书
echo "获取SSL证书..."
certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos --email admin@peanuthzm.com.cn

if [ $? -eq 0 ]; then
    echo "SSL证书配置成功！"
    echo "证书位置: /etc/letsencrypt/live/${DOMAIN}/"
else
    echo "SSL证书配置失败"
    exit 1
fi

echo "=========================================="
echo "SSL证书配置完成"
echo "=========================================="
