# Dify Chatflow 图像生成对话系统 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有图像生成工具基础上引入真正多轮对话：用户与 LLM 对话收集信息 → LLM 自主判断信息足够时触发生图 → 用户可在生成后继续对话迭代修改。

**Architecture:** Dify 4 个 Chatflow 应用（替代原 Workflow）+ 后端新增 `chat_*` DifyClient 方法 + `/chat` 路由 + 前端表单改为对话式 UI。conversation_id 由 Dify 管理，DB 仅存关联字段。

**Tech Stack:**
- Dify 1.x（Chatflow 应用 + LLM 节点 + 工具节点）
- Python 3.10+ / FastAPI / SQLAlchemy / httpx
- React 18 / TypeScript / Zustand

---

## Global Constraints

- **API 协议**：Dify Chatflow 端点是 `POST {api_url}/chat-messages`（不是 `/workflows/run`），请求体结构不同
- **请求体格式**：`{"inputs": {...}, "query": "...", "response_mode": "blocking", "user": "...", "conversation_id": "..."}`
- **响应格式**：Dify 返回 `{"conversation_id", "answer", "message_id"}`，生成的图片 URL 在对话历史变量里（由工作流末尾输出到 conversation_variables）
- **Conversation_id**：首次创建对话时 Dify 返回；后续轮次必须回传以保留上下文
- **<<GENERATE>> 标记**：约定在 answer 文本中嵌入此特殊字符串表示触发生图；前端/后端需检测此标记
- **配额扣减**：仅在生成图片（`<<GENERATE>>` 触发）时扣减；追问不扣
- **历史写入**：仅在生成图片时写 `image_gen_history.conversation_id`
- **新增工作流配置**：需同步更新 `image_gen_dify_config` 的 4 个 workflow_id 字段
- **保持兼容**：原 `/image-generation/generate` 端点（blocking）保留可用
- **代码风格**：中文注释，类型注解完整，遵循现有 `DifyClient` / `ImageGenService` 的命名与异常处理风格

---

## 文件结构

### 后端（修改）

- `backend/app/services/dify_client.py` — 加 `ChatRunResult` dataclass + 4 个 `chat_*` 方法
- `backend/app/services/image_generation_service.py` — 加 `chat_generate` 编排方法
- `backend/app/routes/image_generation.py` — 加 `/chat` 端点
- `backend/app/schemas/image_generation.py` — 加 `ChatGenerateRequest` schema
- `backend/scripts/migrate_add_conversation_id.py` — 新增（迁移脚本，幂等）
- `backend/tests/test_chat_flow.py` — 新增（集成测试）

### 前端（修改）

- `frontend/src/stores/imageGenerationStore.ts` — 加对话状态 + actions
- `frontend/src/api/imageGenerationApi.ts` — 加 `chatGenerate` 函数
- `frontend/src/hooks/useImageGenerate.ts` — 加 `handleChat` + `handleDirectGenerate`
- `frontend/src/components/Tools/ImageGeneration/forms/Text2ImgForm.tsx` — 改为对话式 UI
- `frontend/src/components/Tools/ImageGeneration/forms/Img2ImgForm.tsx` — 加对话简版
- `frontend/src/components/Tools/ImageGeneration/forms/InpaintForm.tsx` — 加对话简版
- `frontend/src/components/Tools/ImageGeneration/forms/UploadEditForm.tsx` — 加对话简版

### Dify（手动创建）

- 应用 1：`text2img-chat` Chatflow
- 应用 2：`img2img-chat` Chatflow
- 应用 3：`inpaint-chat` Chatflow
- 应用 4：`upload-edit-chat` Chatflow

---

## Task 1: 数据库迁移 — 新增 conversation_id 字段

**Files:**
- Create: `backend/scripts/migrate_add_conversation_id.py`
- Modify: `backend/.env.example`（在 `image_gen_history` 注释处追加新字段说明）

**Interfaces:**
- Produces: `image_gen_history.conversation_id VARCHAR(64) DEFAULT NULL` + 索引

- [ ] **Step 1: 写迁移脚本**

```python
"""一次性迁移脚本：为 image_gen_history 表添加 conversation_id 字段"""
import os
import sys
from sqlalchemy import create_engine, text

# 将 backend 加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config.config import settings

def main():
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        # 幂等：列已存在不报错
        conn.execute(text("""
            ALTER TABLE image_gen_history
            ADD COLUMN IF NOT EXISTS conversation_id VARCHAR(64) DEFAULT NULL
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_img_gen_history_conversation
            ON image_gen_history(conversation_id)
            WHERE conversation_id IS NOT NULL
        """))
        print("[OK] conversation_id 字段 + 索引已就绪")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 在本地跑迁移验证幂等**

Run: `cd backend && python scripts/migrate_add_conversation_id.py`
Expected: 第一次打印 `[OK] conversation_id 字段 + 索引已就绪`；第二次再跑仍打印同一行（无错误）

- [ ] **Step 3: 验证 schema**

Run: `cd backend && python -c "from sqlalchemy import create_engine, inspect; from app.config.config import settings; e = create_engine(settings.database_url); ins = inspect(e); cols = [c['name'] for c in ins.get_columns('image_gen_history')]; assert 'conversation_id' in cols, cols; print('OK')"`
Expected: `OK`

- [ ] **Step 4: 提交**

```bash
git add backend/scripts/migrate_add_conversation_id.py backend/.env.example
git commit -m "feat(image-gen): add conversation_id column migration"
```

---

## Task 2: DifyClient — ChatRunResult dataclass

**Files:**
- Modify: `backend/app/services/dify_client.py`（在 `DifyRunResult` 后插入）
- Create: `backend/tests/test_chat_result.py`

**Interfaces:**
- Produces: `ChatRunResult(conversation_id, answer, image_urls, model_used, polish_prompt, raw_response)`

- [ ] **Step 1: 写失败测试**

```python
"""测试 ChatRunResult dataclass"""
from app.services.dify_client import ChatRunResult

def test_chat_result_default_fields():
    result = ChatRunResult(
        conversation_id="conv-1",
        answer="你想用什么风格？",
    )
    assert result.conversation_id == "conv-1"
    assert result.answer == "你想用什么风格？"
    assert result.image_urls == []
    assert result.model_used == ""
    assert result.polish_prompt == ""

def test_chat_result_full():
    result = ChatRunResult(
        conversation_id="conv-2",
        answer="生成完成",
        image_urls=["https://x.com/a.png"],
        model_used="qwen-image-v1",
        polish_prompt="A cat in space",
        raw_response={"x": 1},
    )
    assert result.image_urls == ["https://x.com/a.png"]
    assert result.model_used == "qwen-image-v1"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_chat_result.py -v`
Expected: ImportError: cannot import name 'ChatRunResult'

- [ ] **Step 3: 实现 dataclass**

在 `backend/app/services/dify_client.py` 中 `DifyRunResult` 之后插入：

```python
@dataclass
class ChatRunResult:
    """Chatflow 多轮对话调用的标准化结果"""
    conversation_id: str             # 多轮对话 ID（首次创建时 Dify 返回，后续轮次回传）
    answer: str                      # LLM 回复文本（追问问题 or 生成说明）
    image_urls: List[str] = field(default_factory=list)  # 生成的图片（<<GENERATE>> 触发后才有值）
    model_used: str = ""             # 实际调用的模型
    polish_prompt: str = ""          # 润色后的英文图像生成提示词
    raw_response: Dict[str, Any] = field(default_factory=dict)
```

顶部 import 区域追加 `from dataclasses import dataclass, field` 替换原有 `from dataclasses import dataclass`。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_chat_result.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/dify_client.py backend/tests/test_chat_result.py
git commit -m "feat(dify-client): add ChatRunResult dataclass"
```

---

## Task 3: DifyClient — chat_text2img 方法

**Files:**
- Modify: `backend/app/services/dify_client.py`（在 `test_connection` 之前插入新方法）
- Create: `backend/tests/test_chat_text2img.py`

**Interfaces:**
- Produces: `DifyClient.chat_text2img(prompt, conversation_id, size, n, style, model_preference, user_id, timeout) -> ChatRunResult`

