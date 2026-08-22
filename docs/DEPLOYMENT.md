# 部署指南

本文档描述如何从零开始将本项目部署到生产服务器。

---

## 前置条件

- 一台 Linux 服务器（Ubuntu 20.04+ / CentOS 7+）
- 一个已解析到服务器的域名
- 本地已安装 Python 3.10+、Node.js 18+、Git
- 服务器已配置 SSH 免密登录

---

## 一、服务器初始化

在服务器上执行初始化脚本，安装 Python、Nginx、certbot 并配置 systemd 服务：

```bash
# 在本地执行（需要 SSH 免密）
scp scripts/setup_server.sh root@YOUR_SERVER:/tmp/
ssh root@YOUR_SERVER "bash /tmp/setup_server.sh"
```

脚本会自动：
- 创建部署目录 `/data/www/tools`、`/data/programs/tools`
- 安装 Python3、pip、venv
- 安装 Nginx、certbot
- 安装 PostgreSQL 客户端库
- 注册 systemd 服务 `tools-backend.service`

> ⚠️ 执行后需手动修改 `/etc/systemd/system/tools-backend.service` 中的数据库密码。

---

## 二、配置环境变量

### 2.1 部署脚本配置（本地）

复制并编辑 `deploy.env`：

```bash
cp deploy.env.example deploy.env
# 编辑 deploy.env，填入以下必填项：
#   SERVER_HOST   = 你的服务器 IP
#   DOMAIN        = 你的域名（如 tools.example.com）
```

### 2.2 后端配置（服务器）

将 `backend/.env` 上传到服务器部署目录：

```bash
scp backend/.env root@YOUR_SERVER:/data/programs/tools/.env
```

编辑服务器上的 `/data/programs/tools/.env`，修改：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `ENV` | 运行环境 | `release` |
| `DEBUG` | 调试模式 | `false` |
| `DATABASE_URL` | 数据库连接 | `postgresql://user:pass@localhost:5432/tools_db` |
| `JWT_SECRET_KEY` | JWT 密钥 | 运行 `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` 生成 |
| `DB_ENCRYPTION_KEY` | 数据库加密密钥 | 同上 |
| `CORS_ORIGINS` | 允许的域名 | `https://tools.example.com` |
| `STORAGE_PROVIDER` | 存储类型 | `minio` 或 `aliyun_oss` |

> ⚠️ **安全提示**：`JWT_SECRET_KEY` 和 `DB_ENCRYPTION_KEY` 必须使用随机生成的强密钥，切勿使用默认值。

### 2.3 前端配置（本地构建时）

前端环境变量在构建时注入。`deploy.py` 会自动设置：
- `VITE_API_BASE_URL=https://YOUR_DOMAIN/api`

无需手动修改，除非需要自定义 AI 助手链接等：

```bash
# 可选：在 frontend/.env.production 中添加
VITE_AI_ASSISTANT_URL=https://your-ai.example.com/
```

---

## 三、Nginx 配置

### 3.1 部署 Nginx 配置

```bash
# 将域名替换为实际域名
sed 's/tools.peanuthzm.com.cn/tools.peanuthzm.com.cn/g' scripts/nginx_config.conf > /tmp/tools.peanuthzm.com.cn
scp /tmp/tools.peanuthzm.com.cn root@39.107.229.30:/etc/nginx/sites-available/tools.peanuthzm.com.cn

ssh root@39.107.229.30 "ln -sf /etc/nginx/sites-available/tools.peanuthzm.com.cn /etc/nginx/sites-enabled/ && nginx -t"
```

### 3.2 配置 SSL 证书

```bash
scp scripts/setup_ssl.sh root@39.107.229.30:/tmp/
ssh root@39.107.229.30 "bash /tmp/setup_ssl.sh tools.peanuthzm.com.cn admin@peanuthzm.com.cn"
```

certbot 会自动修改 Nginx 配置并填充 SSL 证书路径。

---

## 四、执行部署

### 4.1 全量部署（前端 + 后端）

```bash
python deploy.py
```

### 4.2 仅部署前端

```bash
python deploy.py --frontend-only
```

### 4.3 仅部署后端

```bash
python deploy.py --backend-only
```

### 4.4 部署后端但不重启服务

```bash
python deploy.py --backend-only --no-restart
```

---

## 五、验证部署

```bash
# 检查后端服务状态
ssh root@39.107.229.30 "systemctl status tools-backend.service"

# 检查后端日志
ssh root@39.107.229.30 "journalctl -u tools-backend.service -f"

# 验证 API 可达
curl https://tools.peanuthzm.com.cn/api/auth/verify

# 验证前端页面
curl -I https://tools.peanuthzm.com.cn/
```

---

## 六、常见问题

### 部署脚本报 `SERVER_HOST 未配置`
→ 检查 `deploy.env` 是否已创建且 `SERVER_HOST` 已填写。

### 后端启动失败
→ 检查 `/data/programs/tools/.env` 是否存在且格式正确，特别关注 `DATABASE_URL` 和 `JWT_SECRET_KEY`。

### 前端页面空白
→ 检查浏览器控制台是否有 API 请求失败，确认 `VITE_API_BASE_URL` 指向正确的后端地址。

### WebSocket 连接失败（K8s/SSH 工具）
→ 检查 Nginx 配置中 WebSocket location 块的 `proxy_set_header Upgrade` 和长超时设置。

### SSL 证书续期
→ certbot 会自动创建定时任务。手动续期：`certbot renew --dry-run`。
