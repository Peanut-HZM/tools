# 自研图像生成 Agent 设计

> **状态：** 设计稿，待用户审阅
> **日期：** 2026-08-23
> **目标读者：** 本项目开发者、维护者

## 1. 背景与目标

### 1.1 背景

当前 `tools` 项目的图像生成功能完全依赖 Dify Chatflow 工作流：
- 后端通过 `dify_client` 调 `POST {api_url}/chat-messages`
- Dify 工作流内部集成 LLM（负责多轮追问、prompt 润色）和外部图像生成 API（通义万相 / 海螺 / 豆包 / DALL-E）
- 历史对话由 Dify 托管，前端通过 `conversation_id` 与 Dify 同步

Dify 路径存在两个问题：
1. **可用性不稳定**：Dify 实例偶发不可用（已观测到 sign-in 502）
2. **配置入口分散**：图像生成模型配置在 Dify 端，LLM API key 配置在 `/admin/llm-configs`，管理分散

### 1.2 目标

新增 **自研图像生成 Agent** 路径：
- 完全用本项目代码实现多轮对话 + 图像生成编排
- 所有模型（对话大脑、图像生成、参考图理解）统一从 `/admin/llm-configs` 读取配置
- 模型按类型分类：文本 / 语音 / 视觉 / 全模态 / 向量 / 图像生成
- 全局统一的**有序模型兜底链**：每次调用按 `priority` 升序逐个试，失败自动跳下一个
- 图像生成可用的 provider：豆包 Seedream、通义万相、海螺、DALL-E 3
- 自研路径与 Dify 路径并存，**用户在图像生成工具页面可自由切换**

### 1.3 非目标（v1 不做）

- 不实现语音 / 视觉 / 多模态 / 向量模型的 adapter（仅扩展 LLMCategory 枚举）
- 不做熔断器（circuit breaker），仅失败跳下一个
- 不做用户级对话导出 / 导入
- 不解决多用户并发同一 conversation_id 的竞态
- 不重做配额计费（沿用"一次生成 = 1 配额单位"，与 Dify 一致）
- 不重构 Dify 路径代码（仅做 strategy 包装）

## 2. 架构概览

### 2.1 核心抽象

把"图像生成后端"抽象为一个 strategy。Dify 与自研两条路径都实现同一接口；service 层通过后端注册表按请求参数分发。模型选择走全局有序兜底链，由升级后的 `OrderedLLMGateway` 统一处理。

```
┌────────────────── Frontend ──────────────────┐
│  Image Gen Tool Page                          │
│  ┌──────────────────────┐                     │
│  │ BackendSwitch:       │                     │
│  │ [Dify] [自研 Agent]  │ ← localStorage 记忆 │
│  └──────────────────────┘                     │
│  Text2Img / Img2Img / Inpaint / UploadEdit    │
│  （沿用现对话版 UI，传 backend= 参数）         │
└───────────────────────────────────────────────┘
                 │ POST /api/image-generation/chat
                 │   {backend: "dify" | "selfdev", ...}
                 ▼
┌────────────────── Backend ────────────────────┐
│ routes/image_generation.py                    │
│   └─► ImageGenerationService.chat_generate()  │
│         │                                      │
│         ├─► quota_svc.check_and_reserve()      │
│         ├─► backend_registry[backend].run(ctx) │
│         │      ├─ DifyBackend                 │
│         │      └─ SelfDevelopedBackend        │
│         │           ├─► AgentOrchestrator     │
│         │           │     ├─► OrderedLLMGateway│
│         │           │     │   ├─ chat (brain) │
│         │           │     │   └─ image_gen    │
│         │           │     └─► ToolExecutor    │
│         │           │           └─► generate_image
│         │           ├─► OSS 上传              │
│         │           └─► history              │
│         ├─► quota_svc.commit() / release()    │
│         └─► history_svc.create_record()       │
└───────────────────────────────────────────────┘
```

### 2.2 关键不变量

