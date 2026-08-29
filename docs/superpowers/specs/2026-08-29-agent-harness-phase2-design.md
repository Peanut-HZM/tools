# Agent Harness Phase 2 — 全面重构设计文档

**日期**: 2026-08-29
**状态**: 设计中（待实现）
**前置依赖**: Phase 1（已完成，20 tasks，36 commits）

## 1. 目标

用 harness 统一纳管所有 agent 能力，彻底消除 Dify 依赖。所有对话走同一个 Agent → AgentRuntime → SSE 通道，工具调用通过 BuiltinTool 扩展。

### 交付物

1. **自研图生**：ImageModelProvider 接口 + 3 种 provider 实现 + image_gen BuiltinTool
2. **Memory long-term**：memory_read/memory_write BuiltinTool + DB 存储
3. **流量切换 + Dify 删除**：渐进式切换 → 验证 → 清理
4. **加固**：Guardrail 审计字段 + 日志脱敏 + error_strategy=retry

## 2. 范围

### 在范围内

| 能力 | 当前状态 | Phase 2 目标 |
|------|----------|-------------|
| 文本对话 | ✅ 已迁移 harness（Phase 1） | 保持 |
| DB 查询 | ✅ 已迁移 harness（Phase 1） | 保持 |
| 网络搜索 | ✅ 已迁移 harness（Phase 1） | 保持 |
| 图像生成（4 种操作） | ❌ 走 Dify workflow/chatflow | 迁移到 harness image_gen BuiltinTool |
| 多轮图生对话 | ❌ 走 Dify chatflow | 统一走 Agent + image_gen 工具 |
| Memory long-term | ⚠️ DB 字段已有，无实现 | memory_read/memory_write BuiltinTool |
| Guardrail 审计 | ⚠️ 部分字段未覆盖 | 扩展审计字段 + 日志脱敏 |
| error_strategy | ⚠️ 仅 fallback_message | 实现 retry + max_retries |

### 不在范围内（留给 Phase 3）

- Memory long-term 向量检索（pgvector）
- MCP tools 接入
- Checkpoint / Resume
- Langfuse / OpenTelemetry 集成

## 3. 架构

### 架构层次

```
┌──────────────────────────────────────────────────────────┐
│  Frontend (React)                                        │
│  ┌──────────┐ ┌──────────────┐ ┌────────────────────┐   │
│  │ Chat UI  │ │ToolRenderers │ │ ImageGenRenderer   │   │
│  │ (existing│ │(WebSearch/   │ │ (新增)             │   │
│  │  SSE)    │ │ DbQuery)     │ │                    │   │
│  └──────────┘ └──────────────┘ └────────────────────┘   │
├──────────────────────────────────────────────────────────┤
│  chat_stream SSE (已迁移到 harness, Phase 1)             │
├──────────────────────────────────────────────────────────┤
│  AgentRuntime                                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ LLM      │ │ Memory   │ │ Guardrail│ │ Handoff   │  │
│  │ Bridge   │ │ short+   │ │ + Audit  │ │           │  │
│  │          │ │ long-term│ │          │ │           │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
├──────────────────────────────────────────────────────────┤
│  ToolRegistry                                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │web_search│ │db_query  │ │image_gen │ │memory_    │  │
│  │(Phase 1) │ │(Phase 1) │ │(Phase 2) │ │read/write │  │
│  │          │ │          │ │          │ │(Phase 2)  │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
├──────────────────────────────────────────────────────────┤
│  Model Layer (复用现有 LLMProvider/LLMModel)             │
│  ┌────────────────────────────────────────────────────┐  │
│  │ LLMProvider: openai/anthropic/aliyun/doubao_seed/  │  │
│  │              qwen_image/minimax_image/...          │  │
│  │ LLMModel: category=text/vision/image_gen/...      │  │
│  │            priority → fallback chain               │  │
│  └────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────┤
│  ImageModelProvider (新增接口)                           │
│  ┌──────────────┐ ┌────────────┐ ┌───────────────────┐  │
│  │TongyiWanxiang│ │ Hailuo     │ │ DoubaoSeedream    │  │
│  │Provider      │ │ Provider   │ │ Provider          │  │
│  └──────────────┘ └────────────┘ └───────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 关键设计决策

1. **Model Config 复用**（方案 A）：ImageModelProvider 不新建 DB 表，直接从 `LLMProvider`/`LLMModel` 读取配置。现有 DB 已有 `category="image_gen"` 和 `doubao_seedream`/`qwen_image` provider_type，几乎为这个场景预制。
2. **统一通道**：图生对话走同一个 chat/stream SSE，`image_generated` 事件 + 前端新渲染器。
3. **Prompt 润色**：在 image_gen BuiltinTool 内部通过 OrderedLLMGateway 调 LLM 完成（中文→英文 + 质量优化）。
4. **Fallback 链**：AgentRuntime 调用 image_gen → 失败时按 `fallback_model_ids` 顺序尝试下一个 provider。
5. **Memory long-term**：Phase 2 先做 key-value（per-user per-agent），pgvector 留给 Phase 3。

## 4. ImageModelProvider 接口

### 4.1 抽象接口

```python
# backend/app/services/harness/image_provider/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ImageGenParams:
    """图像生成参数"""
    size: str = "1024x1024"
    n: int = 1
    style: Optional[str] = None
    model_name: str = ""           # 来自 LLMModel.model_name
    request_params: dict = field(default_factory=dict)  # 来自 LLMModel.request_params


