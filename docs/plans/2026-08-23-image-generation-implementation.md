# 图像生成工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 tools 平台新增图像生成工具，通过 Dify 工作流调用多模型（豆包/通义/DALL-E/SDXL 等）实现文生图 / 图生图 / 局部重绘 / 上传编辑，配套 JWT 鉴权 + 配额管理 + 降级控制 + OSS 保留策略 + 提示词润色。

**Architecture:** 后端走 FastAPI，前端 React + Zustand + Tailwind；新增 7 个 service（DifyClient / ImageGenService / ImageGenQuotaService / DifyConfigService / ImageGenPromptPolisher / DegradationService / OssRetentionService），新增 5 张 PostgreSQL 表，所有图像生成请求通过 Dify HTTP API 路由，本应用不直接调用任何图像生成 API。Dify 部署在 `dify.peanuthzm.com.cn`，详见 spec 附录 C。

**Tech Stack:** Python 3.10+ / FastAPI / SQLAlchemy / Pydantic / PostgreSQL / Redis / httpx / Aliyun OSS (oss2) / React 18 / TypeScript / Vite / Tailwind / Zustand

**Spec:** `docs/plans/2026-08-23-image-generation-tool-design.md`

## Global Constraints

- 语言：所有对话和代码注释使用中文
- 图像生成 API 必须通过 Dify 工作流调用，不直接调图像模型
- 所有图片存储走现有 OSS 服务，前缀 `image-gen/`
- 所有图片相关 API 必须经过 JWT 鉴权中间件
- Dify API Key 在 DB 中加密存储（复用 `DB_ENCRYPTION_KEY`）
- 配额并发使用 `SELECT FOR UPDATE` 事务，防止双花
- 后端不自动重试失败的生成请求（避免配额双花）
- 前端同步 HTTP 调用，超时 60s，可取消（AbortController）
- 配置分层：`.env` 默认 + DB 后台覆盖，每次调用实时读取（不缓存）

## 执行约定（Plan 详细度策略）

- **Phase 1/2 是详细模板**：展示完整的 TDD step-by-step（写失败测试 → 实现 → 验证 → commit），作为后续 phase 的参考
- **Phase 3-13 列出 task 核心要点 + 关键接口定义**：每个 phase 给出"做什么"和"关键代码形态"，具体 step 由执行阶段按 Phase 1/2 的 TDD 模式展开
- **执行方式推荐 Subagent-Driven**：每个 phase 派一个 subagent，subagent 根据上下文（spec + 前面 task 已落地的代码）展开为完整 step，review 后再下一个 phase
- **关键接口必须显式**：Phase 3/4/5 的核心 dataclass/方法签名已在对应 phase 显式定义，避免后续 phase 的 implementer 猜测类型


## 阶段划分与依赖关系

```
Phase 0: Dify 工作空间初始化（手动）
    │
    ▼
Phase 1: 后端基础设施（env + constants + 5 DB 表 + models + migration）
    │
    ▼
Phase 2: DifyConfigService（分层配置管理）
    │
    ▼
Phase 3: DifyClient（Dify HTTP 客户端）
    │
    ▼
Phase 4: QuotaService（配额服务 + 管理员方法）
    │
    ▼
Phase 5: ImageGenService + HistoryService（编排 + 历史）
    │
    ▼
Phase 6: 用户 API 路由
    │
    ▼
Phase 7: 管理 API 路由
    │
    ▼
Phase 8: PromptPolisher（提示词润色）
    │
    ▼
Phase 9: DegradationService（降级控制）
    │
    ▼
Phase 10: OssRetentionService（OSS 保留策略 + 定时任务）
    │
    ▼
Phase 11: 前端用户页面（组件 + 状态 + API）
    │
    ▼
Phase 12: 前端管理页面（5 个 tab）
    │
    ▼
Phase 13: i18n + 集成测试 + 文档
```

**依赖说明**：
- Phase 0 必须在所有后端 phase 之前（Dify API 必须先可用）
- Phase 1 是所有后续后端 phase 的基础
- Phase 2 必须在 Phase 3/4/5 之前（它们依赖配置读取）
- Phase 3/4 必须先于 Phase 5（ImageGenService 编排它们）
- Phase 6 必须先于 Phase 7（共享基础 schema）
- Phase 8/9/10 可在 Phase 6 之后独立进行
- Phase 11 依赖 Phase 6 的 API
- Phase 12 依赖 Phase 7 的 API
- Phase 13 最后收尾

**估算总工时**：约 50-70 小时（2-3 周全职）

---

## Phase 0: Dify 工作空间初始化（手动 + 服务端前置）

**目标**：让 Dify 具备 4 个可调用的工作流 + 1 个 App API Key

**执行人**：用户本人（登录 Dify）+ 开发者（服务端 SSH）

**前置条件**：
- Dify 管理员账号 `peanut_hzm@163.com`（密码自管，初始密码在 `Dify@2026` 之后用户重设）
- 服务器 SSH 免密（已配置）
- 各厂商图像生成 API Key（豆包/通义万相/MiniMax 等）

### Part A: 服务端前置（开发者 SSH 操作）

**Step A1: 安装 uv（Dify 插件依赖）**

```bash
ssh root@39.107.229.30
curl -LsSf https://astral.sh/uv/install.sh | sh
ln -sf /root/.local/bin/uv /usr/local/bin/uv
uv --version
```

**Step A2: 修正 Dify DB 连接池配置（防 500 错误）**

实测发现：Dify 1.14.2 默认连接池配置会在高并发下打满 PostgreSQL `max_connections=100`，导致 `FATAL: too many clients already`。**必须修复**：

```bash
# 追加到 /data/programs/dify/conf/api.env 末尾
cat >> /data/programs/dify/conf/api.env << 'EOF'

# 数据库连接池优化（防止连接数溢出）
DB_PSYCOPG_POOL_MIN_CONN=2
DB_PSYCOPG_POOL_MAX_CONN=15
DB_PSYCOPG_POOL_TIMEOUT=10
DB_SQLALCHEMY_POOL_SIZE=5
DB_SQLALCHEMY_MAX_OVERFLOW=5
DB_SQLALCHEMY_POOL_TIMEOUT=10
DB_HEALTH_CHECK=true
EOF

# 必须直接重启 dify-api（dify.target 有时不杀掉 gunicorn）
systemctl restart dify-api
sleep 12

# 验证
DBPWD=$(grep ^DB_PASSWORD /data/programs/dify/conf/api.env | cut -d= -f2-)
export PGPASSWORD="$DBPWD"
psql -h 127.0.0.1 -U postgres -d dify -c "SELECT count(*) FROM pg_stat_activity WHERE datname='dify';"
# 期望：< 15（不再是 90+）
```

**Step A3: 修正插件安装超时**

```bash
# 默认 15s 太短，下载依赖时会超时
sed -i 's/^PLUGIN_INSTALL_TIMEOUT=15$/PLUGIN_INSTALL_TIMEOUT=300/' \
    /data/programs/dify-plugin-daemon-src/.env
systemctl restart dify-plugin-daemon
```

**Step A4: 安装国内常用插件（开发者可批量执行）**

通过 plugin daemon API 批量安装，**用 marketplace API 的 `latest_package_identifier`（不是文件 sha256）**：

```bash
# 详见 spec §C.6 插件清单
# 用 ssh + curl 触发（示例为 tongyi）
ssh root@39.107.229.30 'curl -s -X POST -H "X-Api-Key: inner-api-key" -H "Content-Type: application/json" \
  "http://127.0.0.1:15002/plugin/4a57b927-c09c-4463-ba1b-0fbc5b2de16e/management/install/identifiers" \
  -d "{\"plugin_unique_identifiers\":[\"langgenius/tongyi:0.2.14@da713345c5587cecafa266cc98db84b9194c30b3c98070c2dbfaae8a8ed92e76\"],\"source\":\"marketplace\",\"metas\":[{}]}"'

# 等安装完成（每个插件需要建 venv + 装依赖，约 1-2 分钟/个）
# 验证
ssh root@39.107.229.30 'curl -s -H "X-Api-Key: inner-api-key" \
  "http://127.0.0.1:15002/plugin/4a57b927-c09c-4463-ba1b-0fbc5b2de16e/management/list?page=1&page_size=256&response_type=paged" | \
  python3 -c "import sys,json;d=json.load(sys.stdin);print(len(d[\"data\"][\"list\"]),\"plugins installed\")"'
```

> **重要**：插件会出现在 Dify UI 的「工具」页面，**不是「模型供应商」**。需要在「工具」页面单独为每个插件授权 API Key。

---

### Part B: 用户手动操作

**Step B1: 登录 Dify**

- 访问 `https://dify.peanuthzm.com.cn`
- 用管理员账号登录

**Step B2: 在「工具」页面配置 API Key**