1. **quota / OSS / history 仍是 `ImageGenerationService` 的职责**——后端类只负责"拿到图像 + 拿到对话回复"，共享逻辑不重复。
2. **`BackendResult` 是统一返回类型**，字段：`image_urls`, `answer_text`, `conversation_id`, `model_used`, `backend`。两个后端都要遵守。
3. **后端切换对 quota / history 一致**：Dify 与自研共用同一张 `image_gen_history` 表，区分字段是 `backend` 列。
4. **OrderedLLMGateway 是唯一的模型调用入口**——所有调用 LLM 的场景（chat、image_polish、image_gen、未来 voice/vision/multimodal/embedding）都通过它，按 category + priority 派发。

## 3. 模块拆分

| 模块 | 路径 | 职责 | 不做什么 |
|---|---|---|---|
| `BackendRegistry` | `app/services/image_gen/backends.py` | 维护 `{"dify": DifyBackend, "selfdev": SelfDevelopedBackend}` 映射 | 不知道请求参数、业务逻辑 |
| `IImageGenerationBackend` | `app/services/image_gen/base.py` | 接口：`async run(ctx) -> BackendResult` | 不做 quota / OSS / history |
| `DifyBackend` | `app/services/image_gen/dify_backend.py` | 包装现有 `dify_client.chat_*` 调用，转换为 `BackendResult` | — |
| `SelfDevelopedBackend` | `app/services/image_gen/selfdev_backend.py` | 调 `AgentOrchestrator` 完成对话+生成 | 不直接调 image-gen adapter |
| `AgentOrchestrator` | `app/services/image_gen/agent_orchestrator.py` | 维护对话循环：发 brain → 解析 tool_call → 执行 → 喂结果 → 收尾 | 不知道 image-gen 细节、OSS |
| `ToolExecutor` | `app/services/image_gen/tool_executor.py` | 收到 `generate_image` tool_call → 走有序兜底链选 image-gen adapter → 调 → 上传 OSS | 不维护对话状态 |
| `OrderedLLMGateway` | `app/services/llm_fallback.py`（重写） | 给定 category + 调用参数，按 `priority` 顺序逐个试，失败跳下一个 | 不感知业务上下文 |
| `ImageGenAdapter` | `app/services/llm/image_gen_base.py` + 4 个具体类 | 与 `LLMProvider` 平级，封装各家图像生成 API | 不维护 quota / OSS |
| `ImageGenFactory` | `app/services/llm/image_gen_factory.py` | `provider_type` → adapter 类映射 | — |

**Files that change together live together**——按职责切分，不按技术层。

## 4. 数据流

### 4.1 自研路径多轮对话主流程

```
POST /api/image-generation/chat
{backend: "selfdev", query, conversation_id?, operation, files?}

↓
ImageGenerationService.chat_generate()
│
├─ 1. quota_svc.check_and_reserve(user_id, op)   # 先占位，无论后续结果

├─ 2. BackendRegistry.get(backend).run(ctx)
│     ↓
│  SelfDevelopedBackend.run(ctx)   # 或 DifyBackend.run(ctx)，两条路径接口一致
│     │
│     ├─ 2.1 加载/初始化对话
│     │     - ctx.conversation_id 为空 → 生成新 UUID
│     │     - 自研路径：从 image_gen_conversations 表查历史消息
│     │     - Dify 路径：Dify 自己托管，无需本步
│     │
│     ├─ 2.2 把用户消息追加到 messages（自研路径）
│     │
│     ├─ 2.3 循环（最多 5 轮）
│     │     ├─ 组装 messages：system + history + tools
│     │     │     tools = [{ name: "generate_image", ... }]
│     │     │
│     │     ├─ OrderedLLMGateway.generate(
│     │     │     category="chat", messages, tools)
│     │     │     → LLMResponse(content, tool_calls?)
│     │     │
│     │     ├─ 若 tool_calls 含 generate_image：
│     │     │     ├─ ToolExecutor.execute(call)
│     │     │     │     ├─ 解析 op / prompt / size / 参考图 URL 等
│     │     │     │     ├─ 若 reference_image_url 在 OSS：直接用
│     │     │     │     ├─ 若 reference_image_url 是用户上传的临时 URL：先下载
│     │     │     │     ├─ OrderedLLMGateway.generate(
│     │     │     │     │     category="image_gen", op, ...)
│     │     │     │     │     → ImageGenAdapter → 外部 API → 二进制图
│     │     │     │     ├─ 下载图 → 上传 OSS → 返回签名 URL 列表
│     │     │     │     └─ 返回 ToolResult(image_urls=[...])
│     │     │     ├─ 把 tool_call + tool_result 追加到 messages
│     │     │     └─ continue 循环
│     │     │
│     │     └─ 若无 tool_call：content 即最终回复，break
│     │
│     ├─ 2.4 自研路径：保存 messages 到 image_gen_conversations（每次轮次后落盘）
│     │
│     └─ 2.5 返回 BackendResult(
│              image_urls=[...],
│              answer_text=...,
│              conversation_id=...,
│              model_used=<实际调用的模型，仅记成功那一个>,
│              backend=<"dify"|"selfdev">)
│
├─ 3. quota_svc.commit() if image_urls 非空
│   quota_svc.release()   if image_urls 为空
│
├─ 4. history_svc.create_record(
│       backend="selfdev", conversation_id, image_urls, ...)
│
└─ 5. 返回 ChatResponse{conversation_id, answer, image_urls, model_used, status}
```

