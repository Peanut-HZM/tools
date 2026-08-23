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

## Phase 0: Dify 工作空间初始化（手动运维）

**目标**：让 Dify 具备 4 个可调用的工作流 + 1 个 App API Key

**执行人**：用户本人（需要 Dify 管理后台账号）

**前置条件**：
- Dify 管理员账号 `peanut_hzm@163.com`（密码自管）
- 至少一个图像生成模型的 API Key（豆包/通义万相/DALL-E 等）

**任务清单**：

- [ ] **Step 1: 登录 Dify**
  - 访问 `https://dify.peanuthzm.com.cn`
  - 用 `peanut_hzm@163.com` + 密码登录
  - 进入 "Dify Workspace"

- [ ] **Step 2: 配置模型供应商**
  - 进入 "工作室" → "模型供应商"
  - 添加至少 1 个图像生成模型（如阿里通义万相 / 豆包 / OpenAI）
  - 填入厂商 API Key
  - 测试连接成功

- [ ] **Step 3: 创建 text2img 工作流**
  - 新建应用 → 选 "工作流" → 命名 "text2img"
  - 配置 Start 节点：`prompt (string)`, `size (enum)`, `n (int)`, `style (enum optional)`, `model_preference (enum)`
  - 配置条件分支（按 model_preference 路由）
  - 配置 HTTP/工具节点调用图像模型
  - 配置 End 节点输出 `image_urls (array<string>)`, `model_used (string)`
  - 测试运行通过

- [ ] **Step 4: 创建 img2img / inpaint / upload_edit 工作流**
  - 按 spec §4.2-4.4 设计，逐个创建并测试

- [ ] **Step 5: 获取 App API Key**
  - 进入任一应用的 "访问 API" 页面
  - 生成 API Key，格式形如 `app-xxxxxxxxxxxx`
  - 记录 4 个 workflow 的 ID（在 URL 或应用设置里）

- [ ] **Step 6: 记录到 .env**
  - 在 `backend/.env` 增加：
    ```bash
    DIFY_API_URL=https://dify.peanuthzm.com.cn/v1
    DIFY_APP_API_KEY=app-xxxxxxxxxxxx
    DIFY_WORKFLOW_TEXT2IMG=wf_xxx
    DIFY_WORKFLOW_IMG2IMG=wf_yyy
    DIFY_WORKFLOW_INPAINT=wf_zzz
    DIFY_WORKFLOW_UPLOAD_EDIT=wf_aaa
    ```

- [ ] **Step 7: 测试 Dify API 可达**
  ```bash
  curl -X POST https://dify.peanuthzm.com.cn/v1/workflows/run \
    -H "Authorization: Bearer app-xxxxxxxxxxxx" \
    -H "Content-Type: application/json" \
    -d '{"inputs": {"prompt": "a cat", "size": "1024x1024", "n": 1, "model_preference": "auto"}, "response_mode": "blocking", "user": "test"}'
  ```
  期望：返回 JSON 包含 `task_id` 和 `workflow_run_id`

**验收标准**：
- ✅ 4 个工作流可独立运行
- ✅ 用 App API Key 能调通至少一个工作流
- ✅ `.env` 已配置

**预估工时**：2-4 小时

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
- 复用 `LLMFallbackService` + 现有 `LLMConfig` 表
- 寻找标签为 "image_gen_polish" 的 LLMConfig（不存在则用默认最小模型）
- 系统提示：「你是图像生成提示词优化专家。根据用户目标 ({operation}) 优化以下提示词，使其更适合 {model_family} 类模型。返回英文版本。原始提示：{prompt}」
- 失败：返回原 prompt（不抛异常）
- 测试：mock LLM，验证优化结果返回；失败时返回原值

**文件：**
- Create: `backend/app/services/image_gen_prompt_polisher.py`
- Create: `backend/tests/test_image_gen_prompt_polisher.py`

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
         ├─▶ Phase 1 ─┐
         │            ├─▶ Phase 2 ─┬─▶ Phase 3 ─┐
         │            │            │            ├─▶ Phase 5 ─┬─▶ Phase 6 ─┬─▶ Phase 11 ─┐
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
3. **Phase 1-3 是基石**：必须一次过
4. **Phase 11（前端用户）工作量最大**：建议拆 3 个 subagent（API+Store / 表单 / 公共组件）
5. **Phase 13 留足缓冲**：集成测试容易有坑
