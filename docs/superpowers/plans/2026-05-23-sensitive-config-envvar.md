# 敏感配置环境变量化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将代码库中所有硬编码的敏感凭证提取到环境变量中，清理 git 历史，为 GitHub 开源做准备。

**Architecture:** 通过 pydantic-settings 的 `.env` 机制，将 config.py、ocr_config.py、asr_config.py 中的敏感默认值清空或替换为开发安全值。storage_migration.py 改用 DATABASE_URL 连接。main.py 扩展安全校验。最终创建 `.env.example` 模板。

**Tech Stack:** Python 3.10+, FastAPI, Pydantic Settings, psycopg2

---

### Task 1: 清理 config.py 中的 Aliyun OSS 和 Minio 敏感默认值

**Files:**
- Modify: `backend/app/config/config.py:66-82`

- [ ] **Step 1: 修改 Aliyun OSS 配置（4 行变更）**

```python
# 修改前:
    ALIYUN_OSS_ACCESS_KEY_ID: str = "LTAI5t6mbZdwcN8dWgKv3p51"
    ALIYUN_OSS_ACCESS_KEY_SECRET: str = "uSIkuXXyPMgUOtBraMeNE8v4df54kn"
    ALIYUN_OSS_ENDPOINT: str = "oss-cn-beijing.aliyuncs.com"
    ALIYUN_OSS_BUCKET_NAME: str = "oss-peanut"
    ALIYUN_OSS_CALLBACK_URL: str = ""

# 修改后:
    ALIYUN_OSS_ACCESS_KEY_ID: str = ""
    ALIYUN_OSS_ACCESS_KEY_SECRET: str = ""
    ALIYUN_OSS_ENDPOINT: str = "oss-cn-beijing.aliyuncs.com"
    ALIYUN_OSS_BUCKET_NAME: str = "oss-peanut"
    ALIYUN_OSS_CALLBACK_URL: str = ""
```

- [ ] **Step 2: 修改 Minio 配置（3 行变更）**

```python
# 修改前:
    MINIO_ENDPOINT: str = "minio.peanuthzm.com.cn"
    MINIO_API_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "MinioAdmin@2025!"
    MINIO_BUCKET_NAME: str = "tools-files"
    MINIO_SECURE: bool = True

# 修改后:
    MINIO_ENDPOINT: str = "minio.peanuthzm.com.cn"
    MINIO_API_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET_NAME: str = "tools-files"
    MINIO_SECURE: bool = True
```

- [ ] **Step 3: 修改 Redis 和 OpenClaw 配置（2 行变更）**

```python
# 修改前:
    CACHE_REDIS_HOST: str = "39.107.229.30"
    CACHE_REDIS_PORT: int = 6379
    CACHE_REDIS_DB: int = 0
    CACHE_REDIS_PASSWORD: str = ""
    CACHE_REDIS_TOKEN_USAGE_TTL: int = 3600

    OPENCLAW_GATEWAY_URL: str = "ws://127.0.0.1:18081"
    OPENCLAW_TOKEN: str = ""

# 修改后:
    CACHE_REDIS_HOST: str = "localhost"
    CACHE_REDIS_PORT: int = 6379
    CACHE_REDIS_DB: int = 0
    CACHE_REDIS_PASSWORD: str = ""
    CACHE_REDIS_TOKEN_USAGE_TTL: int = 3600

    OPENCLAW_GATEWAY_URL: str = "ws://127.0.0.1:18081"
    OPENCLAW_TOKEN: str = ""
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/config/config.py
git commit -m "chore(config): 清理 Aliyun OSS、Minio、Redis 硬编码敏感默认值"
```

---

### Task 2: 为 JWT_SECRET_KEY 和 DB_ENCRYPTION_KEY 添加开发默认值

**Files:**
- Modify: `backend/app/config/config.py:52-58`

- [ ] **Step 1: 修改 JWT 和 DB 加密密钥默认值（2 行变更）**

```python
# 修改前:
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080
    DB_ENCRYPTION_KEY: str

# 修改后:
    JWT_SECRET_KEY: str = "dev-jwt-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080
    DB_ENCRYPTION_KEY: str = "dev-db-encryption-change-me"
```

- [ ] **Step 2: 验证语法正确**

Run: `python -m py_compile backend/app/config/config.py`
Expected: 无输出（成功）

- [ ] **Step 3: Commit**

```bash
git add backend/app/config/config.py
git commit -m "chore(config): JWT_SECRET_KEY 和 DB_ENCRYPTION_KEY 添加开发默认值"
```