- 进入「工具」页面（不是「模型供应商」）
- 为每个图像生成插件配置 API Key：
  - **豆包 Seedream**：火山引擎 ARK API Key
  - **通义 AIGC**：阿里云 DashScope API Key
  - **海螺 Hailuo**：MiniMax API Key

> **注意**：LLM 类插件（tongyi/deepseek/moonshot/zhipuai 等）在「模型供应商」配置 API Key。

**Step B3: 创建 4 个工作流**

按 `docs/plans/2026-08-23-image-generation-workflow-design.md` 设计：

- 新建工作流 → 命名 `image_gen_text2img` / `image_gen_img2img` / `image_gen_inpaint` / `image_gen_upload_edit`
- 配置节点：开始 → 条件分支 → 工具节点（插件的 `text_2_image` / `image_2_image` / inpaint / edit 方法）→ 代码解析 → 结束
- 输出变量统一：`image_urls (array[string>)`, `model_used (string)`

**Step B4: 获取 App API Key + Workflow IDs**

- 进入任一应用「访问 API」→ 生成 API Key（形如 `app-xxxxxxxxxxxx`）
- 记录 4 个 workflow ID（在 URL 或应用设置里）

**Step B5: 写入 `.env`**

```bash
# backend/.env 增加：
DIFY_API_URL=https://dify.peanuthzm.com.cn/v1
DIFY_APP_API_KEY=app-xxxxxxxxxxxx
DIFY_WORKFLOW_TEXT2IMG=wf_xxx
DIFY_WORKFLOW_IMG2IMG=wf_yyy
DIFY_WORKFLOW_INPAINT=wf_zzz
DIFY_WORKFLOW_UPLOAD_EDIT=wf_aaa
```

**Step B6: 测试 API 可达**

```bash
curl -X POST https://dify.peanuthzm.com.cn/v1/workflows/run \
  -H "Authorization: Bearer app-xxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"prompt": "a cat", "size": "1024x1024", "n": 1, "model_preference": "auto"}, "response_mode": "blocking", "user": "test"}'
```

期望：返回 JSON 含 `task_id` + `workflow_run_id`。

---

**验收标准**：
- ✅ uv 已装（`uv --version` 可用）
- ✅ DB 连接池配置生效（pg_stat_activity idle < 15）
- ✅ 插件安装超时改 300s
- ✅ 至少 25 个国内常用插件安装成功
- ✅ 4 个工作流可独立运行
- ✅ 用 App API Key 能调通至少一个工作流
- ✅ `.env` 已配置

**预估工时**：
- Part A（服务端）：30-60 分钟
- Part B（用户手动）：1-2 小时

---

## Phase 1: 后端基础设施

**目标**：建立 env 配置、常量、5 张 DB 表、SQLAlchemy models、Alembic 迁移

**Files:**
- Modify: `backend/app/config/config.py` (加 DIFY_* 字段)
- Create: `backend/app/utils/image_gen_constants.py`
- Create: `backend/app/models/image_generation_models.py` (SQLAlchemy)
- Create: `backend/app/schemas/image_generation.py` (Pydantic)
- Create: `backend/alembic/versions/xxxx_add_image_generation_tables.py`

**Consumes:** 无（首个技术 phase）
**Produces:** 5 张表 + models + schemas + env vars

### Task 1.1: 添加 env 配置

- [ ] **Step 1: 在 `backend/app/config/config.py` 添加字段**

```python
# 在 Settings 类中添加：
# Dify 图像生成（默认值，可被 DB 后台覆盖）
DIFY_API_URL: str = ""
DIFY_APP_API_KEY: str = ""  # 敏感字段，建议放 .env
DIFY_WORKFLOW_TEXT2IMG: str = ""
DIFY_WORKFLOW_IMG2IMG: str = ""
DIFY_WORKFLOW_INPAINT: str = ""
DIFY_WORKFLOW_UPLOAD_EDIT: str = ""
DIFY_DEFAULT_TIMEOUT: float = 60.0

# 图像生成全局开关
IMAGE_GENERATION_ENABLED: bool = True
```

- [ ] **Step 2: 在 `backend/.env` 添加（已添加则跳过）**

```bash
# ========================================
# 图像生成 - Dify 配置
# ========================================
DIFY_API_URL=https://dify.peanuthzm.com.cn/v1
DIFY_APP_API_KEY=app-xxxxxxxxxxxx
DIFY_WORKFLOW_TEXT2IMG=wf_xxx
DIFY_WORKFLOW_IMG2IMG=wf_yyy
DIFY_WORKFLOW_INPAINT=wf_zzz
DIFY_WORKFLOW_UPLOAD_EDIT=wf_aaa
DIFY_DEFAULT_TIMEOUT=60.0
IMAGE_GENERATION_ENABLED=true
```

- [ ] **Step 3: 验证 config 加载**

```bash
cd backend
python -c "from app.config.config import settings; print(settings.DIFY_API_URL, settings.IMAGE_GENERATION_ENABLED)"
```
期望：打印出 .env 里的值

- [ ] **Step 4: Commit**

```bash
git add backend/app/config/config.py backend/.env
git commit -m "feat(image-gen): 添加 Dify 配置字段到 Settings"
```

### Task 1.2: 创建常量模块

- [ ] **Step 1: 创建 `backend/app/utils/image_gen_constants.py`**

```python
"""图像生成工具常量"""

# 操作类型
OPERATION_TEXT2IMG = "text2img"
OPERATION_IMG2IMG = "img2img"
OPERATION_INPAINT = "inpaint"
OPERATION_UPLOAD_EDIT = "upload_edit"

VALID_OPERATIONS = {
    OPERATION_TEXT2IMG,
    OPERATION_IMG2IMG,
    OPERATION_INPAINT,
    OPERATION_UPLOAD_EDIT,
}

# 上传编辑类型
EDIT_TYPE_UPSCALE = "upscale"
EDIT_TYPE_DENOISE = "denoise"
EDIT_TYPE_RELIGHT = "relight"
EDIT_TYPE_STYLE_TRANSFER = "style_transfer"
EDIT_TYPE_BACKGROUND_REMOVE = "background_remove"

VALID_EDIT_TYPES = {
    EDIT_TYPE_UPSCALE,
    EDIT_TYPE_DENOISE,
    EDIT_TYPE_RELIGHT,
    EDIT_TYPE_STYLE_TRANSFER,
    EDIT_TYPE_BACKGROUND_REMOVE,
}

# 尺寸枚举
VALID_SIZES = {
    "1024x1024",
    "1024x1792",
    "1792x1024",
    "512x512",
    "768x768",
}

# 模型偏好枚举
VALID_MODEL_PREFERENCES = {
    "auto",
    "doubao_seedream",
    "qwen_image",
    "dall_e_3",
    "sdxl",
}

# OSS 前缀
OSS_PREFIX_REF = "image-gen/ref"
OSS_PREFIX_MASK = "image-gen/mask"
OSS_PREFIX_RESULT = "image-gen/result"

# 文件限制
MAX_REFERENCE_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_N_IMAGES = 4
SIGNED_URL_EXPIRES_REF = 300    # 5 分钟（Dify 用）
SIGNED_URL_EXPIRES_RESULT = 3600  # 1 小时（前端用）

# 默认配额
DEFAULT_DAILY_LIMIT = 20
DEFAULT_MONTHLY_LIMIT = 300

# 默认降级配置
DEFAULT_DEGRADATION_ENABLED = True
DEFAULT_FAILURE_THRESHOLD = 3
DEFAULT_DEGRADE_DURATION_SECONDS = 300

# 默认保留策略
RETENTION_MODE_KEEP_FOREVER = "keep_forever"
RETENTION_MODE_DELETE_AFTER_N_DAYS = "delete_after_n_days"
RETENTION_MODE_DELETE_IF_UNUSED_FOR_N_DAYS = "delete_if_unused_for_n_days"
DEFAULT_RETENTION_MODE = RETENTION_MODE_KEEP_FOREVER
DEFAULT_RETENTION_N_DAYS = 30
DEFAULT_CLEANUP_CRON = "0 3 * * *"

# 历史状态
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"
```

- [ ] **Step 2: 验证导入**

```bash
cd backend
python -c "from app.utils.image_gen_constants import VALID_OPERATIONS; print(VALID_OPERATIONS)"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/utils/image_gen_constants.py
git commit -m "feat(image-gen): 添加常量模块"
```

### Task 1.3: 创建 SQLAlchemy models（5 张表）

- [ ] **Step 1: 创建 `backend/app/models/image_generation_models.py`**

