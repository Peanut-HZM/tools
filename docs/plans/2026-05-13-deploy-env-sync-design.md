# deploy.py 环境配置同步改进设计

**日期**: 2026-05-13
**背景**: 移除 config.py 硬编码密钥后，deploy.py 部署到服务器时未同步环境变量配置，导致后端启动失败（DB_ENCRYPTION_KEY Field required）。

## 问题根因

- `config.py` 的 `JWT_SECRET_KEY` 和 `DB_ENCRYPTION_KEY` 从硬编码改为必填字段
- 服务器通过 systemd service 文件管理环境变量
- `deploy.py` 部署后端代码时，**不检查/不同步环境变量配置**
- 结果：代码更新了，但服务器环境变量未更新 → 后端启动失败

## 改进方案

### 方案 A：部署时同步 .env 文件

在 `deploy_backend()` 中，将本地 `backend/.env` 文件同步到服务器的后端部署目录。

**实现要点**:
- 使用 `scp backend/.env root@server:/data/programs/tools/.env`
- 在 `deploy.py` 的 `exclude_patterns` 中**不排除 `.env`**（当前本来就不排除）
- 部署完成后，如果服务器上存在 `.env`，让后端优先从 `.env` 读取配置

**好处**:
- 环境变量集中管理在 `.env` 文件中
- 本地和服务器的配置一致
- 减少 systemd service 文件中的环境变量硬编码

### 方案 B：部署时检查 systemd 环境变量完整性

在 `deploy_backend()` 末尾添加环境变量校验逻辑：

1. 读取本地 `backend/.env` 文件中的配置项
2. 检查服务器 systemd service 文件中是否包含这些配置项
3. 如果缺失，自动添加并提示用户

**实现要点**:
- SSH 读取 `/etc/systemd/system/tools-backend.service`
- 解析 `Environment=` 行，与 `.env` 中的键对比
- 缺失时自动添加，然后 `systemctl daemon-reload`

**好处**:
- 即使继续使用 systemd 管理环境变量，也能自动补齐
- 部署时立即发现问题，不等到服务启动失败

## 实施顺序

1. **方案 A 优先**: 同步 .env 文件是最直接的解决方式
2. **方案 B 兜底**: 作为备用检查，确保 systemd 配置也正确

## 验证标准

- [ ] deploy.py 部署后端时，服务器后端目录下有 .env 文件
- [ ] 部署脚本检查 systemd service 环境变量，缺失时自动添加
- [ ] 部署完成后后端服务能正常启动