- [ ] **Step 1: 写失败测试**

```python
"""测试 chat_text2img 调用 Dify Chatflow"""
import pytest
from unittest.mock import AsyncMock, patch
from app.services.dify_client import DifyClient, ChatRunResult
from app.services.dify_config_service import DifyConfig

@pytest.fixture
def fake_config():
    return DifyConfig(
        api_url="https://dify.test/v1",
        app_api_key="app-test-key",
        workflow_text2img="wf-text2img",
        workflow_img2img="wf-img2img",
        workflow_inpaint="wf-inpaint",
        workflow_upload_edit="wf-upload-edit",
    )

@pytest.mark.asyncio
async def test_chat_text2img_posts_to_chat_messages(fake_config):
    fake_response = {
        "conversation_id": "conv-abc",
        "message_id": "msg-1",
        "answer": "你想要什么风格？",
        "metadata": {"retriever_resources": [], "usage": {}},
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = lambda: fake_response
        mock_post.return_value.__aenter__.return_value.post.return_value = mock_resp

        client = DifyClient()
        # 用 monkeypatch 注入 fake_config
        with patch.object(client, "_get_config", return_value=fake_config):
            result = await client.chat_text2img(
                prompt="一只猫",
                conversation_id=None,
                size="1024x1024",
                n=1,
                style="auto",
                model_preference="auto",
                user_id="user-1",
            )

    assert result.conversation_id == "conv-abc"
    assert result.answer == "你想要什么风格？"
    assert result.image_urls == []

    # 验证请求体
    call_args = mock_post.call_args
    body = call_args.kwargs["json"]
    assert body["inputs"]["size"] == "1024x1024"
    assert body["query"] == "一只猫"
    assert body["response_mode"] == "blocking"
    assert body["user"] == "user-1"
    assert body["conversation_id"] is None

@pytest.mark.asyncio
async def test_chat_text2img_extracts_images_from_answer(fake_config):
    """answer 中嵌入 JSON 数组时提取为 image_urls"""
    fake_response = {
        "conversation_id": "conv-abc",
        "message_id": "msg-1",
        "answer": "生成完成 <<GENERATE>>",
        # Dify Chatflow 可在 metadata 或 conversation_variables 传递图片
        "metadata": {"images": ["https://x.com/a.png"]},
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = lambda: fake_response
        mock_post.return_value.__aenter__.return_value.post.return_value = mock_resp

        client = DifyClient()
        with patch.object(client, "_get_config", return_value=fake_config):
            result = await client.chat_text2img(
                prompt="猫", conversation_id=None,
                size="1024x1024", n=1, style="auto",
                model_preference="auto", user_id="u1",
            )

    # 含 <<GENERATE>> 标记 + metadata.images 有值 → 提取 image_urls
    assert "<<GENERATE>>" in result.answer
    assert result.image_urls == ["https://x.com/a.png"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_chat_text2img.py -v`
Expected: AttributeError: 'DifyClient' object has no attribute 'chat_text2img'

- [ ] **Step 3: 实现 chat_text2img 方法**

在 `backend/app/services/dify_client.py` 的 `run_upload_edit` 方法之后、`test_connection` 之前插入：

```python
# ------------------------------------------------------------------
# Chatflow 多轮对话调用（4 个 operation）
# ------------------------------------------------------------------

async def chat_text2img(
    self,
    prompt: str,
    conversation_id: Optional[str],
    size: str,
    n: int,
    style: Optional[str],
    model_preference: str,
    user_id: str,
    timeout: Optional[float] = None,
) -> ChatRunResult:
    """调用 text2img-chat Chatflow（多轮对话模式）"""
    config = self._get_config()
    if not config.workflow_text2img:
        raise DifyError("text2img Chatflow 未配置", kind="config_error")

    inputs = {
        "size": size,
        "n": n,
        "style": style or "auto",
        "model_preference": model_preference,
    }
    payload = {
        "inputs": inputs,
        "query": prompt,
        "response_mode": "blocking",
        "user": user_id or "anonymous",
        "conversation_id": conversation_id or "",
    }
    return await self._call_chat(
        config=config,
        endpoint="/chat-messages",
        payload=payload,
        user_id=user_id,
        timeout=timeout or config.default_timeout,
    )

async def _call_chat(
    self,
    config: "DifyConfig",
    endpoint: str,
    payload: Dict[str, Any],
    user_id: str,
    timeout: float,
) -> ChatRunResult:
    """Chatflow 统一调用：POST /chat-messages"""
    url = f"{config.api_url}{endpoint}"
    headers = {
        "Authorization": f"Bearer {config.app_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                error_body = resp.text[:500]
                logger.error(
                    "[dify-chat] 调用失败: HTTP %d, body: %s",
                    resp.status_code, error_body,
                )
                self._raise_http_error(resp.status_code, "chat", error_body)

            data = resp.json()
            return self._parse_chat_response(data)

    except DifyError:
        raise
    except httpx.TimeoutException:
        raise DifyError(f"Chatflow 调用超时 ({timeout}s)", kind="timeout")
    except httpx.ConnectError as e:
        raise DifyError(f"无法连接 Dify: {e}", kind="connection_error")
    except Exception as e:
        logger.error("[dify-chat] 未预期异常: %s", e, exc_info=True)
        raise DifyError(f"未预期的错误: {e}", kind="http_error")

def _parse_chat_response(self, data: Dict[str, Any]) -> ChatRunResult:
    """解析 Chatflow 响应"""
    conversation_id = data.get("conversation_id", "")
    answer = data.get("answer", "")
    metadata = data.get("metadata", {}) or {}

    # 图片从 metadata.images 提取（如工作流末尾输出到此字段）
    image_urls = metadata.get("images", [])
    if isinstance(image_urls, str):
        try:
            image_urls = json.loads(image_urls)
        except (json.JSONDecodeError, ValueError):
            image_urls = []
    if not isinstance(image_urls, list):
        image_urls = []

    # 若 answer 含 <<GENERATE>> 且 metadata 有 images，标记为已生成
    return ChatRunResult(
        conversation_id=conversation_id,
        answer=answer,
        image_urls=image_urls,
        model_used=metadata.get("model_used", ""),
        polish_prompt=metadata.get("polish_prompt", ""),
        raw_response=data,
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_chat_text2img.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/dify_client.py backend/tests/test_chat_text2img.py
git commit -m "feat(dify-client): add chat_text2img method for Chatflow"
```

---

## Task 4: DifyClient — chat_img2img / chat_inpaint / chat_upload_edit

**Files:**
- Modify: `backend/app/services/dify_client.py`（在 `chat_text2img` 之后）
- Create: `backend/tests/test_chat_other_ops.py`

**Interfaces:**
- Produces:
  - `DifyClient.chat_img2img(prompt, reference_url, conversation_id, strength, size, model_preference, user_id, timeout) -> ChatRunResult`
  - `DifyClient.chat_inpaint(prompt, image_url, mask_url, conversation_id, size, model_preference, user_id, timeout) -> ChatRunResult`
  - `DifyClient.chat_upload_edit(image_url, edit_type, conversation_id, prompt, user_id, timeout) -> ChatRunResult`

- [ ] **Step 1: 写失败测试**