```python
"""图像生成工具 - SQLAlchemy 模型"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, DateTime, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def gen_uuid() -> str:
    return str(uuid.uuid4())


class ImageGenQuota(Base):
    """配额表"""
    __tablename__ = "image_gen_quota"

    user_id = Column(String(64), primary_key=True)
    daily_limit = Column(Integer, nullable=False)
    monthly_limit = Column(Integer, nullable=False)
    daily_used = Column(Integer, nullable=False, default=0)
    monthly_used = Column(Integer, nullable=False, default=0)
    daily_reset_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    monthly_reset_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    granted_by = Column(String(64), nullable=True)
    notes = Column(String(512), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ImageGenHistory(Base):
    """历史表"""
    __tablename__ = "image_gen_history"

    id = Column(String(64), primary_key=True, default=gen_uuid)
    user_id = Column(String(64), nullable=False, index=True)
    operation = Column(String(32), nullable=False)
    prompt = Column(Text, nullable=True)
    params = Column(JSON, nullable=True)
    reference_oss_key = Column(String(512), nullable=True)
    mask_oss_key = Column(String(512), nullable=True)
    result_oss_key = Column(String(512), nullable=False)
    result_width = Column(Integer, nullable=True)
    result_height = Column(Integer, nullable=True)
    model_used = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    last_accessed_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class ImageGenDifyConfig(Base):
    """Dify 配置表（key-value，value 加密）"""
    __tablename__ = "image_gen_dify_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), nullable=False, unique=True)
    value_encrypted = Column(String(4096), nullable=False)  # 加密后的字符串
    updated_by = Column(String(64), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ImageGenDegradationConfig(Base):
    """降级配置表"""
    __tablename__ = "image_gen_degradation_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enabled = Column(Boolean, nullable=False, default=True)
    failure_threshold = Column(Integer, nullable=False, default=3)
    degrade_duration_seconds = Column(Integer, nullable=False, default=300)
    updated_by = Column(String(64), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ImageGenRetentionConfig(Base):
    """OSS 保留策略配置表"""
    __tablename__ = "image_gen_retention_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mode = Column(String(64), nullable=False, default="keep_forever")
    n_days = Column(Integer, nullable=False, default=30)
    cleanup_cron = Column(String(32), nullable=False, default="0 3 * * *")
    updated_by = Column(String(64), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
```

- [ ] **Step 2: 验证 models 可加载**

```bash
cd backend
python -c "from app.models.image_generation_models import ImageGenQuota, ImageGenHistory; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/image_generation_models.py
git commit -m "feat(image-gen): 添加 5 张表的 SQLAlchemy models"
```

### Task 1.4: 创建 Pydantic schemas

- [ ] **Step 1: 创建 `backend/app/schemas/image_generation.py`**

```python
"""图像生成工具 - Pydantic 请求/响应模型"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ==================== 用户侧请求 ====================

class Text2ImgRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    size: str = Field(default="1024x1024")
    n: int = Field(default=1, ge=1, le=4)
    style: Optional[str] = None
    model_preference: str = Field(default="auto")


class Img2ImgRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    size: str = Field(default="1024x1024")
    strength: float = Field(default=0.6, ge=0.0, le=1.0)
    model_preference: str = Field(default="auto")


class InpaintRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    size: str = Field(default="1024x1024")
    model_preference: str = Field(default="auto")


class UploadEditRequest(BaseModel):
    edit_type: str
    prompt: Optional[str] = Field(default=None, max_length=2000)


class PolishPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    target_operation: str = "text2img"


# ==================== 响应 ====================

class GenerationResult(BaseModel):
    record_id: str
    result_url: str                    # OSS 签名 URL (1h)
    model_used: str
    duration_ms: int
    width: Optional[int] = None
    height: Optional[int] = None


class PolishPromptResult(BaseModel):
    polished_prompt: str
    original_prompt: str


class QuotaInfo(BaseModel):
    user_id: str
    daily_limit: int
    daily_used: int
    daily_remaining: int
    monthly_limit: int
    monthly_used: int
    monthly_remaining: int
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_valid: bool


class HistoryRecord(BaseModel):
    id: str
    operation: str
    prompt: Optional[str] = None
    result_url: str
    model_used: Optional[str] = None
    duration_ms: Optional[int] = None
    status: str
    created_at: datetime


class HistoryListResponse(BaseModel):
    items: List[HistoryRecord]
    total: int
    page: int
    page_size: int


# ==================== 管理侧 ====================

class GrantQuotaRequest(BaseModel):
    daily_limit: int = Field(..., ge=1)
    monthly_limit: int = Field(..., ge=1)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None


class QuotaRecord(BaseModel):
    user_id: str
    daily_limit: int
    daily_used: int
    monthly_limit: int
    monthly_used: int
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    granted_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class DifyConfigView(BaseModel):
    """返回给前端（不显示明文 key）"""
    api_url: str
    is_api_key_set: bool
    workflow_text2img: str
    workflow_img2img: str
    workflow_inpaint: str
    workflow_upload_edit: str
    default_timeout: float


class DifyConfigUpdate(BaseModel):
    api_url: Optional[str] = None
    app_api_key: Optional[str] = None
    workflow_text2img: Optional[str] = None
    workflow_img2img: Optional[str] = None
    workflow_inpaint: Optional[str] = None
    workflow_upload_edit: Optional[str] = None
    default_timeout: Optional[float] = None


class DegradationConfigView(BaseModel):
    enabled: bool
    failure_threshold: int
    degrade_duration_seconds: int
    current_status: str              # "normal" / "degraded"
    degraded_until: Optional[datetime] = None
    failure_count: int


class DegradationConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    failure_threshold: Optional[int] = None
    degrade_duration_seconds: Optional[int] = None


class RetentionConfigView(BaseModel):
    mode: str
    n_days: int
    cleanup_cron: str
    total_oss_keys: Optional[int] = None
    total_oss_bytes: Optional[int] = None


class RetentionConfigUpdate(BaseModel):
    mode: Optional[str] = None
    n_days: Optional[int] = None
    cleanup_cron: Optional[str] = None
```

- [ ] **Step 2: 验证导入**

```bash
cd backend
python -c "from app.schemas.image_generation import Text2ImgRequest; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/image_generation.py
git commit -m "feat(image-gen): 添加 Pydantic schemas"
```

### Task 1.5: Alembic 迁移

- [ ] **Step 1: 检查项目是否用 Alembic**

```bash
ls backend/alembic/ 2>/dev/null || echo "no alembic"
ls backend/migrations/ 2>/dev/null || echo "no migrations"
```

如果项目用 `SQLAlchemy.create_all()` 自动建表（查看 `backend/app/main.py` 或 `db/` 初始化代码），跳过此任务，直接跳到验证步骤。

如果项目用 Alembic：

```bash
cd backend
alembic revision --autogenerate -m "add image generation tables"
alembic upgrade head
```

如果项目用 SQLAlchemy `create_all()`：

```bash
cd backend
python -c "
from app.db.database import engine
from app.models.image_generation_models import Base
Base.metadata.create_all(bind=engine)
print('tables created')
"
```

- [ ] **Step 2: 验证 5 张表存在**

```bash
cd backend
python -c "
from sqlalchemy import inspect
from app.db.database import engine
insp = inspect(engine)
expected = ['image_gen_quota', 'image_gen_history', 'image_gen_dify_config', 'image_gen_degradation_config', 'image_gen_retention_config']
for t in expected:
    print(f'{t}: {t in insp.get_table_names()}')
"
```

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/xxxx_add_image_generation_tables.py  # 如果用 Alembic
git commit -m "feat(image-gen): 数据库迁移 - 5 张新表"
```

**Phase 1 验收标准**：
- ✅ `settings.DIFY_API_URL` 可读取
- ✅ 常量模块可导入
- ✅ 5 张 DB 表已创建（通过 SQL 或 inspect 验证）
- ✅ 所有 models 和 schemas 可加载

---

## Phase 1.5: 大模型配置重构（v1 必需，见 spec §16）

**目标**：把现有扁平 `llm_configs` 表拆为 `llm_providers` + `llm_models`，Alembic 迁移现有数据，4 个消费方改读新表，前端 LLMConfigsPage 拆为 2 tabs。

**Files:**
- Create: `backend/app/models/llm_provider.py`
- Create: `backend/app/models/llm_model.py`
- Modify: `backend/app/models/__init__.py`（导出新 models）
- Modify: `backend/app/models/llm_config.py`（头部加 DEPRECATED 注释）
- Create: `backend/alembic/versions/xxxx_split_llm_configs_into_providers_and_models.py`
- Create: `backend/app/services/llm_provider_service.py`
- Create: `backend/app/services/llm_model_service.py`
- Modify: `backend/app/services/llm_fallback.py`（改读 LLMModel+provider）
- Modify: `backend/app/services/agent_service.py`
- Modify: `backend/app/api/routes/chat_stream.py`
- Modify: `backend/app/api/routes/conversations.py`
- Create: `backend/app/api/routes/admin_llm_providers.py`
- Create: `backend/app/api/routes/admin_llm_models.py`
- Modify: `frontend/src/components/Admin/LLMConfigsPage.tsx`（拆 2 tabs）
- Create: `frontend/src/components/Admin/LLMConfigs/ProvidersTab.tsx`
- Create: `frontend/src/components/Admin/LLMConfigs/ModelsTab.tsx`
- Create: `frontend/src/components/Admin/LLMConfigs/ProviderDialog.tsx`
- Create: `frontend/src/components/Admin/LLMConfigs/ModelDialog.tsx`
- Modify: `frontend/src/components/Admin/LLMStats.tsx`（更新统计维度）
- Create: `frontend/src/services/llmProviderApi.ts`
- Create: `frontend/src/services/llmModelApi.ts`
- Tests: `backend/tests/test_llm_provider_service.py`, `test_llm_model_service.py`, `test_llm_config_migration.py`

**Consumes:** Phase 1（DB + models 基础）
**Produces:** `LLMProviderService` / `LLMModelService` / 2 个前端 tabs / 4 个消费方改读新表

### Task 1.5.1: 新建 LLMProvider / LLMModel models + Alembic 迁移

- [ ] **Step 1: 创建 `backend/app/models/llm_provider.py`**

```python
"""大模型供应商 model（spec §16.3）"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base


class LLMProvider(Base):
    __tablename__ = "llm_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    provider_type = Column(String(50), nullable=False)  # openai/anthropic/azure_openai/baidu/aliyun/doubao_seedream/qwen_image/other
    base_url = Column(String(500), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    api_key_suffix = Column(String(4), nullable=True)
    notes = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
```

- [ ] **Step 2: 创建 `backend/app/models/llm_model.py`**

```python
"""大模型 model（spec §16.3）"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class LLMModel(Base):
    __tablename__ = "llm_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    model_name = Column(String(100), nullable=False)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("llm_providers.id"), nullable=False, index=True)
    request_params = Column(Text, nullable=True)  # JSON 字符串
    category = Column(String(20), nullable=False, default="chat", index=True)
    is_default = Column(Boolean, nullable=False, default=False, index=True)
    is_default_for_category = Column(Boolean, nullable=False, default=False)
    notes = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    provider = relationship("LLMProvider", lazy="joined")