@dataclass
class ImageGenResult:
    """图像生成结果"""
    image_urls: List[str]          # 生成的图片 URL 列表（OSS）
    model_used: str                # 实际使用的模型标识
    revised_prompt: str = ""       # provider 修改后的 prompt（如有）
    elapsed_seconds: float = 0.0


class ImageGenError(Exception):
    """图像生成错误，携带可重试标记"""
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class ImageModelProvider(ABC):
    """图像生成 Provider 抽象接口"""

    def __init__(self, base_url: str, api_key: str, oss_client=None):
        self.base_url = base_url
        self.api_key = api_key
        self.oss_client = oss_client

    @abstractmethod
    async def text2img(self, prompt: str, params: ImageGenParams) -> ImageGenResult:
        """文生图"""

    @abstractmethod
    async def img2img(self, prompt: str, reference_image: str, params: ImageGenParams) -> ImageGenResult:
        """图生图（reference_image 为 OSS URL）"""

    @abstractmethod
    async def inpaint(self, prompt: str, image_url: str, mask_url: str, params: ImageGenParams) -> ImageGenResult:
        """局部重绘"""

    @abstractmethod
    async def upload_edit(self, image_url: str, instruction: str, params: ImageGenParams) -> ImageGenResult:
        """上传编辑（指令式）"""

    @abstractmethod
    def validate_config(self) -> None:
        """校验 provider 配置是否可用（启动时调用）"""
```

### 4.2 Provider Registry

```python
# backend/app/services/harness/image_provider/registry.py

from typing import Dict, Type

_PROVIDER_MAP: Dict[str, Type[ImageModelProvider]] = {
    "qwen_image": TongyiWanxiangProvider,
    "minimax_image": HailuoProvider,
    "doubao_seedream": DoubaoSeedProvider,
}


def resolve_provider(llm_provider, oss_client=None) -> ImageModelProvider:
    """从 LLMProvider.provider_type 解析到具体实现"""
    cls = _PROVIDER_MAP.get(llm_provider.provider_type)
    if cls is None:
        raise ImageGenError(f"图像 Provider 不支持: {llm_provider.provider_type}")
    return cls(
        base_url=llm_provider.base_url,
        api_key=decrypt_api_key(llm_provider.api_key_encrypted),
        oss_client=oss_client,
    )
```

### 4.3 Provider 实现

| Provider | provider_type | API 基础 | 优先级 |
|----------|---------------|----------|--------|
| `TongyiWanxiangProvider` | `qwen_image` | 阿里云 DashScope API | 最高（已有 OSS 集成） |
| `HailuoProvider` | `minimax_image` | MiniMax / 海螺 API | 中（需新增 provider_type） |
| `DoubaoSeedProvider` | `doubao_seedream` | 字节火山引擎 API | 中（已有 provider_type） |

每个 Provider 内部行为：
- 用 `httpx.AsyncClient` 异步调用外部 API
- 下载生成图片 → 上传到自有 OSS → 返回 OSS URL
- 错误分类：`retryable`（超时/限流/5xx）或 `fatal`（鉴权失败/参数错误/余额不足）
- retryable 错误触发 fallback 链尝试下一个 provider

### 4.4 Fallback 链工作流

```
image_gen BuiltinTool 被 AgentRuntime 调用
  → 从 Agent.default_model_id 读取主模型 LLMModel
  → resolve_provider(llm_model.provider)
  → provider.text2img(...)
  → 如果 ImageGenError(retryable=True):
      → 按 Agent.fallback_model_ids 顺序尝试下一个
      → 直到成功或全部耗尽
  → 全部失败 → 返回 ToolResult(success=False, error="所有图像模型均不可用")