```python
"""测试 chat_img2img / chat_inpaint / chat_upload_edit"""
import pytest
from unittest.mock import AsyncMock, patch
from app.services.dify_client import DifyClient
from app.services.dify_config_service import DifyConfig

@pytest.fixture
def fake_config():
    return DifyConfig(
        api_url="https://dify.test/v1",
        app_api_key="app-test-key",
        workflow_text2img="wf-t2i",
        workflow_img2img="wf-i2i",
        workflow_inpaint="wf-inpaint",
        workflow_upload_edit="wf-edit",
    )

def _mock_chat_response(answer, images=None):
    return {
        "conversation_id": "conv-xyz",
        "message_id": "msg-1",
        "answer": answer,
        "metadata": {"images": images or []},
    }

@pytest.mark.asyncio
async def test_chat_img2img_passes_reference_url(fake_config):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = lambda: _mock_chat_response("ok")
        mock_post.return_value.__aenter__.return_value.post.return_value = mock_resp

        client = DifyClient()
        with patch.object(client, "_get_config", return_value=fake_config):
            await client.chat_img2img(
                prompt="改成水彩",
                reference_url="https://oss/x.png",
                conversation_id="conv-1",
                strength=0.6,
                size="1024x1024",
                model_preference="auto",
                user_id="u1",
            )

    body = mock_post.call_args.kwargs["json"]
    assert body["inputs"]["reference_url"] == "https://oss/x.png"
    assert body["inputs"]["strength"] == 0.6
    assert body["conversation_id"] == "conv-1"

@pytest.mark.asyncio
async def test_chat_inpaint_passes_image_and_mask(fake_config):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = lambda: _mock_chat_response("ok")
        mock_post.return_value.__aenter__.return_value.post.return_value = mock_resp

        client = DifyClient()
        with patch.object(client, "_get_config", return_value=fake_config):
            await client.chat_inpaint(
                prompt="改成花",
                image_url="https://oss/img.png",
                mask_url="https://oss/mask.png",
                conversation_id=None,
                size="1024x1024",
                model_preference="auto",
                user_id="u1",
            )

    body = mock_post.call_args.kwargs["json"]
    assert body["inputs"]["image_url"] == "https://oss/img.png"
    assert body["inputs"]["mask_url"] == "https://oss/mask.png"

@pytest.mark.asyncio
async def test_chat_upload_edit_passes_edit_type(fake_config):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = lambda: _mock_chat_response("ok")
        mock_post.return_value.__aenter__.return_value.post.return_value = mock_resp

        client = DifyClient()
        with patch.object(client, "_get_config", return_value=fake_config):
            await client.chat_upload_edit(
                image_url="https://oss/img.png",
                edit_type="upscale",
                conversation_id=None,
                prompt="",
                user_id="u1",
            )

    body = mock_post.call_args.kwargs["json"]
    assert body["inputs"]["edit_type"] == "upscale"
    assert body["query"] == ""  # upload_edit 允许 prompt 为空
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_chat_other_ops.py -v`
Expected: AttributeError: 'DifyClient' object has no attribute 'chat_img2img'

- [ ] **Step 3: 实现 3 个方法**

在 `chat_text2img` 之后插入：

```python
async def chat_img2img(
    self,
    prompt: str,
    reference_url: str,
    conversation_id: Optional[str],
    strength: float,
    size: str,
    model_preference: str,
    user_id: str,
    timeout: Optional[float] = None,
) -> ChatRunResult:
    """调用 img2img-chat Chatflow"""
    config = self._get_config()
    if not config.workflow_img2img:
        raise DifyError("img2img Chatflow 未配置", kind="config_error")

    inputs = {
        "reference_url": reference_url,
        "strength": strength,
        "size": size,
        "model_preference": model_preference,
    }
    payload = {
        "inputs": inputs,
        "query": prompt,
        "response_mode": "blocking",
        "user": user_id or "anonymous",
        "conversation_id": conversation_id or "",
    }
    return await self._call_chat(
        config=config,
        endpoint="/chat-messages",
        payload=payload,
        user_id=user_id,
        timeout=timeout or config.default_timeout,
    )

async def chat_inpaint(
    self,
    prompt: str,
    image_url: str,
    mask_url: str,
    conversation_id: Optional[str],
    size: str,
    model_preference: str,
    user_id: str,
    timeout: Optional[float] = None,
) -> ChatRunResult:
    """调用 inpaint-chat Chatflow"""
    config = self._get_config()
    if not config.workflow_inpaint:
        raise DifyError("inpaint Chatflow 未配置", kind="config_error")

    inputs = {
        "image_url": image_url,
        "mask_url": mask_url,
        "size": size,
        "model_preference": model_preference,
    }
    payload = {
        "inputs": inputs,
        "query": prompt,
        "response_mode": "blocking",
        "user": user_id or "anonymous",
        "conversation_id": conversation_id or "",
    }
    return await self._call_chat(
        config=config,
        endpoint="/chat-messages",
        payload=payload,
        user_id=user_id,
        timeout=timeout or config.default_timeout,
    )

async def chat_upload_edit(
    self,
    image_url: str,
    edit_type: str,
    conversation_id: Optional[str],
    prompt: Optional[str],
    user_id: str,
    timeout: Optional[float] = None,
) -> ChatRunResult:
    """调用 upload-edit-chat Chatflow"""
    config = self._get_config()
    if not config.workflow_upload_edit:
        raise DifyError("upload_edit Chatflow 未配置", kind="config_error")

    inputs = {
        "image_url": image_url,
        "edit_type": edit_type,
    }
    payload = {
        "inputs": inputs,
        "query": prompt or "",
        "response_mode": "blocking",
        "user": user_id or "anonymous",
        "conversation_id": conversation_id or "",
    }
    return await self._call_chat(
        config=config,
        endpoint="/chat-messages",
        payload=payload,
        user_id=user_id,
        timeout=timeout or config.default_timeout,
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_chat_other_ops.py -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/dify_client.py backend/tests/test_chat_other_ops.py
git commit -m "feat(dify-client): add chat_img2img / chat_inpaint / chat_upload_edit"
```

---

## Task 5: ImageGenService — chat_generate 方法

**Files:**
- Modify: `backend/app/services/image_generation_service.py`（在 `generate` 之后）
- Create: `backend/tests/test_chat_service.py`

**Interfaces:**
- Produces: `ImageGenService.chat_generate(user_id, operation, prompt, conversation_id, params, reference_bytes, mask_bytes, edit_type) -> ChatRunResult`

- [ ] **Step 1: 写失败测试**

```python
"""测试 chat_generate：编排 chat_* + OSS + 历史写入"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.image_generation_service import ImageGenService
from app.services.dify_client import ChatRunResult

@pytest.fixture
def fake_components():
    return {
        "db": MagicMock(),
        "dify_client": MagicMock(),
        "quota_svc": MagicMock(),
        "oss_svc": MagicMock(),
        "history_svc": MagicMock(),
    }

@pytest.mark.asyncio
async def test_chat_generate_asking_no_quota_deduct(fake_components):
    """追问不生成时，不扣配额，不写历史"""
    fake_components["dify_client"].chat_text2img = AsyncMock(
        return_value=ChatRunResult(
            conversation_id="conv-1",
            answer="你想要什么风格？",
        )
    )

    svc = ImageGenService(
        db=fake_components["db"],
        dify_client=fake_components["dify_client"],
        quota_svc=fake_components["quota_svc"],
        oss_svc=fake_components["oss_svc"],
        history_svc=fake_components["history_svc"],
    )
    result = await svc.chat_generate(
        user_id="u1",
        operation="text2img",
        prompt="一只猫",
        conversation_id=None,
        params={"size": "1024x1024", "n": 1, "style": "auto", "model_preference": "auto"},
        reference_bytes=None,
        mask_bytes=None,
        edit_type=None,
    )

    assert result.answer == "你想要什么风格？"
    assert result.image_urls == []
    # 不应扣配额
    fake_components["quota_svc"].check_and_reserve.assert_not_called()
    # 不应写历史
    fake_components["history_svc"].create_record.assert_not_called()

@pytest.mark.asyncio
async def test_chat_generate_triggers_quota_and_history(fake_components):
    """<<GENERATE>> 触发时扣配额、写历史（带 conversation_id）"""
    fake_components["dify_client"].chat_text2img = AsyncMock(
        return_value=ChatRunResult(
            conversation_id="conv-2",
            answer="生成完成 <<GENERATE>>",
            image_urls=["https://x.com/a.png"],
            model_used="qwen-image-v1",
        )
    )
    fake_components["quota_svc"].check_and_reserve = MagicMock()
    fake_components["history_svc"].create_record = MagicMock(return_value=MagicMock(id="hist-1"))
    fake_components["oss_svc"].upload_file = MagicMock()
    fake_components["oss_svc"].sign_url = MagicMock(return_value="https://oss/signed.png")
    fake_components["db"].commit = MagicMock()

    svc = ImageGenService(**fake_components)
    # patch _upload_to_oss + _download_image 简化
    svc._upload_to_oss = MagicMock(side_effect=["ref-key", "result-key"])
    svc._download_image = AsyncMock(return_value=b"img-bytes")

    result = await svc.chat_generate(
        user_id="u1",
        operation="text2img",
        prompt="猫",
        conversation_id="conv-1",
        params={"size": "1024x1024", "n": 1, "style": "auto", "model_preference": "auto"},
        reference_bytes=None,
        mask_bytes=None,
        edit_type=None,
    )

    fake_components["quota_svc"].check_and_reserve.assert_called_once()
    create_kwargs = fake_components["history_svc"].create_record.call_args.kwargs
    assert create_kwargs["conversation_id"] == "conv-2"  # 历史记录带 conversation_id
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_chat_service.py -v`
Expected: AttributeError: 'ImageGenService' object has no attribute 'chat_generate'