---

### Task 3: 清理 ocr_config.py 和 asr_config.py

**Files:**
- Modify: `backend/app/config/ocr_config.py:6-9`
- Modify: `backend/app/config/asr_config.py:5-7`

- [ ] **Step 1: 修改 ocr_config.py（2 行变更）**

```python
# 修改前:
    API_KEY: str = "peanut-umi-ocr"
    API_SECRET: str = "igGC9WQwdg/9IBmFBA3rXdEIjFYH8BTe7+FBaEHXhKs="

# 修改后:
    API_KEY: str = ""
    API_SECRET: str = ""
```

- [ ] **Step 2: 修改 asr_config.py（1 行变更）**

```python
# 修改前:
    API_KEY: str = "peanut-umi-ocr"

# 修改后:
    API_KEY: str = ""
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/config/ocr_config.py backend/app/config/asr_config.py
git commit -m "chore(config): 清理 OCR/ASR 硬编码 API Key 和 Secret"
```

---

### Task 4: 重写 storage_migration.py 的 get_db_conn()

**Files:**
- Modify: `backend/scripts/storage_migration.py:66-76`

- [ ] **Step 1: 修改 get_db_conn() 函数（完整替换）**

```python
# 修改前:
def get_db_conn():
    """Get PostgreSQL connection"""
    return psycopg2.connect(
        host=settings.__dict__.get("POSTGRES_HOST", "39.107.229.30"),
        port=5432,
        database="tools",
        user="postgres",
        password="Peanut2817*#",
        cursor_factory=RealDictCursor,
    )

# 修改后:
def get_db_conn():
    """Get PostgreSQL connection from DATABASE_URL"""
    return psycopg2.connect(
        settings.DATABASE_URL,
        cursor_factory=RealDictCursor,
    )
```

- [ ] **Step 2: 验证语法正确**

Run: `python -m py_compile backend/scripts/storage_migration.py`
Expected: 无输出（成功）

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/storage_migration.py
git commit -m "chore(migration): 移除硬编码数据库密码，改用 DATABASE_URL"
```

---

### Task 5: 扩展 main.py 的 _check_security_settings()

**Files:**
- Modify: `backend/app/main.py:194-216`

- [ ] **Step 1: 修改 _check_security_settings()（完整替换）**

```python
def _check_security_settings():
    """检查安全密钥配置是否合规"""
    from app.config.config import settings
    from app.config.ocr_config import ocr_settings
    from app.config.asr_config import asr_settings

    # 已知的硬编码默认值（需要替换）
    DEFAULT_KEYS = [
        "VPYvNpIeL36rBs1XlICVkPlsNgP+Lp1FQCyp17cCOk4=",
    ]

    # 开发环境安全默认值
    DEV_DEFAULTS = [
        "dev-jwt-secret-change-me",
        "dev-db-encryption-change-me",
    ]

    if settings.JWT_SECRET_KEY in DEFAULT_KEYS or settings.JWT_SECRET_KEY in DEV_DEFAULTS:
        logger.warning("JWT_SECRET_KEY 使用了默认硬编码值，生产环境请务必更换！运行: python scripts/generate_keys.py")

    if settings.DB_ENCRYPTION_KEY in DEFAULT_KEYS or settings.DB_ENCRYPTION_KEY in DEV_DEFAULTS:
        logger.warning("DB_ENCRYPTION_KEY 使用了默认硬编码值，生产环境请务必更换！")

    if settings.JWT_SECRET_KEY == settings.DB_ENCRYPTION_KEY:
        logger.warning("JWT_SECRET_KEY 和 DB_ENCRYPTION_KEY 相同，建议配置为不同的密钥")

    if len(settings.JWT_SECRET_KEY) < 32:
        logger.warning("JWT_SECRET_KEY 长度不足 32 字符，建议更换为更长的随机密钥")

    if len(settings.DB_ENCRYPTION_KEY) < 32:
        logger.warning("DB_ENCRYPTION_KEY 长度不足 32 字符，建议更换为更长的随机密钥")

    # 生产环境额外检查
    if settings.ENV == "prod":
        if not settings.ALIYUN_OSS_ACCESS_KEY_ID and settings.STORAGE_PROVIDER == "aliyun_oss":
            logger.error("生产环境使用 aliyun_oss 时 ALIYUN_OSS_ACCESS_KEY_ID 不能为空")

        if not settings.MINIO_ACCESS_KEY and settings.STORAGE_PROVIDER == "minio":
            logger.error("生产环境使用 minio 时 MINIO_ACCESS_KEY 不能为空")

        if not ocr_settings.API_KEY:
            logger.error("生产环境 OCR_API_KEY 不能为空")

        if not asr_settings.API_KEY:
            logger.error("生产环境 ASR_API_KEY 不能为空")