```

### 4.5 Prompt 润色

在 `image_gen` BuiltinTool 的 `execute()` 内部，调用 provider 之前：

1. 通过 `OrderedLLMGateway` 调用一个 LLM（text 类模型）
2. System prompt: "将以下中文描述转化为高质量的英文图像生成 prompt，保留关键细节，优化构图描述"
3. 润色后的 prompt 传给 provider
4. 润色 prompt 记录在 trace 中（便于调试）
5. 如果 LLM 不可用（超时/错误），直接用原始中文 prompt 调用（不阻塞生成）

## 5. image_gen BuiltinTool

### 5.1 工具 Schema（对 LLM 暴露）

```json
{
  "name": "image_gen",
  "description": "生成或编辑图像。支持文生图、图生图、局部重绘、指令编辑四种操作。",
  "parameters": {
    "type": "object",
    "required": ["operation", "prompt"],
    "properties": {
      "operation": {
        "type": "string",
        "enum": ["text2img", "img2img", "inpaint", "upload_edit"],
        "description": "操作类型"
      },
      "prompt": {
        "type": "string",
        "description": "图像描述或编辑指令（中文即可，系统自动润色为英文）"
      },
      "reference_image_url": {
        "type": "string",
        "description": "参考图片 URL（img2img 时必填）"
      },
      "mask_url": {
        "type": "string",
        "description": "遮罩图片 URL（inpaint 时必填）"
      },
      "size": {
        "type": "string",
        "enum": ["1024x1024", "1024x1792", "1792x1024", "512x512"],
        "default": "1024x1024"
      },
      "n": {
        "type": "integer",
        "minimum": 1,
        "maximum": 4,
        "default": 1
      },
      "style": {
        "type": "string",
        "description": "风格预设（可选）"
      }
    }
  }
}
```

### 5.2 执行流程

```
image_gen.execute(arguments, context)
  │
  ├── 1. 参数校验（operation 与必填字段匹配）
  │
  ├── 2. Prompt 润色（LLM 调用，可降级跳过）
  │     └── 中文 → 英文 + 构图优化
  │
  ├── 3. 模型选择 + Fallback 链
  │     ├── 主模型: Agent.default_model_id → LLMModel → resolve_provider()
  │     ├── 备选: Agent.fallback_model_ids 按 priority 排序
  │     └── 每个 provider 尝试 → retryable error 则切换下一个
  │
  ├── 4. 调用 provider.{operation}(revised_prompt, params)
  │     └── 返回 ImageGenResult { image_urls, model_used, revised_prompt }
  │
  ├── 5. 结果组装
  │     ├── ToolResult.content = { operation, model_used, revised_prompt }
  │     ├── ToolResult.attachments = [Attachment(type="image", url=oss_url)]
  │     └── emit image_generated 事件（含 attachments + model_used）
  │
  └── 6. 返回 ToolResult(success=True)
```

### 5.3 前端渲染：ImageGenRenderer

```
ToolCallRenderer dispatch → registry.get("image_gen") → ImageGenRenderer
  │
  ├── 显示 operation badge（文生图/图生图/局部重绘/指令编辑）
  ├── 显示 model_used 标签
  ├── 显示 revised_prompt（可折叠）
  ├── 图片网格渲染（1-4 张）
  │   └── 每张图片：缩略图 + 点击放大 + 下载按钮
  └── 失败时显示 error message
