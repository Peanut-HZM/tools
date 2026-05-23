---
author: Peanut
created_at: 2026-05-23
purpose: 将项目中的硬编码敏感配置提取到环境变量中，为 GitHub 开源做准备
---

# 敏感配置环境变量化设计

## 背景

项目计划在 GitHub 上开源。当前代码中存在硬编码的敏感凭证（OSS AK/SK、Minio 密码、Redis 地址、OCR/ASR API Key 等），必须全部提取到环境变量中，确保开源后不会泄露生产环境凭证。

**前置条件（必须在代码修改前完成）：**
- [ ] 轮换所有已暴露在 git history 中的凭证（Aliyun OSS AK/SK、Minio 密码、PostgreSQL 密码、Redis 密码、OCR/ASR API Key）
- [ ] 使用 `git-filter-repo` 或 BFG Repo-Cleaner 清理 git history 中的敏感信息

## 目标

1. 所有 Python config 文件中不再包含真实敏感默认值
2. 创建 `backend/.env.example` 模板供开源用户参考
3. `storage_migration.py` 中移除硬编码数据库密码
4. 部署流程能正确将 `.env` 上传到服务器
5. 新开发者克隆仓库后可以直接运行（提供 dev 默认值 + 启动警告）

## 范围

| 组件 | 是否涉及 | 说明 |
|------|----------|------|
| backend/app/config/config.py | 是 | 移除硬编码敏感默认值 |
| backend/app/config/ocr_config.py | 是 | 移除硬编码 API_KEY/API_SECRET |
| backend/app/config/asr_config.py | 是 | 移除硬编码 API_KEY |
| backend/.env | 否 | 已 gitignored，保持现状 |
| backend/.env.example | 是 | 新增模板文件 |
| backend/scripts/storage_migration.py | 是 | 移除硬编码 PostgreSQL 密码 |
| backend/app/main.py | 是 | 扩展敏感配置启动检查 |
| frontend/.env* | 否 | 无敏感信息，无需改动 |
| root/.gitignore | 是 | 确认 `.env` 已排除 |

## 详细设计

### 1. config.py 敏感字段清理

**清理策略：** 敏感字段默认值设为空字符串 `''`，非敏感字段保留开发环境通用值。

```python
# 需要清理的字段
ALIYUN_OSS_ACCESS_KEY_ID: str = ""
ALIYUN_OSS_ACCESS_KEY_SECRET: str = ""
ALIYUN_OSS_ENDPOINT: str = "oss-cn-beijing.aliyuncs.com"        # 非敏感，保留
ALIYUN_OSS_BUCKET_NAME: str = "oss-peanut"                      # 非敏感，保留
ALIYUN_OSS_CALLBACK_URL: str = ""

MINIO_ENDPOINT: str = "minio.peanuthzm.com.cn"                  # 非敏感，保留
MINIO_API_ENDPOINT: str = ""                                    # 非敏感，可为空
MINIO_ACCESS_KEY: str = ""
MINIO_SECRET_KEY: str = ""
MINIO_BUCKET_NAME: str = "tools-files"                          # 非敏感，保留
MINIO_SECURE: bool = True                                        # 非敏感，保留

CACHE_REDIS_HOST: str = "localhost"                              # 改为 localhost
CACHE_REDIS_PORT: int = 6379
CACHE_REDIS_DB: int = 0
CACHE_REDIS_PASSWORD: str = ""
CACHE_REDIS_TOKEN_USAGE_TTL: int = 3600

OPENCLAW_GATEWAY_URL: str = "ws://127.0.0.1:18081"              # 非敏感，保留
OPENCLAW_TOKEN: str = ""

# JWT 和加密密钥：提供 dev 默认值（启动时会警告）
JWT_SECRET_KEY: str = "dev-jwt-secret-change-me"
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_MINUTES: int = 10080
DB_ENCRYPTION_KEY: str = "dev-db-encryption-change-me"

# 非敏感字段保持不变
APP_NAME: str = "Tool Aggregation API"
ENV: str = "dev"
DEBUG: bool = True
USERS_DATA_PATH: str = "./data/users"
BACKEND_PORT: Optional[int] = 19092
DATABASE_URL: str = "sqlite:///./data/tools.db"
CORS_ORIGINS: str = "http://localhost:5173"
STORAGE_PROVIDER: str = "minio"
```

### 2. ocr_config.py / asr_config.py 清理

`ocr_config.py`：
```python
class OCRSettings(BaseSettings):
    OCR_API_URL: str = "https://ocr.peanuthzm.com.cn"
    API_KEY: str = ""           # 清理前："peanut-umi-ocr"
    API_SECRET: str = ""        # 清理前："igGC9WQwdg/..."
```

`asr_config.py`：
```python
class ASRSettings(BaseSettings):
    ASR_API_URL: str = "https://ocr.peanuthzm.com.cn"
    API_KEY: str = ""           # 清理前："peanut-umi-ocr"
```

### 3. 启动安全校验（扩展现有逻辑）

`app/main.py` 中已有 `_check_security_settings()` 函数（约 194-216 行），需扩展：

- 保留现有 `JWT_SECRET_KEY` 和 `DB_ENCRYPTION_KEY` 默认值检测
- 新增：当 `ENV=prod` 时，若 `ALIYUN_OSS_ACCESS_KEY_ID` 为空 → ERROR
- 新增：当 `ENV=prod` 时，若 `MINIO_ACCESS_KEY` 为空 → ERROR
- 新增：当 `ENV=prod` 时，若 `CACHE_REDIS_PASSWORD` 为空 → WARNING（Redis 可能无密码）
- 新增：当 `ENV=prod` 时，若 `OCR_API_KEY` 为空 → ERROR（如果使用 OCR 功能）