### 4.2 有序兜底链 OrderedLLMGateway

```
generate(category, **kwargs):
    factory = ImageGenFactory if category == "image_gen" else LLMFactory
    models = db.query(LLMModel)
                .filter(category=category, is_active=True, provider.is_active=True)
                .order_by(priority.asc(), id.asc()).all()

    failures = []
    for model in models:
        try:
            adapter = factory.get(
                provider_type=model.provider.provider_type,
                api_key=decrypt(model.provider.api_key_encrypted),
                base_url=model.provider.base_url,
                model_name=model.model_name,
                **model.request_params_dict,
            )
            result = adapter.generate(messages=..., tools=...)
            log.info(f"OK: model={model.id} priority={model.priority}")
            return result
        except RecoverableFailure as e:
            # 限速 / 网络 / 5xx / 超时 / 无额度 / OperationNotSupported
            log.warning(f"FAIL: model={model.id} reason={e}; trying next")
            failures.append((model.id, str(e)))
            continue
        except UnrecoverableFailure as e:
            # 鉴权失败 / 参数非法
            log.error(f"FATAL: model={model.id} reason={e}")
            raise

    raise AllModelsUnavailableError(failures)
```

**可恢复 vs 不可恢复分类（在 `app/services/llm/exceptions.py` 集中定义）：**

| 类型 | 异常 / 错误码 | 处理 |
|---|---|---|
| 可恢复 | `httpx.ConnectError` / `TimeoutException` / 429 / 5xx / `"quota"` / `"rate limit"` / `"insufficient balance"` / `OperationNotSupportedError` | 跳过，下一个 |
| 不可恢复 | 401 / 403 / 400（参数错） / `"invalid api key"` / `"model not found"` | 立即抛 |

### 4.3 Tool 定义（注册到 brain 的工具）

```json
{
  "name": "generate_image",
  "description": "生成或修改图像。可用操作：text2img（纯文本生图）、img2img（图生图，给参考图）、inpaint（局部重绘，要 mask）、upload_edit（上传图后做风格/编辑转换）。",
  "parameters": {
    "type": "object",
    "properties": {
      "operation": {"enum": ["text2img", "img2img", "inpaint", "upload_edit"]},
      "prompt":    {"type": "string", "description": "最终用于生成的提示词，应为润色过的英文短句"},
      "size":      {"enum": ["512x512","768x768","1024x1024","1024x1792","1792x1024"]},
      "n":         {"type": "integer", "minimum": 1, "maximum": 4, "default": 1},
      "reference_image_url": {"type": "string"},
      "mask_image_url":      {"type": "string"},
      "strength":  {"type": "number", "minimum": 0, "maximum": 1},
      "edit_type": {"enum": ["style","background","object_remove","object_replace"]}
    },
    "required": ["operation", "prompt"]
  }
}
```

