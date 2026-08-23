# 图像生成工具设计规格

- **日期**：2026-08-23
- **状态**：Draft，待用户 review
- **作者**：Claude（brainstorming 流程产出）
- **路径**：`docs/superpowers/specs/2026-08-23-image-generation-tool-design.md`

---

## 1. 背景与目标

### 1.1 背景

项目 `tools` 是一个聚合多种工具的平台，前端入口在 `http://localhost:5178`，后端是 FastAPI。现有一个工具目录 `/tools/`，里面已有图片下载器、Token 用量、OpenClaw 聊天、数据库工具等。

用户希望新增一个**图像生成工具**，调用大模型能力，支持文生图 / 图生图 / 局部重绘 / 上传编辑等进阶功能。

约束：
- 服务器上已部署 Dify（当前未被本项目使用）
- 需要支持多模型（豆包 / 通义 / DALL-E / SDXL 等），用户手动切换或自动路由 + 负载均衡
- 需要管理员为用户分配配额（含有效期）

### 1.2 目标

1. **新增一个图像生成工具**：用户在前端 `/tools/image-generation` 进入
2. **支持 4 种生成操作**：
   - `text2img`：纯文生图
   - `img2img`：参考图 + 提示词生成
   - `inpaint`：参考图 + 蒙版 + 提示词重绘
   - `upload_edit`：上传编辑（超分/去噪/风格迁移/换背景等）
3. **多模型路由**：由 Dify 工作流承担路由、负载均衡、失败降级
4. **配额管控**：JWT 登录 + 每人每日/每月限额 + 管理员分配额度与有效期
5. **配置分层**：`.env` 默认 + 后台管理可覆盖（热加载）
6. **提示词润色**：v1 支持调用现有 LLM 优化提示词后再去生图
7. **可观测性**：所有关键路径有日志；降级策略、OSS 保留策略都在后台可配
8. **可回滚**：软禁用 → 硬禁用 → 完全回滚三级

### 1.3 非目标（明确不做）

- ❌ v1 不做内容安全过滤（后期可扩展）
- ❌ v1 不做异步任务队列（v1 同步 60s 超时，超了再升级）
- ❌ v1 不做多画布蒙版编辑（蒙版通过上传黑白图实现）
- ❌ 不直接调任何图像生成 API（全部走 Dify）

---

## 2. 关键决策记录

| # | 决策点 | 选择 | 理由 |
|---|---|---|---|
| D1 | 调用大模型方式 | **Dify 工作流** | 多模型路由 + 负载均衡 + 失败降级是 Dify 产品级能力，自建至少 1-2 周；Dify 已部署；进阶功能 API 差异由 Dify 节点抹平 |
| D2 | 图片存储 | **项目现有 OSS** | 复用已有上传 / 签名 URL / 代理预览能力；与现有工具统一；合规可控 |
| D3 | 鉴权模式 | **JWT + 每人每日/每月配额 + 管理员分配有效期** | 与项目现有工具一致；满足"给特定用户分配额度和有效期"的需求 |
| D4 | Dify 配置管理 | **.env 默认 + 后台覆盖** | 部署期静态配置 + 运行期热加载，覆盖常见场景 |
| D5 | Dify 工作流数量 | **4 个（每种 operation 一个）** | 便于独立调优、独立发布；避免一个超大工作流里塞 if/else 造成调试困难 |
| D6 | 后端调用模式 | **同步 HTTP，60s 超时** | v1 简单可控；超时再升级到异步任务 |
| D7 | 后端重试策略 | **不自动重试** | 图像生成贵，避免配额双花；用户主动重试更可控 |
| D8 | 提示词润色 | **v1 要做，复用现有 LLMConfig + llm_fallback** | 锦上添花成本很低，直接调现有适配器 |
| D9 | 降级策略 | **后台可配置** | 让管理员按实际 Dify 可用性调整，日志输出便于排查 |
| D10 | OSS 保留策略 | **后台可配置，默认永久保留** | 管理员可改为 N 天/N 天未访问删除，覆盖成本敏感场景 |

---