### 4. storage_migration.py 修复

当前 `get_db_conn()`：
```python
return psycopg2.connect(
    host=settings.__dict__.get("POSTGRES_HOST", "39.107.229.30"),
    port=5432,
    database="tools",
    user="postgres",
    password="Peanut2817*#",
    cursor_factory=RealDictCursor,
)
```

替换为：
```python
return psycopg2.connect(
    settings.DATABASE_URL,
    cursor_factory=RealDictCursor,
)
```

同时删除 `get_db_conn()` 中所有硬编码参数，完全依赖 `DATABASE_URL`。

### 5. .env.example 模板

创建 `backend/.env.example`：

```bash
# ========================================
# 应用基础配置
# ========================================
APP_NAME=Tool Aggregation API
ENV=dev
DEBUG=true
BACKEND_PORT=19092
DATABASE_URL=sqlite:///./data/tools.db

# JWT 密钥（开发环境可用默认值，生产环境必须修改！运行: python scripts/generate_keys.py）
JWT_SECRET_KEY=dev-jwt-secret-change-me
DB_ENCRYPTION_KEY=dev-db-encryption-change-me

# CORS 来源（开发环境默认值，生产环境按需修改）
CORS_ORIGINS=http://localhost:5173

# ========================================
# 存储配置
# ========================================
# 存储提供者: aliyun_oss | minio
STORAGE_PROVIDER=minio

# Aliyun OSS（如使用 aliyun_oss 则必填）
ALIYUN_OSS_ACCESS_KEY_ID=
ALIYUN_OSS_ACCESS_KEY_SECRET=
ALIYUN_OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
ALIYUN_OSS_BUCKET_NAME=oss-peanut
ALIYUN_OSS_CALLBACK_URL=

# Minio（如使用 minio 则必填）
MINIO_ENDPOINT=minio.peanuthzm.com.cn
MINIO_API_ENDPOINT=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET_NAME=tools-files
MINIO_SECURE=true

# ========================================
# 缓存配置
# ========================================
CACHE_REDIS_HOST=localhost
CACHE_REDIS_PORT=6379
CACHE_REDIS_DB=0
CACHE_REDIS_PASSWORD=
CACHE_REDIS_TOKEN_USAGE_TTL=3600

# ========================================
# OpenClaw 网关
# ========================================
OPENCLAW_GATEWAY_URL=ws://127.0.0.1:18081
OPENCLAW_TOKEN=

# ========================================
# OCR / ASR 服务（可选，如使用则必填）
# ========================================
OCR_API_URL=https://ocr.peanuthzm.com.cn
OCR_API_KEY=
OCR_API_SECRET=
ASR_API_URL=https://ocr.peanuthzm.com.cn
ASR_API_KEY=
```

### 6. .gitignore 确认

根目录 `.gitignore` 已包含 `.env`（第 14 行），无需修改。

### 7. 部署流程

当前部署流程（tar + scp）已上传整个 `backend/` 目录。`.env` 在 `.gitignore` 中不会被包含在 git 提交中。

部署时通过独立的 `scp` 命令将 `.env` 上传到服务器：
```bash
# 部署 .env 到服务器
scp backend/.env root@$DEPLOY_HOST:/data/programs/tools/
```

服务器上 `.env` 权限应设为 `600`：
```bash
chmod 600 /data/programs/tools/.env
```

### 8. 凭证轮换与 Git History 清理

**在开源前必须完成：**

1. **凭证轮换**：
   - Aliyun OSS：在阿里云控制台禁用当前 AccessKey，创建新的
   - Minio：修改 Minio admin 密码
   - PostgreSQL：修改数据库用户密码，更新 `.env`
   - Redis：修改 Redis 密码，更新 `.env`
   - OCR/ASR 服务：修改 API Key/Secret

2. **Git History 清理**：
   ```bash
   # 使用 git-filter-repo 清理 config.py 历史中的敏感值
   git filter-repo --replace-text <(echo 's/LTAI5t6mbZdwcN8dWgKv3p51/<REDACTED>/g')
   # 或使用 BFG Repo-Cleaner
   java -jar bfg.jar --replace-text passwords.txt
   ```

3. **GitHub Secret Scanning**：开源后 GitHub 会自动扫描仓库中的凭证。确保所有凭证已轮换。

### 9. 开发者入门指南

在 `backend/README.md`（或项目根目录 README）中添加：

```markdown
## 快速开始

1. 复制环境变量模板：
   ```bash
   cp backend/.env.example backend/.env
   ```

2. 生成安全密钥：
   ```bash
   cd backend
   python scripts/generate_keys.py
   # 将输出复制到 .env 中
   ```

3. 安装依赖并启动：
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 19092
   ```
```

## 验收标准

- [ ] `config.py` 中无硬编码敏感凭证
- [ ] `ocr_config.py` 和 `asr_config.py` 中无硬编码 API Key/Secret
- [ ] `storage_migration.py` 中无硬编码数据库密码
- [ ] `backend/.env.example` 存在且完整
- [ ] 新开发者克隆后 `cp .env.example .env` 即可启动（SQLite + dev 默认值）
- [ ] 生产模式启动时，缺少敏感字段会输出 ERROR 日志
- [ ] git status 中不出现 `.env` 文件
- [ ] 所有生产凭证已轮换
- [ ] Git history 已清理（可选但强烈建议）