### 4.4 后端切换协议

请求统一加 `backend` 字段：

```python
class ChatGenerateRequest:
    backend: Literal["dify", "selfdev"] = "selfdev"
    query: str
    conversation_id: Optional[str] = None
    operation: str
    reference_image: Optional[UploadFile] = None
    mask_image: Optional[UploadFile] = None
    size: str = "1024x1024"
    n: int = 1
```

**默认后端：** 客户端首屏未设置时，localStorage 为空 → 前端默认选中 "selfdev"（匹配用户"先做自研"意图）。如果所选后端未配置（selfdev 缺 chat 或 image_gen 模型 / dify 未启用），返回 503 + code=`BACKEND_NOT_CONFIGURED`，前端展示"该后端暂未配置，请去 /admin/llm-configs 配置"并提示用户切换。**不做自动 fallback**（用户明确选择哪个路径就只走那个）。

## 5. 数据模型改动

### 5.1 `LLMModel` 新增 `priority` 字段

```python
# backend/app/models/llm_model.py
class LLMModel(Base):
    __tablename__ = "llm_models"
    # ... 现有字段 ...
    priority: int = 100  # 越小越优先；同 priority 内按 id 稳定排序
```

迁移脚本 `backend/scripts/migrate_add_llm_model_priority.py`：

```sql
ALTER TABLE llm_models ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 100;
```

### 5.2 `LLMModel.category` 枚举扩展

新增 `backend/app/constants/llm_categories.py`：

```python
class LLMCategory:
    CHAT         = "chat"
    CODE         = "code"
    VOICE        = "voice"          # 新：语音合成/识别
    VISION       = "vision"         # 新：图像理解
    MULTIMODAL   = "multimodal"     # 新：图文混合输入/输出
    EMBEDDING    = "embedding"      # 新：向量
    IMAGE_POLISH = "image_polish"  # 把现有 polisher 用的字符串正式列入枚举
    IMAGE_GEN    = "image_gen"      # 新：实际图像生成
```

数据库是 String 列，无需迁移；只需前端下拉 + 后端校验扩展。

### 5.3 `LLMProvider.provider_type` 枚举扩展

```python
class LLMProviderType:
    # 文本/多模态 chat
    OPENAI       = "openai"
    ANTHROPIC    = "anthropic"
    AZURE_OPENAI = "azure_openai"
    BAIDU        = "baidu"
    ALIYUN       = "aliyun"        # 通义千问
    OTHER        = "other"

    # 图像生成（v1 新增）
    DOUBAO_SEEDREAM = "doubao_seedream"   # 字节豆包
    QWEN_IMAGE      = "qwen_image"        # 通义万相
    HAILUO          = "hailuo"            # 海螺 MiniMax       # 新
    OPENAI_IMAGE    = "openai_image"      # DALL-E 3           # 新
```

> 备注：`doubao_seedream` 和 `qwen_image` 已存在于当前 `provider_type` 例子中（原计划就有 image-gen provider），但对应 adapter 还没写，这次补齐。

### 5.4 `ImageGenRecord` 新增 `backend` 列

```python
# backend/app/models/image_generation_models.py
class ImageGenRecord(Base):
    # ... 现有字段 ...
    backend: str = "dify"  # "dify" | "selfdev"
```

迁移脚本 `backend/scripts/migrate_add_record_backend.py`：

```sql
ALTER TABLE image_gen_records ADD COLUMN IF NOT EXISTS backend VARCHAR(16) DEFAULT 'dify';
```

### 5.5 新表 `image_gen_conversations`（仅自研路径）

```python
class ImageGenSelfDevConversation(Base):
    __tablename__ = "image_gen_conversations"
    id: UUID primary key default=uuid4
    user_id: UUID indexed              # 用于权限校验
    conversation_id: str unique indexed # 对外暴露的 UUID 字符串
    operation: str                       # text2img / img2img / inpaint / upload_edit
    messages: JSON                       # list[Message dict]，每个 Message 形如：
                                       # {"role": "user"|"assistant"|"tool",
                                       #  "content": "...",
                                       #  "tool_calls": [{"id": "...", "name": "generate_image", "arguments": {...}}]?,  # 仅 assistant
                                       #  "tool_call_id": "..."}                                          # 仅 tool
    created_at, updated_at
```

