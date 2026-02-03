# 部署指南

本文档说明如何将前后端项目部署到服务器。

## 服务器信息

- **服务器IP**: 39.107.229.30
- **域名**: tools.peanuthzm.com.cn
- **前端部署路径**: /data/www/tools
- **后端部署路径**: /data/programs/tools

## 前置要求

1. 已配置SSH免密登录到服务器
2. 服务器已安装Python 3.10+、Node.js、Nginx、PostgreSQL
3. 域名已解析到服务器IP

## 部署步骤

### 1. 服务器初始化（首次部署）

在服务器上执行初始化脚本：

```bash
# 将初始化脚本上传到服务器
scp scripts/setup_server.sh root@39.107.229.30:/tmp/

# SSH到服务器执行
ssh root@39.107.229.30
chmod +x /tmp/setup_server.sh
/tmp/setup_server.sh
```

### 2. 配置PostgreSQL数据库

在服务器上创建数据库和用户：

```bash
# SSH到服务器
ssh root@39.107.229.30

# 连接到PostgreSQL
sudo -u postgres psql

# 在PostgreSQL中执行以下命令
CREATE DATABASE tools_db;
CREATE USER tools_user WITH PASSWORD 'YOUR_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE tools_db TO tools_user;
\q
```

### 3. 配置后端环境变量

修改服务器上的systemd服务文件：

```bash
ssh root@39.107.229.30
nano /etc/systemd/system/tools-backend.service
```

修改以下环境变量：
- `DATABASE_URL`: 替换 `YOUR_PASSWORD` 为实际的数据库密码
- `JWT_SECRET_KEY`: 设置一个安全的密钥

### 4. 配置Nginx

将nginx配置文件复制到服务器：

```bash
scp scripts/nginx_config.conf root@39.107.229.30:/etc/nginx/sites-available/tools.peanuthzm.com.cn
```

在服务器上启用配置：

```bash
ssh root@39.107.229.30
ln -sf /etc/nginx/sites-available/tools.peanuthzm.com.cn /etc/nginx/sites-enabled/
nginx -t  # 测试配置
systemctl reload nginx
```

### 5. 配置SSL证书

在服务器上执行SSL证书配置脚本：

```bash
# 上传SSL配置脚本
scp scripts/setup_ssl.sh root@39.107.229.30:/tmp/
ssh root@39.107.229.30
chmod +x /tmp/setup_ssl.sh
/tmp/setup_ssl.sh
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

在服务器上启动后端服务：

```bash
ssh root@39.107.229.30
systemctl enable tools-backend.service
systemctl start tools-backend.service
systemctl status tools-backend.service
```

## 验证部署

1. **检查前端**: 访问 https://tools.peanuthzm.com.cn
2. **检查后端API**: 访问 https://tools.peanuthzm.com.cn/api
3. **检查后端服务状态**: `systemctl status tools-backend.service`
4. **查看后端日志**: `journalctl -u tools-backend.service -f`

## 更新部署

当代码更新后，只需重新运行部署脚本：

```bash
python deploy.py
```

部署脚本会自动：
1. 构建前端项目
2. 上传文件到服务器
3. 在服务器上安装依赖
4. 重启后端服务

## 故障排查

### 后端服务无法启动

1. 检查服务状态: `systemctl status tools-backend.service`
2. 查看日志: `journalctl -u tools-backend.service -n 50`
3. 检查数据库连接: 确认 `DATABASE_URL` 配置正确
4. 检查端口占用: `netstat -tlnp | grep 19092`

### Nginx配置错误

1. 测试配置: `nginx -t`
2. 查看错误日志: `tail -f /var/log/nginx/error.log`
3. 检查访问日志: `tail -f /var/log/nginx/tools_access.log`

### SSL证书问题

1. 检查证书: `certbot certificates`
2. 手动更新证书: `certbot renew`
3. 检查证书路径: `/etc/letsencrypt/live/tools.peanuthzm.com.cn/`

## 文件说明

- `deploy.py`: 本地部署脚本，用于部署前后端项目
- `scripts/setup_server.sh`: 服务器初始化脚本
- `scripts/setup_ssl.sh`: SSL证书配置脚本
- `scripts/nginx_config.conf`: Nginx配置文件模板
- `scripts/tools-backend.service`: systemd服务文件模板
- `backend/config/database.py`: 数据库配置模块

## 注意事项

1. **数据库密码**: 部署前务必修改 `DATABASE_URL` 中的密码
2. **JWT密钥**: 生产环境必须修改 `JWT_SECRET_KEY`
3. **文件权限**: 确保 `/data/programs/tools` 目录有正确的读写权限
4. **防火墙**: 确保服务器防火墙允许80和443端口
5. **SSL证书**: 证书会自动续期，但需要确保certbot定时任务正常运行