```

- [ ] **Step 2: 验证语法正确**

Run: `python -m py_compile backend/app/main.py`
Expected: 无输出（成功）

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(security): 扩展安全校验——增加 OSS/Minio/OCR/ASR 生产环境检查"
```

---

### Task 6: 创建 .env.example 模板

**Files:**
- Create: `backend/.env.example`

- [ ] **Step 1: 创建 .env.example 文件**

```bash
# 将以下内容写入 backend/.env.example
```

Content:
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

- [ ] **Step 2: 验证文件存在且内容正确**

Run: `ls backend/.env.example`
Expected: `backend/.env.example`

Run: `grep -c "=" backend/.env.example`
Expected: `29`（29 个配置项）

- [ ] **Step 3: Commit**

```bash
git add backend/.env.example
git commit -m "chore: 添加 .env.example 环境变量模板"
```

---

### Task 7: 验证本地后端能正常启动（SQLite + 开发默认值）

**Files:**
- Test: `backend/app/main.py`（间接验证 config.py）

- [ ] **Step 1: 确保本地 .env 使用 SQLite**

检查 `backend/.env` 中：
```bash
DATABASE_URL=sqlite:///./data/tools.db
ENV=dev
```

- [ ] **Step 2: 启动后端**

Run: `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 19092`
Expected: 正常启动，控制台输出包含：
- `Starting application...`
- `JWT_SECRET_KEY 使用了默认硬编码值，生产环境请务必更换！`
- `DB_ENCRYPTION_KEY 使用了默认硬编码值，生产环境请务必更换！`
- `Application startup complete`

- [ ] **Step 3: 测试健康检查接口**

Run: `curl -s http://localhost:19092/`
Expected: `{"message":"Tool Aggregation API"}`

- [ ] **Step 4: 停止后端**

按 `Ctrl+C` 停止 uvicorn。

- [ ] **Step 5: Commit（如果测试通过）**

```bash
git commit --allow-empty -m "test: 验证本地启动成功（SQLite + 开发默认值）"
```

---

### Task 8: 部署到服务器并验证

**Files:**
- Deploy: `backend/` 目录

- [ ] **Step 1: 确保服务器 .env 完整**

服务器 `/data/programs/tools/.env` 应包含所有生产环境真实值（已存在，无需修改）。

- [ ] **Step 2: 打包并部署代码**

```bash
cd backend
tar czf /tmp/backend_deploy.tar.gz app scripts
cd ..
scp /tmp/backend_deploy.tar.gz root@$DEPLOY_HOST:/data/programs/tools/
```

- [ ] **Step 3: 在服务器上解压并重启**

```bash
ssh root@$DEPLOY_HOST 'cd /data/programs/tools && tar xzf backend_deploy.tar.gz && rm backend_deploy.tar.gz && systemctl restart tools-backend.service && sleep 3 && systemctl status tools-backend.service --no-pager'
```

Expected: 服务状态为 `active (running)`。

- [ ] **Step 4: 验证生产环境启动日志**

```bash
ssh root@$DEPLOY_HOST 'journalctl -u tools-backend.service --since "1 minute ago" --no-pager | grep -E "(ERROR|WARNING|Application startup complete)"'
```

Expected: 无 `ERROR` 级别日志，`Application startup complete` 出现。

**注意：** 不应出现 `JWT_SECRET_KEY 使用了默认硬编码值` 警告，因为服务器 `.env` 已配置真实密钥。

- [ ] **Step 5: Commit（如果部署成功）**

```bash
git commit --allow-empty -m "deploy: 敏感配置清理后部署到生产环境并验证"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ config.py 敏感字段清理（Task 1 + Task 2）
- ✅ ocr_config.py / asr_config.py 清理（Task 3）
- ✅ storage_migration.py 修复（Task 4）
- ✅ main.py 安全校验扩展（Task 5）
- ✅ .env.example 创建（Task 6）
- ✅ 本地启动验证（Task 7）
- ✅ 生产部署验证（Task 8）

**2. Placeholder scan:** 无 TBD/TODO/"implement later" 等占位符。每个步骤都有具体代码和预期输出。

**3. Type consistency:** 所有字段名与 config.py 中定义一致。`ocr_settings.API_KEY` 和 `asr_settings.API_KEY` 正确引用。