表创建：跟 `llm_providers` / `llm_models` 同样通过 `Base.metadata.create_all` 在 `main.py` 启动时建。

## 6. Image-Gen Adapter 契约

### 6.1 抽象基类

新建 `app/services/llm/image_gen_base.py`（与 `LLMProvider` 平级，不共用基类——语义不同）：

```python
class ImageGenAdapter(ABC):
    @abstractmethod
    async def generate(
        self,
        operation: str,
        prompt: str,
        *,
        size: str = "1024x1024",
        n: int = 1,
        reference_image: Optional[bytes] = None,
        reference_mime: Optional[str] = None,
        mask_image: Optional[bytes] = None,
        mask_mime: Optional[str] = None,
        strength: Optional[float] = None,
        edit_type: Optional[str] = None,
        **provider_specific,
    ) -> list[bytes]:                       # 返回 N 张图的二进制列表
        ...

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]: ...
```

### 6.2 Factory

新建 `app/services/llm/image_gen_factory.py`：

```python
class ImageGenFactory:
    _REGISTRY: dict[str, type[ImageGenAdapter]] = {
        "doubao_seedream": DoubaoSeedreamAdapter,
        "qwen_image":      QwenImageAdapter,
        "hailuo":          HailuoAdapter,
        "openai_image":    OpenAIImageAdapter,
    }

    @classmethod
    def get(cls, provider_type, api_key, base_url, model_name, **kw):
        if provider_type not in cls._REGISTRY:
            raise UnknownProviderError(provider_type)
        return cls._REGISTRY[provider_type](
            api_key=api_key, base_url=base_url, model=model_name, **kw)
```

### 6.3 4 个 Adapter 的能力矩阵

| Adapter | text2img | img2img | inpaint | upload_edit | 备注 |
|---|---|---|---|---|---|
| **DoubaoSeedreamAdapter** | ✅ | ✅ | ✅ | ✅ | 主选；火山 ark API |
| **QwenImageAdapter** | ✅ | ✅ | ✅ | ⚠️ 部分 | 阿里 DashScope，task 异步轮询 |
| **HailuoAdapter** | ✅ | ⚠️ 部分 | ❌ | ❌ | MiniMax API；当前仅 text2img 稳定 |
| **OpenAIImageAdapter** | ✅ (DALL-E 3) | ❌ | ❌ | ❌ | 仅 text2img；不支持参考图（DALL-E 3 限制） |

**兜底行为：** 不支持 operation 时抛 `OperationNotSupportedError`（**可恢复**），OrderedLLMGateway 自动跳到下一个 image_gen 模型。

## 7. 错误处理矩阵

| 场景 | 触发 | HTTP | quota 处理 | 用户看到 |
|---|---|---|---|---|
| brain 所有模型失败 | chat 兜底链全跳过 | 503 | release | "所有对话模型暂不可用，请稍后重试" |
| image_gen 所有模型失败 | image_gen 兜底链全跳过 | 503 | release | "所有图像模型暂不可用，请稍后重试" |
| 单个 brain 不可恢复错误 | 401/400 | 500 | release | "对话模型配置异常，请联系管理员" |
| 单个 image_gen 不可恢复错误 | 401/400 | 500 | release | "图像模型配置异常，请联系管理员" |
| 用户配额已用完 | quota_svc 抛 QuotaExceededError | 429 | 不扣 | "今日配额已用完" |
| 缺参考图 | 请求里没文件 | 422 | 不扣 | "请上传参考图" |
| OSS 上传失败 | 下载/上传到 OSS 抛异常 | 500 | release | "图像存储失败，请重试" |
| brain 返回无法解析的 tool_call | JSON 解析失败 | 503 | release | "对话模型输出异常，已切换下一个" |
| tool-calling 循环超过 5 轮 | 防死循环 | 200 | 看是否生成过图 | 200 + 当前 best-effort 回复 + 日志告警 |
| conversation_id 不存在或非本用户 | 跨用户访问 | 404 | 不扣 | "对话不存在，请开启新对话" |
| 后端未配置 | 启动校验 / 启动时发现注册表为空 | 503 | release | "请先在 /admin/llm-configs 配置模型" |