```

## 6. Memory Long-term

### 6.1 设计定位

- Phase 2: 简单 key-value 存储，Agent 通过 `memory_read`/`memory_write` BuiltinTool 主动读写
- Phase 3: 可扩展到 pgvector 向量检索（本次不做）

### 6.2 DB 表

```sql
-- 新增表 agent_memory_long_term
CREATE TABLE agent_memory_long_term (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id),
    user_id UUID NOT NULL REFERENCES users(id),
    key VARCHAR(200) NOT NULL,
    value JSONB NOT NULL DEFAULT '{}',
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(agent_id, user_id, key)
);
```

### 6.3 BuiltinTool Schema

**memory_read:**

```json
{
  "name": "memory_read",
  "description": "读取当前用户的长期记忆。不传 key 则返回所有记忆条目。",
  "parameters": {
    "type": "object",
    "properties": {
      "key": {
        "type": "string",
        "description": "记忆键名（可选，不传则返回全部）"
      }
    }
  }
}
```

**memory_write:**

```json
{
  "name": "memory_write",
  "description": "写入或更新一条长期记忆。相同 key 会被覆盖。",
  "parameters": {
    "type": "object",
    "required": ["key", "value"],
    "properties": {
      "key": {
        "type": "string",
        "description": "记忆键名"
      },
      "value": {
        "type": "object",
        "description": "记忆内容（JSON 对象）"
      },
      "summary": {
        "type": "string",
        "description": "可选摘要"
      }
    }
  }
}
```

### 6.4 执行逻辑

- `memory_read`: 从 `agent_memory_long_term` 表按 (agent_id, user_id, key) 查询 → 返回 JSON
- `memory_write`: UPSERT 到 `agent_memory_long_term` 表 → 返回确认
- 权限隔离：user_id 从 session context 获取，Agent 只能读写当前用户的记忆
- 大小限制：单条 value ≤ 10KB，每 (agent_id, user_id) 最多 100 条

### 6.5 Agent 配置控制

- `Agent.memory_long_term_enabled`（Phase 1 已加 DB 字段）= true 时，memory_read/memory_write 才注册到该 Agent 的 ToolRegistry
- `Agent.memory_long_term_config`（Phase 1 已加）可配置限制（max_entries, max_value_size 等）

## 7. 流量切换 + Dify 删除

### 7.1 三阶段渐进式切换

```
阶段 1: 双写（Feature Flag 控制）
├── 新请求同时走 harness image_gen 和 Dify（但只返回 harness 结果）
├── 对比两者结果一致性（日志记录差异）
├── 持续 1 周观察

阶段 2: 主切
├── 关闭 Dify 路径，所有图生流量走 harness
├── 保留 Dify 代码但不调用（feature flag = "harness_only"）
├── 持续 1 周验证稳定性

阶段 3: 清理
├── 删除所有 Dify 相关代码
├── 删除 Dify DB 配置数据
├── 删除 admin 页面中的 Dify 配置入口
```

### 7.2 Feature Flag

```python
# backend/app/config/config.py 新增
IMAGE_GEN_BACKEND = os.getenv("IMAGE_GEN_BACKEND", "dify")
# "dify"    — 全走 Dify（初始默认，安全回滚位）
# "harness" — 全走 harness（验证稳定后切换为目标状态）
# "dual"    — 双写对比（阶段 1 验证用）
```

### 7.3 Dify 删除清单

**后端文件**（阶段 3 删除）：

| 文件 | 说明 |
|------|------|
| `app/services/dify_client.py` | Dify API 客户端 |
| `app/services/dify_config_service.py` | Dify 配置管理 |
| `app/services/image_gen/dify_backend.py` | Dify 后端适配器 |
| `app/services/image_gen/base.py` | 旧 backend 抽象层 |
| `app/routes/image_generation.py` | 旧图像生成路由 |
| `app/routes/admin_image_generation.py` | Dify 配置 admin 路由 |
| `app/models/image_generation_models.py` | 旧图像生成模型 |
| `app/models/image_gen_conversation.py` | Dify chatflow 会话模型 |
| `app/utils/image_gen_constants.py` | Dify 相关常量 |
| `app/core/exceptions.py` 中 DifyError | Dify 异常类 |

**测试文件**（对应删除）：

| 文件 |
|------|
| `tests/test_dify_backend.py` |
| `tests/test_dify_client.py` |
| `tests/test_dify_config_service.py` |
| `tests/test_image_generation_*.py`（旧路径测试） |
| `tests/test_chat_text2img.py` |

**前端**：
- admin 页面中的 Dify 配置入口删除
- 现有 ImageGenRenderer（§5.3 新建）替代旧图像结果渲染

**保留**：
- `app/services/image_generation_service.py` 中与 OSS/历史相关的逻辑（迁移到 harness 或独立服务）
- `app/services/image_gen_history_service.py`（历史记录与 Dify 无关）

### 7.4 DB 清理

- `llm_providers` 表中无 Dify 相关 provider_type，无需清理
- `image_gen_conversations` 表（Dify chatflow 会话）→ 删除表 + migration
- 旧 `image_generation_*` 相关表 → 根据是否被 harness 替代决定保留/删除

## 8. 加固项（Phase 1 Deferred）

### 8.1 Guardrail 审计字段完整性

扩展 `_GUARDRAIL_FIELDS` 覆盖所有可修改字段：

```python
# backend/app/api/routes/agents.py
_GUARDRAIL_FIELDS = {
    # 现有字段...
    "can_handoff_to",
    "handoff_instruction",
    "max_steps_per_turn",
    "memory_long_term_enabled",
    "memory_long_term_config",
}
```

修改这些字段时记录审计日志（before/after 状态）。

### 8.2 Guardrail 审计日志脱敏

```python
_REDACTED_FIELDS = {"api_key", "api_key_encrypted", "secret", "password"}