- [ ] **Step 3: 实现 chat_generate 方法**

在 `image_generation_service.py` 的 `generate` 方法之后插入：

```python
async def chat_generate(
    self,
    user_id: str,
    operation: str,
    prompt: str,
    conversation_id: Optional[str],
    params: Dict[str, Any],
    reference_bytes: Optional[bytes] = None,
    mask_bytes: Optional[bytes] = None,
    edit_type: Optional[str] = None,
) -> "ChatRunResult":
    """
    多轮对话生成入口。

    流程：
      1. 降级检查（同 generate）
      2. 上传参考图/蒙版 → 生成签名 URL
      3. 调对应 chat_* 方法
      4. 若 LLM 触发 <<GENERATE>> 且有图片 → 走完整 OSS + 历史 + 配额流程
      5. 若仅为追问 → 仅返回 answer + conversation_id
    """
    start_time = time.monotonic()

    # ---- 1. 降级检查 ----
    if self.degradation_svc is not None and self.degradation_svc.is_degraded():
        logger.warning("服务降级中，拒绝对话请求: user=%s op=%s", user_id, operation)
        raise ServiceDegraded()

    # ---- 2. 上传参考图/蒙版 ----
    reference_oss_key = None
    mask_oss_key = None
    reference_url = None
    mask_url = None

    if reference_bytes is not None:
        reference_oss_key = self._upload_to_oss(reference_bytes, OSS_PREFIX_REF, "image/png")
        reference_url = self.oss_svc.sign_url("GET", reference_oss_key, SIGNED_URL_EXPIRES_REF)

    if mask_bytes is not None:
        mask_oss_key = self._upload_to_oss(mask_bytes, OSS_PREFIX_MASK, "image/png")
        mask_url = self.oss_svc.sign_url("GET", mask_oss_key, SIGNED_URL_EXPIRES_REF)

    # ---- 3. 调对应 chat_* 方法 ----
    if operation == OPERATION_TEXT2IMG:
        dify_result = await self.dify_client.chat_text2img(
            prompt=prompt,
            conversation_id=conversation_id,
            size=params["size"],
            n=params.get("n", 1),
            style=params.get("style"),
            model_preference=params.get("model_preference", "auto"),
            user_id=user_id,
        )
    elif operation == OPERATION_IMG2IMG:
        dify_result = await self.dify_client.chat_img2img(
            prompt=prompt,
            reference_url=reference_url,
            conversation_id=conversation_id,
            strength=params.get("strength", 0.6),
            size=params["size"],
            model_preference=params.get("model_preference", "auto"),
            user_id=user_id,
        )
    elif operation == OPERATION_INPAINT:
        dify_result = await self.dify_client.chat_inpaint(
            prompt=prompt,
            image_url=reference_url,
            mask_url=mask_url,
            conversation_id=conversation_id,
            size=params["size"],
            model_preference=params.get("model_preference", "auto"),
            user_id=user_id,
        )
    elif operation == OPERATION_UPLOAD_EDIT:
        dify_result = await self.dify_client.chat_upload_edit(
            image_url=reference_url,
            edit_type=edit_type or "upscale",
            conversation_id=conversation_id,
            prompt=prompt,
            user_id=user_id,
        )
    else:
        raise DifyError(f"未知操作类型: {operation}", kind="config_error")

    # ---- 4. 判断是否触发生成 ----
    has_generate_marker = "<<GENERATE>>" in dify_result.answer
    has_images = len(dify_result.image_urls) > 0

    if not (has_generate_marker and has_images):
        # 仅追问：返回 answer + conversation_id（不扣配额、不写历史）
        logger.info(
            "对话追问: user=%s op=%s conv=%s",
            user_id, operation, dify_result.conversation_id,
        )
        return dify_result

    # ---- 5. 触发生成：走完整流程 ----
    try:
        self.quota_svc.check_and_reserve(user_id, operation, dify_result.image_urls and 1)
    except Exception:
        raise

    try:
        # 下载结果图 → 上传 OSS
        result_oss_keys = []
        for idx, img_url in enumerate(dify_result.image_urls):
            img_bytes = await self._download_image(img_url)
            oss_key = self._upload_to_oss(img_bytes, OSS_PREFIX_RESULT, "image/png")
            result_oss_keys.append(oss_key)
        primary_result_key = result_oss_keys[0] if result_oss_keys else ""

        duration_ms = int((time.monotonic() - start_time) * 1000)
        history = self.history_svc.create_record(
            user_id=user_id,
            operation=operation,
            status=STATUS_SUCCESS,
            result_oss_key=primary_result_key,
            prompt=prompt,
            params=params,
            reference_oss_key=reference_oss_key,
            mask_oss_key=mask_oss_key,
            model_used=dify_result.model_used,
            duration_ms=duration_ms,
            conversation_id=dify_result.conversation_id,
        )
        self.quota_svc.commit()
        if self.degradation_svc is not None:
            self.degradation_svc.reset_failure_count()

        # 生成签名 URL 返回
        signed_urls = [
            self.oss_svc.sign_url("GET", key, SIGNED_URL_EXPIRES_RESULT)
            for key in result_oss_keys
        ]

        # 覆盖 result 的 image_urls 为签名 URL
        dify_result.image_urls = signed_urls
        logger.info(
            "对话生成成功: user=%s op=%s history=%s conv=%s",
            user_id, operation, history.id, dify_result.conversation_id,
        )
        return dify_result

    except DifyError:
        self.quota_svc.release()
        raise
```

顶部 import 区域追加：`from app.services.dify_client import DifyClient, DifyRunResult, ChatRunResult`。

**注意**：`create_record` 需要新增 `conversation_id` 参数；下一步修改 `history_service` 来支持。

- [ ] **Step 4: 修改 history_service.create_record 接受 conversation_id**

修改 `backend/app/services/image_gen_history_service.py` 中 `create_record` 方法签名，新增 `conversation_id: Optional[str] = None` 参数，并存入 ORM 对象。

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_chat_service.py -v`
Expected: 2 passed

- [ ] **Step 6: 提交**

```bash
git add backend/app/services/image_generation_service.py backend/app/services/image_gen_history_service.py backend/tests/test_chat_service.py
git commit -m "feat(image-gen): add chat_generate orchestration in ImageGenService"
```

---

## Task 6: Schema — ChatGenerateRequest

**Files:**
- Modify: `backend/app/schemas/image_generation.py`（在 `PolishPromptRequest` 之后插入）

**Interfaces:**
- Produces: `ChatGenerateRequest(operation, prompt, conversation_id?, size, n, style, strength, model_preference, edit_type)`

- [ ] **Step 1: 添加 schema**

```python
class ChatGenerateRequest(BaseModel):
    """多轮对话生成请求"""
    operation: str
    prompt: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = Field(default=None, max_length=64)
    size: str = Field(default="1024x1024")
    n: int = Field(default=1, ge=1, le=MAX_N_IMAGES)
    style: Optional[str] = None
    strength: float = Field(default=0.6, ge=0.0, le=1.0)
    model_preference: str = Field(default="auto")
    edit_type: Optional[str] = None

    _check_operation = field_validator("operation")(_validate_operation)
    _check_size = field_validator("size")(_validate_size)
    _check_model_preference = field_validator("model_preference")(_validate_model_preference)

    @field_validator("edit_type")
    @classmethod
    def _check_edit_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_EDIT_TYPES:
            raise ValueError(f"无效的编辑类型: {v}，允许值: {sorted(VALID_EDIT_TYPES)}")
        return v