**统一错误响应形态：**

```python
{
    "detail": "人类可读的错误信息",
    "code": "BRAIN_UNAVAILABLE" | "IMAGE_GEN_UNAVAILABLE"
          | "QUOTA_EXCEEDED" | "BACKEND_NOT_CONFIGURED" | ...,
    "retry_after_seconds": int | null,
}
```

## 8. 测试策略

### 8.1 单元测试（mock 外部 API）

| 文件 | 覆盖 |
|---|---|
| `test_ordered_gateway.py` | 有序遍历、可恢复跳过、不可恢复抛出、空列表报错 |
| `test_image_gen_factory.py` | provider_type → adapter 映射、未知类型报错 |
| `test_doubao_seedream_adapter.py` | 4 种操作 happy path + 异常分类 |
| `test_qwen_image_adapter.py` | 异步 task 提交 + 轮询 + 结果下载 |
| `test_hailuo_adapter.py` | text2img happy + unsupported op |
| `test_openai_image_adapter.py` | DALL-E 3 + img2img 抛 OperationNotSupported |
| `test_selfdev_backend.py` | mock gateway + tool executor，跑完整对话循环 |
| `test_agent_orchestrator.py` | tool-call 解析、最大循环数、brain 失败回退 |
| `test_tool_executor.py` | image-gen 调通、OSS 上传、不可恢复错误传播 |
| `test_backend_registry.py` | 查表、不存在报错 |
| `test_image_gen_conversation_repo.py` | 自研对话 CRUD + 用户隔离 |

### 8.2 集成测试

| 文件 | 覆盖 |
|---|---|
| `test_chat_route_selfdev.py` | `/api/image-generation/chat?backend=selfdev` 全流程 |
| `test_chat_route_backend_param.py` | 同路由 backend=dify vs selfdev 两条路径都跑通 |
| `test_chat_route_quota.py` | 自研路径 quota reserve / commit / release |
| `test_chat_route_conversation.py` | conversation_id 跨轮次保持、多用户隔离 |
| `test_priority_ordering.py` | mock 3 个 model，第一个 429 → 第二个 200 即可 |

### 8.3 前端测试

| 文件 | 覆盖 |
|---|---|
| `BackendSwitch.test.tsx` | 切换、localStorage 写入/读取、默认值 |
| `useImageGenerate.test.ts` | 传递 backend 参数到 API |
| `ModelsTab.test.tsx` | 列表展示 priority 列 |
| `ModelDialog.test.tsx` | 提交 priority、新 category 下拉 |

## 9. 迁移步骤

```
M1. 模型扩展（不改行为）
    - 加 LLMCategory / LLMProviderType 常量文件
    - 加 priority 字段到 LLMModel + migration 脚本
    - 加 backend 列到 ImageGenRecord + migration 脚本
    - 加 image_gen_conversations 表（main.py create_all）

M2. 前端 admin UI 改造
    - llmModelApi.ts 类型扩展
    - ModelsTab + ModelDialog 加 priority、新 category 下拉
    - 默认值：priority=100，category 仍是 chat/code

M3. 适配层骨架（不接业务）
    - ImageGenAdapter 抽象基类
    - ImageGenFactory
    - 4 个 adapter 的最小实现（mock 跑通 happy path）

M4. 有序兜底链升级
    - 新建 `app/services/llm/exceptions.py`（RecoverableFailure / UnrecoverableFailure / AllModelsUnavailableError / UnknownProviderError / OperationNotSupportedError）
    - LLMFallbackService 重构为 OrderedLLMGateway
    - 加 image_gen 路径分发到 ImageGenFactory
    - 加可恢复 / 不可恢复错误分类
    - 现有 chat / image_polish 调用全部走新 gateway（行为不变）

M5. 后端 strategy 拆分
    - IImageGenerationBackend 接口
    - DifyBackend（包装现有调用）
    - SelfDevelopedBackend（AgentOrchestrator + ToolExecutor）
    - BackendRegistry
    - ImageGenerationService 接入注册表分发

M6. 自研核心逻辑
    - AgentOrchestrator：消息循环、tool_call 解析、最大轮次
    - ToolExecutor：image_gen tool 调用、参考图处理、OSS 上传
    - 失败处理按错误矩阵

M7. 路由与持久化
    - /chat 路由加 backend 参数
    - conversation_id 处理（Dify vs 自研各自的存储路径）
    - quota / history 接入自研路径

M8. 前端整合
    - BackendSwitch 组件
    - useImageGenerate / imageGenerationApi 加 backend 参数
    - Text2Img / Img2Img / Inpaint / UploadEdit 表单接入

M9. 测试与文档
    - 单元 + 集成 + 前端测试全部到位
    - 更新 image-gen 用户文档
```