def sanitize_audit_log(changes: dict) -> dict:
    """审计日志脱敏：敏感字段只保留前4字符"""
    sanitized = {}
    for key, (old, new) in changes.items():
        if key.lower() in _REDACTED_FIELDS:
            old_s = f"{str(old)[:4]}..." if old else None
            new_s = f"{str(new)[:4]}..." if new else None
            sanitized[key] = (old_s, new_s)
        else:
            sanitized[key] = (old, new)
    return sanitized
```

### 8.3 error_strategy=retry + max_retries

```python
# backend/app/services/harness/agent_runtime.py
async def _execute_tool_with_retry(self, tool, arguments, agent):
    max_retries = agent.max_retries if agent.error_strategy == "retry" else 0

    for attempt in range(max_retries + 1):
        try:
            result = await tool.execute(arguments, context)
            if result.success:
                return result
            if not tool.is_retryable_error(result.error):
                return result
        except RetryableError:
            if attempt >= max_retries:
                raise
            await asyncio.sleep(2 ** attempt)  # 指数退避
```

- `error_strategy = "retry"`: 工具调用失败时按 `max_retries` 重试
- `error_strategy = "fallback_message"`: 失败后返回预设消息（已实现）
- `max_retries` 默认 0，上限 5

## 9. 子系统分解与执行顺序

| Plan | 内容 | 优先级 | 估计规模 |
|------|------|--------|----------|
| **P2-Plan-1**: 自研图生 | ImageModelProvider 接口 + 3 provider + image_gen BuiltinTool + prompt 润色 + fallback chain | **最高** | ~10 tasks |
| **P2-Plan-2**: Memory long-term | memory_read/memory_write BuiltinTool + DB 存储 + Agent 集成 | 高 | ~5 tasks |
| **P2-Plan-3**: 流量切换 + Dify 删除 | chat/stream 图生流量切到 harness → 验证 → 删除 Dify 全家桶 | 高（依赖 Plan-1） | ~5 tasks |
| **P2-Plan-4**: 加固 | Guardrail 审计字段 + 日志脱敏 + error_strategy=retry | 中 | ~4 tasks |

**执行顺序**: Plan-1 → Plan-2 → Plan-3 → Plan-4

## 10. 测试策略

### 单元测试

- ImageModelProvider 每个实现：mock 外部 API，验证参数映射 + 错误分类
- image_gen BuiltinTool：mock provider，验证 fallback 链 + prompt 润色降级
- memory_read/memory_write：mock DB session，验证 UPSERT + 权限隔离

### 集成测试

- image_gen 端到端：使用真实 provider（测试环境 key），验证 OSS 上传
- Dify 双写对比：harness 结果 vs Dify 结果，记录差异日志

### 前端测试

- ImageGenRenderer：snapshot 测试 + 交互测试（折叠/展开、图片点击）
- eventStreamClient：image_generated 事件处理

## 11. 安全考量

1. **SSRF 防护**：ImageModelProvider 调用外部 API 时复用 Phase 1 HttpTool 的 SSRF 防护逻辑（IPv4/IPv6 blocked networks, DNS TOCTOU）
2. **API Key 安全**：复用现有 AES-256-GCM 加密存储，运行时解密
3. **Prompt 注入**：image_gen prompt 不直接拼接，通过 LLM 润色后传给 provider
4. **Memory 隔离**：memory_read/write 严格限制在当前 user_id + agent_id
5. **审计日志脱敏**：所有涉及敏感字段的变更日志通过 sanitize_audit_log 处理
6. **XSS 防护**：ImageGenRenderer 渲染图片 URL 时验证 URL scheme（仅 http/https）

## 12. 约束

- Python 3.10+, FastAPI, SQLAlchemy 2.0, Pydantic v2, httpx
- React 18, TypeScript, Vite, Tailwind CSS, Zustand
- 所有代码注释使用中文
- 不引入新的外部依赖（图像 provider SDK 除外，优先用 httpx 直接调用 REST API）
- 现有 admin UI 风格保持一致
- DB migration 使用 alembic
- 测试覆盖率 ≥ 80%（新增代码）