```

- [ ] **Step 2: 验证 import 路径**

Run: `cd backend && python -c "from app.schemas.image_generation import ChatGenerateRequest; r = ChatGenerateRequest(operation='text2img', prompt='x'); print(r)"`
Expected: 打印 `operation='text2img' prompt='x' conversation_id=None size='1024x1024' n=1 ...`

- [ ] **Step 3: 提交**

```bash
git add backend/app/schemas/image_generation.py
git commit -m "feat(image-gen): add ChatGenerateRequest schema"
```

---

## Task 7: Route — /chat 端点

**Files:**
- Modify: `backend/app/routes/image_generation.py`（在 `/generate` 之后插入）
- Create: `backend/tests/test_chat_route.py`

**Interfaces:**
- Produces: `POST /image-generation/chat` 返回 `{conversation_id, answer, image_urls?, model_used?, polish_prompt?, history_id?, status: "asking" | "generated"}`

- [ ] **Step 1: 写失败测试**

```python
"""测试 /chat 端点：basic flow"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.dify_client import ChatRunResult

@pytest.fixture
def client():
    return TestClient(app)

def test_chat_endpoint_returns_asking_status(client):
    """追问时返回 status=asking"""
    fake_result = ChatRunResult(
        conversation_id="conv-1",
        answer="你想要什么风格？",
    )
    with patch("app.routes.image_generation.get_image_gen_service") as mock_dep:
        mock_svc = MagicMock()
        mock_svc.chat_generate = AsyncMock(return_value=fake_result)
        mock_dep.return_value = mock_svc

        # 需要 mock 鉴权
        with patch("app.routes.image_generation.get_current_user", return_value={"id": "u1", "username": "test", "role": "user"}):
            resp = client.post(
                "/image-generation/chat",
                data={
                    "operation": "text2img",
                    "prompt": "一只猫",
                    "size": "1024x1024",
                    "n": "1",
                },
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "asking"
    assert body["conversation_id"] == "conv-1"
    assert body["answer"] == "你想要什么风格？"
    assert "image_urls" not in body or body["image_urls"] == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_chat_route.py -v`
Expected: 404 Not Found（路由未注册）

- [ ] **Step 3: 实现 /chat 端点**

在 `/generate` 端点之后插入：

```python
@router.post("/chat")
async def chat(
    operation: str = Form(...),
    prompt: str = Form(...),
    conversation_id: Optional[str] = Form(None),
    size: str = Form("1024x1024"),
    n: int = Form(1),
    style: Optional[str] = Form(None),
    strength: float = Form(0.6),
    model_preference: str = Form("auto"),
    edit_type: Optional[str] = Form(None),
    reference_image: Optional[UploadFile] = File(None),
    mask_image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    svc: ImageGenService = Depends(get_image_gen_service),
):
    """
    多轮对话入口（multipart/form-data）。

    追问时返回 status=asking；
    生成完成时返回 status=generated + image_urls + history_id。
    """
    user_id = _extract_user_id(current_user)

    # 参数校验
    _validate_operation(operation)
    _validate_size(size)
    _validate_n(n)
    _validate_edit_type(operation, edit_type)

    # 读取上传文件
    ref_bytes = await _read_upload_file(reference_image)
    mask_bytes = await _read_upload_file(mask_image)

    params = {
        "size": size,
        "n": n,
        "style": style,
        "strength": strength,
        "model_preference": model_preference,
    }

    try:
        result = await svc.chat_generate(
            user_id=user_id,
            operation=operation,
            prompt=prompt,
            conversation_id=conversation_id,
            params=params,
            reference_bytes=ref_bytes,
            mask_bytes=mask_bytes,
            edit_type=edit_type,
        )
    except (QuotaExceeded, DifyError, ServiceDegraded) as exc:
        raise _map_service_exception(exc)

    response = {
        "conversation_id": result.conversation_id,
        "answer": result.answer,
        "model_used": result.model_used,
        "polish_prompt": result.polish_prompt,
        "status": "generated" if result.image_urls else "asking",
    }
    if result.image_urls:
        response["image_urls"] = result.image_urls
    # history_id 暂时从 raw_response 提取（service 层返回）
    if result.raw_response.get("history_id"):
        response["history_id"] = result.raw_response["history_id"]

    return response
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_chat_route.py -v`
Expected: 1 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/routes/image_generation.py backend/tests/test_chat_route.py
git commit -m "feat(image-gen): add /chat endpoint for multi-turn conversation"
```

---

## Task 8: 后端集成测试 — 端到端对话流程

**Files:**
- Create: `backend/tests/test_chat_integration.py`

- [ ] **Step 1: 写测试**

```python
"""端到端测试：用户对话 3 轮后生成图片"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.dify_client import ChatRunResult

@pytest.fixture
def client():
    return TestClient(app)

def test_full_chat_flow_text2img(client):
    """完整流程：3 轮追问 → 第 3 轮生成图片"""

    asking = ChatRunResult(conversation_id="conv-flow", answer="你想要什么风格？")
    asking2 = ChatRunResult(conversation_id="conv-flow", answer="在什么场景？")
    generated = ChatRunResult(
        conversation_id="conv-flow",
        answer="生成完成 <<GENERATE>>",
        image_urls=["https://x.com/a.png"],
        model_used="qwen-image-v1",
    )

    with patch("app.routes.image_generation.get_image_gen_service") as mock_dep:
        mock_svc = MagicMock()
        mock_svc.chat_generate = AsyncMock(side_effect=[asking, asking2, generated])
        mock_dep.return_value = mock_svc

        with patch("app.routes.image_generation.get_current_user", return_value={"id": "u1", "username": "t", "role": "user"}):
            # 轮次 1
            r1 = client.post("/image-generation/chat", data={
                "operation": "text2img", "prompt": "一只猫", "size": "1024x1024", "n": "1",
            })
            assert r1.json()["status"] == "asking"
            assert r1.json()["answer"] == "你想要什么风格？"

            # 轮次 2（带 conversation_id）
            r2 = client.post("/image-generation/chat", data={
                "operation": "text2img", "prompt": "卡通",
                "conversation_id": r1.json()["conversation_id"],
                "size": "1024x1024", "n": "1",
            })
            assert r2.json()["status"] == "asking"

            # 轮次 3（生图）
            r3 = client.post("/image-generation/chat", data={
                "operation": "text2img", "prompt": "在太空",
                "conversation_id": r1.json()["conversation_id"],
                "size": "1024x1024", "n": "1",
            })
            assert r3.json()["status"] == "generated"
            assert r3.json()["image_urls"] == ["https://x.com/a.png"]
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_chat_integration.py -v`
Expected: 1 passed

- [ ] **Step 3: 跑全部后端测试确认无回归**

Run: `cd backend && python -m pytest tests/ -v --ignore=tests/test_image_generation_integration.py`
Expected: 全部通过（如果 PostgreSQL 相关测试 skip，正常）

- [ ] **Step 4: 提交**

```bash
git add backend/tests/test_chat_integration.py
git commit -m "test(image-gen): add end-to-end chat flow integration test"
```

---

## Task 9: 前端 store — 对话状态

**Files:**
- Modify: `frontend/src/stores/imageGenerationStore.ts`

- [ ] **Step 1: 添加状态字段**

在 `ImageGenState` 接口中追加：

```typescript
// 对话相关
conversationId: string | null;
conversationHistory: Array<{
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}>;
chatAnswer: string | null;
chatStatus: 'idle' | 'asking' | 'generated';
```

在 `INITIAL_STATE` 中追加：

```typescript
conversationId: null,
conversationHistory: [],
chatAnswer: null,
chatStatus: 'idle',
```

在 `ImageGenActions` 中追加：

```typescript
chatGenerate: (operation: Operation, prompt: string, params: ChatParams) => Promise<ChatResult>;
resetConversation: () => void;
setChatAnswer: (answer: string | null) => void;
```

底部 store 实现追加：

```typescript
chatGenerate: async (operation, prompt, params) => {
  set({
    loading: true,
    error: null,
    chatStatus: 'asking',
    conversationHistory: [
      ...get().conversationHistory,
      { role: 'user', content: prompt, timestamp: Date.now() },
    ],
  });
  try {
    const result = await api.chatGenerate(
      operation,
      prompt,
      get().conversationId,
      params,
      params.referenceImage,
      params.maskImage,
    );
    const convId = result.conversation_id;
    const answer = result.answer || '';
    const imageUrls = result.image_urls || [];
    const status = result.status === 'generated' ? 'generated' : 'asking';

    set({
      conversationId: convId,
      chatAnswer: answer,
      chatStatus: status,
      conversationHistory: [
        ...get().conversationHistory,
        { role: 'assistant', content: answer, timestamp: Date.now() },
      ],
      currentResult: imageUrls.length > 0
        ? {
            history_id: result.history_id || '',
            image_urls: imageUrls,
            model_used: result.model_used || '',
            duration_ms: 0,
            operation,
            prompt,
          }
        : get().currentResult,
      loading: false,
    });
    return { conversation_id: convId, answer, image_urls: imageUrls, status };
  } catch (err: any) {
    set({ error: err.message || '对话失败', loading: false, chatStatus: 'idle' });
    throw err;
  }
},

