# 图像生成工具开发指南

## 概述

`image_gen` BuiltinTool 提供 4 种图像生成操作，通过 `ImageModelProvider` 抽象支持多家 provider。

| 操作 | 说明 | 必填参数 |
|------|------|----------|
| `text2img` | 文生图 | `prompt` |
| `img2img` | 图生图 | `prompt`、`reference_image_url` |
| `inpaint` | 局部重绘 | `prompt`、`image_url`、`mask_url` |
| `upload_edit` | 指令式编辑 | `prompt`、`image_url` |

完整调用流程：

```
用户 prompt
  → prompt 润色（中文 → 英文，LLM 不可用时降级为原始 prompt）
  → 解析 Provider 链（default_model_id + fallback_model_ids）
  → 依次尝试每个 provider（retryable 错误自动 fallback）
  → 组装结果 + 发送 image_generated 事件
```

## 架构

```
image_gen BuiltinTool
├── prompt_refiner.refine_image_prompt()   # prompt 润色（含超时保护 + 注入过滤）
├── _resolve_provider_chain()              # 从 Agent 配置解析 provider 链
│   └── registry.resolve_provider()        # 按 provider_type 路由到具体实现
│       ├── TongyiWanxiangProvider (qwen_image)
│       ├── HailuoProvider (minimax_image)
│       └── DoubaoSeedProvider (doubao_seedream)
└── Fallback 链（按 Agent.fallback_model_ids 顺序）
```

关键模块：

| 文件 | 职责 |
|------|------|
| `image_gen.py` | 工具主逻辑：参数校验、流程编排、结果组装 |
| `image_provider/base.py` | `ImageModelProvider` 抽象接口 + `ImageGenResult`/`ImageGenError` 数据结构 |
| `image_provider/registry.py` | provider 注册与解析 |
| `tools/prompt_refiner.py` | prompt 润色 + 净化（防注入） |

## 添加新 Provider

1. 在 `backend/app/services/harness/image_provider/` 下创建新文件（如 `your_provider.py`）

2. 实现 `ImageModelProvider` 抽象类：

```python
from app.services.harness.image_provider.base import (
    ImageModelProvider, ImageGenResult, ImageGenError, ImageGenParams
)
from app.services.harness.image_provider.registry import register_provider

class YourProvider(ImageModelProvider):
    async def text2img(self, prompt: str, params: ImageGenParams) -> ImageGenResult:
        # 调用你的 API，返回 ImageGenResult
        ...

    async def img2img(self, prompt, reference_image, params) -> ImageGenResult: ...
    async def inpaint(self, prompt, image_url, mask_url, params) -> ImageGenResult: ...
    async def upload_edit(self, image_url, instruction, params) -> ImageGenResult: ...

    def validate_config(self) -> None:
        # 启动时校验配置是否完整（如 API key 是否有效）
        ...

# 模块末尾注册
register_provider("your_provider_type", YourProvider)
```

3. 确保 `LLMProvider.provider_type` 数据库记录值为 `"your_provider_type"`

4. 添加单元测试（mock `httpx`，验证参数映射和错误分类）

## 模型配置

在 Admin → 模型管理 中：

1. **创建 LLMProvider**：`provider_type` 对应图像 provider 类型（如 `qwen_image`）
2. **创建 LLMModel**：`category="image_gen"`，关联到上面的 Provider，填写 `model_name`、`request_params` 等
3. **配置 Agent**：在 Agent 编辑页设置 `default_model_id` 为该 LLMModel；可配置多个模型通过 `fallback_model_ids` 实现 fallback

## 错误处理

`ImageGenError` 携带 `retryable` 标记：

| retryable | 触发场景 | 行为 |
|-----------|----------|------|
| `True` | 超时、限流（429）、服务端错误（5xx） | 自动 fallback 到下一个 provider |
| `False` | 鉴权失败（401/403）、参数错误（400）、余额不足 | 不 fallback，直接返回错误 |

Provider 实现时务必正确分类错误：

```python
if response.status_code == 429:
    raise ImageGenError("请求频率超限", retryable=True)
if response.status_code == 401:
    raise ImageGenError("API key 无效", retryable=False)
```

**错误消息脱敏**：`ImageGenError` 的 message 会直接返回给用户，请确保不包含 API key、内部 IP、完整 stack trace 等敏感信息。

## 前端渲染

`ImageGenRenderer`（前端组件）自动渲染图像生成结果，包括：

- 操作类型 badge（text2img / img2img 等）
- 模型标签
- 润色后 prompt（可折叠展开）
- 图片网格（点击放大）

**安全说明**：
- 图片 URL 经 `safeHref` 校验，仅允许 `http` / `https` scheme
- 入参 URL（`reference_image_url` / `image_url` / `mask_url`）同样校验，阻断 `file://` / `javascript:` / `data:` 等危险 scheme
- SSRF 防护：URL hostname 经 DNS 解析后检查 IP，拒绝内网/loopback/link-local 地址（含 IPv6 AAAA 记录）
- URL 含 userinfo（如 `http://attacker@10.0.0.1/`）被拒绝
- URL 长度限制 2048 字符