## 3. 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React)                                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  /tools/image-generation                              │  │
│  │  - 4 个 operation tabs                                │  │
│  │  - 提示词输入 + 参数 + 参考图/蒙版上传               │  │
│  │  - 提示词润色按钮（调 LLM 优化后回填）               │  │
│  │  - 结果预览 + 下载                                    │  │
│  │  - 历史抽屉                                           │  │
│  │  - 配额徽章 + 过期提示                                │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  /admin/image-generation                              │  │
│  │  - 用户配额管理 + 分配对话框                           │  │
│  │  - Dify 配置（URL/Key/4 个 workflow id）              │  │
│  │  - 降级策略配置                                        │  │
│  │  - OSS 保留策略配置                                    │  │
│  │  - 使用统计                                            │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────────────────┘
                  │ JWT 认证 + 业务请求
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                          │
│                                                              │
│  routes/                                                     │
│    /image-generation/*              用户 API                 │
│    /admin/image-generation/*        管理 API                 │
│                                                              │
│  services/                                                   │
│    ┌────────────────────┐                                    │
│    │ ImageGenService    │  业务编排（上传→调 Dify→存 OSS→  │
│    │ (编排层)           │  写历史）                          │
│    └─────────┬──────────┘                                    │
│              │                                               │
│    ┌─────────┼───────────────────────────────────────────┐  │
│    │         │            │            │                  │  │
│    ▼         ▼            ▼            ▼                  │  │
│  DifyClient ImageGen    DifyConfig   ImageGenQuotaService │  │
│            Prompt        Service      (含管理员方法)      │  │
│            Polisher                                       │  │
│                                                           │  │
│            ┌──────────────────────┐                       │  │
│            │ DegradationService   │  降级控制（可配置）    │  │
│            ├──────────────────────┤                       │  │
│            │ OssRetentionService  │  OSS 保留策略（可配）  │  │
│            ├──────────────────────┤                       │  │
│            │ ImageGenHistorySvc   │  历史 + 清理调度       │  │
│            └──────────────────────┘                       │  │
└─────────────────┼───────────────────────────────────────────┘
                  │ HTTPS
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  Dify (外部部署)                                            │
│  Workflow1 (text2img)    Workflow2 (img2img)                │
│  Workflow3 (inpaint)     Workflow4 (upload_edit)            │
│  内部路由至: 阿里通义 / OpenAI / Stable Diffusion / 豆包   │
└─────────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  Aliyun OSS                                                 │
│  image-gen/ref/{user_id}/{uuid}.png                         │
│  image-gen/mask/{user_id}/{uuid}.png                        │
│  image-gen/result/{user_id}/{record_id}.png                 │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 关键边界

- **本应用**：不直接调任何图像生成 API，只调 Dify。所有模型差异、路由、负载均衡都在 Dify 工作流里。
- **Dify**：纯业务编排，不存业务数据，不做用户鉴权。
- **OSS**：唯一的图片存储层。
- **本应用 DB**：唯一的业务数据存储（配额、历史、配置、管理员操作）。

---

## 4. Dify 工作流设计

4 个工作流各自独立。每个工作流的输出 schema 必须一致：

```json
{
  "image_urls": ["https://..."],    // 至少 1 张，可多张
  "model_used": "qwen-image-v1",     // 实际调用的模型
  "generation_meta": { ... }         // 模型特定元数据，透传给用户前端展示
}
```

### 4.1 Workflow 1: text2img

```
[开始]
  ├ prompt: string (必填)
  ├ size: enum (1024x1024, 1024x1792, 1792x1024, 默认 1024x1024)
  ├ n: int (1-4, 默认 1)
  ├ style: enum (natural, vivid, auto) | optional
  └ model_preference: enum (auto, doubao_seedream, qwen_image, dall_e_3, sdxl)
   │
   ▼
[条件分支: model_preference]
   ├ auto ──▶ [LLM 节点: 小模型判断 prompt 特征路由到合适模型]
   └ 直接选定目标模型
   ▼
[HTTP/工具节点: 调选定模型]
   ▼
[代码节点: 解析响应，提取 image_urls + model_used]
   ▼
[结束]
```

### 4.2 Workflow 2: img2img

```
[开始]
  ├ prompt, size, model_preference
  ├ reference_image_url: string   ← OSS 签名 URL（300s 有效）
  └ strength: float (0.0-1.0)
   │
   ▼
[模型分支] ──▶ [代码节点: 下载 reference → 转 base64/multipart]
   （抹平各模型对参考图的 API 差异）
   ▼
[结束]
```

### 4.3 Workflow 3: inpaint

```
[开始]
  ├ prompt, size, model_preference
  ├ image_url + mask_url (两张 OSS 签名 URL)
   │
   ▼
[模型分支] ──▶ [模型节点: 接受 image + mask]
   ▼
[结束]
```

### 4.4 Workflow 4: upload_edit

```
[开始]
  ├ image_url: string
  ├ edit_type: enum (upscale, denoise, relight, style_transfer, background_remove)
  └ prompt: optional
   │
   ▼
[条件分支: edit_type] ──▶ 各 edit_type 对应模型/工具
   ▼
[结束]
```

### 4.5 工作流公共规范

- **超时**：Dify 工作流内部节点级超时由 Dify 配置；工作流整体超时由后端 HTTP 客户端控制（默认 60s，后台可调）
- **错误**：工作流失败时，输出 `error_message` 字段，后端记录日志
- **重试**：Dify 工作流内部节点可配置重试；后端不做额外重试

---

## 5. 后端服务设计

### 5.1 DifyClient（`services/dify_client.py`）

封装 4 个工作流调用 + 连通性测试。

```python
class DifyClient:
    def __init__(self):
        self._config_svc = DifyConfigService()   # 运行时读配置

    async def run_text2img(prompt, size, n, style, model_preference, user_id, timeout=60.0) -> DifyRunResult: ...
    async def run_img2img(prompt, reference_url, strength, size, model_preference, user_id, timeout=60.0) -> DifyRunResult: ...
    async def run_inpaint(prompt, image_url, mask_url, size, model_preference, user_id, timeout=60.0) -> DifyRunResult: ...
    async def run_upload_edit(image_url, edit_type, prompt, user_id, timeout=60.0) -> DifyRunResult: ...
    async def test_connection() -> tuple[bool, str]: ...

@dataclass
class DifyRunResult:
    image_urls: list[str]
    model_used: str
    raw_response: dict
```

**配置读取**：每次调用前实时读 `DifyConfigService.get_config()`，拿到 `.env` 默认 + admin 覆盖后的最终值。不缓存。

### 5.2 ImageGenService（`services/image_generation_service.py`）

编排层，串联所有服务。

```python
async def generate(user_id, operation, prompt, params, reference_file, mask_file):
    # 0. 降级检查
    if DegradationService.is_degraded():
        raise ServiceDegraded("图像生成服务暂时不可用")

    # 1. 配额检查 + 预留
    reservation = QuotaService.check_and_reserve(user_id)
    if not reservation.ok:
        raise QuotaExceeded(reservation.reason)

    record_id = uuid4()
    try:
        # 2. 上传参考图/蒙版到 OSS（如有）
        ref_key = upload_to_oss(reference_file, "ref", user_id) if reference_file else None
        mask_key = upload_to_oss(mask_file, "mask", user_id) if mask_file else None

        # 3. 生成签名 URL（Dify 用，300s 有效）
        ref_url = oss.get_signed_url(ref_key, 300) if ref_key else None
        mask_url = oss.get_signed_url(mask_key, 300) if mask_key else None

        # 4. 调 Dify
        start = time.monotonic()
        result = await dify_client.run_<operation>(...)
        duration_ms = int((time.monotonic() - start) * 1000)

        # 5. 下载生成结果 → 上传 OSS
        result_key = download_and_store(result.image_urls[0], "result", user_id, record_id)

        # 6. 写历史 + 提交配额
        HistoryService.create(record_id, user_id, operation, ..., status="success")
        QuotaService.commit(reservation)

        # 7. 重置降级计数器（成功调用）
        DegradationService.reset()

        return GenerationResult(record_id, oss.get_signed_url(result_key, 3600), result.model_used, duration_ms)

    except DifyError as e:
        QuotaService.release(reservation)
        HistoryService.create(record_id, ..., status="failed", error=str(e))
        DegradationService.record_failure()
        raise
    except Exception:
        QuotaService.release(reservation)
        raise
```

### 5.3 ImageGenQuotaService（含管理员方法）

#### 5.3.1 配额检查与预留

```python
async def check_and_reserve(user_id: str) -> QuotaReservation:
    """
    事务内完成：
    - SELECT FOR UPDATE 锁定当前用户配额行
    - 校验 valid_from <= now <= valid_until
    - 校验 daily_used < daily_limit
    - 校验 monthly_used < monthly_limit
    - 递增 daily_used + 1, monthly_used + 1
    - 返回 reservation（成功/失败原因）
    """
```

#### 5.3.2 配额提交 / 释放

- `commit(reservation)`: 事务提交即完成
- `release(reservation)`: 事务回滚，计数器不变

#### 5.3.3 管理员方法

- `grant(user_id, daily_limit, monthly_limit, valid_from, valid_until, granted_by, notes)`: 分配或更新
- `revoke(user_id)`: 删除配额记录（用户回到"无配额=不能使用"）
- `reset_counters(user_id)`: 重置计数器，保留记录
- `list_users(keyword, page, page_size)`: 分页查询
- `get_user_quota(user_id)`: 单用户详情

#### 5.3.4 有效期语义

- `valid_from` 空 = 立即生效
- `valid_until` 空 = 永久有效
- 两者都空 = 立即生效且永久
- 任一非空但过期 → `check_and_reserve` 拒绝

### 5.4 ImageGenHistoryService

- `create(...)`: 写历史记录
- `list_by_user(user_id, page, page_size)`: 分页
- `get(record_id)`: 单条详情
- `soft_delete(record_id)`: 软删除（标记 `is_deleted=true`）
- `count_by_user(user_id, since)`: 配额统计用
- `cleanup_before(cutoff_date)`: OSS 保留策略调用，删除过期记录并清理 OSS

### 5.5 DifyConfigService（分层配置）

配置优先级：**DB 覆盖 > .env 默认**

```python
@dataclass
class DifyConfig:
    api_url: str
    app_api_key: str       # 加密存储
    workflow_text2img: str
    workflow_img2img: str
    workflow_inpaint: str
    workflow_upload_edit: str
    default_timeout: float = 60.0

class DifyConfigService:
    async def get_config() -> DifyConfig:
        """读 DB；无则回退 .env；仍无则报错"""

    async def update_config(partial: dict):
        """admin 调，写入 DB（app_api_key 加密）"""

    async def test_connection() -> tuple[bool, str]:
        """测试当前配置能否调通 Dify"""

    async def get_config_view() -> DifyConfigView:
        """返回给 admin 前端：是否已配置，不返回明文 key"""
```

**热加载**：每次 `DifyClient.run_*` 都重新读 `get_config()`，无缓存，管理员修改立即生效。

**加密**：`app_api_key` 使用 `DB_ENCRYPTION_KEY`（已有）加密存库。

### 5.6 ImageGenPromptPolisher（提示词润色）

v1 新功能，**复用现有 LLM 体系**。

```python
class ImageGenPromptPolisher:
    """
    调用现有 LLMConfig + llm_fallback 机制优化提示词。
    使用一个轻量 LLM（如 gpt-4o-mini / qwen-turbo）。
    """
    async def polish(prompt: str, user_id: str, target_operation: str) -> str:
        """
        1. 从 LLMConfig 表找到标签为 "image_gen_polish" 的配置
           （或 fallback 到最小可用模型）
        2. 构造 system prompt: 你是图像生成提示词优化专家...
        3. 调 LLM 适配器生成优化版本
        4. 记录 token 用量（可选，走现有 token_usage 体系）
        5. 返回优化后提示词
        """
```

**API 端点**：
- `POST /image-generation/polish-prompt` → `{ prompt, target_operation }` → `{ polished_prompt }`

**失败处理**：润色失败时，前端保留用户原始提示词（用户仍可点"生成"）。

### 5.7 DegradationService（降级控制）

可配置的自动降级机制。

```python
@dataclass
class DegradationConfig:
    enabled: bool = True
    failure_threshold: int = 3          # 连续失败 N 次后降级
    degrade_duration_seconds: int = 300 # 降级持续时间
    # 后续可扩展：通知邮箱/钉钉/webhook 等

class DegradationService:
    def __init__(self):
        self._config_svc = DegradationConfigService()
        self._failure_count = 0
        self._degraded_until: datetime | None = None

    async def record_failure():
        self._failure_count += 1
        cfg = await self._config_svc.get_config()
        if cfg.enabled and self._failure_count >= cfg.failure_threshold:
            self._degraded_until = now() + timedelta(seconds=cfg.degrade_duration_seconds)
            logger.warning(f"[image-gen] 触发降级: 连续 {self._failure_count} 次失败, "
                          f"禁用至 {self._degraded_until}")
            self._failure_count = 0

    async def record_success():
        # 成功调用重置计数（不重置降级状态，需等时间到）
        self._failure_count = 0

    async def reset():
        self._degraded_until = None
        self._failure_count = 0
        logger.info("[image-gen] 管理员手动重置降级状态")

    def is_degraded() -> bool:
        if self._degraded_until and now() < self._degraded_until:
            return True
        if self._degraded_until and now() >= self._degraded_until:
            self._degraded_until = None  # 自动解除
            logger.info("[image-gen] 降级自动解除")
        return False
```

**管理 API**：
- `GET /admin/image-generation/degradation`: 当前降级状态
- `PUT /admin/image-generation/degradation`: 配置（enabled, threshold, duration）
- `POST /admin/image-generation/degradation/reset`: 手动解除

**日志要求**（每条降级相关事件必须记录）：
```
INFO  [image-gen] 用户 alice 触发 text2img, duration_ms=3200
WARN  [image-gen] 用户 bob 触发 img2img 失败: Dify 返回 500
WARN  [image-gen] 触发降级: 连续 3 次失败, 禁用至 2026-08-23T15:30:00
INFO  [image-gen] 降级自动解除
INFO  [image-gen] 管理员手动重置降级状态
```

### 5.8 OssRetentionService（OSS 保留策略）

可配置的清理策略。

```python
@dataclass
class RetentionConfig:
    mode: Literal["keep_forever", "delete_after_n_days", "delete_if_unused_for_n_days"]
    n_days: int = 30                       # 仅在后两种模式有效
    cleanup_cron: str = "0 3 * * *"        # 每天凌晨 3 点（后台任务框架实现）

class OssRetentionService:
    async def run_cleanup():
        """被后台定时任务调度"""
        cfg = await self._config_svc.get_config()
        if cfg.mode == "keep_forever":
            return

        if cfg.mode == "delete_after_n_days":
            cutoff = now() - timedelta(days=cfg.n_days)
            expired = await HistoryService.list_before(cutoff, limit=1000)

        else:  # delete_if_unused_for_n_days
            cutoff = now() - timedelta(days=cfg.n_days)
            expired = await HistoryService.list_not_accessed_since(cutoff, limit=1000)

        for record in expired:
            try:
                oss.delete(record.result_oss_key)
                if record.reference_oss_key: oss.delete(record.reference_oss_key)
                if record.mask_oss_key: oss.delete(record.mask_oss_key)
                record.is_deleted = True
                await db.commit()
                logger.info(f"[image-gen] 清理过期记录 {record.id}")
            except Exception as e:
                logger.error(f"[image-gen] 清理失败 {record.id}: {e}")
```

**管理 API**：
- `GET /admin/image-generation/retention`: 当前配置
- `PUT /admin/image-generation/retention`: 更新配置
- `POST /admin/image-generation/retention/trigger`: 手动触发一次清理

---

## 6. 数据库设计

### 6.1 image_gen_quota（配额表）

```sql
CREATE TABLE image_gen_quota (
    user_id          VARCHAR(64) PRIMARY KEY,
    daily_limit      INT NOT NULL,
    monthly_limit    INT NOT NULL,
    daily_used       INT NOT NULL DEFAULT 0,
    monthly_used     INT NOT NULL DEFAULT 0,
    daily_reset_date TIMESTAMP NOT NULL,
    monthly_reset_date TIMESTAMP NOT NULL,
    valid_from       TIMESTAMP,                     -- 可空 = 立即生效
    valid_until      TIMESTAMP,                     -- 可空 = 永久
    granted_by       VARCHAR(64),                   -- 授予人 user_id
    notes            VARCHAR(512),                  -- 备注
    created_at       TIMESTAMP NOT NULL DEFAULT now(),
    updated_at       TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_image_gen_quota_valid_until ON image_gen_quota(valid_until);
```

### 6.2 image_gen_history（历史表）

```sql
CREATE TABLE image_gen_history (
    id               VARCHAR(64) PRIMARY KEY,
    user_id          VARCHAR(64) NOT NULL,
    operation        VARCHAR(32) NOT NULL,          -- text2img/img2img/inpaint/upload_edit
    prompt           TEXT,
    params           JSONB,                         -- size/n/style/strength/edit_type 等
    reference_oss_key VARCHAR(512),                 -- 参考图 OSS key
    mask_oss_key     VARCHAR(512),
    result_oss_key   VARCHAR(512) NOT NULL,         -- 生成结果 OSS key
    result_width     INT,
    result_height    INT,
    model_used       VARCHAR(128),                  -- Dify 返回的实际模型
    status           VARCHAR(32) NOT NULL,          -- success/failed/cancelled
    error_message    TEXT,
    duration_ms      INT,
    is_deleted       BOOLEAN DEFAULT FALSE,
    last_accessed_at TIMESTAMP,                     -- OSS 保留策略用
    created_at       TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_image_gen_history_user_id ON image_gen_history(user_id);
CREATE INDEX idx_image_gen_history_created_at ON image_gen_history(created_at);
CREATE INDEX idx_image_gen_history_last_accessed ON image_gen_history(last_accessed_at);
CREATE INDEX idx_image_gen_history_is_deleted ON image_gen_history(is_deleted);
```

### 6.3 image_gen_dify_config（Dify 配置表）

```sql
CREATE TABLE image_gen_dify_config (
    id               SERIAL PRIMARY KEY,
    key              VARCHAR(64) NOT NULL UNIQUE,   -- api_url / app_api_key / workflow_text2img 等
    value_encrypted  BYTEA NOT NULL,                -- 加密存储
    updated_by       VARCHAR(64),
    updated_at       TIMESTAMP NOT NULL DEFAULT now()
);
```

### 6.4 image_gen_degradation_config（降级配置表）

```sql
CREATE TABLE image_gen_degradation_config (
    id                       SERIAL PRIMARY KEY,
    enabled                  BOOLEAN DEFAULT TRUE,
    failure_threshold        INT DEFAULT 3,
    degrade_duration_seconds INT DEFAULT 300,
    updated_by               VARCHAR(64),
    updated_at               TIMESTAMP NOT NULL DEFAULT now()
);
```

### 6.5 image_gen_retention_config（保留策略配置表）

```sql
CREATE TABLE image_gen_retention_config (
    id            SERIAL PRIMARY KEY,
    mode          VARCHAR(64) NOT NULL DEFAULT 'keep_forever',
    n_days        INT DEFAULT 30,
    cleanup_cron  VARCHAR(32) DEFAULT '0 3 * * *',
    updated_by    VARCHAR(64),
    updated_at    TIMESTAMP NOT NULL DEFAULT now()
);
```

---

## 7. API 端点

### 7.1 用户 API（`/image-generation/*`，需 JWT）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/generate` | 提交生成请求（multipart：prompt + params + 可选文件） |
| POST | `/polish-prompt` | 提示词润色 |
| GET | `/history` | 分页历史（按 user_id 过滤） |
| GET | `/history/{id}` | 单条详情 |
| DELETE | `/history/{id}` | 软删除 |
| GET | `/quota/me` | 我的配额（含剩余 + 有效期） |
| GET | `/result/{history_id}` | 拿签名 URL（1 小时有效；顺带更新 `last_accessed_at`） |

### 7.2 管理 API（`/admin/image-generation/*`，需管理员权限）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/users` | 有配额用户列表（分页 + 搜索） |
| POST | `/users/{user_id}/grant` | 分配/更新配额 + 有效期 |
| DELETE | `/users/{user_id}/quota` | 撤销配额 |
| POST | `/users/{user_id}/reset` | 重置计数器 |
| GET | `/quota/{user_id}` | 用户配额详情 |
| GET | `/config` | Dify 配置视图（不返回明文 key） |
| PUT | `/config` | 更新 Dify 配置 |
| POST | `/config/test` | 测试 Dify 连通性 |
| GET | `/degradation` | 降级状态 + 配置 |
| PUT | `/degradation` | 更新降级配置 |
| POST | `/degradation/reset` | 手动解除降级 |
| GET | `/retention` | 保留策略配置 |
| PUT | `/retention` | 更新保留策略 |
| POST | `/retention/trigger` | 手动触发清理 |
| GET | `/stats` | 使用统计（总次数/模型分布/失败率） |

---

## 8. 前端设计

### 8.1 用户侧（`/tools/image-generation`）

#### 8.1.1 组件结构

```
frontend/src/components/Tools/ImageGeneration/
├── index.tsx                        # 主页面
├── OperationTabs.tsx                # 4 个 operation tabs
├── forms/
│   ├── Text2ImgForm.tsx
│   ├── Img2ImgForm.tsx
│   ├── InpaintForm.tsx
│   └── UploadEditForm.tsx
├── components/
│   ├── ImageUploader.tsx            # 通用图片上传（拖拽 + 预览）
│   ├── MaskUploader.tsx             # 蒙版上传（上传黑白图，不做画布编辑）
│   ├── ResultPanel.tsx              # 结果展示 + 下载 + "以此图为参考"
│   ├── HistoryDrawer.tsx            # 历史右侧抽屉
│   └── QuotaBadge.tsx               # 配额徽章
├── hooks/
│   ├── useImageGenerate.ts          # 含 AbortController
│   ├── useImageGenQuota.ts          # 配额查询 + 自动刷新
│   └── useImageGenHistory.ts        # 历史分页
└── types.ts
```

#### 8.1.2 主页面布局

```
┌────────────────────────────────────────────────────────────────┐
│ 图像生成工具                          [📊 配额: 8/20 今日 ▼] │
├────────────────────────────────────────────────────────────────┤
│ ┌─────────┬─────────┬─────────┬─────────┐                      │
│ │ 文生图  │ 图生图  │ 局部重绘│ 上传编辑│                       │
│ └─────────┴─────────┴─────────┴─────────┘                      │
│                                                                  │
│ 提示词 *                                                         │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ 一只橘猫坐在窗台上，背景是日落                            │  │
│ └──────────────────────────────────────────────────────────┘  │
│ [✨ 提示词润色] (按钮，点击调 LLM 优化后回填)                 │
│                                                                  │
│ 模型偏好: [自动 ▼]  尺寸: [1024x1024 ▼]  数量: [1 ▼]            │
│ 风格: [auto ▼]                                                  │
│                                                                  │
│                            [清空]    [生成]                    │
│                                                                  │
│ ── 结果 ──                                                       │
│ ┌──────────────────┐                                            │
│ │                  │  模型: qwen-image-v1                      │
│ │   [生成图预览]    │  耗时: 3.2s                                │
│ │                  │  [下载] [以此图为参考] [删除]              │
│ └──────────────────┘                                            │
│                                                                  │
│ ── 右侧 ──                                                       │
│ [📁 历史 (32 条)]  ← 点击打开抽屉                                │
└────────────────────────────────────────────────────────────────┘
```

#### 8.1.3 表单差异化

- **文生图**：纯提示词 + 参数
- **图生图**：+ 参考图上传 + 强度滑块
- **局部重绘**：+ 参考图 + 蒙版图上传（v1 上传黑白图，不做画布）
- **上传编辑**：+ 参考图 + edit_type 下拉（upscale/denoise/relight/style_transfer/background_remove），可选提示词

#### 8.1.4 状态管理（Zustand）

```typescript
interface ImageGenerationState {
  operation: OperationType;
  prompt: string;
  params: Record<string, any>;
  referenceImage: File | null;
  maskImage: File | null;
  currentResult: GenerationResult | null;
  history: HistoryRecord[];
  historyTotal: number;
  loading: boolean;
  error: string | null;
  quota: QuotaInfo | null;
  abortController: AbortController | null;
  
  // actions
  setOperation, setPrompt, setParams, setReferenceImage, setMaskImage,
  generate, abort, reset,
  loadHistory, loadQuota, refreshQuota,
  polishPrompt,
}
```

### 8.2 管理后台（`/admin/image-generation`）

```
┌────────────────────────────────────────────────────────────────┐
│ 图像生成 - 管理                                                │
├────────────────────────────────────────────────────────────────┤
│ [使用统计] [Dify 配置] [降级策略] [保留策略] [用户配额]         │
│                                                                  │
│ ── 用户配额（默认 tab） ──                                     │
│ 搜索: [用户名____] [状态: 全部 ▼] [+ 分配配额]                 │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ 用户名 │ 今日/今日上限 │ 本月/本月上限 │ 有效期  │ 操作 │  │
│ ├──────────────────────────────────────────────────────────┤  │
│ │ alice  │ 5/20         │ 50/300       │ 至年底  │ 编辑 │  │
│ │ bob    │ 0/10         │ 0/100        │ 永久    │ 编辑 │  │
│ │ carol  │ -            │ -            │ -       │ 分配 │  │
│ └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘

── Dify 配置 tab ──
┌────────────────────────────────────────────────────────────────┐
│ API URL: [___________________]                                  │
│ App API Key: [已配置 ▼ 点击更新]                                │
│ Workflow text2img: [wf_xxx__________]                          │
│ Workflow img2img:  [wf_yyy__________]                          │
│ Workflow inpaint:  [wf_zzz__________]                          │
│ Workflow upload_edit: [wf_aaa_________]                        │
│ 默认超时 (s): [60]                                              │
│ [测试连通性]   [保存]                                          │
└────────────────────────────────────────────────────────────────┘

── 降级策略 tab ──
┌────────────────────────────────────────────────────────────────┐
│ 启用自动降级: [✓]                                               │
│ 连续失败阈值: [3] 次                                            │
│ 降级持续时间: [300] 秒                                          │
│ 当前状态: [🟢 正常 / 🔴 降级中 至 15:30:00]                    │
│ [手动解除降级]   [保存]                                        │
└────────────────────────────────────────────────────────────────┘

── 保留策略 tab ──
┌────────────────────────────────────────────────────────────────┐
│ 模式: [永久保留 ▼]  / [N 天后删除 ▼] / [N 天未访问删除 ▼]      │
│ N = [30] 天                                                      │
│ 清理调度: [0 3 * * *]                                           │
│ 当前 OSS 用量: 12.3 GB                                          │
│ [手动触发一次清理]   [保存]                                    │
└────────────────────────────────────────────────────────────────┘
```

---

## 9. 数据流时序

### 9.1 文生图 (text2img)

```
Frontend            Backend              Dify               OSS
  │ POST /generate    │                    │                  │
  │ (multipart)       │                    │                  │
  ├──────────────────▶│                    │                  │
  │                   │ quota.check_reserve│                  │
  │                   │ (事务)             │                  │
  │                   │                    │                  │
  │                   │ dify.run_text2img  │                  │
  │                   ├───────────────────▶│                  │
  │                   │                    │ 路由+生图         │
  │                   │◀───────────────────┤                  │
  │                   │                    │                  │
  │                   │ 下载结果            │                  │
  │                   ├──────────────────────────────────────▶│
  │                   │◀──────────────────────────────────────┤
  │                   │ 上传 OSS           │                  │
  │                   ├──────────────────────────────────────▶│
  │                   │◀──────────────────────────────────────┤
  │                   │                    │                  │
  │                   │ history.create + quota.commit          │
  │                   │ degradation.reset  │                  │
  │◀──────────────────┤                   │                  │
  │ {record_id, ...}  │                    │                  │
```

### 9.2 图生图 (img2img) — 带参考图上传

```
Frontend            Backend              Dify               OSS
  │ POST /generate    │                    │                  │
  │ (+reference_file) │                    │                  │
  ├──────────────────▶│                    │                  │
  │                   │ quota.check_reserve│                  │
  │                   │ upload reference   │                  │
  │                   ├──────────────────────────────────────▶│
  │                   │◀──────────────────────────────────────┤ ref_key
  │                   │ get_signed_url(300s)                   │
  │                   │ dify.run_img2img(ref_url, ...)         │
  │                   ├───────────────────▶│                  │
  │                   │                    │ 下载参考图 + 生图 │
  │                   │◀───────────────────┤                  │
  │                   │ (后续同 text2img)   │                  │
```

inpaint 类似，多传 mask_url。upload_edit 类似，多传 edit_type。

### 9.3 提示词润色（独立 API）

```
Frontend            Backend
  │ POST /polish-prompt│
  │ { prompt, op }    │
  ├──────────────────▶│
  │                   │ LLMFallback 调"image_gen_polish"模型
  │                   │ 记录 token 用量
  │◀──────────────────┤
  │ { polishedPrompt } │
```

失败时返回 200 + 空结果，前端保留用户原输入。

---

## 10. 测试策略

### 10.1 最小可运行测试集（v1 必须）

| 类别 | 测试 |
|---|---|
| 配额并发 | 100 个并发请求，最终 daily_used 不超限 |
| 配额有效期 | valid_from / valid_until 边界测试 |
| Dify 失败 | Mock 5xx / 超时 / 响应格式错，验证释放配额 + 写 failed 历史 |
| 降级触发 | 连续失败 3 次后 is_degraded() 返回 true |
| 降级解除 | 降级时间到后 is_degraded() 自动返回 false |
| OSS 清理 | mode=delete_after_n_days，验证过期记录被删除 |
| 表单渲染 | 4 种 operation 表单切换正确渲染 |
| 上传校验 | 文件 > 10MB / 错误格式 被拒绝 |

### 10.2 集成测试（v1 应做）

- Mock Dify + Mock OSS，验证端到端生成流程
- Mock Dify 返回 4 种 operation 各自的 schema，验证结果正确处理

### 10.3 E2E 测试（v1 可选）

- 登录 → 进工具 → 文生图 → 看历史（依赖可访问的 Dify 环境）

---

## 11. 部署清单

### 11.1 后端

1. 环境变量 `.env`：
   ```bash
   DIFY_API_URL=https://your-dify.example.com/v1
   DIFY_APP_API_KEY=app-xxxxxxxxxxxx
   DIFY_WORKFLOW_TEXT2IMG=wf_xxx
   DIFY_WORKFLOW_IMG2IMG=wf_yyy
   DIFY_WORKFLOW_INPAINT=wf_zzz
   DIFY_WORKFLOW_UPLOAD_EDIT=wf_aaa
   ```
2. 数据库迁移：5 张新表（按 section 6 定义）
3. 路由注册：
   - `routes/image_generation.py` 挂到主 `router.py`
   - `routes/admin_image_generation.py` 挂到主 `router.py`
4. OSS 前缀：
   - `image-gen/ref/{user_id}/{uuid}.png`
   - `image-gen/mask/{user_id}/{uuid}.png`
   - `image-gen/result/{user_id}/{record_id}.png`
5. 后台定时任务注册：`OssRetentionService.run_cleanup`（按 retention_config.cleanup_cron 调度）

### 11.2 Dify 端

- 4 个新工作流（按 section 4 定义）
- 1 个 Dify App API Key（后端用）
- 建议先在测试环境调通 text2img，再铺开另外 3 个

### 11.3 前端

- 新路由 `/tools/image-generation`
- 新路由 `/admin/image-generation`（5 个 tab）
- 工具列表入口
- i18n：`en-US.ts` / `zh-CN.ts` 新增 keys
- 管理后台侧边栏入口

### 11.4 配置初始化

- `.env` 默认值部署期生效
- 管理员首次进管理后台，可配置覆盖值（写入 DB）
- 降级配置 / 保留策略配置首次写入后生效

---

## 12. 监控与可观测性

### 12.1 日志规范

每条生成请求：
```
INFO  [image-gen] user=xxx op=text2img model=qwen-image-v1 duration_ms=3200 status=success record_id=yyy
WARN  [image-gen] user=xxx op=img2img model=xxx duration_ms=58000 status=timeout
ERROR [image-gen] user=xxx op=inpaint dify_error="model rate limit"
```

每次降级事件：
```
WARN  [image-gen-degrade] 触发降级: 连续 3 次失败, 禁用至 2026-08-23T15:30:00
INFO  [image-gen-degrade] 降级自动解除
INFO  [image-gen-degrade] 管理员手动重置降级状态
```

每次清理事件：
```
INFO  [image-gen-retention] 清理 15 条过期记录, 释放 2.3GB
ERROR [image-gen-retention] 清理失败 record_id=xxx: xxx
```

### 12.2 告警

| 指标 | 阈值 |
|---|---|
| 生成成功率 | < 95% 持续 5 分钟 |
| P95 延迟 | > 30s 持续 10 分钟 |
| Dify 失败率 | > 10% 持续 5 分钟 |
| 每日配额使用峰值 | 接近 100% 时通知管理员 |
| OSS 存储增量 | 单用户 > 5GB 或总量突增 |

---

## 13. 风险与缓解

| 风险 | 等级 | 缓解 |
|---|---|---|
| Dify 服务宕机 | 🔴 高 | DegradationService 自动降级 + 日志告警；管理员手动重置 |
| Dify 工作流 > 60s | 🟡 中 | v1 默认 60s，后台可调；v2 升级到异步任务 |
| OSS 签名 URL 过期 | 🟡 中 | 默认 300s 有效；Dify 工作流节点可重试 |
| 配额并发双花 | 🟡 中 | SELECT FOR UPDATE + 事务 + 单元测试 |
| 大文件上传 DoS | 🟡 中 | 前端 + 后端双限制 10MB |
| 模型返回不当内容 | 🟢 低 | 模型侧负责；v2 可接敏感词过滤 |
| OSS 存储暴涨 | 🟢 低 | OssRetentionService 可配置清理 |
| Dify API Key 泄露 | 🟢 低 | 不暴露到前端；admin 配置只返回"是否已配置" |

---

## 14. 回滚方案

### 14.1 三级回滚

**Level 1 软禁用（最快，0 停机）**：
- 管理后台一键关闭入口（前端不显示）

**Level 2 硬禁用**：
- `.env` 加 `IMAGE_GENERATION_ENABLED=false`
- 后端所有请求返回 503

**Level 3 完全回滚**：
- 删除路由注册
- 保留 `image_gen_*` 表（数据保留，不删）
- 删除前端组件与路由
- 删除 `.env` 配置项
- 删除 Dify 工作流

### 14.2 数据保留

- OSS 文件：保留 30 天再物理删除，方便回滚期间恢复
- DB 表：保留 indefinitely，需要时重新启用即可

---

## 15. 未来扩展（v2+）

明确 v1 不做，留作未来增强：

- **内容安全过滤**：接敏感词模型 / 阿里云内容审核
- **异步任务队列**：处理 > 60s 的生成任务（Redis queue + WebSocket 推送）
- **备用 Dify 实例 failover**：多实例自动切换
- **画布蒙版编辑**：前端画布涂抹代替上传黑白图
- **多模型结果对比**：同时调用多个模型，让用户选最佳
- **图像批量生成**：一次提交 N 个提示词
- **历史导出**：导出为 zip

---

## 16. 大模型配置重构（v1 必需，Phase 1.5）

### 16.1 背景

现有 `llm_configs` 表是扁平设计：每条记录绑定一个 (provider, base_url, api_key, model) 四元组。问题：
- 同一厂商多模型需要重复存储 API Key 和 base_url（明文风险 × 重复次数）
- 增删模型时改 Key 不便
- 「类目默认」（如 `image_polish` 默认模型）语义缺失

本次重构把 `llm_configs` 拆为 `llm_providers` + `llm_models` 两张表，是图像生成工具（Phase 8 提示词润色）以及其他工具（Product Manager Agent / chat_stream / conversations）的**前置依赖**。

### 16.2 决策记录

| # | 决策点 | 选择 | 理由 |
|---|---|---|---|
| R1 | 拆分方式 | 拆 2 张表（Provider + Model） | 经典归一化，1 个 Key 配 N 模型只存 1 份 |
| R2 | 老数据迁移 | 保留 `llm_configs` 表不删，标记 deprecated | 可回滚；Alembic 迁移 backfill 到新表 |
| R3 | 默认模型 | 全局默认 + 类目默认双开关 | 灵活；不同工具（chat/code/image_polish）可独立默认 |
| R4 | 消费方迁移 | 一次性切换到新表，老服务标记 deprecated | 集中一次回归测试优于双轨运行 |
| R5 | 厂商枚举 | 增加 `doubao_seedream` 等图像生成厂商 | 图像生成会用到豆包 |
| R6 | UI | LLMConfigsPage 拆为「供应商」+「模型」2 tabs | 与后端 2 张表对应 |

### 16.3 新 Schema

#### `llm_providers`

```python
class LLMProvider(Base):
    __tablename__ = "llm_providers"
    id            = UUID, PK, default=uuid.uuid4
    name          = String(100), NOT NULL          # 展示名，如 "OpenAI 主力"
    provider_type = String(50), NOT NULL           # openai/anthropic/azure_openai/baidu/aliyun/doubao_seedream/qwen_image/other
    base_url      = String(500), NOT NULL
    api_key_encrypted = Text, NOT NULL
    api_key_suffix = String(4), nullable            # 末 4 位识别
    notes         = String(500), nullable
    is_active     = Boolean, default=True
    created_at    = DateTime, server_default=now()
    updated_at    = DateTime, onupdate=now()
```

#### `llm_models`

```python
class LLMModel(Base):
    __tablename__ = "llm_models"
    id            = UUID, PK, default=uuid.uuid4
    name          = String(100), NOT NULL          # 展示名，如 "GPT-4o 视觉"
    model_name    = String(100), NOT NULL          # API model 名，如 "gpt-4o"
    provider_id   = UUID, FK → llm_providers.id, NOT NULL
    request_params = JSON, nullable                 # {temperature, max_tokens, timeout}
    category      = String(20), NOT NULL, default="chat"   # chat / code / image_polish
    is_default    = Boolean, default=False         # 全局默认
    is_default_for_category = Boolean, default=False  # 类目默认
    notes         = String(500), nullable
    is_active     = Boolean, default=True
    created_at    = DateTime, server_default=now()
    updated_at    = DateTime, onupdate=now()
```

索引：
- `llm_models(provider_id)`, `llm_models(category)`, `llm_models(is_default)`, `llm_models(is_default_for_category)`

### 16.4 数据迁移（Alembic）

```
1. CREATE TABLE llm_providers (...) / llm_models (...)
2. INSERT INTO llm_providers
   按 (provider_type, base_url, api_key_encrypted, api_key_suffix) GROUP BY
   每组一条 provider，name = "Migrated: {provider_type} {api_key_suffix}"
3. 临时映射 _provider_mapping(old_config_id, new_provider_id)
   JOIN 条件: 上述 4 个字段完全相等
4. INSERT INTO llm_models
   每条老配置 → 一条 model，FK 用 _provider_mapping 解析
   request_params / category / is_default / is_active 全部继承
5. 保留 llm_configs 表不删，列加 comment 'DEPRECATED: see llm_providers + llm_models'
6. 代码注释: llm_config.py 头部加 # DEPRECATED, use llm_provider.py + llm_model.py
```

回滚路径：drop 新表 + 清空 mapping（llm_configs 数据完整无损）。

### 16.5 新 Services

#### `LLMProviderService`（`backend/app/services/llm_provider_service.py`）

```python
class LLMProviderService:
    def list_providers(active_only=False) -> List[LLMProvider]
    def get_provider(provider_id) -> LLMProvider | None
    def create_provider(name, provider_type, base_url, api_key, notes, is_active) -> LLMProvider
    def update_provider(provider_id, **kwargs) -> LLMProvider | None
    def delete_provider(provider_id) -> bool       # 仅当无关联 model 才允许
    def test_connection(provider_id) -> (bool, str, int)
    def reveal_api_key(provider_id) -> str        # 返回明文，仅管理员
```

#### `LLMModelService`（`backend/app/services/llm_model_service.py`）

```python
class LLMModelService:
    def list_models(filters=None, active_only=False) -> List[LLMModel]
    def get_model(model_id) -> LLMModel | None
    def get_default_model(category) -> LLMModel | None
    def create_model(name, model_name, provider_id, request_params, category, is_default, is_default_for_category, notes) -> LLMModel
    def update_model(model_id, **kwargs) -> LLMModel | None
    def delete_model(model_id) -> bool
    def set_default(model_id, category=None) -> bool   # category=None 设为全局默认
```

#### `LLMConfigService`（保留为 deprecated wrapper）

仅保留 `list_configs()` / `get_config()` 等只读方法，从 `llm_providers + llm_models` JOIN 读取，给老代码一个过渡。所有写方法抛 `NotImplementedError`。

### 16.6 消费方迁移（4 个文件）

| 文件 | 改动 |
|---|---|
| `llm_fallback.py` | `_get_available_configs()` → `_get_available_models()`，每个 model join provider 拿 (provider_type, api_key, base_url) |
| `agent_service.py` | 同上模式 |
| `chat_stream.py` | 同上 |
| `conversations.py` | 同上 |

新增的 `image_gen_prompt_polisher.py`（图像生成 Phase 8）直接用新接口，不走 deprecated 路径。

### 16.7 前端 UI 重构

```
frontend/src/components/Admin/LLMConfigs/
├── ProvidersTab.tsx          # 供应商列表 + 新增/编辑对话框（含 API Key 显隐）
├── ModelsTab.tsx             # 模型列表 + 新增/编辑对话框（含 provider 下拉 + category + 默认开关）
├── ProviderDialog.tsx
├── ModelDialog.tsx
└── （保留现有 LLMStats.tsx，更新统计维度）
```

`LLMConfigsPage.tsx`：从单列表 → 顶部 2 tabs。

```
┌──────────────────────────────────────────────────────────┐
│ 大模型配置                                              │
├──────────────────────────────────────────────────────────┤
│ [📦 模型供应商]  [🤖 模型配置]  (2 tabs)               │
│                                                          │
│ ── 模型供应商 ──                                       │
│ [+ 新建供应商]                                          │
│ ┌────────────────────────────────────────────────────┐  │
│ │ 名称 │ 厂商 │ base URL │ key 末4 │ 启用 │ 操作   │  │
│ ├────────────────────────────────────────────────────┤  │
│ │ OpenAI 主力 │ openai │ api.openai.com │ ****abcd │ ✓ │  │
│ │ 阿里通义 │ aliyun │ dashscope.aliyuncs │ ****efgh │ ✓ │  │
│ │ 豆包 │ doubao_seedream │ ark.cn-beijing.volc │ ****1234 │ ✓ │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ ── 模型配置 ──                                          │
│ [+ 新建模型]                                            │
│ ┌────────────────────────────────────────────────────�  │
│ │ 名称 │ model │ 供应商 │ category │ 默认 │ 启用 │  │
│ ├────────────────────────────────────────────────────┤  │
│ │ GPT-4o │ gpt-4o │ OpenAI 主力 │ chat │ 全局 │ ✓ │  │
│ │ 通义千问 Turbo │ qwen-turbo │ 阿里通义 │ chat │ 类目 │ ✓ │  │
│ │ 提示词润色专用 │ qwen-turbo │ 阿里通义 │ image_polish │ 类目 │ ✓ │  │
│ └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 16.8 API 端点

#### Provider CRUD（`/admin/llm-providers/*`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/llm-providers` | 列表 |
| GET | `/admin/llm-providers/{id}` | 详情 |
| POST | `/admin/llm-providers` | 新建（含 api_key） |
| PUT | `/admin/llm-providers/{id}` | 更新 |
| DELETE | `/admin/llm-providers/{id}` | 删除（无关联 model 才允许） |
| POST | `/admin/llm-providers/{id}/test` | 测试连通性 |
| POST | `/admin/llm-providers/{id}/reveal` | 返回明文 API Key（仅管理员） |

#### Model CRUD（`/admin/llm-models/*`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/llm-models` | 列表（可按 category/provider 过滤） |
| GET | `/admin/llm-models/{id}` | 详情 |
| POST | `/admin/llm-models` | 新建 |
| PUT | `/admin/llm-models/{id}` | 更新 |
| DELETE | `/admin/llm-models/{id}` | 删除 |
| POST | `/admin/llm-models/{id}/set-default` | 设默认（body: `{category: optional}`） |
| POST | `/admin/llm-models/test` | 测试模型（不入库，临时调一次） |

### 16.9 对图像生成的影响

- **Phase 8（PromptPolisher）**：从「找标签为 image_gen_polish 的 LLMConfig」改成：
  ```python
  model = LLMModelService.get_default_model(category="image_polish")
  if not model: model = LLMModelService.get_default_model(category="chat")  # 兜底
  provider = model.provider
  # 用 provider.api_key + provider.base_url + model.model_name 调 LLM
  ```
- **Phase 1.5 必须在 Phase 2 之前完成**（其他工具会立即消费新接口）
- **Phase 8 引用新的 LLMModelService**

### 16.10 测试

- Migration 单元测试：构造 N 条老配置（含重复 API Key），跑迁移脚本，验证新表去重正确
- 消费方测试：mock LLMProviderService / LLMModelService，验证 llm_fallback 行为不变
- UI 测试：vitest + React Testing Library，验证 2 tabs 切换、对话框字段、新建/编辑/删除流程
- 端到端：用旧 LLMConfig 数据跑一遍 chat，确认行为不变

---

## 附录 A：术语

| 术语 | 含义 |
|---|---|
| text2img | 文生图 |
| img2img | 图生图 |
| inpaint | 局部重绘 |
| upload_edit | 上传编辑 |
| OSS | 阿里云对象存储 |
| Dify | 外部部署的 LLM 应用编排平台 |
| 降级 | 服务连续失败后主动禁用一段时间 |
| 配额预留 | 在事务内递增计数器，防止并发超限 |

## 附录 B：相关文档

- `backend/app/services/llm_fallback.py`（现有 LLM 故障回退机制，提示词润色复用）
- `backend/app/services/oss_service.py`（现有 OSS 服务）
- `backend/app/services/image_downloader_service.py`（ImageDownloader 配额模型参考）
- `frontend/src/components/Tools/ImageDownloader.tsx`（图片工具参考）
- `frontend/src/i18n/locales/zh-CN.ts` / `en-US.ts`（国际化 key）

## 附录 C：Dify 部署现状（2026-08-23 实测）

实施前需先确认 Dify 工作空间已就绪。实测情况：

### C.1 基础设施（✅ 就绪）

| 项 | 详情 |
|---|---|
| Dify 版本 | 1.14.2 |
| 访问域名 | `https://dify.peanuthzm.com.cn`（SSL, letsencrypt） |
| API 端点 | `https://dify.peanuthzm.com.cn/v1`（返回 401 = 端点正常） |
| 部署路径 | `/data/programs/dify/current/` |
| systemd 服务 | `dify-api/web/worker/beat/plugin-daemon/weaviate`（全 active） |
| PostgreSQL | `dify` DB, user=postgres, 本地 5432 |
| Redis | 本地 6379, DB 3 |
| Weaviate | 本地 18180（向量） |
| MinIO | `https://minio.peanuthzm.com.cn`, bucket `dify-files`（Dify 文件存储） |
| nginx 上传限制 | `client_max_body_size 100M` |
| nginx 代理超时 | `proxy_read_timeout 120s`, `proxy_send_timeout 120s`（图像生成够用，但 SDXL 大图如超 120s 需调整） |
| 管理员账号 | `peanut_hzm@163.com` |
| 租户 | "Dify Workspace" |

### C.2 工作空间（❌ 待初始化）

| 项 | 状态 | 实施前必须完成 |
|---|---|---|
| Apps/Workflows | 0 个 | 创建 4 个工作流（text2img/img2img/inpaint/upload_edit） |
| 模型供应商 | 0 个 | 在 Dify 后台添加模型（豆包/通义万相/DALL-E/SDXL 等） |
| API Token | 0 个 | 生成 1 个 App API Key 配到本项目的 `.env` |

### C.3 实施前置步骤（实施 plan 阶段 0）

1. 登录 Dify 管理后台：`https://dify.peanuthzm.com.cn`
2. 在「模型供应商」中添加所需的图像生成模型（API Key 来自各厂商）
3. 按 §4 设计创建 4 个工作流，每个工作流配置 input/output 变量与业务节点
4. 在 Dify「应用 API」生成 App API Key
5. 把 Key + Workflow ID 配到本项目的 `.env`（或管理后台）
6. 测试 `/v1/info` 鉴权通过（即 API 可达）

### C.4 性能边界备忘

- nginx `proxy_read_timeout=120s` 是图像生成硬上限；如某模型常态超 120s，需调整 nginx
- Dify 工作流内部节点级超时建议设为 60s，工作流整体超时由本应用 `DIFY_WORKFLOW_TIMEOUT` 控制（默认 60s，后台可调）
- 单文件上传上限 10MB（应用层限制），OSS 签名 URL 300s 有效（Dify 需在此时间内拉取参考图）