resetConversation: () => {
  set({
    conversationId: null,
    conversationHistory: [],
    chatAnswer: null,
    chatStatus: 'idle',
  });
},
```

顶部 import 区域追加 `import * as api from '../api/imageGenerationApi';`（如果还未引入）。

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -E "imageGenerationStore|conversationId"`
Expected: 无输出（无错误）

- [ ] **Step 3: 提交**

```bash
git add frontend/src/stores/imageGenerationStore.ts
git commit -m "feat(image-gen): add conversation state to frontend store"
```

---

## Task 10: 前端 api — chatGenerate

**Files:**
- Modify: `frontend/src/api/imageGenerationApi.ts`

- [ ] **Step 1: 添加 chatGenerate 函数**

在文件末尾追加：

```typescript
export interface ChatResult {
  conversation_id: string;
  answer: string;
  image_urls?: string[];
  model_used?: string;
  polish_prompt?: string;
  history_id?: string;
  status: 'asking' | 'generated';
}

export async function chatGenerate(
  operation: Operation,
  prompt: string,
  conversationId: string | null,
  params: {
    size?: string;
    n?: number;
    style?: string;
    strength?: number;
    model_preference?: string;
    edit_type?: string;
  },
  referenceImage?: File | null,
  maskImage?: File | null,
): Promise<ChatResult> {
  const formData = new FormData();
  formData.append('operation', operation);
  formData.append('prompt', prompt);
  if (conversationId) formData.append('conversation_id', conversationId);
  if (params.size) formData.append('size', params.size);
  if (params.n) formData.append('n', params.n.toString());
  if (params.style) formData.append('style', params.style);
  if (params.strength !== undefined) formData.append('strength', params.strength.toString());
  if (params.model_preference) formData.append('model_preference', params.model_preference);
  if (params.edit_type) formData.append('edit_type', params.edit_type);
  if (referenceImage) formData.append('reference_image', referenceImage);
  if (maskImage) formData.append('mask_image', maskImage);

  const response = await authedFetch(`${API_BASE_URL}/image-generation/chat`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail?.message || '对话失败');
  }
  return response.json();
}
```

确认 `API_BASE_URL` 常量已定义（参考现有 `generate` 函数的写法）。

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep "imageGenerationApi"`
Expected: 无输出

- [ ] **Step 3: 提交**

```bash
git add frontend/src/api/imageGenerationApi.ts
git commit -m "feat(image-gen): add chatGenerate API function"
```

---

## Task 11: 前端 hook — handleChat / handleDirectGenerate

**Files:**
- Modify: `frontend/src/hooks/useImageGenerate.ts`

- [ ] **Step 1: 在 hook 中添加对话方法**

在 `useImageGenerate` 函数中追加：

```typescript
const chatGenerate = useImageGenStore((s) => s.chatGenerate);
const resetConversation = useImageGenStore((s) => s.resetConversation);

const handleChat = useCallback(async (prompt: string, params: Record<string, any>) => {
  return chatGenerate(operation, prompt, params);
}, [chatGenerate, operation]);

const handleDirectGenerate = useCallback(async () => {
  // 调用原有的 generate() 方法，跳过对话
  await generate();
}, [generate]);

return {
  generate: handleDirectGenerate,
  chat: handleChat,
  abort,
  loading,
  error,
  setError,
  resetConversation,
};
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep "useImageGenerate"`
Expected: 无输出

- [ ] **Step 3: 提交**

```bash
git add frontend/src/hooks/useImageGenerate.ts
git commit -m "feat(image-gen): add handleChat and handleDirectGenerate in hook"
```

---

## Task 12: 前端 — Text2ImgForm 改为对话式 UI

**Files:**
- Modify: `frontend/src/components/Tools/ImageGeneration/forms/Text2ImgForm.tsx`（**完全重写**）

- [ ] **Step 1: 重写为对话式 UI**

```typescript
/**
 * Text2ImgForm — 对话式文生图
 * 显示 LLM 追问对话 + 用户输入框 + 生成结果
 */
import { useState, useRef, useEffect } from 'react';
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import { useImageGenerate } from '../../../../hooks/useImageGenerate';
import { useI18n } from '../../../../i18n';

