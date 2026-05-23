---
author: Peanut
created_at: 2026-05-23
purpose: 将项目中的硬编码敏感配置提取到环境变量中，为开源做准备
---

# 敏感配置环境变量化设计

## 背景

项目计划在 GitHub 上开源。当前 `backend/app/config/config.py` 中存在硬编码的敏感凭证（OSS AK/SK、Minio 密码、Redis 地址等），这些值必须全部提取到环境变量中，确保开源后不会泄露生产环境凭证。

## 目标

1. `config.py` 中不再包含任何真实敏感默认值
2. 创建 `.env.example` 模板供开源用户参考
3. `storage_migration.py` 中移除硬编码数据库密码
4. 部署流程能正确将 `.env` 上传到服务器
5. 确保 `.gitignore` 正确排除所有 `.env` 文件

## 范围

| 组件 | 是否涉及 | 说明 |
|------|----------|------|
| backend/config.py | 是 | 移除硬编码敏感默认值 |
| backend/.env | 是 | 已 gitignored，保持现状 |
| backend/.env.example | 是 | 新增模板文件 |
| backend/scripts/storage_migration.py | 是 | 移除硬编码 PostgreSQL 密码 |
| backend/app/main.py | 是 | 添加敏感配置启动检查 |
| frontend/.env* | 否 | 无敏感信息，无需改动 |
| root/.gitignore | 是 | 确认 `.env` 已排除 |

## 详细设计

### 1. config.py 敏感字段清理

以下字段的默认值需要清理：

```python
# 清理前
ALIYUN_OSS_ACCESS_KEY_ID: str = "LTAI5t6mbZdwcN8dWgKv3p51"
ALIYUN_OSS_ACCESS_KEY_SECRET: str = "uSIkuXXyPMgUOtBraMeNE8v4df54kn"
MINIO_ACCESS_KEY: str = "admin"
MINIO_SECRET_KEY: str = "MinioAdmin@2025!"
CACHE_REDIS_HOST: str = "39.107.229.30"
CACHE_REDIS_PASSWORD: str = ""
OPENCLAW_TOKEN: str = ""

# 清理后
ALIYUN_OSS_ACCESS_KEY_ID: str = ""
ALIYUN_OSS_ACCESS_KEY_SECRET: str = ""
MINIO_ACCESS_KEY: str = ""
MINIO_SECRET_KEY: str = ""
CACHE_REDIS_HOST: str = "localhost"
CACHE_REDIS_PASSWORD: str = ""
OPENCLAW_TOKEN: str = ""
```

非敏感字段保留默认值（如 endpoint、bucket name、算法等）。

### 2. 启动安全校验

在 `app/main.py` 的 startup 事件中，增加对敏感字段的校验：

- 如果 `ENV=prod` 且 `JWT_SECRET_KEY` 为空或使用了已知的默认值列表 → ERROR 级别日志
- 如果 `ENV=prod` 且 `DB_ENCRYPTION_KEY` 为空或使用了已知的默认值 → ERROR 级别日志
- 该检查不影响启动，但会明确提示运维人员

### 3. storage_migration.py 修复

当前脚本中有两处硬编码：

```python
host=settings.__dict__.get("POSTGRES_HOST", "39.107.229.30"),
password="Peanut2817*#",
```

修复方案：改为从 `DATABASE_URL` 环境变量解析，或改为不连接数据库（因为 `DATABASE_URL` 已包含完整连接信息）。

实际上，`storage_migration.py` 当前已使用 `settings.DATABASE_URL`，可以直接复用。对于 `POSTGRES_HOST` 和硬编码密码的问题：

- 移除 `get_db_conn()` 中的硬编码
- 改为使用 `psycopg2.connect(settings.DATABASE_URL)` 或 SQLAlchemy 方式连接

### 4. .env.example 模板

创建 `backend/.env.example`：

```bash
# 数据库
DATABASE_URL=postgresql://user:pass@host:port/db

# JWT 密钥（生产环境请使用强随机字符串）
JWT_SECRET_KEY=
DB_ENCRYPTION_KEY=

# Aliyun OSS
ALIYUN_OSS_ACCESS_KEY_ID=
ALIYUN_OSS_ACCESS_KEY_SECRET=
ALIYUN_OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
ALIYUN_OSS_BUCKET_NAME=oss-peanut

# Minio
MINIO_ENDPOINT=minio.peanuthzm.com.cn
MINIO_API_ENDPOINT=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET_NAME=tools-files
MINIO_SECURE=true

# Redis
CACHE_REDIS_HOST=localhost
CACHE_REDIS_PORT=6379
CACHE_REDIS_DB=0
CACHE_REDIS_PASSWORD=

# OpenClaw
OPENCLAW_GATEWAY_URL=ws://127.0.0.1:18081
OPENCLAW_TOKEN=
```

### 5. .gitignore 确认

根目录 `.gitignore` 已包含：

```
.env
.env.local
.env.*.local
```

已满足需求，无需改动。

### 6. 部署流程

当前部署流程（tar + scp）已经上传整个 `backend/` 目录。由于 `.env` 在 `.gitignore` 中，它不会被包含在 git 中，但可以通过独立的 `scp` 命令上传到服务器：

```bash
scp backend/.env root@39.107.229.30:/data/programs/tools/backend/
```

或者在部署脚本中增加此步骤。

## 验收标准

- [ ] `config.py` 中无硬编码敏感凭证
- [ ] `storage_migration.py` 中无硬编码数据库密码
- [ ] `backend/.env.example` 存在且包含所有必需变量
- [ ] 生产环境 `.env` 正常生效（通过 API 上传测试）
- [ ] git status 中不出现 `.env` 文件
