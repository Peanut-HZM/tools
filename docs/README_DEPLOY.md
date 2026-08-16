# 部署指南

本文档说明如何将前后端项目部署到生产服务器。

## 前置要求

1. 已配置 SSH 免密登录到服务器
2. 服务器已安装 Python 3.10+、Node.js、Nginx、PostgreSQL
3. 域名已解析到服务器 IP
4. 已复制 `deploy.env.example` 为 `deploy.env` 并填入配置

## 配置部署脚本

在本地项目根目录：

```bash
cp deploy.env.example deploy.env
```

编辑 `deploy.env`，填入你的服务器配置：

```bash
SERVER_HOST=your-server-ip
SERVER_USER=root
DOMAIN=your-domain.com
FRONTEND_DEPLOY_PATH=/data/www/tools
BACKEND_DEPLOY_PATH=/data/programs/tools
```

## 部署步骤

### 1. 服务器初始化（首次部署）

将初始化脚本上传到服务器并执行：

```bash
scp scripts/setup_server.sh ${SERVER_USER}@${SERVER_HOST}:/tmp/
ssh ${SERVER_USER}@${SERVER_HOST}
chmod +x /tmp/setup_server.sh
/tmp/setup_server.sh
```

### 2. 配置 PostgreSQL 数据库

在服务器上创建数据库和用户：

```bash
sudo -u postgres psql

CREATE DATABASE tools_db;
CREATE USER tools_user WITH PASSWORD 'YOUR_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE tools_db TO tools_user;
\q
```

### 3. 配置后端环境变量

修改服务器上的 systemd 服务文件：

```bash
nano /etc/systemd/system/tools-backend.service
```

修改以下环境变量：
- `DATABASE_URL`: 替换 `YOUR_PASSWORD` 为实际的数据库密码
- `JWT_SECRET_KEY`: 运行 `python scripts/generate_keys.py` 生成

### 4. 配置 Nginx

将 nginx 配置模板复制到服务器：

```bash
scp scripts/nginx_config.conf ${SERVER_USER}@${SERVER_HOST}:/etc/nginx/sites-available/${DOMAIN}
```

编辑服务器上的配置文件，替换 `your-domain.com` 为实际域名，然后启用：

```bash
ln -sf /etc/nginx/sites-available/${DOMAIN} /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### 5. 配置 SSL 证书

```bash
scp scripts/setup_ssl.sh ${SERVER_USER}@${SERVER_HOST}:/tmp/
ssh ${SERVER_USER}@${SERVER_HOST}
chmod +x /tmp/setup_ssl.sh
/tmp/setup_ssl.sh ${DOMAIN} admin@${DOMAIN}
```

### 6. 部署项目

在本地项目根目录执行部署脚本：

```bash
# 部署前后端
python deploy.py

# 仅部署前端
python deploy.py --frontend-only

# 仅部署后端
python deploy.py --backend-only

# 部署后不重启服务
python deploy.py --no-restart
```

### 7. 启动后端服务

```bash
ssh ${SERVER_USER}@${SERVER_HOST}
systemctl enable tools-backend.service
systemctl start tools-backend.service
systemctl status tools-backend.service
```

## 验证部署

1. **检查前端**: 访问 `https://${DOMAIN}`
2. **检查后端 API**: 访问 `https://${DOMAIN}/api`
3. **检查后端服务状态**: `systemctl status tools-backend.service`
4. **查看后端日志**: `journalctl -u tools-backend.service -f`

## 故障排查

### 后端服务无法启动

1. 检查服务状态: `systemctl status tools-backend.service`
2. 查看日志: `journalctl -u tools-backend.service -n 50`
3. 检查数据库连接: 确认 `DATABASE_URL` 配置正确
4. 检查端口占用: `netstat -tlnp | grep 19092`

### Nginx 配置错误

1. 测试配置: `nginx -t`
2. 查看错误日志: `tail -f /var/log/nginx/error.log`

### SSL 证书问题

1. 检查证书: `certbot certificates`
2. 手动更新证书: `certbot renew`

## 文件说明

- `deploy.py`: 远程部署脚本（通过 SSH 部署到服务器）
- `local_deploy.sh`: 本地部署脚本（直接在服务器上执行）
- `scripts/setup_server.sh`: 服务器初始化脚本
- `scripts/setup_ssl.sh`: SSL 证书配置脚本
- `scripts/nginx_config.conf`: Nginx 配置文件模板
- `scripts/tools-backend.service`: systemd 服务文件模板
- `scripts/verify_deployment.sh`: 部署验证脚本