export default function Text2ImgForm() {
  const { t } = useI18n();
  const igT = t.imageGeneration;
  const [input, setInput] = useState('');
  const [size, setSize] = useState('1024x1024');
  const [n, setN] = useState(1);
  const [style, setStyle] = useState('auto');
  const [modelPreference, setModelPreference] = useState('auto');
  const [polishPrompt, setPolishPrompt] = useState(false);

  const history = useImageGenStore((s) => s.conversationHistory);
  const chatAnswer = useImageGenStore((s) => s.chatAnswer);
  const chatStatus = useImageGenStore((s) => s.chatStatus);
  const currentResult = useImageGenStore((s) => s.currentResult);
  const resetConversation = useImageGenStore((s) => s.resetConversation);

  const { chat, loading } = useImageGenerate();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history, chatAnswer]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userInput = input;
    setInput('');
    await chat(userInput, {
      size,
      n,
      style,
      model_preference: modelPreference,
      polish_prompt: polishPrompt,
    });
  };

  return (
    <div className="flex flex-col h-full">
      {/* 对话历史 */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-3 p-2 bg-slate-900/50 rounded-lg max-h-96">
        {history.length === 0 && (
          <div className="text-center text-slate-500 py-8">
            🤖 {igT.chat.welcome}
          </div>
        )}
        {history.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] px-4 py-2 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-100'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg animate-pulse">
              {igT.chat.thinking}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 生成结果显示 */}
      {chatStatus === 'generated' && currentResult && currentResult.image_urls.length > 0 && (
        <div className="mb-4 p-4 bg-slate-800 rounded-lg">
          <img
            src={currentResult.image_urls[0]}
            alt="generated"
            className="w-full rounded-lg mb-2"
          />
          <div className="text-xs text-slate-400">
            {igT.result.model}: {currentResult.model_used}
          </div>
          <div className="flex gap-2 mt-2">
            <button
              onClick={() => window.open(currentResult.image_urls[0])}
              className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
            >
              {igT.result.download}
            </button>
            <button
              onClick={resetConversation}
              className="px-3 py-1 bg-slate-700 text-slate-200 text-sm rounded hover:bg-slate-600"
            >
              {igT.chat.newConversation}
            </button>
          </div>
        </div>
      )}

      {/* 参数面板（首次对话时显示，可折叠） */}
      {history.length === 0 && (
        <div className="mb-4 p-3 bg-slate-800 rounded-lg space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <label className="text-slate-400 w-20">{igT.form.size}</label>
            <select
              value={size}
              onChange={(e) => setSize(e.target.value)}
              className="flex-1 bg-slate-700 text-slate-100 px-2 py-1 rounded"
            >
              <option value="1024x1024">1024×1024</option>
              <option value="1024x1792">1024×1792</option>
              <option value="1792x1024">1792×1024</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-slate-400 w-20">{igT.form.count}</label>
            <select
              value={n}
              onChange={(e) => setN(Number(e.target.value))}
              className="flex-1 bg-slate-700 text-slate-100 px-2 py-1 rounded"
            >
              <option value={1}>1 张</option>
              <option value={2}>2 张</option>
              <option value={3}>3 张</option>
              <option value={4}>4 张</option>
            </select>
          </div>
        </div>
      )}

      {/* 输入框 */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={igT.chat.inputPlaceholder}
          disabled={loading}
          className="flex-1 px-4 py-2 bg-slate-700 text-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {igT.chat.send}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: i18n key 补充**

修改 `frontend/src/i18n/locales/zh-CN.ts` 和 `en-US.ts`，在 `imageGeneration` 下添加：

```typescript
chat: {
  welcome: '你想画什么？告诉我主题、风格、场景等',
  thinking: '思考中...',
  inputPlaceholder: '输入你的回复...',
  send: '发送',
  newConversation: '开始新对话',
},
result: {
  model: '模型',
  download: '下载',
},
```

- [ ] **Step 3: 类型检查 + 构建**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -E "Text2ImgForm|imageGeneration"`
Expected: 无输出

Run: `cd frontend && npm run build`
Expected: 构建成功

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/Tools/ImageGeneration/forms/Text2ImgForm.tsx frontend/src/i18n/locales/zh-CN.ts frontend/src/i18n/locales/en-US.ts
git commit -m "feat(image-gen): rewrite Text2ImgForm as chat UI"
```

---

## Task 13: 前端 — 其他 3 个 Form 简化对话版

**Files:**
- Modify: `frontend/src/components/Tools/ImageGeneration/forms/Img2ImgForm.tsx`
- Modify: `frontend/src/components/Tools/ImageGeneration/forms/InpaintForm.tsx`
- Modify: `frontend/src/components/Tools/ImageGeneration/forms/UploadEditForm.tsx`

**对每个 form 的改动模式相同：**
- 保留参考图上传控件
- 保留操作特有参数（如 strength、mask_image、edit_type）
- 添加简化对话输入框（不显示历史，最多 1-2 轮）
- 用 `chat` hook 调用 `/chat` 端点

- [ ] **Step 1: 简化 Img2ImgForm**

保留：参考图上传 + strength 滑块 + size 选择 + 对话输入框
删除：完整的 n / style / 4 个参数面板

```typescript
import { useState } from 'react';
import { useImageGenStore } from '../../../../stores/imageGenerationStore';
import { useImageGenerate } from '../../../../hooks/useImageGenerate';

export default function Img2ImgForm() {
  const { chat, loading } = useImageGenerate();
  const referenceImage = useImageGenStore((s) => s.referenceImage);
  const setReferenceImage = useImageGenStore((s) => s.setReferenceImage);
  const [prompt, setPrompt] = useState('');
  const [strength, setStrength] = useState(0.6);

  const handleSend = async () => {
    if (!prompt.trim() || !referenceImage) return;
    await chat(prompt, { strength, model_preference: 'auto' });
    setPrompt('');
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm text-slate-400 mb-2">参考图</label>
        <input
          type="file"
          accept="image/*"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) setReferenceImage(file, URL.createObjectURL(file));
          }}
        />
        {referenceImage && <img src={URL.createObjectURL(referenceImage)} className="mt-2 max-h-32 rounded" />}
      </div>
      <div>
        <label className="block text-sm text-slate-400 mb-2">变化强度 {strength}</label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={strength}
          onChange={(e) => setStrength(Number(e.target.value))}
          className="w-full"
        />
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="你想改成什么样？比如改成水彩风格"
          disabled={loading || !referenceImage}
          className="flex-1 px-3 py-2 bg-slate-700 text-slate-100 rounded"
        />
        <button
          onClick={handleSend}
          disabled={loading || !prompt.trim() || !referenceImage}
          className="px-4 py-2 bg-blue-600 text-white rounded"
        >
          {loading ? '生成中...' : '开始对话生成'}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 简化 InpaintForm**

保留：参考图 + 蒙版图上传，添加对话输入框
删除：4 个参数面板

（结构类似 Img2ImgForm，加上 mask_image 上传控件）

- [ ] **Step 3: 简化 UploadEditForm**

保留：参考图 + edit_type 选择，添加可选 prompt
删除：完整参数面板

（结构类似，提供 edit_type 下拉）

- [ ] **Step 4: 类型检查 + 构建**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -E "Img2ImgForm|InpaintForm|UploadEditForm"`
Expected: 无输出

Run: `cd frontend && npm run build`
Expected: 构建成功

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/Tools/ImageGeneration/forms/
git commit -m "feat(image-gen): simplify 3 other forms to chat input"
```

---

## Task 14: Dify Chatflow 创建 — text2img-chat（浏览器操作）

**Files:**
- 在 Dify UI 创建（无代码）

- [ ] **Step 1: 登录 Dify**

浏览器访问 `https://dify.peanuthzm.com.cn`，用管理员账号登录。

- [ ] **Step 2: 创建 Chatflow 应用**

1. 顶部菜单点击「工作室」
2. 点击「创建空白应用」
3. 选择「Chatflow」（**不是 Workflow**）
4. 编排方式：基础编排
5. 名称：`text2img-chat`
6. 描述：图像生成对话（文生图）

- [ ] **Step 3: 配置对话大脑 LLM 节点**

1. 默认会有「开始 → LLM → 直接回复」结构
2. 点击中间 LLM 节点
3. 模型选择：`qwen-max` 或类似强模型
4. System Prompt：
```
你是图像生成助手。你的任务是帮用户收集足够的信息来生成图片。

需要了解的信息：
- 主题（主体物）
- 风格（写实/卡通/油画/水彩/3D/赛博朋克 等）
- 场景（背景/环境）
- 光照（自然光/霓虹/夕阳 等）
- 细节（人物姿态/表情/配色 等）

规则：
1. 每轮最多问 1 个问题（不要一次问一堆）
2. 用户回答后，把已知信息总结成 JSON 格式输出
3. 当信息满足主题 + 风格 + 场景这 3 项时，输出特殊标记 <<GENERATE>>
4. 在 <<GENERATE>> 之后，输出润色后的完整英文图像生成提示词

输出格式（必须严格遵守）：
仅追问时：只输出追问文本
触发生成时：<<GENERATE>>
英文提示词：[润色后的英文 prompt]
```
5. User Prompt（变量 `sys.query` 即用户输入）：
```
用户消息：{{sys.query}}
对话历史：{{sys.conversation}}
```

- [ ] **Step 4: 添加条件分支节点**

在 LLM 节点之后、「直接回复」之前，添加「条件分支」节点：
- IF 条件：`{{llm.text}}` contains `<<GENERATE>>`
- THEN 分支：进入"提示词路由+润色"节点
- ELSE 分支：连接到「直接回复」节点（显示追问）

- [ ] **Step 5: 添加"提示词路由+润色" LLM 节点**

1. 在 THEN 分支添加 LLM 节点
2. System Prompt：
```
你是图像生成提示词专家。基于用户原始输入和对话历史，输出英文结构化提示词。

判断复杂度：
- 简单（<50字、单主体、无复杂场景）：直接输出
- 复杂（多元素、氛围、光影）：丰富描述

输出 JSON 格式：
{
  "polish_prompt": "...",
  "size": "1024x1024",
  "n": 1,
  "style": "auto",
  "model_used": "qwen-image-v1"
}
```
3. User Prompt：`{{sys.query}}`

- [ ] **Step 6: 添加"图像生成"工具节点**

1. 添加「工具」节点
2. 选择已安装的图像生成插件（如「通义万相」或「豆包」）
3. 工具方法：`text_2_image`
4. 参数映射：
   - `prompt`：来自上一 LLM 节点的 `polish_prompt`
   - `size`：来自上一节点的 `size`
   - `n`：来自上一节点的 `n`

- [ ] **Step 7: 添加"代码节点"组装输出**

1. 添加「代码节点」（Python）
2. 代码：
```python
import json

def main(llm_output: str, tool_output: list) -> dict:
    try:
        llm_data = json.loads(llm_output)
    except:
        llm_data = {"polish_prompt": "", "size": "1024x1024", "n": 1, "style": "auto", "model_used": "unknown"}

    images = []
    if isinstance(tool_output, list):
        for item in tool_output:
            if isinstance(item, dict) and "url" in item:
                images.append(item["url"])
            elif isinstance(item, str):
                images.append(item)

    return {
        "answer": f"生成完成！模型：{llm_data.get('model_used', '')}\n提示词：{llm_data.get('polish_prompt', '')}",
        "metadata": {
            "images": json.dumps(images),
            "model_used": llm_data.get("model_used", ""),
            "polish_prompt": llm_data.get("polish_prompt", ""),
        },
    }
```

- [ ] **Step 8: 配置结束节点输出**

将代码节点的输出连接到「直接回复」或「结束」节点（注意：Chatflow 的「结束」节点有特殊结构，需要选「回答」模式）。

- [ ] **Step 9: 测试**

点击右上角「预览」，输入"一只猫"，验证追问逻辑。回答几轮后输入触发条件，验证生图。

- [ ] **Step 10: 发布 + 获取 API key**

1. 点击「发布」→「发布更新」
2. 左侧「访问 API」 → 复制 API Key（`app-...`）
3. **记录 workflow_id / app_id 与 API Key 对应关系**

- [ ] **Step 11: 更新后端配置**

修改 `backend/.env`：
```
DIFY_WORKFLOW_TEXT2IMG=<该 Chatflow 的 app_id>
```

注：app_id 不是 workflow_id；在 Dify Chatflow 的访问 API 页面查看。

---

## Task 15: Dify Chatflow 创建 — img2img-chat（浏览器操作）

**Files:**
- Dify UI（无代码）

- [ ] **Step 1: 同 Task 14 的 Step 1-2**，创建 Chatflow 应用 `img2img-chat`

- [ ] **Step 2: 配置对话大脑 LLM 节点**

System Prompt：
```
你是图像生成助手（参考图模式）。用户已上传参考图。

你的任务：询问用户想修改什么、想要什么风格效果。

规则：
1. 已知有参考图，不要问"主体物"
2. 询问：改什么内容？什么风格？什么效果？
3. 信息足够（目标内容+风格明确）→ 输出 <<GENERATE>>
4. 在 <<GENERATE>> 后输出润色英文提示词
```

User Prompt：`{{sys.query}}`（原始用户输入）+ 引用变量 `{{sys.files}}`（参考图）

- [ ] **Step 3: 配置工具节点**

工具方法：`image_2_image`（不同插件名字略不同）
输入：
- `prompt`：润色后的英文提示词
- `image_url` 或 `image_file`：来自 `sys.files[0]`

- [ ] **Step 4: 测试、发布、记录 API Key**

同 Task 14 Step 9-11。更新 `DIFY_WORKFLOW_IMG2IMG`。

---

## Task 16: Dify Chatflow 创建 — inpaint-chat

- [ ] **Step 1-3**: 同 Task 15，但工具方法选 `inpaint`（或 `image_edit` 取决于插件）

- [ ] **Step 4**: System Prompt 强调"蒙版区域"：

```
你是图像生成助手（局部重绘模式）。用户已有原图 + 蒙版（白色=重绘区域）。

询问：蒙版区域想画什么？什么风格？

信息足够 → <<GENERATE>>
```

- [ ] **Step 5**: 发布、更新 `DIFY_WORKFLOW_INPAINT`

---

## Task 17: Dify Chatflow 创建 — upload-edit-chat

- [ ] **Step 1-3**: 工具方法选 `image_edit` / `upscale` / `denoise` / `style_transfer`

- [ ] **Step 4**: System Prompt：

```
你是图像编辑助手。用户已上传图片。

询问：
1. 想要什么编辑效果？（超分/去噪/风格迁移/换背景）
2. 可选：具体调整描述

信息足够 → <<GENERATE>>
```

- [ ] **Step 5**: 发布、更新 `DIFY_WORKFLOW_UPLOAD_EDIT`

---

## Task 18: 端到端联调

- [ ] **Step 1: 后端重启加载新配置**

```bash
cd /d/CodeProjects/tools
python dev-services.py restart backend
```

- [ ] **Step 2: 前端重启加载新代码**

```bash
python dev-services.py restart frontend
```

- [ ] **Step 3: 浏览器访问 http://localhost:5178/tools/image-generation**

- [ ] **Step 4: 验证 text2img 流程**

| 步骤 | 期望 |
|---|---|
| 进入 text2img tab | 显示欢迎语 "你想画什么？" |
| 输入"一只猫" | 1-2 秒后显示 LLM 追问 |
| 回答"卡通" | LLM 追问场景 |
| 回答"在太空" | LLM 触发 `<<GENERATE>>`，显示生成的猫图片 |
| 历史抽屉看 | 该记录带 `conversation_id` |

- [ ] **Step 5: 验证迭代修改**

| 步骤 | 期望 |
|---|---|
| 在对话中说"颜色再亮一点" | 重新生成一张图（带上下文） |
| 历史记录数增加 | 新生成一条 history 记录 |

- [ ] **Step 6: 验证其他 3 个 Form**

- img2img：上传参考图 → 输入"改成水彩" → 生图
- inpaint：上传图 + 蒙版 → 输入"重绘成樱花" → 生图
- upload_edit：上传图 + 选 edit_type → 输入"超分" → 生图

- [ ] **Step 7: 验证配额**

- 追问不扣配额
- 生图扣 1 次配额
- 历史记录 `conversation_id` 正确写入 DB

Run:
```bash
cd backend && python -c "
from sqlalchemy import create_engine, text
from app.config.config import settings
e = create_engine(settings.database_url)
with e.connect() as c:
    rows = c.execute(text('SELECT id, conversation_id FROM image_gen_history ORDER BY created_at DESC LIMIT 5')).fetchall()
    for r in rows:
        print(r)
"
```

Expected: 至少有一条记录的 `conversation_id` 不为 NULL。

---

## 验收标准

✅ 完成定义：

1. **后端**：
   - [ ] DB 迁移脚本运行成功，column + index 存在
   - [ ] `DifyClient.chat_*` 4 个方法通过单元测试
   - [ ] `ImageGenService.chat_generate` 通过集成测试
   - [ ] `/image-generation/chat` 端点可用，3 轮对话后生图
   - [ ] 追问时 status=asking；生图时 status=generated
   - [ ] 历史记录带 `conversation_id`

2. **前端**：
   - [ ] Text2ImgForm 改为对话式 UI，对话历史 + 输入框 + 结果展示
   - [ ] 其他 3 个 Form 保留参数面板 + 对话输入框
   - [ ] `chatGenerate` API 函数可用
   - [ ] `handleChat` / `handleDirectGenerate` hook 工作
   - [ ] i18n key 完整（中/英）

3. **Dify**：
   - [ ] 4 个 Chatflow 应用创建完成
   - [ ] 每个 Chatflow 的对话大脑 LLM 节点配置完成
   - [ ] 工具节点配置完成（调用对应图像生成插件）
   - [ ] API Key 记录在 `.env` 中

4. **端到端**：
   - [ ] 用户能 3 轮对话后生图
   - [ ] 用户能基于上一步迭代修改
   - [ ] 配额正确扣减
   - [ ] 历史正确写入

---

## 已知风险与回滚

| 风险 | 缓解 |
|---|---|
| Dify Chatflow streaming 不稳定 | response_mode=blocking；如需 streaming 后续再加 |
| LLM 路由判断不准确 | 路由节点 prompt 规则 + 测试用例调优 |
| conversation_id 失效 | 前端兜底：丢失时重新发起对话 |
| 浏览器配置 Dify 失败 | 失败时回滚到原 Workflow（无需切换） |