每步独立 commit、可单独回滚。**M1-M2 先合**，让 admin 能配置新分类；**M3-M4 合**让兜底链基础设施可用；**M5-M8 是核心**，按顺序合；**M9 收尾**。

## 10. 主要风险与开放问题

| 风险 | 影响 | 缓解 |
|---|---|---|
| Hailuo API 实际端点 / 鉴权方式需确认 | adapter 实现延后 | M3 阶段先 mock 占位，真实接入推迟到用户首次配置时验证 |
| Qwen Wanxiang 是 task 异步模式 | adapter 复杂 | adapter 内部用 `httpx.AsyncClient` + 轮询循环封装，对外仍是 `async def generate() -> list[bytes]` |
| OpenAI / Anthropic / 通义的 tool-call 消息格式略有差异 | AgentOrchestrator 适配 | OrderedLLMGateway 出口做一层 provider-agnostic 规范化（统一为 `{role, content, tool_calls, tool_call_id}`），下游再分发 |
| Brain 中途切换 chat 模型时历史上下文丢失 | 用户感受到"AI 换了一个人" | OrderedLLMGateway 自动重发完整 messages 历史给新模型；这是 OpenAI/Anthropic 通用的无状态调用模式，自动 work |
| 自研 conversation_id 与 Dify 的 conversation_id 冲突 | API 层歧义 | 两者使用独立 UUID 命名空间；前端无需区分，存到 `image_gen_records.conversation_id` 列 |
| 配额按 `n` 张数计费的语义不直观 | 用户可能误以为"扣了 4 张" | v1 与 Dify 行为一致；后续做计费页面时再统一调整 |

## 11. 关键接口签名

```python
# app/services/image_gen/base.py
class IImageGenerationBackend(ABC):
    @abstractmethod
    async def run(self, ctx: BackendContext) -> BackendResult: ...

@dataclass
class BackendContext:
    user_id: UUID
    operation: str                    # "text2img" | ...
    query: str
    conversation_id: Optional[str]
    reference_image: Optional[bytes]
    reference_mime: Optional[str]
    mask_image: Optional[bytes]
    mask_mime: Optional[str]
    size: str
    n: int
    strength: Optional[float]
    edit_type: Optional[str]

@dataclass
class BackendResult:
    image_urls: list[str]             # OSS 签名 URL，可能为空
    answer_text: str                  # 给用户看的回复
    conversation_id: str              # 后端生成的 UUID
    model_used: str                   # 实际调用的模型
    backend: str                      # "dify" | "selfdev"

# app/services/image_gen/backends.py
class BackendRegistry:
    _REGISTRY: dict[str, IImageGenerationBackend] = {}

    @classmethod
    def register(cls, name: str, backend: IImageGenerationBackend): ...

    @classmethod
    def get(cls, name: str) -> IImageGenerationBackend:
        if name not in cls._REGISTRY:
            raise BackendNotConfiguredError(name)
        return cls._REGISTRY[name]
```

---

**End of spec.** 待用户审阅。