```

- [ ] **Step 3: 在 `backend/app/models/__init__.py` 导出**

```python
from .llm_provider import LLMProvider  # noqa
from .llm_model import LLMModel  # noqa
```

- [ ] **Step 4: 标记 `llm_config.py` deprecated**

文件头部加：
```python
"""
LLM 配置 model - DEPRECATED

v1 起请使用 LLMProvider + LLMModel（见 backend/app/models/llm_provider.py 和 llm_model.py）。
保留本表仅用于回滚过渡。
"""
```

- [ ] **Step 5: 生成 Alembic 迁移**

```bash
cd backend
alembic revision -m "split llm_configs into providers and models"
```

生成的迁移文件编辑内容（关键步骤）：

```python
"""split llm_configs into providers and models

Revision ID: xxxx
Revises: <previous_revision>
Create Date: ...
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = 'xxxx'
down_revision = '<previous_revision>'

def upgrade():
    # 1. 建新表
    op.create_table(
        'llm_providers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('provider_type', sa.String(50), nullable=False),
        sa.Column('base_url', sa.String(500), nullable=False),
        sa.Column('api_key_encrypted', sa.Text, nullable=False),
        sa.Column('api_key_suffix', sa.String(4), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_table(
        'llm_models',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('provider_id', UUID(as_uuid=True), sa.ForeignKey('llm_providers.id'), nullable=False),
        sa.Column('request_params', sa.Text, nullable=True),
        sa.Column('category', sa.String(20), nullable=False, server_default='chat'),
        sa.Column('is_default', sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column('is_default_for_category', sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index('idx_llm_models_provider_id', 'llm_models', ['provider_id'])
    op.create_index('idx_llm_models_category', 'llm_models', ['category'])
    op.create_index('idx_llm_models_is_default', 'llm_models', ['is_default'])

    # 2. Backfill providers（按 4 字段 GROUP BY）
    op.execute("""
        INSERT INTO llm_providers (id, name, provider_type, base_url, api_key_encrypted, api_key_suffix, is_active, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            'Migrated: ' || provider_type || '-' || COALESCE(api_key_suffix, '????'),
            provider_type,
            base_url,
            api_key_encrypted,
            api_key_suffix,
            is_active,
            MIN(created_at),
            MIN(updated_at)
        FROM llm_configs
        GROUP BY provider_type, base_url, api_key_encrypted, api_key_suffix, is_active
    """)

    # 3. Backfill models
    op.execute("""
        INSERT INTO llm_models (id, name, model_name, provider_id, request_params, category, is_default, is_active, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            c.name,
            c.model_name,
            p.id,
            c.request_params::text,
            c.category,
            c.is_default,
            c.is_active,
            c.created_at,
            c.updated_at
        FROM llm_configs c
        JOIN llm_providers p
          ON c.provider_type = p.provider_type
         AND c.base_url = p.base_url
         AND c.api_key_encrypted = p.api_key_encrypted
         AND COALESCE(c.api_key_suffix, '') = COALESCE(p.api_key_suffix, '')
    """)

    # 4. 标记 llm_configs deprecated（保留数据）
    op.execute("COMMENT ON TABLE llm_configs IS 'DEPRECATED: see llm_providers + llm_models'")


def downgrade():
    op.execute("DELETE FROM llm_models")
    op.execute("DELETE FROM llm_providers")
    op.drop_index('idx_llm_models_is_default', table_name='llm_models')
    op.drop_index('idx_llm_models_category', table_name='llm_models')
    op.drop_index('idx_llm_models_provider_id', table_name='llm_models')
    op.drop_table('llm_models')
    op.drop_table('llm_providers')
```

- [ ] **Step 6: 跑迁移**

```bash
cd backend
alembic upgrade head
```

- [ ] **Step 7: 验证 backfill 正确**

```bash
cd backend
python -c "
from app.db.database import SessionLocal
from sqlalchemy import text
with SessionLocal() as db:
    n_old = db.execute(text('SELECT COUNT(*) FROM llm_configs')).scalar()
    n_providers = db.execute(text('SELECT COUNT(*) FROM llm_providers')).scalar()
    n_models = db.execute(text('SELECT COUNT(*) FROM llm_models')).scalar()
    print(f'老配置: {n_old}, 新供应商: {n_providers}, 新模型: {n_models}')
"
```

期望：`新模型 == 老配置`，`新供应商 <= 老配置`（按 Key 去重）。

- [ ] **Step 8: 写迁移测试 `backend/tests/test_llm_config_migration.py`**

```python
"""验证迁移正确性：构造 3 条老配置（2 条共用 Key），跑迁移，断言供应商去重 + 模型全量"""
import pytest
from sqlalchemy import text
from app.models.llm_config import LLMConfig
from app.core.security import encrypt_api_key


def test_migration_dedupes_providers(db_session):
    # 构造 3 条老配置：2 条共享同一 API key
    same_key = encrypt_api_key("sk-same123")
    db_session.add_all([
        LLMConfig(name="A", provider_type="openai", base_url="https://api.openai.com/v1",
                  api_key_encrypted=same_key, api_key_suffix="3123", model_name="gpt-4o",
                  category="chat", is_active=True),
        LLMConfig(name="B", provider_type="openai", base_url="https://api.openai.com/v1",
                  api_key_encrypted=same_key, api_key_suffix="3123", model_name="gpt-4o-mini",
                  category="chat", is_active=True),
        LLMConfig(name="C", provider_type="openai", base_url="https://api.openai.com/v1",
                  api_key_encrypted=encrypt_api_key("sk-diff999"), api_key_suffix="d999",
                  model_name="o1", category="chat", is_active=True),
    ])
    db_session.commit()

    # 跑迁移（调用 alembic upgrade 或者手动 SQL）
    from alembic.config import Config
    from alembic import command
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    # 验证
    n_providers = db_session.execute(text("SELECT COUNT(*) FROM llm_providers")).scalar()
    n_models = db_session.execute(text("SELECT COUNT(*) FROM llm_models")).scalar()
    assert n_providers == 2  # 去重后 2 个供应商
    assert n_models == 3      # 3 条模型
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/llm_provider.py backend/app/models/llm_model.py backend/app/models/__init__.py backend/app/models/llm_config.py backend/alembic/versions/xxxx_split_llm_configs_into_providers_and_models.py backend/tests/test_llm_config_migration.py
git commit -m "feat(llm): 拆分 llm_configs 为 llm_providers + llm_models，含数据迁移"
```

### Task 1.5.2: 消费方迁移（4 个文件）

- [ ] **Step 1: 改 `backend/app/services/llm_fallback.py`**

原 `_get_available_configs()` 改读 `LLMModel` + `LLMProvider`：

```python
def _get_available_models(self, primary_model_id=None):
    """获取可用模型列表（按优先级排序）"""
    from app.models.llm_model import LLMModel
    from app.models.llm_provider import LLMProvider
    from sqlalchemy.orm import joinedload

    query = self.db.query(LLMModel).options(joinedload(LLMModel.provider)).filter(LLMModel.is_active == True, LLMProvider.is_active == True)
    if primary_model_id:
        primary = query.filter(LLMModel.id == primary_model_id).first()
        if primary:
            others = query.filter(LLMModel.id != primary_model_id).all()
            return [primary] + others
    return query.all()
```

循环逻辑保持不变，只把 `config.provider_type/api_key/base_url/model_name/request_params` 替换成 `model.provider.provider_type / model.provider.api_key / model.provider.base_url / model.model_name / model.request_params`。

- [ ] **Step 2: 改 `agent_service.py` / `chat_stream.py` / `conversations.py`**

按相同模式：把 `LLMConfig` 读改成 `LLMModel + LLMProvider` join 读。函数签名不变（保持外部接口稳定）。

- [ ] **Step 3: 跑现有 chat 相关测试，确认行为不变**

```bash
cd backend
pytest tests/test_chat_stream.py tests/test_agent_service.py -v
```

期望：所有测试通过（接口语义未变）。

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/llm_fallback.py backend/app/services/agent_service.py backend/app/api/routes/chat_stream.py backend/app/api/routes/conversations.py
git commit -m "refactor(llm): 4 个消费方改读 LLMProvider + LLMModel"
```

### Task 1.5.3: 新建 LLMProviderService / LLMModelService

- [ ] **Step 1: 写失败测试 `backend/tests/test_llm_provider_service.py`**

```python
import pytest
from app.services.llm_provider_service import LLMProviderService
from app.services.llm_model_service import LLMModelService


def test_create_and_list_provider(db_session):
    svc = LLMProviderService(db_session)
    p = svc.create_provider(name="OpenAI", provider_type="openai",
                            base_url="https://api.openai.com/v1", api_key="sk-xxx")
    assert p.id is not None
    assert svc.list_providers()[0].name == "OpenAI"


def test_delete_provider_with_linked_models_fails(db_session):
    """有模型关联时不允许删除"""
    p_svc = LLMProviderService(db_session)
    m_svc = LLMModelService(db_session)
    p = p_svc.create_provider(name="X", provider_type="openai",
                              base_url="https://api.openai.com/v1", api_key="sk-x")
    m_svc.create_model(name="gpt-4o", model_name="gpt-4o", provider_id=p.id, category="chat")
    with pytest.raises(ValueError, match="存在关联模型"):
        p_svc.delete_provider(p.id)


def test_get_default_model_by_category(db_session):
    p_svc = LLMProviderService(db_session)
    m_svc = LLMModelService(db_session)
    p = p_svc.create_provider(name="Y", provider_type="openai",
                              base_url="https://api.openai.com/v1", api_key="sk-y")
    m = m_svc.create_model(name="polish", model_name="qwen-turbo", provider_id=p.id,
                           category="image_polish", is_default_for_category=True)
    found = m_svc.get_default_model("image_polish")
    assert found.id == m.id
```

- [ ] **Step 2: 跑测试，确认失败**

```bash
cd backend
pytest tests/test_llm_provider_service.py -v
```
预期：`ModuleNotFoundError`

- [ ] **Step 3: 实现 `backend/app/services/llm_provider_service.py`**

```python
"""供应商服务（spec §16.5）"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.llm_provider import LLMProvider
from app.core.security import encrypt_api_key, decrypt_api_key
from app.services.llm.factory import get_provider


class LLMProviderService:
    def __init__(self, db: Session):
        self.db = db

    def list_providers(self, active_only: bool = False) -> List[LLMProvider]:
        q = self.db.query(LLMProvider)
        if active_only:
            q = q.filter(LLMProvider.is_active == True)
        return q.all()

    def get_provider(self, provider_id: str) -> Optional[LLMProvider]:
        return self.db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()

    def create_provider(self, name, provider_type, base_url, api_key, notes=None, is_active=True) -> LLMProvider:
        p = LLMProvider(
            name=name, provider_type=provider_type, base_url=base_url,
            api_key_encrypted=encrypt_api_key(api_key),
            api_key_suffix=api_key[-4:] if len(api_key) >= 4 else api_key,
            notes=notes, is_active=is_active,
        )
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p

    def update_provider(self, provider_id, **kwargs) -> Optional[LLMProvider]:
        p = self.get_provider(provider_id)
        if not p:
            return None
        if "api_key" in kwargs:
            api_key = kwargs.pop("api_key")
            kwargs["api_key_encrypted"] = encrypt_api_key(api_key)
            kwargs["api_key_suffix"] = api_key[-4:] if len(api_key) >= 4 else api_key
        for k, v in kwargs.items():
            if hasattr(p, k):
                setattr(p, k, v)
        self.db.commit()
        self.db.refresh(p)
        return p

    def delete_provider(self, provider_id) -> bool:
        from app.models.llm_model import LLMModel
        linked = self.db.query(LLMModel).filter(LLMModel.provider_id == provider_id).count()
        if linked > 0:
            raise ValueError(f"存在关联模型 {linked} 条，请先删除/迁移")
        p = self.get_provider(provider_id)
        if not p:
            return False
        self.db.delete(p)
        self.db.commit()
        return True

    def test_connection(self, provider_id) -> Tuple[bool, str, int]:
        p = self.get_provider(provider_id)
        if not p:
            return False, "供应商不存在", 0
        try:
            api_key = decrypt_api_key(p.api_key_encrypted)
        except Exception as e:
            return False, f"API Key 解密失败: {e}", 0
        import time
        try:
            provider = get_provider(p.provider_type, api_key, p.base_url, "test-model")
            start = time.time()
            ok, err = await provider.test_connection()  # 注意：get_provider 是同步，test_connection 异步
            latency = int((time.time() - start) * 1000)
            return ok, err, latency
        except Exception as e:
            return False, str(e), 0

    def reveal_api_key(self, provider_id) -> Optional[str]:
        p = self.get_provider(provider_id)
        if not p:
            return None
        return decrypt_api_key(p.api_key_encrypted)
```

注意：上面的 `test_connection` 在 async 上下文需要用 `async def`。请按项目实际模式调整（同步测试或异步测试）。

- [ ] **Step 4: 实现 `backend/app/services/llm_model_service.py`**

```python
"""模型服务（spec §16.5）"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.llm_model import LLMModel
from app.models.llm_provider import LLMProvider


class LLMModelService:
    def __init__(self, db: Session):
        self.db = db

    def list_models(self, category=None, provider_id=None, active_only=False) -> List[LLMModel]:
        q = self.db.query(LLMModel)
        if active_only:
            q = q.filter(LLMModel.is_active == True)
        if category:
            q = q.filter(LLMModel.category == category)
        if provider_id:
            q = q.filter(LLMModel.provider_id == provider_id)
        return q.all()

    def get_model(self, model_id) -> Optional[LLMModel]:
        return self.db.query(LLMModel).filter(LLMModel.id == model_id).first()

    def get_default_model(self, category=None) -> Optional[LLMModel]:
        q = self.db.query(LLMModel).filter(LLMModel.is_active == True)
        if category:
            q = q.filter(and_(LLMModel.category == category,
                              LLMModel.is_default_for_category == True))
        else:
            q = q.filter(LLMModel.is_default == True)
        return q.first()

    def create_model(self, name, model_name, provider_id, request_params=None,
                     category="chat", is_default=False, is_default_for_category=False,
                     notes=None, is_active=True) -> LLMModel:
        m = LLMModel(
            name=name, model_name=model_name, provider_id=provider_id,
            request_params=request_params, category=category,
            is_default=is_default, is_default_for_category=is_default_for_category,
            notes=notes, is_active=is_active,
        )
        if is_default:
            self._unset_default_models()
        if is_default_for_category:
            self._unset_category_defaults(category)
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return m

    def update_model(self, model_id, **kwargs) -> Optional[LLMModel]:
        m = self.get_model(model_id)
        if not m:
            return None
        if kwargs.get("is_default"):
            self._unset_default_models()
        if kwargs.get("is_default_for_category"):
            self._unset_category_defaults(m.category)
        for k, v in kwargs.items():
            if hasattr(m, k):
                setattr(m, k, v)
        self.db.commit()
        self.db.refresh(m)
        return m

    def delete_model(self, model_id) -> bool:
        m = self.get_model(model_id)
        if not m:
            return False
        self.db.delete(m)
        self.db.commit()
        return True

    def set_default(self, model_id, category=None) -> bool:
        m = self.get_model(model_id)
        if not m:
            return False
        if category:
            self._unset_category_defaults(category)
            m.is_default_for_category = True
            m.category = category
        else:
            self._unset_default_models()
            m.is_default = True
        self.db.commit()
        return True

    def _unset_default_models(self):
        self.db.query(LLMModel).filter(LLMModel.is_default == True).update({"is_default": False})
        self.db.commit()

    def _unset_category_defaults(self, category):
        self.db.query(LLMModel).filter(
            LLMModel.category == category, LLMModel.is_default_for_category == True
        ).update({"is_default_for_category": False})
        self.db.commit()
```

- [ ] **Step 5: 跑测试，确认通过**

```bash
cd backend
pytest tests/test_llm_provider_service.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/llm_provider_service.py backend/app/services/llm_model_service.py backend/tests/test_llm_provider_service.py
git commit -m "feat(llm): LLMProviderService + LLMModelService"
```

### Task 1.5.4: 管理 API + 前端 UI 重构

- [ ] **Step 1: 创建 `backend/app/api/routes/admin_llm_providers.py`**

端点：`GET/POST /admin/llm-providers`, `GET/PUT/DELETE /admin/llm-providers/{id}`, `POST /admin/llm-providers/{id}/test`, `POST /admin/llm-providers/{id}/reveal`

按项目现有 admin 路由模式（鉴权中间件 + JSON body）实现，调用 `LLMProviderService` 对应方法。

- [ ] **Step 2: 创建 `backend/app/api/routes/admin_llm_models.py`**

端点：`GET/POST /admin/llm-models`, `GET/PUT/DELETE /admin/llm-models/{id}`, `POST /admin/llm-models/{id}/set-default`

- [ ] **Step 3: 注册路由到 `backend/app/api/router.py`**

```python
from app.api.routes.admin_llm_providers import router as admin_llm_providers_router
from app.api.routes.admin_llm_models import router as admin_llm_models_router

api_router.include_router(admin_llm_providers_router, prefix="/api", tags=["admin-llm-providers"])
api_router.include_router(admin_llm_models_router, prefix="/api", tags=["admin-llm-models"])
```

- [ ] **Step 4: 创建 `frontend/src/services/llmProviderApi.ts` + `llmModelApi.ts`**

按 spec §16.8 端点封装 fetch 调用。

- [ ] **Step 5: 重构 `frontend/src/components/Admin/LLMConfigsPage.tsx`**

从单列表 → 顶部 2 tabs：
- 引入 `ProvidersTab` + `ModelsTab`
- 移除原 `ConfigModal` 引用

```tsx
import { Tabs } from 'antd';
import ProvidersTab from './LLMConfigs/ProvidersTab';
import ModelsTab from './LLMConfigs/ModelsTab';

export default function LLMConfigsPage() {
  return (
    <Tabs
      items={[
        { key: 'providers', label: '模型供应商', children: <ProvidersTab /> },
        { key: 'models', label: '模型配置', children: <ModelsTab /> },
      ]}
    />
  );
}
```

- [ ] **Step 6: 实现 `ProvidersTab.tsx`**

- 表格：名称 / 厂商 / base URL / key 末4 / 启用 / 操作
- 「新建供应商」按钮 → 打开 `ProviderDialog`
- 操作列：编辑 / 测试连通性 / 显示 Key / 删除

- [ ] **Step 7: 实现 `ModelsTab.tsx`**

- 表格：名称 / model_name / 供应商 / category / 默认 / 启用 / 操作
- 「新建模型」按钮 → 打开 `ModelDialog`（含 provider 下拉 + category + 默认开关）
- 操作列：编辑 / 设为默认 / 删除

- [ ] **Step 8: 更新 `frontend/src/components/Admin/LLMStats.tsx`**

统计维度改为按 `provider_type` / `category` 聚合。

- [ ] **Step 9: i18n 更新**

`frontend/src/i18n/locales/zh-CN.ts` + `en-US.ts` 新增 `llm.providersTab` / `llm.modelsTab` 等 key。

- [ ] **Step 10: 前端测试**

```bash
cd frontend
npm run test
```

- [ ] **Step 11: Commit**

```bash
git add backend/app/api/routes/admin_llm_providers.py backend/app/api/routes/admin_llm_models.py backend/app/api/router.py frontend/src/services/llmProviderApi.ts frontend/src/services/llmModelApi.ts frontend/src/components/Admin/LLMConfigsPage.tsx frontend/src/components/Admin/LLMConfigs/ frontend/src/components/Admin/LLMStats.tsx frontend/src/i18n/locales/zh-CN.ts frontend/src/i18n/locales/en-US.ts
git commit -m "feat(llm): 2 tabs UI + provider/model 管理 API"
```

**Phase 1.5 验收标准**：
- ✅ `llm_providers` + `llm_models` 表已建，老数据已迁移
- ✅ 老 LLMConfig 数据 0 丢失（去重后供应商数 ≤ 老配置数，模型数 == 老配置数）
- ✅ `LLMProviderService` / `LLMModelService` CRUD 全可用
- ✅ 4 个老消费方（llm_fallback / agent_service / chat_stream / conversations）改读新表，行为不变
- ✅ 前端 LLMConfigsPage 拆为 2 tabs
- ✅ 新增 / 编辑 / 删除供应商 + 模型 UI 全可用

---

## Phase 2: DifyConfigService（分层配置管理）

**Files:**
- Create: `backend/app/services/dify_config_service.py`
- Create: `backend/tests/test_dify_config_service.py`

**Consumes:** Phase 1 (models + env vars)
**Produces:** `DifyConfigService` 单例，方法 `get_config() / update_config() / get_config_view() / test_connection()`

### Task 2.1: TDD - get_config 读取分层配置

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_dify_config_service.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from app.services.dify_config_service import DifyConfigService, DifyConfig


@pytest.fixture
def svc():
    return DifyConfigService()


@pytest.mark.asyncio
async def test_get_config_uses_db_when_set(svc, db_session):
    """DB 覆盖优先于 .env"""
    # 预置 DB 配置（mock 加密）
    from app.models.image_generation_models import ImageGenDifyConfig
    db_session.add(ImageGenDifyConfig(key="api_url", value_encrypted="<encrypted>https://db.example.com/v1</encrypted>"))
    db_session.commit()

    # mock 解密
    with patch.object(svc, "_decrypt", return_value="https://db.example.com/v1"):
        cfg = await svc.get_config()
    assert cfg.api_url == "https://db.example.com/v1"


@pytest.mark.asyncio
async def test_get_config_falls_back_to_env(svc):
    """DB 未配置时回退 .env"""
    from app.config.config import settings
    settings.DIFY_API_URL = "https://env.example.com/v1"
    cfg = await svc.get_config()
    assert cfg.api_url == "https://env.example.com/v1"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend
pytest tests/test_dify_config_service.py -v
```
预期：`ModuleNotFoundError: app.services.dify_config_service`

- [ ] **Step 3: 实现 `backend/app/services/dify_config_service.py`**

```python
"""Dify 配置服务 - 分层（DB 覆盖 .env）"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.config import settings
from app.models.image_generation_models import ImageGenDifyConfig
from app.utils.crypto import encrypt_str, decrypt_str  # 复用现有加密工具（如有）

logger = logging.getLogger(__name__)


@dataclass
class DifyConfig:
    api_url: str
    app_api_key: str
    workflow_text2img: str
    workflow_img2img: str
    workflow_inpaint: str
    workflow_upload_edit: str
    default_timeout: float


class DifyConfigService:
    """配置优先级：DB > .env"""

    def __init__(self, db: Optional[Session] = None):
        self._db = db

    async def get_config(self) -> DifyConfig:
        db_cfg = await self._load_db_config()
        return DifyConfig(
            api_url=db_cfg.get("api_url") or settings.DIFY_API_URL,
            app_api_key=db_cfg.get("app_api_key") or settings.DIFY_APP_API_KEY,
            workflow_text2img=db_cfg.get("workflow_text2img") or settings.DIFY_WORKFLOW_TEXT2IMG,
            workflow_img2img=db_cfg.get("workflow_img2img") or settings.DIFY_WORKFLOW_IMG2IMG,
            workflow_inpaint=db_cfg.get("workflow_inpaint") or settings.DIFY_WORKFLOW_INPAINT,
            workflow_upload_edit=db_cfg.get("workflow_upload_edit") or settings.DIFY_WORKFLOW_UPLOAD_EDIT,
            default_timeout=float(db_cfg.get("default_timeout") or settings.DIFY_DEFAULT_TIMEOUT),
        )

    async def _load_db_config(self) -> Dict[str, str]:
        if not self._db:
            from app.db.database import SessionLocal
            with SessionLocal() as db:
                return await self._load_db_config_from_session(db)
        return await self._load_db_config_from_session(self._db)

    async def _load_db_config_from_session(self, db: Session) -> Dict[str, str]:
        result = {}
        rows = (await db.execute(select(ImageGenDifyConfig))).scalars().all()
        for row in rows:
            try:
                result[row.key] = decrypt_str(row.value_encrypted)
            except Exception as e:
                logger.error(f"[image-gen-config] 解密失败 key={row.key}: {e}")
        return result

    async def update_config(self, partial: dict, updated_by: str) -> None:
        """更新 DB 配置（部分更新）"""
        from app.db.database import SessionLocal
        with SessionLocal() as db:
            for key, value in partial.items():
                if value is None:
                    continue
                encrypted = encrypt_str(str(value))
                existing = (await db.execute(
                    select(ImageGenDifyConfig).where(ImageGenDifyConfig.key == key)
                )).scalar_one_or_none()
                if existing:
                    existing.value_encrypted = encrypted
                    existing.updated_by = updated_by
                else:
                    db.add(ImageGenDifyConfig(
                        key=key, value_encrypted=encrypted, updated_by=updated_by
                    ))
            await db.commit()

    async def get_config_view(self) -> dict:
        """返回给前端（不显示明文 key）"""
        cfg = await self.get_config()
        return {
            "api_url": cfg.api_url,
            "is_api_key_set": bool(cfg.app_api_key),
            "workflow_text2img": cfg.workflow_text2img,
            "workflow_img2img": cfg.workflow_img2img,
            "workflow_inpaint": cfg.workflow_inpaint,
            "workflow_upload_edit": cfg.workflow_upload_edit,
            "default_timeout": cfg.default_timeout,
        }

    async def test_connection(self) -> tuple:
        """测试 Dify 连通性"""
        cfg = await self.get_config()
        if not cfg.api_url or not cfg.app_api_key:
            return False, "配置不完整"
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{cfg.api_url}/info",
                    headers={"Authorization": f"Bearer {cfg.app_api_key}"}
                )
                if resp.status_code == 200:
                    return True, "连接成功"
                return False, f"HTTP {resp.status_code}"
        except Exception as e:
            return False, str(e)
```

注意：需要检查 `app/utils/crypto.py` 是否存在 `encrypt_str/decrypt_str`。如果不存在，用 `cryptography.fernet` 自行实现（用 `DB_ENCRYPTION_KEY`）。

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend
pytest tests/test_dify_config_service.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/dify_config_service.py backend/tests/test_dify_config_service.py
git commit -m "feat(image-gen): DifyConfigService 分层配置"
```

**Phase 2 验收**：
- ✅ `get_config()` 能从 DB 读配置（覆盖 .env）
- ✅ `get_config()` 回退到 .env 默认
- ✅ `update_config()` 加密存储到 DB
- ✅ `get_config_view()` 不暴露明文 API key
- ✅ `test_connection()` 调 Dify `/info` 验证连通

---

## Phase 3: DifyClient

**核心要点：**
- 使用 `httpx.AsyncClient`，每次调用从 `DifyConfigService.get_config()` 读配置
- 4 个方法 `run_text2img/run_img2img/run_inpaint/run_upload_edit`
- 都 POST 到 `{api_url}/workflows/run`，body: `{inputs, response_mode: "blocking", user: user_id}`
- 解析响应：从 `outputs` 字段取 `image_urls` / `model_used`
- 错误处理：HTTP 异常 / 工作流 failed / 超时 → 抛 `DifyError`
- 测试：Mock httpx，验证请求体、超时、错误处理

**关键接口定义（Phase 5+ 依赖）：**

```python
# backend/app/services/dify_client.py

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class DifyRunResult:
    image_urls: List[str]
    model_used: str
    raw_response: Dict[str, Any]
    elapsed_seconds: float


class DifyError(Exception):
    """Dify 调用错误（含分类）"""
    def __init__(self, message: str, kind: str = "unknown"):
        super().__init__(message)
        self.kind = kind  # "http_error" / "workflow_failed" / "timeout" / "parse_error" / "config_error"


class DifyClient:
    def __init__(self, config_svc: Optional[DifyConfigService] = None):
        self._config_svc = config_svc or DifyConfigService()

    async def run_text2img(
        self, prompt: str, size: str, n: int,
        style: Optional[str], model_preference: str,
        user_id: str, timeout: Optional[float] = None,
    ) -> DifyRunResult: ...

    async def run_img2img(
        self, prompt: str, reference_url: str, strength: float,
        size: str, model_preference: str,
        user_id: str, timeout: Optional[float] = None,
    ) -> DifyRunResult: ...

    async def run_inpaint(
        self, prompt: str, image_url: str, mask_url: str,
        size: str, model_preference: str,
        user_id: str, timeout: Optional[float] = None,
    ) -> DifyRunResult: ...

    async def run_upload_edit(
        self, image_url: str, edit_type: str,
        prompt: Optional[str],
        user_id: str, timeout: Optional[float] = None,
    ) -> DifyRunResult: ...

    async def test_connection(self) -> tuple[bool, str]: ...
```

**Files:**
- Create: `backend/app/services/dify_client.py`
- Create: `backend/tests/test_dify_client.py`

### Phase 4: QuotaService

**核心要点：**
- `check_and_reserve`: `SELECT FOR UPDATE` 锁行 → 校验有效期 → 校验余额 → 递增 counter
- `commit`: 事务提交
- `release`: 事务回滚（`db.rollback()`）
- 管理员方法：`grant/revoke/reset_counters/list_users/get_user_quota`
- 重置日期逻辑：`daily_reset_date` 不是今天则重置 daily_used=0 并更新 reset_date
- 测试：并发 100 请求验证不超限；有效期边界；有效期过期拒绝

**文件：**
- Create: `backend/app/services/image_gen_quota_service.py`
- Create: `backend/tests/test_image_gen_quota_service.py`

### Phase 5: ImageGenService + HistoryService

**核心要点：**
- ImageGenService 编排：降级检查 → 配额预留 → 上传参考图 OSS → 生成签名 URL → 调 Dify → 下载结果 → 上传结果 OSS → 写历史 → 提交配额 → 重置降级计数
- 失败分支：释放配额 + 写 failed 历史 + 记录降级失败
- 取消分支（CancelledError）：释放配额 + 写 cancelled 历史
- HistoryService：CRUD + `cleanup_before` 供保留策略调用
- 测试：mock DifyClient / OSS / QuotaService，验证成功路径、Dify 失败路径、超时路径

**文件：**
- Create: `backend/app/services/image_generation_service.py`
- Create: `backend/app/services/image_gen_history_service.py`
- Create: `backend/tests/test_image_generation_service.py`

### Phase 6: 用户 API 路由

**核心要点：**
- 端点：`POST /image-generation/generate` (multipart), `POST /image-generation/polish-prompt`, `GET /image-generation/history`, `GET /image-generation/history/{id}`, `DELETE /image-generation/history/{id}`, `GET /image-generation/quota/me`, `GET /image-generation/result/{history_id}`
- 全部用 `Depends(get_current_user_id)` 鉴权
- generate 端点用 `UploadFile` 接收参考图/蒙版
- result 端点：返回新签名 URL，顺便更新 `last_accessed_at`
- 测试：FastAPI TestClient，验证鉴权、参数校验、响应格式

**文件：**
- Create: `backend/app/routes/image_generation.py`
- Create: `backend/tests/test_image_generation_routes.py`

### Phase 7: 管理 API 路由

**核心要点：**
- 端点：按 spec §7.2
- 需要管理员鉴权中间件（复用项目现有）
- config 更新用 `DifyConfigService.update_config()`
- degradation reset 调用 `DegradationService.reset()`
- retention trigger 直接调 `OssRetentionService.run_cleanup()`
- stats：聚合查询（按 model_used 分布、成功率、日调用量）
- 测试：FastAPI TestClient + 管理员 token

**文件：**
- Create: `backend/app/routes/admin_image_generation.py`
- Create: `backend/tests/test_admin_image_generation_routes.py`

### Phase 8: PromptPolisher

**核心要点：**
- 复用 `LLMFallbackService` + 新的 `LLMModelService` / `LLMProviderService`（见 Phase 1.5）
- 通过 `LLMModelService.get_default_model(category="image_polish")` 找到默认润色模型，不存在则兜底 `category="chat"` 的默认模型
- 从 `model.provider` 拿到 (provider_type, api_key, base_url, model_name)，调 `LLMFallbackService.generate_with_fallback`
- 系统提示：「你是图像生成提示词优化专家。根据用户目标 ({operation}) 优化以下提示词，使其更适合 {model_family} 类模型。返回英文版本。原始提示：{prompt}」
- 失败：返回原 prompt（不抛异常），写日志
- 测试：mock LLMModelService / LLMProviderService / LLMFallbackService，验证优化结果返回；失败时返回原值

**关键接口定义：**

```python
# backend/app/services/image_gen_prompt_polisher.py

from typing import Optional
from app.services.llm_model_service import LLMModelService
from app.services.llm_fallback import LLMFallbackService


class ImageGenPromptPolisher:
    def __init__(self, db, fallback_svc: Optional[LLMFallbackService] = None):
        self._model_svc = LLMModelService(db)
        self._fallback_svc = fallback_svc or LLMFallbackService(db)

    async def polish(
        self, prompt: str, user_id: str, target_operation: str = "text2img"
    ) -> str:
        """
        返回优化后的提示词。失败时返回原 prompt。
        """
        model = self._model_svc.get_default_model(category="image_polish")
        if not model:
            model = self._model_svc.get_default_model(category="chat")
        if not model:
            logger.warning("[image-gen-polish] 无可用默认模型，返回原提示词")
            return prompt

        provider = model.provider
        # 构造 system prompt
        system_msg = (
            f"你是图像生成提示词优化专家。根据用户目标 ({target_operation}) "
            f"优化以下提示词，使其更适合 {model.model_name} 类模型。"
            f"返回英文版本。原始提示：{prompt}"
        )

        try:
            result = await self._fallback_svc.generate_with_fallback(
                prompt=prompt,
                primary_config_id=str(model.id),  # 复用 llm_fallback 的接口（已支持）
                context=[{"role": "system", "content": system_msg}],
            )
            return result if result else prompt
        except Exception as e:
            logger.warning(f"[image-gen-polish] 润色失败: {e}")
            return prompt
```

**文件：**
- Create: `backend/app/services/image_gen_prompt_polisher.py`
- Create: `backend/tests/test_image_gen_prompt_polisher.py`

**注意**：Phase 8 依赖 Phase 1.5 完成的 `LLMModelService` 和 `LLMFallbackService`（已改读新表）。

### Phase 9: DegradationService

**核心要点：**
- 内存状态（不持久化）：`_failure_count`, `_degraded_until`
- `record_failure`: 计数 + 触发降级
- `record_success`: 重置 failure_count（不解除降级）
- `reset`: 手动解除降级
- `is_degraded`: 检查时间 + 自动解除
- 配置从 `DegradationConfigService` 读（DB 持久化，admin 可调）
- 测试：连续失败触发 → 时间到自动解除 → 手动 reset

**文件：**
- Create: `backend/app/services/degradation_service.py`
- Create: `backend/tests/test_degradation_service.py`

### Phase 10: OssRetentionService + 定时任务

**核心要点：**
- `run_cleanup`: 根据配置模式查询过期记录 → 删 OSS 文件 → 标记 `is_deleted=true`
- 定时任务：用 APScheduler 或 Celery Beat（项目已有 `token_usage_background_sync` 可参考其模式）
- 配置：从 DB 读，admin 可调
- 测试：mock OSS + DB，验证清理逻辑

**文件：**
- Create: `backend/app/services/oss_retention_service.py`
- Create: `backend/tests/test_oss_retention_service.py`
- Modify: `backend/app/main.py` (注册定时任务启动)

### Phase 11: 前端用户页面

**核心要点：**

1. **API 层** `frontend/src/api/imageGenerationApi.ts`:
   - `generate(formData)`, `polishPrompt(prompt, op)`, `getHistory(page, pageSize)`, `getHistoryDetail(id)`, `deleteHistory(id)`, `getMyQuota()`, `getResultUrl(historyId)`

2. **Store** `frontend/src/stores/imageGenerationStore.ts` (Zustand):
   - state: `operation`, `prompt`, `params`, `referenceImage`, `maskImage`, `currentResult`, `history`, `quota`, `loading`, `error`, `abortController`
   - actions: `setOperation`, `setPrompt`, `generate`, `abort`, `reset`, `polishPrompt`, `loadHistory`, `loadQuota`

3. **主组件** `ImageGeneration/index.tsx`:
   - 顶部 QuotaBadge
   - OperationTabs（4 个 tab）
   - 当前表单（按 operation 切换）
   - ResultPanel
   - HistoryDrawer 触发按钮

4. **表单组件** `forms/`:
   - `Text2ImgForm`: prompt + size + n + style + model_preference + 润色按钮
   - `Img2ImgForm`: + ImageUploader + strength slider
   - `InpaintForm`: + ImageUploader + MaskUploader（上传黑白图）
   - `UploadEditForm`: + ImageUploader + edit_type select + prompt

5. **公共组件** `components/`:
   - `ImageUploader`: drag-drop + preview + 10MB 校验
   - `MaskUploader`: drag-drop 黑白图
   - `ResultPanel`: 大图 + 下载 + "以此图为参考" + 删除
   - `HistoryDrawer`: 右侧抽屉 + 分页
   - `QuotaBadge`: 显示今日剩余

6. **路由注册**:
   - 修改 `frontend/src/App.tsx` 添加 `/tools/image-generation` 路由
   - 工具列表入口（查项目现有工具注册方式）

7. **Hooks**:
   - `useImageGenerate`: 封装 store 的 generate + abort
   - `useImageGenQuota`: 自动加载 + 30 秒刷新
   - `useImageGenHistory`: 分页 + 触发刷新

**测试**:
- vitest + React Testing Library: 表单渲染、上传校验、tabs 切换

### Phase 12: 前端管理页面

**核心要点：**

1. **API 层** `frontend/src/api/adminImageGenerationApi.ts`

2. **5 个 tab 组件**（在 `Admin/ImageGeneration/`）:
   - `UsageStats`: 总调用数 / 各模型分布 / 成功率 / 近 7 天图表
   - `DifyConfigPanel`: URL + 4 个 workflow id + 超时 + "测试连通性" 按钮
   - `DegradationConfigPanel`: 开关 + 阈值 + 时长 + 当前状态 + "手动解除" 按钮
   - `RetentionConfigPanel`: mode select + n_days + cron + OSS 用量 + "手动触发" 按钮
   - `UserQuotaTable`: 搜索 + 分页 + 编辑 / 分配 / 撤销 / 重置

3. **GrantQuotaDialog**: 分配配额的对话框（daily/monthly + valid_from + valid_until + notes）

4. **路由**: `/admin/image-generation` 注册到 admin 路由 + 菜单

### Phase 13: i18n + 集成测试 + 文档

**核心要点：**
- `frontend/src/i18n/locales/zh-CN.ts` 和 `en-US.ts` 新增 `imageGeneration` 命名空间
- 集成测试：真实后端 + 真实 Dify（如有）跑一遍 4 种 operation
- 更新 README（如果项目有）
- 编写 `docs/plans/2026-08-23-image-generation-tool-deployment-checklist.md`（部署清单）

---

## 任务依赖图（简化）

```
Phase 0 ─┐
         ├─▶ Phase 1 ─▶ Phase 1.5 ─┬─▶ Phase 2 ─�─▶ Phase 3 ─┐
         │            (LLM 拆分)    │            │            ├─▶ Phase 5 ─┬─▶ Phase 6 ─�─▶ Phase 11 ─┐
         │            │            │            │            │           │              │
         │            │            │            └─▶ Phase 4 ─┘           ├─▶ Phase 13
         │            │            │                                      │
         │            │            ├─▶ Phase 8 ──────────────────────────┤
         │            │            │                                      │
         │            │            ├─▶ Phase 9 ──────────────────────────┤
         │            │            │                                      │
         │            │            └─▶ Phase 10 ─────────────────────────┤
         │            │                                                   │
         │            └─▶ Phase 7 ──────────────────────────▶ Phase 12 ──┘
```

**关键依赖**：
- **Phase 1.5 必须在 Phase 2 之前**（其他工具的 LLM 消费方在 Phase 1.5.2 切换；Phase 8 引用 Phase 1.5.3 的新 LLMModelService）
- **Phase 1.5 是平台级重构**，可独立于图像生成 Phase 0 进行（但要在 Phase 1 之后）
- Phase 8（提示词润色）显式依赖 Phase 1.5 的 LLMModelService

---

## 风险与缓解（plan 级）

| 风险 | 缓解 |
|---|---|
| Phase 0 Dify 工作流创建复杂 | 先只做一个 text2img 跑通端到端，再复制到其他 3 个 |
| OSS 签名 URL 300s 不够 Dify 拉取 | 监控 Dify 日志，必要时延长到 600s |
| 并发配额竞态 | Phase 4 强制跑并发测试 |
| 前端组件数量多 | Phase 11 拆 3 个子任务：API+Store / 表单 / 公共组件 |
| Dify 响应 schema 与预期不符 | Phase 6 加详细日志，快速迭代 schema 解析 |

---

## 执行建议

1. **强推荐 Subagent-Driven 模式**：每个 phase 派一个 subagent，review 后再下一个
2. **Phase 0 必须用户本人完成**：Dify 后台操作无法自动化
3. **Phase 1 + 1.5 是基石**：必须先做 LLM 拆分，其他工具依赖新表
4. **Phase 1.5 拆 3 个 subagent**：建议 (a) models + 迁移，(b) 4 个消费方切换，(c) UI 重构
5. **Phase 11（前端用户）工作量最大**：建议拆 3 个 subagent（API+Store / 表单 / 公共组件）
6. **Phase 13 留足缓冲**：集成测试容易有坑
