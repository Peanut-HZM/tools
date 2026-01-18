#!/bin/bash
# 部署验证脚本

echo "=========================================="
echo "验证部署状态"
echo "=========================================="

DOMAIN="tools.peanuthzm.com.cn"

echo ""
echo "1. 检查前端文件..."
ssh root@39.107.229.30 "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && ls -lh /data/www/tools/index.html"

echo ""
echo "2. 检查后端服务..."
ssh root@39.107.229.30 "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && systemctl is-active tools-backend.service"

echo ""
echo "3. 检查Nginx配置..."
ssh root@39.107.229.30 "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && nginx -t"

echo ""
echo "4. 测试前端访问..."
curl -s -I https://${DOMAIN}/ -k | head -5

echo ""
echo "5. 测试API访问..."
curl -s https://${DOMAIN}/api/tools -k | head -c 200
echo "..."

echo ""
echo "=========================================="
echo "验证完成"
echo "=========================================="
