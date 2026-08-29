# P2-Plan-1: 自研图生 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现自研图像生成系统，替换 Dify 工作流，通过 ImageModelProvider 抽象支持通义万相/海螺AI/豆包 Seed 三家 provider，image_gen BuiltinTool 提供 4 种操作（text2img/img2img/inpaint/upload_edit），含 prompt 润色和模型 fallback 链。

**Architecture:** 新增 `harness/image_provider/` 包定义 ImageModelProvider 抽象接口和 3 个具体实现，通过 Provider Registry 从现有 `LLMProvider.provider_type` 路由。`image_gen` BuiltinTool 继承 Phase 1 的 `BuiltinTool` 基类，内部通过 `ctx.llm_gateway` 做 prompt 润色，按 `Agent.fallback_model_ids` 实现故障转移。前端新增 `ImageGenRenderer` 注册到 `ToolCallRenderer` 的 DEFAULT_BUILTINS。

**Tech Stack:** Python 3.10+, httpx (async HTTP), SQLAlchemy 2.0, Pydantic v2, React 18, TypeScript, Zustand, Tailwind CSS

## Global Constraints

- Python 3.10+, FastAPI, SQLAlchemy 2.0, Pydantic v2, httpx
- React 18, TypeScript, Vite, Tailwind CSS, Zustand
- 所有代码注释使用中文
- 不引入新的外部依赖（图像 provider SDK 除外，优先用 httpx 直接调用 REST API）
- 复用现有 `LLMProvider`/`LLMModel` 表（不新建 DB 表）
- `LLMModel.category = "image_gen"` 标识图像模型
- `LLMModel.priority` 字段用于 fallback 排序
- 测试覆盖率 ≥ 80%（新增代码）
- 安全：URL scheme 白名单 (http/https)，异常信息脱敏，XSS 防护

---

## File Structure

```
backend/app/services/harness/image_provider/
├── __init__.py              # 包导出
├── base.py                  # ImageModelProvider 抽象 + ImageGenParams/ImageGenResult/ImageGenError
├── registry.py              # resolve_provider() 路由函数
├── tongyi.py                # 通义万相实现 (provider_type: qwen_image)
├── hailuo.py                # 海螺 AI 实现 (provider_type: minimax_image)
└── doubao.py                # 豆包 Seed 实现 (provider_type: doubao_seedream)

backend/app/services/harness/tools/
├── image_gen.py             # image_gen BuiltinTool（4 种操作 + prompt 润色 + fallback）
└── prompt_refiner.py        # Prompt 润色 helper

backend/tests/harness/
├── test_image_provider_base.py
├── test_image_provider_registry.py
├── test_tongyi_provider.py
├── test_hailuo_provider.py
├── test_doubao_provider.py
├── test_prompt_refiner.py
├── test_image_gen_tool.py
└── test_image_gen_integration.py

frontend/src/components/Chat/ToolRenderers/
└── ImageGenRenderer.tsx     # 图像生成结果渲染器
```

---

### Task 1: ImageModelProvider 抽象接口 + Provider Registry

**Files:**
- Create: `backend/app/services/harness/image_provider/__init__.py`
- Create: `backend/app/services/harness/image_provider/base.py`
- Create: `backend/app/services/harness/image_provider/registry.py`
- Test: `backend/tests/harness/test_image_provider_base.py`
- Test: `backend/tests/harness/test_image_provider_registry.py`

**Interfaces:**
- Consumes: `LLMProvider` (ORM model), existing API key decryption utilities
- Produces: `ImageModelProvider` (ABC), `ImageGenParams`, `ImageGenResult`, `ImageGenError`, `resolve_provider()`

- [ ] **Step 1: Write tests for ImageGenParams / ImageGenResult / ImageGenError**

```python
# backend/tests/harness/test_image_provider_base.py
"""ImageModelProvider 抽象接口 + 数据结构测试"""
import pytest
from app.services.harness.image_provider.base import (
    ImageGenParams,
    ImageGenResult,
    ImageGenError,
    ImageModelProvider,
)


class TestImageGenParams:
    def test_defaults(self):
        p = ImageGenParams()
        assert p.size == "1024x1024"
        assert p.n == 1
        assert p.style is None
        assert p.model_name == ""
        assert p.request_params == {}

    def test_custom_values(self):
        p = ImageGenParams(size="512x512", n=4, style="anime", model_name="wanx-v1")
        assert p.size == "512x512"
        assert p.n == 4
        assert p.style == "anime"
        assert p.model_name == "wanx-v1"


class TestImageGenResult:
    def test_fields(self):
        r = ImageGenResult(
            image_urls=["https://oss.example.com/img1.png"],
            model_used="wanx-v1",
            revised_prompt="a cat sitting on a mat",
            elapsed_seconds=3.5,
        )
        assert len(r.image_urls) == 1
        assert r.model_used == "wanx-v1"
        assert r.revised_prompt == "a cat sitting on a mat"
        assert r.elapsed_seconds == 3.5

    def test_defaults(self):
        r = ImageGenResult(image_urls=["url"], model_used="m")
        assert r.revised_prompt == ""
        assert r.elapsed_seconds == 0.0


class TestImageGenError:
    def test_retryable(self):
        e = ImageGenError("timeout", retryable=True)
        assert e.retryable is True
        assert str(e) == "timeout"

    def test_fatal(self):
        e = ImageGenError("invalid api key", retryable=False)
        assert e.retryable is False


class TestImageModelProviderABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ImageModelProvider(base_url="http://x", api_key="k")

    def test_concrete_subclass(self):
        class MockProvider(ImageModelProvider):
            async def text2img(self, prompt, params):
                return ImageGenResult(image_urls=[], model_used="mock")
            async def img2img(self, prompt, reference_image, params):
                return ImageGenResult(image_urls=[], model_used="mock")
            async def inpaint(self, prompt, image_url, mask_url, params):
                return ImageGenResult(image_urls=[], model_used="mock")
            async def upload_edit(self, image_url, instruction, params):
                return ImageGenResult(image_urls=[], model_used="mock")
            def validate_config(self):
                pass

        p = MockProvider(base_url="http://x", api_key="k")
        assert p.base_url == "http://x"
        assert p.api_key == "k"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/harness/test_image_provider_base.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.harness.image_provider'"

- [ ] **Step 3: Implement ImageGenParams, ImageGenResult, ImageGenError, ImageModelProvider**

```python
# backend/app/services/harness/image_provider/base.py
"""ImageModelProvider 抽象接口 + 数据结构

参考 spec §4.1
"""
import time
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
    """图像生成错误，携带可重试标记

    retryable=True: 超时/限流/5xx → 触发 fallback 链
    retryable=False: 鉴权失败/参数错误/余额不足 → 不重试
    """
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class ImageModelProvider(ABC):
    """图像生成 Provider 抽象接口

    子类实现 4 种操作 + validate_config。
    通过 Provider Registry 从 LLMProvider.provider_type 路由到具体实现。
    """

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

- [ ] **Step 4: Create package __init__.py**

```python
# backend/app/services/harness/image_provider/__init__.py
"""图像生成 Provider 包

提供 ImageModelProvider 抽象接口 + Provider Registry + 具体实现。
"""
from app.services.harness.image_provider.base import (
    ImageGenError,
    ImageGenParams,
    ImageGenResult,
    ImageModelProvider,
)
from app.services.harness.image_provider.registry import resolve_provider

__all__ = [
    "ImageGenError",
    "ImageGenParams",
    "ImageGenResult",
    "ImageModelProvider",
    "resolve_provider",
]
```

- [ ] **Step 5: Write tests for Provider Registry**

```python
# backend/tests/harness/test_image_provider_registry.py
"""Provider Registry 测试"""
import pytest
from unittest.mock import MagicMock

from app.services.harness.image_provider.base import ImageGenError, ImageModelProvider
from app.services.harness.image_provider.registry import resolve_provider, _PROVIDER_MAP


class StubProvider(ImageModelProvider):
    """测试用 stub provider"""
    async def text2img(self, prompt, params):
        pass
    async def img2img(self, prompt, reference_image, params):
        pass
    async def inpaint(self, prompt, image_url, mask_url, params):
        pass
    async def upload_edit(self, image_url, instruction, params):
        pass
    def validate_config(self):
        pass


class TestResolveProvider:
    def test_known_provider_type(self, monkeypatch):
        """已知 provider_type 能解析到对应实现"""
        monkeypatch.setitem(_PROVIDER_MAP, "test_type", StubProvider)
        mock_llm_provider = MagicMock()
        mock_llm_provider.provider_type = "test_type"
        mock_llm_provider.base_url = "https://api.example.com"
        mock_llm_provider.api_key_encrypted = "encrypted_key"

        # mock decrypt 函数
        import app.services.harness.image_provider.registry as reg
        monkeypatch.setattr(reg, "decrypt_api_key", lambda k: "decrypted_key")

        result = resolve_provider(mock_llm_provider)
        assert isinstance(result, StubProvider)
        assert result.base_url == "https://api.example.com"
        assert result.api_key == "decrypted_key"

    def test_unknown_provider_type_raises(self):
        """未知 provider_type 抛出 ImageGenError"""
        mock_llm_provider = MagicMock()
        mock_llm_provider.provider_type = "unknown_type"

        with pytest.raises(ImageGenError, match="不支持"):
            resolve_provider(mock_llm_provider)

    def test_oss_client_passed_through(self, monkeypatch):
        """oss_client 透传给 provider"""
        monkeypatch.setitem(_PROVIDER_MAP, "test_type2", StubProvider)
        mock_llm_provider = MagicMock()
        mock_llm_provider.provider_type = "test_type2"
        mock_llm_provider.base_url = "https://api.example.com"
        mock_llm_provider.api_key_encrypted = "key"

        import app.services.harness.image_provider.registry as reg
        monkeypatch.setattr(reg, "decrypt_api_key", lambda k: "key")

        mock_oss = MagicMock()
        result = resolve_provider(mock_llm_provider, oss_client=mock_oss)
        assert result.oss_client is mock_oss
```

- [ ] **Step 6: Run registry tests to verify they fail**

Run: `cd backend && python -m pytest tests/harness/test_image_provider_registry.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 7: Implement Provider Registry**

先找到现有 API key 解密函数：

```bash
# 查找 decrypt 相关函数
cd backend && grep -rn "decrypt.*api_key\|api_key.*decrypt\|decrypt_api_key" app/
```

根据搜索结果确定解密函数路径，然后实现 registry：

```python
# backend/app/services/harness/image_provider/registry.py
"""Provider Registry — 从 LLMProvider.provider_type 路由到 ImageModelProvider 实现

参考 spec §4.2
"""
import logging
from typing import Dict, Optional, Type

from app.services.harness.image_provider.base import ImageGenError, ImageModelProvider

logger = logging.getLogger(__name__)

# provider_type → 实现类映射
# 延迟导入避免循环依赖，在 resolve_provider() 中填充
_PROVIDER_MAP: Dict[str, Type[ImageModelProvider]] = {}


def _ensure_providers_loaded():
    """确保所有 provider 实现已注册到 _PROVIDER_MAP

    首次调用时导入各 provider 模块触发注册。
    """
    if _PROVIDER_MAP:
        return
    # 导入各 provider 模块（它们会在模块级别注册到 _PROVIDER_MAP）
    try:
        from app.services.harness.image_provider import tongyi  # noqa: F401
    except ImportError:
        logger.debug("tongyi provider 未加载")
    try:
        from app.services.harness.image_provider import hailuo  # noqa: F401
    except ImportError:
        logger.debug("hailuo provider 未加载")
    try:
        from app.services.harness.image_provider import doubao  # noqa: F401
    except ImportError:
        logger.debug("doubao provider 未加载")


def register_provider(provider_type: str, cls: Type[ImageModelProvider]):
    """注册 provider 实现（由 provider 模块在导入时调用）"""
    _PROVIDER_MAP[provider_type] = cls


# 复用现有的 API key 解密逻辑
def _decrypt_api_key(encrypted: str) -> str:
    """解密 API key

    复用项目现有的 AES-256-GCM 解密工具。
    """
    from app.utils.crypto import decrypt_text
    return decrypt_text(encrypted)


def resolve_provider(llm_provider, oss_client=None) -> ImageModelProvider:
    """从 LLMProvider 实例解析到具体 ImageModelProvider 实现

    Args:
        llm_provider: LLMProvider ORM 实例（需有 provider_type, base_url, api_key_encrypted）
        oss_client: OSS 客户端实例（用于上传图片）

    Returns:
        ImageModelProvider 实例

    Raises:
        ImageGenError: provider_type 未注册
    """
    _ensure_providers_loaded()

    cls = _PROVIDER_MAP.get(llm_provider.provider_type)
    if cls is None:
        raise ImageGenError(
            f"图像 Provider 不支持: {llm_provider.provider_type}，"
            f"已注册: {list(_PROVIDER_MAP.keys())}"
        )

    api_key = _decrypt_api_key(llm_provider.api_key_encrypted)

    return cls(
        base_url=llm_provider.base_url,
        api_key=api_key,
        oss_client=oss_client,
    )
```

- [ ] **Step 8: Run all Task 1 tests to verify they pass**

Run: `cd backend && python -m pytest tests/harness/test_image_provider_base.py tests/harness/test_image_provider_registry.py -v`
Expected: ALL PASS

注意：registry 测试中 `_PROVIDER_MAP` 在 `resolve_provider` 调用 `_ensure_providers_loaded()` 时会尝试导入还不存在的 tongyi/hailuo/doubao 模块。需要调整测试用 monkeypatch 先填充 `_PROVIDER_MAP`，或在 Step 7 中确保 `_ensure_providers_loaded()` 在 `_PROVIDER_MAP` 已被测试 monkeypatch 填充时跳过导入。实际上由于 Step 5 的测试直接 monkeypatch.setitem 到 `_PROVIDER_MAP`，而 `_ensure_providers_loaded` 检查 `if _PROVIDER_MAP: return`，所以测试中的 monkeypatch 会让它跳过导入。但 `test_unknown_provider_type_raises` 没有 monkeypatch，此时 `_PROVIDER_MAP` 为空，会尝试导入不存在的模块——这些 import 失败会被 `try/except ImportError` 捕获并 debug log，不影响测试。

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/harness/image_provider/ backend/tests/harness/test_image_provider_base.py backend/tests/harness/test_image_provider_registry.py
git commit -m "feat(harness): add ImageModelProvider abstract interface + provider registry"
```

---

### Task 2: TongyiWanxiangProvider 实现

**Files:**
- Create: `backend/app/services/harness/image_provider/tongyi.py`
- Test: `backend/tests/harness/test_tongyi_provider.py`

**Interfaces:**
- Consumes: `ImageModelProvider`, `ImageGenParams`, `ImageGenResult`, `ImageGenError` from Task 1; `httpx.AsyncClient`
- Produces: `TongyiWanxiangProvider` class, registered as `provider_type="qwen_image"`

- [ ] **Step 1: Write tests for TongyiWanxiangProvider**

```python
# backend/tests/harness/test_tongyo_provider.py
"""通义万相 Provider 测试

使用 mock httpx 验证：
1. text2img 请求构造正确
2. 成功响应解析正确
3. retryable 错误（5xx/timeout）正确标记
4. fatal 错误（401/参数错误）正确标记
5. validate_config 检查 api_key
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.harness.image_provider.base import ImageGenError, ImageGenParams
from app.services.harness.image_provider.tongyi import TongyiWanxiangProvider


@pytest.fixture
def provider():
    return TongyiWanxiangProvider(
        base_url="https://dashscope.aliyuncs.com/api/v1",
        api_key="test-api-key",
        oss_client=MagicMock(),
    )


class TestTongyiWanxiangProvider:
    @pytest.mark.asyncio
    async def test_text2img_success(self, provider):
        """text2img 成功场景"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output": {
                "task_id": "task-123",
                "results": [{"url": "https://oss.example.com/generated.png"}]
            },
            "usage": {"image_count": 1}
        }

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            with patch.object(provider, "_download_and_upload", new_callable=AsyncMock, return_value="https://my-oss.com/img.png"):
                params = ImageGenParams(size="1024x1024", n=1, model_name="wanx-v1")
                result = await provider.text2img("一只猫", params)

        assert result.image_urls == ["https://my-oss.com/img.png"]
        assert result.model_used == "wanx-v1"

    @pytest.mark.asyncio
    async def test_text2img_timeout_is_retryable(self, provider):
        """超时错误标记为 retryable"""
        import httpx
        with patch.object(provider, "_http_post", new_callable=AsyncMock, side_effect=httpx.ReadTimeout("timeout")):
            params = ImageGenParams(model_name="wanx-v1")
            with pytest.raises(ImageGenError) as exc_info:
                await provider.text2img("一只猫", params)
            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_text2img_401_is_fatal(self, provider):
        """401 鉴权错误标记为 fatal"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            params = ImageGenParams(model_name="wanx-v1")
            with pytest.raises(ImageGenError) as exc_info:
                await provider.text2img("一只猫", params)
            assert exc_info.value.retryable is False

    @pytest.mark.asyncio
    async def test_text2img_500_is_retryable(self, provider):
        """500 服务端错误标记为 retryable"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            params = ImageGenParams(model_name="wanx-v1")
            with pytest.raises(ImageGenError) as exc_info:
                await provider.text2img("一只猫", params)
            assert exc_info.value.retryable is True

    def test_validate_config_with_api_key(self, provider):
        """有 api_key 时 validate_config 通过"""
        provider.validate_config()  # 不抛异常

    def test_validate_config_without_api_key(self):
        """无 api_key 时 validate_config 抛异常"""
        p = TongyiWanxiangProvider(base_url="http://x", api_key="", oss_client=None)
        with pytest.raises(ImageGenError, match="api_key"):
            p.validate_config()

    def test_registered_as_qwen_image(self):
        """Provider 注册为 qwen_image"""
        from app.services.harness.image_provider.registry import _PROVIDER_MAP
        # 触发导入
        from app.services.harness.image_provider import tongyi  # noqa: F401
        assert "qwen_image" in _PROVIDER_MAP
        assert _PROVIDER_MAP["qwen_image"] is TongyiWanxiangProvider
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/harness/test_tongyi_provider.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement TongyiWanxiangProvider**

```python
# backend/app/services/harness/image_provider/tongyi.py
"""通义万相 (Tongyi Wanxiang) Provider

通过阿里云 DashScope API 调用通义万相图像生成。
参考文档：https://help.aliyun.com/zh/dashscope/developer-reference/tongyi-wanxiang

provider_type: qwen_image
"""
import logging
import time
from typing import Optional

import httpx

from app.services.harness.image_provider.base import (
    ImageGenError,
    ImageGenParams,
    ImageGenResult,
    ImageModelProvider,
)
from app.services.harness.image_provider.registry import register_provider

logger = logging.getLogger(__name__)

# 请求超时（秒）
_DEFAULT_TIMEOUT = 60.0


class TongyiWanxiangProvider(ImageModelProvider):
    """通义万相 Provider

    DashScope API 调用流程：
    1. POST 创建异步任务
    2. 轮询任务状态直到完成
    3. 下载生成的图片 → 上传到自有 OSS
    4. 返回 OSS URL
    """

    def __init__(self, base_url: str, api_key: str, oss_client=None):
        super().__init__(base_url, api_key, oss_client)
        self._timeout = _DEFAULT_TIMEOUT

    async def text2img(self, prompt: str, params: ImageGenParams) -> ImageGenResult:
        model = params.model_name or "wanx-v1"
        start = time.time()

        # 构造 DashScope 请求体
        body = {
            "model": model,
            "input": {
                "prompt": prompt,
            },
            "parameters": {
                "size": params.size,
                "n": params.n,
            },
        }
        if params.style:
            body["input"]["style"] = params.style

        # 调用 API
        resp = await self._http_post(
            f"{self.base_url}/services/aigc/text2image/image-synthesis",
            json=body,
            headers=self._build_headers(async_call=True),
        )
        self._check_response(resp)

        data = resp.json()
        task_id = data.get("output", {}).get("task_id", "")
        if not task_id:
            raise ImageGenError("DashScope 未返回 task_id", retryable=True)

        # 轮询任务状态
        result_urls = await self._poll_task(task_id)

        # 下载并上传到自有 OSS
        oss_urls = []
        for url in result_urls:
            oss_url = await self._download_and_upload(url)
            oss_urls.append(oss_url)

        return ImageGenResult(
            image_urls=oss_urls,
            model_used=model,
            elapsed_seconds=time.time() - start,
        )

    async def img2img(self, prompt: str, reference_image: str, params: ImageGenParams) -> ImageGenResult:
        model = params.model_name or "wanx-v1"
        start = time.time()

        body = {
            "model": model,
            "input": {
                "prompt": prompt,
                "ref_img": reference_image,
            },
            "parameters": {
                "size": params.size,
                "n": params.n,
            },
        }

        resp = await self._http_post(
            f"{self.base_url}/services/aigc/image2image/image-synthesis",
            json=body,
            headers=self._build_headers(async_call=True),
        )
        self._check_response(resp)

        data = resp.json()
        task_id = data.get("output", {}).get("task_id", "")
        if not task_id:
            raise ImageGenError("DashScope 未返回 task_id", retryable=True)

        result_urls = await self._poll_task(task_id)
        oss_urls = [await self._download_and_upload(u) for u in result_urls]

        return ImageGenResult(
            image_urls=oss_urls,
            model_used=model,
            elapsed_seconds=time.time() - start,
        )

    async def inpaint(self, prompt: str, image_url: str, mask_url: str, params: ImageGenParams) -> ImageGenResult:
        model = params.model_name or "wanx-v1"
        start = time.time()

        body = {
            "model": model,
            "input": {
                "prompt": prompt,
                "image_url": image_url,
                "mask_url": mask_url,
            },
            "parameters": {
                "size": params.size,
                "n": params.n,
            },
        }

        resp = await self._http_post(
            f"{self.base_url}/services/aigc/image-inpaint/image-synthesis",
            json=body,
            headers=self._build_headers(async_call=True),
        )
        self._check_response(resp)

        data = resp.json()
        task_id = data.get("output", {}).get("task_id", "")
        if not task_id:
            raise ImageGenError("DashScope 未返回 task_id", retryable=True)

        result_urls = await self._poll_task(task_id)
        oss_urls = [await self._download_and_upload(u) for u in result_urls]

        return ImageGenResult(
            image_urls=oss_urls,
            model_used=model,
            elapsed_seconds=time.time() - start,
        )

    async def upload_edit(self, image_url: str, instruction: str, params: ImageGenParams) -> ImageGenResult:
        model = params.model_name or "wanx-v1"
        start = time.time()

        body = {
            "model": model,
            "input": {
                "image_url": image_url,
                "prompt": instruction,
            },
            "parameters": {
                "size": params.size,
                "n": params.n,
            },
        }

        resp = await self._http_post(
            f"{self.base_url}/services/aigc/image-edit/image-synthesis",
            json=body,
            headers=self._build_headers(async_call=True),
        )
        self._check_response(resp)

        data = resp.json()
        task_id = data.get("output", {}).get("task_id", "")
        if not task_id:
            raise ImageGenError("DashScope 未返回 task_id", retryable=True)

        result_urls = await self._poll_task(task_id)
        oss_urls = [await self._download_and_upload(u) for u in result_urls]

        return ImageGenResult(
            image_urls=oss_urls,
            model_used=model,
            elapsed_seconds=time.time() - start,
        )

    def validate_config(self) -> None:
        if not self.api_key:
            raise ImageGenError("通义万相 api_key 未配置")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _build_headers(self, async_call: bool = False) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if async_call:
            headers["X-DashScope-Async"] = "enable"
        return headers

    async def _http_post(self, url: str, **kwargs) -> httpx.Response:
        """HTTP POST（可被测试 mock）"""
        timeout = kwargs.pop("timeout", self._timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.post(url, **kwargs)

    async def _http_get(self, url: str, **kwargs) -> httpx.Response:
        """HTTP GET（可被测试 mock）"""
        timeout = kwargs.pop("timeout", self._timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.get(url, **kwargs)

    def _check_response(self, resp: httpx.Response) -> None:
        """检查 HTTP 响应状态码，抛出分类错误"""
        if 200 <= resp.status_code < 300:
            return
        # retryable: 5xx / 429 (rate limit) / timeout
        if resp.status_code >= 500 or resp.status_code == 429:
            raise ImageGenError(
                f"DashScope HTTP {resp.status_code}: {resp.text[:200]}",
                retryable=True,
            )
        # fatal: 4xx (except 429)
        raise ImageGenError(
            f"DashScope HTTP {resp.status_code}: {resp.text[:200]}",
            retryable=False,
        )

    async def _poll_task(self, task_id: str, max_attempts: int = 60, interval: float = 2.0) -> list:
        """轮询异步任务状态直到完成

        Returns:
            生成的图片 URL 列表
        """
        import asyncio
        url = f"{self.base_url}/tasks/{task_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        for _ in range(max_attempts):
            resp = await self._http_get(url, headers=headers)
            self._check_response(resp)
            data = resp.json()
            status = data.get("output", {}).get("task_status", "")

            if status == "SUCCEEDED":
                results = data.get("output", {}).get("results", [])
                return [r.get("url", "") for r in results if r.get("url")]
            elif status == "FAILED":
                msg = data.get("output", {}).get("message", "任务失败")
                raise ImageGenError(f"DashScope 任务失败: {msg}", retryable=False)
            elif status in ("PENDING", "RUNNING"):
                await asyncio.sleep(interval)
            else:
                raise ImageGenError(f"未知任务状态: {status}", retryable=True)

        raise ImageGenError(f"任务轮询超时 ({max_attempts} 次)", retryable=True)

    async def _download_and_upload(self, url: str) -> str:
        """下载图片并上传到自有 OSS，返回 OSS URL

        如果 oss_client 不可用，直接返回原始 URL（降级模式）。
        """
        if not self.oss_client:
            return url

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning("下载图片失败 HTTP %s: %s", resp.status_code, url)
                    return url

                # 上传到 OSS
                import uuid
                key = f"image-gen/{uuid.uuid4().hex}.png"
                oss_url = self.oss_client.upload_bytes(key, resp.content, "image/png")
                return oss_url
        except Exception as e:
            logger.warning("下载/上传图片失败: %s", e)
            return url


# 注册到 provider registry
register_provider("qwen_image", TongyiWanxiangProvider)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/harness/test_tongyi_provider.py -v`
Expected: ALL PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/harness/image_provider/tongyi.py backend/tests/harness/test_tongyi_provider.py
git commit -m "feat(harness): add TongyiWanxiangProvider (qwen_image)"
```

---

### Task 3: HailuoProvider 实现

**Files:**
- Create: `backend/app/services/harness/image_provider/hailuo.py`
- Test: `backend/tests/harness/test_hailuo_provider.py`

**Interfaces:**
- Consumes: `ImageModelProvider`, `ImageGenParams`, `ImageGenResult`, `ImageGenError`, `register_provider` from Task 1
- Produces: `HailuoProvider` class, registered as `provider_type="minimax_image"`

- [ ] **Step 1: Write tests for HailuoProvider**

```python
# backend/tests/harness/test_hailuo_provider.py
"""海螺 AI (MiniMax) Provider 测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.harness.image_provider.base import ImageGenError, ImageGenParams
from app.services.harness.image_provider.hailuo import HailuoProvider


@pytest.fixture
def provider():
    return HailuoProvider(
        base_url="https://api.minimax.chat/v1",
        api_key="test-hailuo-key",
        oss_client=MagicMock(),
    )


class TestHailuoProvider:
    @pytest.mark.asyncio
    async def test_text2img_success(self, provider):
        """text2img 成功场景"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "image_urls": ["https://cdn.minimax.com/generated.png"],
                "model": "hailuo-v1",
            }
        }

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            with patch.object(provider, "_download_and_upload", new_callable=AsyncMock, return_value="https://my-oss.com/img.png"):
                params = ImageGenParams(size="1024x1024", n=1, model_name="hailuo-v1")
                result = await provider.text2img("一只猫", params)

        assert result.image_urls == ["https://my-oss.com/img.png"]
        assert result.model_used == "hailuo-v1"

    @pytest.mark.asyncio
    async def test_401_is_fatal(self, provider):
        """401 鉴权错误标记为 fatal"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            params = ImageGenParams(model_name="hailuo-v1")
            with pytest.raises(ImageGenError) as exc_info:
                await provider.text2img("一只猫", params)
            assert exc_info.value.retryable is False

    @pytest.mark.asyncio
    async def test_500_is_retryable(self, provider):
        """500 服务端错误标记为 retryable"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            params = ImageGenParams(model_name="hailuo-v1")
            with pytest.raises(ImageGenError) as exc_info:
                await provider.text2img("test", params)
            assert exc_info.value.retryable is True

    def test_validate_config_with_key(self, provider):
        provider.validate_config()

    def test_validate_config_without_key(self):
        p = HailuoProvider(base_url="http://x", api_key="", oss_client=None)
        with pytest.raises(ImageGenError, match="api_key"):
            p.validate_config()

    def test_registered_as_minimax_image(self):
        from app.services.harness.image_provider.registry import _PROVIDER_MAP
        from app.services.harness.image_provider import hailuo  # noqa: F401
        assert "minimax_image" in _PROVIDER_MAP
        assert _PROVIDER_MAP["minimax_image"] is HailuoProvider
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/harness/test_hailuo_provider.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement HailuoProvider**

```python
# backend/app/services/harness/image_provider/hailuo.py
"""海螺 AI (MiniMax) Provider

通过 MiniMax API 调用海螺 AI 图像生成。
参考文档：https://www.minimaxi.com/document/guides/image-generation

provider_type: minimax_image
"""
import logging
import time
from typing import Optional

import httpx

from app.services.harness.image_provider.base import (
    ImageGenError,
    ImageGenParams,
    ImageGenResult,
    ImageModelProvider,
)
from app.services.harness.image_provider.registry import register_provider

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 60.0


class HailuoProvider(ImageModelProvider):
    """海螺 AI Provider

    MiniMax API 调用流程：
    1. POST 图像生成请求（同步或异步）
    2. 解析返回的图片 URL
    3. 下载 → 上传到自有 OSS
    4. 返回 OSS URL
    """

    def __init__(self, base_url: str, api_key: str, oss_client=None):
        super().__init__(base_url, api_key, oss_client)
        self._timeout = _DEFAULT_TIMEOUT

    async def text2img(self, prompt: str, params: ImageGenParams) -> ImageGenResult:
        model = params.model_name or "hailuo-v1"
        start = time.time()

        body = {
            "model": model,
            "prompt": prompt,
            "size": params.size,
            "n": params.n,
        }
        if params.style:
            body["style"] = params.style

        resp = await self._http_post(
            f"{self.base_url}/image/generation",
            json=body,
            headers=self._build_headers(),
        )
        self._check_response(resp)

        data = resp.json()
        raw_urls = data.get("data", {}).get("image_urls", [])
        if not raw_urls:
            raise ImageGenError("海螺 AI 未返回图片 URL", retryable=True)

        oss_urls = [await self._download_and_upload(u) for u in raw_urls]

        return ImageGenResult(
            image_urls=oss_urls,
            model_used=model,
            elapsed_seconds=time.time() - start,
        )

    async def img2img(self, prompt: str, reference_image: str, params: ImageGenParams) -> ImageGenResult:
        model = params.model_name or "hailuo-v1"
        start = time.time()

        body = {
            "model": model,
            "prompt": prompt,
            "reference_image": reference_image,
            "size": params.size,
            "n": params.n,
        }

        resp = await self._http_post(
            f"{self.base_url}/image/img2img",
            json=body,
            headers=self._build_headers(),
        )
        self._check_response(resp)

        data = resp.json()
        raw_urls = data.get("data", {}).get("image_urls", [])
        if not raw_urls:
            raise ImageGenError("海螺 AI 未返回图片 URL", retryable=True)

        oss_urls = [await self._download_and_upload(u) for u in raw_urls]

        return ImageGenResult(
            image_urls=oss_urls,
            model_used=model,
            elapsed_seconds=time.time() - start,
        )

    async def inpaint(self, prompt: str, image_url: str, mask_url: str, params: ImageGenParams) -> ImageGenResult:
        model = params.model_name or "hailuo-v1"
        start = time.time()

        body = {
            "model": model,
            "prompt": prompt,
            "image_url": image_url,
            "mask_url": mask_url,
            "size": params.size,
            "n": params.n,
        }

        resp = await self._http_post(
            f"{self.base_url}/image/inpaint",
            json=body,
            headers=self._build_headers(),
        )
        self._check_response(resp)

        data = resp.json()
        raw_urls = data.get("data", {}).get("image_urls", [])
        if not raw_urls:
            raise ImageGenError("海螺 AI 未返回图片 URL", retryable=True)

        oss_urls = [await self._download_and_upload(u) for u in raw_urls]

        return ImageGenResult(
            image_urls=oss_urls,
            model_used=model,
            elapsed_seconds=time.time() - start,
        )

    async def upload_edit(self, image_url: str, instruction: str, params: ImageGenParams) -> ImageGenResult:
        model = params.model_name or "hailuo-v1"
        start = time.time()

        body = {
            "model": model,
            "image_url": image_url,
            "prompt": instruction,
            "size": params.size,
            "n": params.n,
        }

        resp = await self._http_post(
            f"{self.base_url}/image/edit",
            json=body,
            headers=self._build_headers(),
        )
        self._check_response(resp)

        data = resp.json()
        raw_urls = data.get("data", {}).get("image_urls", [])
        if not raw_urls:
            raise ImageGenError("海螺 AI 未返回图片 URL", retryable=True)

        oss_urls = [await self._download_and_upload(u) for u in raw_urls]

        return ImageGenResult(
            image_urls=oss_urls,
            model_used=model,
            elapsed_seconds=time.time() - start,
        )

    def validate_config(self) -> None:
        if not self.api_key:
            raise ImageGenError("海螺 AI api_key 未配置")

    # ------------------------------------------------------------------
    # 内部方法（与 TongyiWanxiangProvider 共享模式）
    # ------------------------------------------------------------------

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _http_post(self, url: str, **kwargs) -> httpx.Response:
        timeout = kwargs.pop("timeout", self._timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.post(url, **kwargs)

    def _check_response(self, resp: httpx.Response) -> None:
        if 200 <= resp.status_code < 300:
            return
        if resp.status_code >= 500 or resp.status_code == 429:
            raise ImageGenError(
                f"海螺 AI HTTP {resp.status_code}: {resp.text[:200]}",
                retryable=True,
            )
        raise ImageGenError(
            f"海螺 AI HTTP {resp.status_code}: {resp.text[:200]}",
            retryable=False,
        )

    async def _download_and_upload(self, url: str) -> str:
        if not self.oss_client:
            return url
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning("下载图片失败 HTTP %s: %s", resp.status_code, url)
                    return url
                import uuid
                key = f"image-gen/{uuid.uuid4().hex}.png"
                oss_url = self.oss_client.upload_bytes(key, resp.content, "image/png")
                return oss_url
        except Exception as e:
            logger.warning("下载/上传图片失败: %s", e)
            return url


# 注册到 provider registry
register_provider("minimax_image", HailuoProvider)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/harness/test_hailuo_provider.py -v`
Expected: ALL PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/harness/image_provider/hailuo.py backend/tests/harness/test_hailuo_provider.py
git commit -m "feat(harness): add HailuoProvider (minimax_image)"
```

---

### Task 4: DoubaoSeedProvider 实现

**Files:**
- Create: `backend/app/services/harness/image_provider/doubao.py`
- Test: `backend/tests/harness/test_doubao_provider.py`

**Interfaces:**
- Consumes: `ImageModelProvider`, `ImageGenParams`, `ImageGenResult`, `ImageGenError`, `register_provider` from Task 1
- Produces: `DoubaoSeedProvider` class, registered as `provider_type="doubao_seedream"`

- [ ] **Step 1: Write tests for DoubaoSeedProvider**

```python
# backend/tests/harness/test_doubao_provider.py
"""豆包 Seed (ByteDance) Provider 测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.harness.image_provider.base import ImageGenError, ImageGenParams
from app.services.harness.image_provider.doubao import DoubaoSeedProvider


@pytest.fixture
def provider():
    return DoubaoSeedProvider(
        base_url="https://visual.volcengineapi.com/v1",
        api_key="test-doubao-key",
        oss_client=MagicMock(),
    )


class TestDoubaoSeedProvider:
    @pytest.mark.asyncio
    async def test_text2img_success(self, provider):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "images": [{"url": "https://cdn.doubao.com/generated.png"}],
                "model": "seedream-v1",
            }
        }

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            with patch.object(provider, "_download_and_upload", new_callable=AsyncMock, return_value="https://my-oss.com/img.png"):
                params = ImageGenParams(size="1024x1024", n=1, model_name="seedream-v1")
                result = await provider.text2img("一只猫", params)

        assert result.image_urls == ["https://my-oss.com/img.png"]
        assert result.model_used == "seedream-v1"

    @pytest.mark.asyncio
    async def test_401_is_fatal(self, provider):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            params = ImageGenParams(model_name="seedream-v1")
            with pytest.raises(ImageGenError) as exc_info:
                await provider.text2img("test", params)
            assert exc_info.value.retryable is False

    @pytest.mark.asyncio
    async def test_500_is_retryable(self, provider):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(provider, "_http_post", new_callable=AsyncMock, return_value=mock_response):
            params = ImageGenParams(model_name="seedream-v1")
            with pytest.raises(ImageGenError) as exc_info:
                await provider.text2img("test", params)
            assert exc_info.value.retryable is True

    def test_validate_config_with_key(self, provider):
        provider.validate_config()

    def test_validate_config_without_key(self):
        p = DoubaoSeedProvider(base_url="http://x", api_key="", oss_client=None)
        with pytest.raises(ImageGenError, match="api_key"):
            p.validate_config()

    def test_registered_as_doubao_seedream(self):
        from app.services.harness.image_provider.registry import _PROVIDER_MAP
        from app.services.harness.image_provider import doubao  # noqa: F401
        assert "doubao_seedream" in _PROVIDER_MAP
        assert _PROVIDER_MAP["doubao_seedream"] is DoubaoSeedProvider
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/harness/test_doubao_provider.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement DoubaoSeedProvider**

```python
# backend/app/services/harness/image_provider/doubao.py
"""豆包 Seed (ByteDance Doubao Seedream) Provider

通过火山引擎视觉 API 调用豆包 Seed 图像生成。
参考文档：https://www.volcengine.com/docs/6791/1347773

provider_type: doubao_seedream
"""
import logging
import time

import httpx

from app.services.harness.image_provider.base import (
    ImageGenError,
    ImageGenParams,
    ImageGenResult,
    ImageModelProvider,
)
from app.services.harness.image_provider.registry import register_provider

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 60.0


class DoubaoSeedProvider(ImageModelProvider):
    """豆包 Seed Provider

    火山引擎 API 调用流程：
    1. POST 图像生成请求
    2. 解析返回的图片 URL
    3. 下载 → 上传到自有 OSS
    4. 返回 OSS URL
    """

    def __init__(self, base_url: str, api_key: str, oss_client=None):
        super().__init__(base_url, api_key, oss_client)
        self._timeout = _DEFAULT_TIMEOUT

    async def text2img(self, prompt: str, params: ImageGenParams) -> ImageGenResult:
        model = params.model_name or "seedream-v1"
        start = time.time()

        body = {
            "model": model,
            "prompt": prompt,
            "width": self._parse_size(params.size)[0],
            "height": self._parse_size(params.size)[1],
            "n": params.n,
        }
        if params.style:
            body["style"] = params.style

        resp = await self._http_post(
            f"{self.base_url}/images/generations",
            json=body,
            headers=self._build_headers(),
        )
        self._check_response(resp)

        data = resp.json()
        images = data.get("data", {}).get("images", [])
        raw_urls = [img.get("url", "") for img in images if img.get("url")]
        if not raw_urls:
            raise ImageGenError("豆包 Seed 未返回图片 URL", retryable=True)

        oss_urls = [await self._download_and_upload(u) for u in raw_urls]

        return ImageGenResult(
            image_urls=oss_urls,
            model_used=model,
            elapsed_seconds=time.time() - start,
        )

    async def img2img(self, prompt: str, reference_image: str, params: ImageGenParams) -> ImageGenResult:
        model = params.model_name or "seedream-v1"
        start = time.time()

        body = {
            "model": model,
            "prompt": prompt,
            "reference_image": reference_image,
            "width": self._parse_size(params.size)[0],
            "height": self._parse_size(params.size)[1],
            "n": params.n,
        }

        resp = await self._http_post(
            f"{self.base_url}/images/img2img",
            json=body,
            headers=self._build_headers(),
        )
        self._check_response(resp)

        data = resp.json()
        images = data.get("data", {}).get("images", [])
        raw_urls = [img.get("url", "") for img in images if img.get("url")]
        if not raw_urls:
            raise ImageGenError("豆包 Seed 未返回图片 URL", retryable=True)

        oss_urls = [await self._download_and_upload(u) for u in raw_urls]

        return ImageGenResult(
            image_urls=oss_urls,
            model_used=model,
            elapsed_seconds=time.time() - start,
        )

    async def inpaint(self, prompt: str, image_url: str, mask_url: str, params: ImageGenParams) -> ImageGenResult:
        model = params.model_name or "seedream-v1"
        start = time.time()

        body = {
            "model": model,
            "prompt": prompt,
            "image_url": image_url,
            "mask_url": mask_url,
            "width": self._parse_size(params.size)[0],
            "height": self._parse_size(params.size)[1],
            "n": params.n,
        }

        resp = await self._http_post(
            f"{self.base_url}/images/inpaint",
            json=body,
            headers=self._build_headers(),
        )
        self._check_response(resp)

        data = resp.json()
        images = data.get("data", {}).get("images", [])
        raw_urls = [img.get("url", "") for img in images if img.get("url")]
        if not raw_urls:
            raise ImageGenError("豆包 Seed 未返回图片 URL", retryable=True)

        oss_urls = [await self._download_and_upload(u) for u in raw_urls]

        return ImageGenResult(
            image_urls=oss_urls,
            model_used=model,
            elapsed_seconds=time.time() - start,
        )

    async def upload_edit(self, image_url: str, instruction: str, params: ImageGenParams) -> ImageGenResult:
        model = params.model_name or "seedream-v1"
        start = time.time()

        body = {
            "model": model,
            "image_url": image_url,
            "prompt": instruction,
            "width": self._parse_size(params.size)[0],
            "height": self._parse_size(params.size)[1],
            "n": params.n,
        }

        resp = await self._http_post(
            f"{self.base_url}/images/edit",
            json=body,
            headers=self._build_headers(),
        )
        self._check_response(resp)

        data = resp.json()
        images = data.get("data", {}).get("images", [])
        raw_urls = [img.get("url", "") for img in images if img.get("url")]
        if not raw_urls:
            raise ImageGenError("豆包 Seed 未返回图片 URL", retryable=True)

        oss_urls = [await self._download_and_upload(u) for u in raw_urls]

        return ImageGenResult(
            image_urls=oss_urls,
            model_used=model,
            elapsed_seconds=time.time() - start,
        )

    def validate_config(self) -> None:
        if not self.api_key:
            raise ImageGenError("豆包 Seed api_key 未配置")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_size(size: str) -> tuple:
        """解析 '1024x1024' → (1024, 1024)"""
        try:
            w, h = size.split("x")
            return int(w), int(h)
        except (ValueError, AttributeError):
            return 1024, 1024

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _http_post(self, url: str, **kwargs) -> httpx.Response:
        timeout = kwargs.pop("timeout", self._timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.post(url, **kwargs)

    def _check_response(self, resp: httpx.Response) -> None:
        if 200 <= resp.status_code < 300:
            return
        if resp.status_code >= 500 or resp.status_code == 429:
            raise ImageGenError(
                f"豆包 Seed HTTP {resp.status_code}: {resp.text[:200]}",
                retryable=True,
            )
        raise ImageGenError(
            f"豆包 Seed HTTP {resp.status_code}: {resp.text[:200]}",
            retryable=False,
        )

    async def _download_and_upload(self, url: str) -> str:
        if not self.oss_client:
            return url
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning("下载图片失败 HTTP %s: %s", resp.status_code, url)
                    return url
                import uuid
                key = f"image-gen/{uuid.uuid4().hex}.png"
                oss_url = self.oss_client.upload_bytes(key, resp.content, "image/png")
                return oss_url
        except Exception as e:
            logger.warning("下载/上传图片失败: %s", e)
            return url


# 注册到 provider registry
register_provider("doubao_seedream", DoubaoSeedProvider)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/harness/test_doubao_provider.py -v`
Expected: ALL PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/harness/image_provider/doubao.py backend/tests/harness/test_doubao_provider.py
git commit -m "feat(harness): add DoubaoSeedProvider (doubao_seedream)"
```

---

### Task 5: Prompt 润色 Helper

**Files:**
- Create: `backend/app/services/harness/tools/prompt_refiner.py`
- Test: `backend/tests/harness/test_prompt_refiner.py`

**Interfaces:**
- Consumes: `ToolContext.llm_gateway`（OrderedLLMGateway 实例）
- Produces: `refine_image_prompt(prompt: str, ctx: ToolContext) -> str`

- [ ] **Step 1: Write tests for prompt refinement**

```python
# backend/tests/harness/test_prompt_refiner.py
"""Prompt 润色 helper 测试

验证：
1. 正常润色（中文 → 英文）
2. LLM 不可用时降级返回原始 prompt
3. LLM 超时时降级返回原始 prompt
4. 空 prompt 返回空字符串
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.harness.tools.prompt_refiner import refine_image_prompt
from app.services.harness.tool_protocol import ToolContext


def _make_ctx(llm_gateway=None):
    return ToolContext(
        user_id="user-1",
        conversation_id="conv-1",
        agent_id="agent-1",
        llm_gateway=llm_gateway,
    )


class TestRefineImagePrompt:
    @pytest.mark.asyncio
    async def test_normal_refinement(self):
        """LLM 正常返回英文 prompt"""
        mock_gateway = AsyncMock()
        mock_gateway.generate.return_value = {
            "content": "a beautiful cat sitting on a wooden table, high quality, detailed",
            "usage": {"total_tokens": 50},
        }

        ctx = _make_ctx(llm_gateway=mock_gateway)
        result = await refine_image_prompt("一只漂亮的猫坐在桌子上", ctx)

        assert "cat" in result
        assert len(result) > 0
        mock_gateway.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_prompt_returns_empty(self):
        """空 prompt 返回空字符串"""
        ctx = _make_ctx()
        result = await refine_image_prompt("", ctx)
        assert result == ""

    @pytest.mark.asyncio
    async def test_whitespace_prompt_returns_empty(self):
        """纯空白 prompt 返回空字符串"""
        ctx = _make_ctx()
        result = await refine_image_prompt("   ", ctx)
        assert result == ""

    @pytest.mark.asyncio
    async def test_llm_unavailable_fallback(self):
        """LLM 不可用时返回原始 prompt"""
        mock_gateway = AsyncMock()
        mock_gateway.generate.side_effect = Exception("LLM service unavailable")

        ctx = _make_ctx(llm_gateway=mock_gateway)
        original = "一只漂亮的猫"
        result = await refine_image_prompt(original, ctx)

        assert result == original

    @pytest.mark.asyncio
    async def test_llm_timeout_fallback(self):
        """LLM 超时时返回原始 prompt"""
        import asyncio
        mock_gateway = AsyncMock()
        mock_gateway.generate.side_effect = asyncio.TimeoutError()

        ctx = _make_ctx(llm_gateway=mock_gateway)
        original = "日落风景"
        result = await refine_image_prompt(original, ctx)

        assert result == original

    @pytest.mark.asyncio
    async def test_no_gateway_fallback(self):
        """ctx.llm_gateway 为 None 时返回原始 prompt"""
        ctx = _make_ctx(llm_gateway=None)
        original = "一只狗"
        result = await refine_image_prompt(original, ctx)
        assert result == original

    @pytest.mark.asyncio
    async def test_already_english_passthrough(self):
        """已经是英文的 prompt 直接返回（不调 LLM）"""
        mock_gateway = AsyncMock()
        ctx = _make_ctx(llm_gateway=mock_gateway)

        result = await refine_image_prompt("a beautiful sunset over the ocean", ctx)

        assert result == "a beautiful sunset over the ocean"
        mock_gateway.generate.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/harness/test_prompt_refiner.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement prompt refiner**

```python
# backend/app/services/harness/tools/prompt_refiner.py
"""Prompt 润色 helper

将中文图像描述转化为高质量英文 prompt，用于传给图像生成 provider。
通过 ctx.llm_gateway 调用 LLM 完成润色。

降级策略：LLM 不可用 / 超时 / 异常时返回原始 prompt，不阻塞生成。
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 判断字符串是否基本为英文（>80% ASCII 字母/空格/标点）
_ENGLISH_RATIO_THRESHOLD = 0.8
_ENGLISH_CHAR_RE = re.compile(r'[a-zA-Z\s\.,!?;:\'"()\-\[\]{}]')

# 润色 system prompt
_REFINE_SYSTEM_PROMPT = (
    "You are an expert image generation prompt engineer. "
    "Convert the following Chinese description into a high-quality English prompt "
    "for image generation. Keep key details, enhance composition descriptions, "
    "add quality modifiers (e.g., 'high quality', 'detailed', 'professional photography'). "
    "Return ONLY the English prompt, no explanation."
)

# 润色超时（秒）
_REFINE_TIMEOUT = 10.0


def _is_mostly_english(text: str) -> bool:
    """判断文本是否主要为英文"""
    if not text:
        return False
    chars = list(text)
    if not chars:
        return False
    en_count = sum(1 for c in chars if _ENGLISH_CHAR_RE.match(c))
    return (en_count / len(chars)) >= _ENGLISH_RATIO_THRESHOLD


async def refine_image_prompt(prompt: str, ctx) -> str:
    """润色图像生成 prompt

    Args:
        prompt: 原始 prompt（可能中文或英文）
        ctx: ToolContext（通过 ctx.llm_gateway 调用 LLM）

    Returns:
        润色后的英文 prompt。LLM 不可用时返回原始 prompt。
    """
    if not prompt or not prompt.strip():
        return ""

    stripped = prompt.strip()

    # 已经基本是英文 → 直接返回，不调 LLM
    if _is_mostly_english(stripped):
        return stripped

    # 无 LLM gateway → 降级返回原始
    gateway = getattr(ctx, "llm_gateway", None)
    if gateway is None:
        logger.debug("Prompt 润色：llm_gateway 不可用，返回原始 prompt")
        return stripped

    try:
        messages = [
            {"role": "system", "content": _REFINE_SYSTEM_PROMPT},
            {"role": "user", "content": stripped},
        ]

        result = await gateway.generate(
            category="text",
            messages=messages,
            temperature=0.7,
            max_tokens=300,
        )

        # 解析返回值（gateway.generate 返回 dict 或 str）
        if isinstance(result, str):
            refined = result.strip()
        elif isinstance(result, dict):
            content = result.get("content", "")
            refined = content.strip() if isinstance(content, str) else str(content).strip()
        else:
            refined = getattr(result, "content", str(result)).strip()

        if not refined:
            logger.warning("Prompt 润色返回空值，使用原始 prompt")
            return stripped

        return refined

    except Exception as e:
        logger.warning("Prompt 润色失败（降级使用原始 prompt）: %s", e)
        return stripped
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/harness/test_prompt_refiner.py -v`
Expected: ALL PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/harness/tools/prompt_refiner.py backend/tests/harness/test_prompt_refiner.py
git commit -m "feat(harness): add prompt refiner for image generation"
```

---

### Task 6: image_gen BuiltinTool（核心）

**Files:**
- Create: `backend/app/services/harness/tools/image_gen.py`
- Test: `backend/tests/harness/test_image_gen_tool.py`

**Interfaces:**
- Consumes: `BuiltinTool` base (Task 0), `ImageModelProvider`/`ImageGenParams`/`ImageGenResult`/`ImageGenError` (Task 1), `resolve_provider` (Task 1), `refine_image_prompt` (Task 5), `ToolContext`, `ToolResult`, `Attachment`
- Produces: `ImageGenTool` class (name="image_gen")

- [ ] **Step 1: Write tests for ImageGenTool**

```python
# backend/tests/harness/test_image_gen_tool.py
"""image_gen BuiltinTool 测试

覆盖：
1. text2img 成功路径
2. img2img 缺少 reference_image_url 返回错误
3. inpaint 缺少 mask_url 返回错误
4. upload_edit 正常路径
5. fallback 链：主 provider retryable 失败 → 切到备选
6. fallback 链：全部失败 → 返回 ToolResult.error
7. prompt 润色降级（LLM 不可用 → 用原始 prompt）
8. 无效 operation 返回错误
9. 结果包含 attachments
10. emit image_generated 事件
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.harness.tools.image_gen import ImageGenTool
from app.services.harness.image_provider.base import (
    ImageGenError,
    ImageGenParams,
    ImageGenResult,
)
from app.services.harness.tool_protocol import ToolContext, ToolResult


def _make_ctx(agent=None, event_emitter=None, llm_gateway=None):
    ctx = MagicMock(spec=ToolContext)
    ctx.user_id = "user-1"
    ctx.conversation_id = "conv-1"
    ctx.agent_id = "agent-1"
    ctx.agent = agent or MagicMock(
        default_model_id="model-uuid-1",
        fallback_model_ids=["model-uuid-2"],
    )
    ctx.event_emitter = event_emitter
    ctx.llm_gateway = llm_gateway
    ctx.db = MagicMock()
    ctx.oss_service = MagicMock()
    return ctx


class TestImageGenTool:
    def test_tool_metadata(self):
        tool = ImageGenTool()
        assert tool.name == "image_gen"
        assert tool.display_name == "图像生成"
        assert "operation" in tool.parameters_schema.get("properties", {})

    @pytest.mark.asyncio
    async def test_text2img_success(self):
        tool = ImageGenTool()
        mock_provider = AsyncMock()
        mock_provider.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/img.png"],
            model_used="wanx-v1",
            elapsed_seconds=2.5,
        )

        ctx = _make_ctx()

        with patch.object(tool, "_resolve_provider_chain", return_value=[("wanx-v1", mock_provider)]):
            with patch("app.services.harness.tools.image_gen.refine_image_prompt", new_callable=AsyncMock, return_value="a cat"):
                result = await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫"},
                    ctx,
                )

        assert result.success is True
        assert len(result.attachments) == 1
        assert result.attachments[0].type == "image"
        assert result.attachments[0].url == "https://oss.example.com/img.png"

    @pytest.mark.asyncio
    async def test_img2img_missing_reference_returns_error(self):
        tool = ImageGenTool()
        ctx = _make_ctx()
        result = await tool.execute(
            {"operation": "img2img", "prompt": "修改这张图"},
            ctx,
        )
        assert result.success is False
        assert "reference_image_url" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_inpaint_missing_mask_returns_error(self):
        tool = ImageGenTool()
        ctx = _make_ctx()
        result = await tool.execute(
            {"operation": "inpaint", "prompt": "修改区域", "image_url": "https://example.com/img.png"},
            ctx,
        )
        assert result.success is False
        assert "mask_url" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_invalid_operation_returns_error(self):
        tool = ImageGenTool()
        ctx = _make_ctx()
        result = await tool.execute(
            {"operation": "invalid_op", "prompt": "test"},
            ctx,
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_fallback_on_retryable_error(self):
        """主 provider retryable 失败 → 切到备选 provider"""
        tool = ImageGenTool()

        primary = AsyncMock()
        primary.text2img.side_effect = ImageGenError("timeout", retryable=True)

        secondary = AsyncMock()
        secondary.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/fallback.png"],
            model_used="hailuo-v1",
        )

        ctx = _make_ctx()

        with patch.object(tool, "_resolve_provider_chain", return_value=[("wanx-v1", primary), ("hailuo-v1", secondary)]):
            with patch("app.services.harness.tools.image_gen.refine_image_prompt", new_callable=AsyncMock, return_value="a cat"):
                result = await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫"},
                    ctx,
                )

        assert result.success is True
        assert result.metadata.get("model_used") == "hailuo-v1"
        primary.text2img.assert_called_once()
        secondary.text2img.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_providers_fail_returns_error(self):
        """所有 provider 失败 → ToolResult.error"""
        tool = ImageGenTool()

        primary = AsyncMock()
        primary.text2img.side_effect = ImageGenError("timeout", retryable=True)
        secondary = AsyncMock()
        secondary.text2img.side_effect = ImageGenError("auth failed", retryable=False)

        ctx = _make_ctx()

        with patch.object(tool, "_resolve_provider_chain", return_value=[("wanx-v1", primary), ("hailuo-v1", secondary)]):
            with patch("app.services.harness.tools.image_gen.refine_image_prompt", new_callable=AsyncMock, return_value="a cat"):
                result = await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫"},
                    ctx,
                )

        assert result.success is False
        assert "所有图像模型均不可用" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_fatal_error_stops_fallback(self):
        """fatal 错误不触发 fallback（直接失败）"""
        tool = ImageGenTool()

        primary = AsyncMock()
        primary.text2img.side_effect = ImageGenError("invalid api key", retryable=False)
        secondary = AsyncMock()

        ctx = _make_ctx()

        with patch.object(tool, "_resolve_provider_chain", return_value=[("wanx-v1", primary), ("hailuo-v1", secondary)]):
            with patch("app.services.harness.tools.image_gen.refine_image_prompt", new_callable=AsyncMock, return_value="a cat"):
                result = await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫"},
                    ctx,
                )

        assert result.success is False
        secondary.text2img.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_prompt_returns_error(self):
        tool = ImageGenTool()
        ctx = _make_ctx()
        result = await tool.execute(
            {"operation": "text2img", "prompt": ""},
            ctx,
        )
        assert result.success is False
        assert "prompt" in (result.error_message or "").lower()

    @pytest.mark.asyncio
    async def test_emits_image_generated_event(self):
        """成功时通过 event_emitter 发送 image_generated 事件"""
        tool = ImageGenTool()
        mock_provider = AsyncMock()
        mock_provider.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/img.png"],
            model_used="wanx-v1",
        )

        emitter = AsyncMock()
        ctx = _make_ctx(event_emitter=emitter)

        with patch.object(tool, "_resolve_provider_chain", return_value=[("wanx-v1", mock_provider)]):
            with patch("app.services.harness.tools.image_gen.refine_image_prompt", new_callable=AsyncMock, return_value="a cat"):
                await tool.execute(
                    {"operation": "text2img", "prompt": "一只猫"},
                    ctx,
                )

        emitter.assert_called_once()
        call_args = emitter.call_args
        event = call_args[0][0]
        assert event.type == "image_generated"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/harness/test_image_gen_tool.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement ImageGenTool**

```python
# backend/app/services/harness/tools/image_gen.py
"""image_gen BuiltinTool — 图像生成工具

支持 4 种操作：text2img / img2img / inpaint / upload_edit
通过 ImageModelProvider 抽象支持多 provider，含 prompt 润色和 fallback 链。

参考 spec §5
"""
import logging
import time
from typing import List, Tuple

from app.services.harness.tool_protocol import (
    Attachment,
    ToolContext,
    ToolResult,
)
from app.services.harness.tools.base import BuiltinTool
from app.services.harness.tools.prompt_refiner import refine_image_prompt
from app.services.harness.image_provider.base import (
    ImageGenError,
    ImageGenParams,
    ImageGenResult,
)
from app.services.harness.image_provider.registry import resolve_provider

logger = logging.getLogger(__name__)

# 操作与必填字段映射
_OPERATION_REQUIRED_FIELDS = {
    "text2img": ["prompt"],
    "img2img": ["prompt", "reference_image_url"],
    "inpaint": ["prompt", "image_url", "mask_url"],
    "upload_edit": ["prompt", "image_url"],
}


class ImageGenTool(BuiltinTool):
    """图像生成工具"""

    name = "image_gen"
    display_name = "图像生成"
    description = (
        "生成或编辑图像。支持文生图(text2img)、图生图(img2img)、"
        "局部重绘(inpaint)、指令编辑(upload_edit)四种操作。"
    )
    parameters_schema = {
        "type": "object",
        "required": ["operation", "prompt"],
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["text2img", "img2img", "inpaint", "upload_edit"],
                "description": "操作类型",
            },
            "prompt": {
                "type": "string",
                "description": "图像描述或编辑指令（中文即可，系统自动润色为英文）",
            },
            "reference_image_url": {
                "type": "string",
                "description": "参考图片 URL（img2img 时必填）",
            },
            "mask_url": {
                "type": "string",
                "description": "遮罩图片 URL（inpaint 时必填）",
            },
            "image_url": {
                "type": "string",
                "description": "原始图片 URL（inpaint/upload_edit 时必填）",
            },
            "size": {
                "type": "string",
                "enum": ["1024x1024", "1024x1792", "1792x1024", "512x512"],
                "default": "1024x1024",
            },
            "n": {
                "type": "integer",
                "minimum": 1,
                "maximum": 4,
                "default": 1,
            },
            "style": {
                "type": "string",
                "description": "风格预设（可选）",
            },
        },
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "image_urls": {"type": "array", "items": {"type": "string"}},
            "model_used": {"type": "string"},
            "revised_prompt": {"type": "string"},
        },
    }

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        # 1. 参数校验
        operation = args.get("operation", "").strip()
        if operation not in _OPERATION_REQUIRED_FIELDS:
            return ToolResult.error(f"无效操作: {operation}，支持: {list(_OPERATION_REQUIRED_FIELDS.keys())}")

        prompt = (args.get("prompt") or "").strip()
        if not prompt:
            return ToolResult.error("prompt 不能为空")

        # 检查必填字段
        for field_name in _OPERATION_REQUIRED_FIELDS[operation]:
            if field_name == "prompt":
                continue
            if not args.get(field_name):
                return ToolResult.error(f"操作 {operation} 需要参数: {field_name}")

        # 2. Prompt 润色（可降级）
        revised_prompt = await refine_image_prompt(prompt, ctx)

        # 3. 构造参数
        params = ImageGenParams(
            size=args.get("size", "1024x1024"),
            n=min(max(int(args.get("n", 1)), 1), 4),
            style=args.get("style"),
        )

        # 4. 模型选择 + Fallback 链
        provider_chain = self._resolve_provider_chain(ctx)
        if not provider_chain:
            return ToolResult.error("无可用图像模型")

        last_error = None
        for model_name, provider in provider_chain:
            try:
                params.model_name = model_name
                result = await self._dispatch(provider, operation, revised_prompt, args, params)

                # 5. 结果组装
                attachments = [
                    Attachment(type="image", url=url, name=f"generated_{i}.png")
                    for i, url in enumerate(result.image_urls)
                ]

                tool_result = ToolResult(
                    success=True,
                    content={
                        "operation": operation,
                        "model_used": result.model_used,
                        "revised_prompt": result.revised_prompt or revised_prompt,
                        "image_count": len(result.image_urls),
                    },
                    content_type="json",
                    metadata={
                        "model_used": result.model_used,
                        "elapsed_seconds": result.elapsed_seconds,
                    },
                    attachments=attachments,
                )

                # 6. 发送 image_generated 事件
                await self._emit_event(ctx, result, operation)

                return tool_result

            except ImageGenError as e:
                logger.warning(
                    "图像生成失败 model=%s operation=%s: %s (retryable=%s)",
                    model_name, operation, e, e.retryable,
                )
                last_error = e
                if not e.retryable:
                    # fatal 错误不触发 fallback
                    break
                continue
            except Exception as e:
                logger.error("图像生成异常 model=%s: %s", model_name, e, exc_info=True)
                last_error = e
                break

        return ToolResult.error(
            f"所有图像模型均不可用: {last_error}" if last_error else "所有图像模型均不可用"
        )

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    async def _dispatch(self, provider, operation: str, prompt: str, args: dict, params: ImageGenParams) -> ImageGenResult:
        """分发到 provider 的具体操作方法"""
        if operation == "text2img":
            return await provider.text2img(prompt, params)
        elif operation == "img2img":
            return await provider.img2img(prompt, args["reference_image_url"], params)
        elif operation == "inpaint":
            return await provider.inpaint(prompt, args["image_url"], args["mask_url"], params)
        elif operation == "upload_edit":
            return await provider.upload_edit(args["image_url"], prompt, params)
        else:
            raise ValueError(f"未知操作: {operation}")

    def _resolve_provider_chain(self, ctx: ToolContext) -> List[Tuple[str, object]]:
        """从 Agent 配置解析 provider 链（主模型 + fallback）

        Returns:
            [(model_name, provider_instance), ...] 按优先级排序
        """
        chain = []
        agent = getattr(ctx, "agent", None)
        if agent is None:
            return chain

        db = getattr(ctx, "db", None)
        oss = getattr(ctx, "oss_service", None)

        # 收集所有候选 model ID（主模型 + fallback）
        model_ids = []
        if getattr(agent, "default_model_id", None):
            model_ids.append(agent.default_model_id)
        fallback_ids = getattr(agent, "fallback_model_ids", None) or []
        model_ids.extend(fallback_ids)

        if not model_ids:
            return chain

        # 从 DB 查询 LLMModel 并解析 provider
        if db is None:
            return chain

        from app.models.llm_model import LLMModel

        for model_id in model_ids:
            try:
                llm_model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
                if llm_model is None:
                    continue
                if llm_model.category != "image_gen":
                    continue
                if not llm_model.is_active:
                    continue

                provider = resolve_provider(llm_model.provider, oss_client=oss)
                chain.append((llm_model.model_name, provider))
            except Exception as e:
                logger.warning("解析图像模型失败 model_id=%s: %s", model_id, e)
                continue

        return chain

    async def _emit_event(self, ctx: ToolContext, result: ImageGenResult, operation: str):
        """通过 event_emitter 发送 image_generated 事件"""
        emitter = getattr(ctx, "event_emitter", None)
        if emitter is None:
            return
        try:
            from app.services.harness.events import Event
            event = Event.image_generated(
                urls=result.image_urls,
                metadata={
                    "model_used": result.model_used,
                    "operation": operation,
                    "elapsed_seconds": result.elapsed_seconds,
                },
            )
            await emitter(event)
        except Exception as e:
            logger.warning("发送 image_generated 事件失败: %s", e)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/harness/test_image_gen_tool.py -v`
Expected: ALL PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/harness/tools/image_gen.py backend/tests/harness/test_image_gen_tool.py
git commit -m "feat(harness): add image_gen BuiltinTool with fallback chain and prompt refinement"
```

---

### Task 7: image_gen 注册 + chat_stream 集成

**Files:**
- Modify: `backend/app/api/routes/chat_stream.py` — 注册 ImageGenTool 到 ToolRegistry
- Modify: `backend/app/main.py` — lifespan 日志
- Test: `backend/tests/harness/test_image_gen_registration.py`

**Interfaces:**
- Consumes: `ImageGenTool` (Task 6), `ToolRegistry` (Phase 1), `chat_stream` (Phase 1)
- Produces: image_gen 工具在每次 chat_stream 请求中可用

- [ ] **Step 1: Write tests for registration**

```python
# backend/tests/harness/test_image_gen_registration.py
"""image_gen 工具注册测试"""
import pytest
from unittest.mock import MagicMock

from app.services.harness.tool_registry import ToolRegistry
from app.services.harness.tools.image_gen import ImageGenTool


class TestImageGenRegistration:
    def test_register_image_gen_tool(self, test_db):
        """ImageGenTool 可以注册到 ToolRegistry"""
        registry = ToolRegistry(db=test_db)
        tool = ImageGenTool()
        registry.register_builtin(tool)
        assert "image_gen" in registry._builtin

    def test_image_gen_in_function_schemas(self, test_db):
        """image_gen 出现在 function schemas 中"""
        registry = ToolRegistry(db=test_db)
        tool = ImageGenTool()
        registry.register_builtin(tool)
        schemas = registry.to_function_schemas([tool])
        assert len(schemas) == 1
        assert schemas[0]["name"] == "image_gen"
        assert "operation" in schemas[0]["parameters"]["properties"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/harness/test_image_gen_registration.py -v`
Expected: FAIL if ImageGenTool not importable, otherwise PASS (since tool_registry already supports register_builtin)

- [ ] **Step 3: Modify chat_stream.py to register ImageGenTool**

先读取 chat_stream.py 找到注册工具的代码位置：

```bash
cd backend && grep -n "register_builtin\|WebSearchTool\|DbQueryTool\|ToolRegistry" app/api/routes/chat_stream.py
```

在现有的工具注册代码处追加：

```python
# 在 chat_stream.py 中注册工具的位置追加：
from app.services.harness.tools.image_gen import ImageGenTool

# 注册 image_gen 工具
registry.register_builtin(ImageGenTool())
```

- [ ] **Step 4: Modify main.py lifespan 日志**

在 `backend/app/main.py` lifespan 启动阶段的 harness 日志处追加：

```python
# 追加到 harness 初始化日志块
try:
    from app.services.harness.tools.image_gen import ImageGenTool
    logger.info("Harness ImageGenTool 模块已就绪（按需注册）")
except Exception as e:
    logger.warning(f"ImageGenTool 模块加载失败: {e}")
```

- [ ] **Step 5: Run registration tests**

Run: `cd backend && python -m pytest tests/harness/test_image_gen_registration.py -v`
Expected: ALL PASS

- [ ] **Step 6: Run full harness test suite to verify no regressions**

Run: `cd backend && python -m pytest tests/harness/ -v --tb=short`
Expected: ALL PASS (所有既有测试不受影响)

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/routes/chat_stream.py backend/app/main.py backend/tests/harness/test_image_gen_registration.py
git commit -m "feat(harness): register image_gen tool in chat_stream + lifespan"
```

---

### Task 8: ImageGenRenderer 前端组件

**Files:**
- Create: `frontend/src/components/Chat/ToolRenderers/ImageGenRenderer.tsx`
- Modify: `frontend/src/components/Chat/ToolCallRenderer.tsx` — 添加 image_gen 到 DEFAULT_BUILTINS
- Test: `frontend/src/components/Chat/ToolRenderers/__tests__/ImageGenRenderer.test.tsx`（如 vitest 支持）

**Interfaces:**
- Consumes: `ToolRendererProps` from `useToolRegistry`, `ToolCall`/`ToolResult` from `@/types/tool`, `safeHref` from `WebSearchRenderer`
- Produces: `ImageGenRenderer` component

- [ ] **Step 1: Write ImageGenRenderer component**

```tsx
// frontend/src/components/Chat/ToolRenderers/ImageGenRenderer.tsx
/**
 * ImageGen 工具渲染器
 *
 * 显示图像生成结果：
 * - 操作类型 badge（文生图/图生图/局部重绘/指令编辑）
 * - 模型标签 (model_used)
 * - 润色后 prompt（可折叠）
 * - 图片网格（1-4 张）：缩略图 + 点击放大
 * - 失败时显示 error message
 *
 * 安全：图片 URL 经 safeHref 校验（仅 http/https）
 */
import React, { useState } from 'react';
import type { ToolRendererProps } from '@/stores/useToolRegistry';
import { safeHref } from './WebSearchRenderer';

/** operation 中文映射 */
const OPERATION_LABELS: Record<string, string> = {
  text2img: '文生图',
  img2img: '图生图',
  inpaint: '局部重绘',
  upload_edit: '指令编辑',
};

interface ImageGenContent {
  operation?: string;
  model_used?: string;
  revised_prompt?: string;
  image_count?: number;
}

export const ImageGenRenderer: React.FC<ToolRendererProps> = ({ call, result, pending }) => {
  const operation = (call.arguments?.operation as string) ?? '';
  const [showPrompt, setShowPrompt] = useState(false);

  // 解析 result.content
  const content = React.useMemo<ImageGenContent>(() => {
    if (!result) return {};
    const c = result.content;
    if (typeof c === 'string') {
      try { return JSON.parse(c) as ImageGenContent; } catch { return {}; }
    }
    if (c && typeof c === 'object') return c as ImageGenContent;
    return {};
  }, [result]);

  // 提取图片附件
  const imageUrls = React.useMemo<string[]>(() => {
    if (!result?.attachments) return [];
    return result.attachments
      .filter((a) => a.type === 'image')
      .map((a) => a.url);
  }, [result]);

  return (
    <div className="rounded-lg border border-surface-2 bg-surface-1 dark:bg-canvas p-3 text-sm">
      {/* 顶部：操作 badge + 模型标签 */}
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-accent-info/10 text-accent-info">
          image_gen
        </span>
        {operation && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-surface-2 text-ink-faint dark:text-ink-muted">
            {OPERATION_LABELS[operation] ?? operation}
          </span>
        )}
        {content.model_used && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-surface-2 text-ink-faint dark:text-ink-muted">
            {content.model_used}
          </span>
        )}
      </div>

      {/* 执行中 */}
      {pending && !result && (
        <div className="text-ink-faint dark:text-ink-muted text-xs italic py-3">
          正在生成图像...
        </div>
      )}

      {/* 失败 */}
      {result && !result.success && (
        <div className="text-danger text-xs py-2">
          生成失败：{result.error ?? '未知错误'}
        </div>
      )}

      {/* 润色后 prompt（可折叠） */}
      {result?.success && content.revised_prompt && (
        <div className="mb-2">
          <button
            type="button"
            onClick={() => setShowPrompt(!showPrompt)}
            className="text-xs text-accent-info hover:underline"
          >
            {showPrompt ? '收起润色 prompt' : '查看润色 prompt'}
          </button>
          {showPrompt && (
            <div className="mt-1 px-2 py-1 rounded bg-surface-2 text-xs text-ink-faint dark:text-ink-muted italic">
              {content.revised_prompt}
            </div>
          )}
        </div>
      )}

      {/* 图片网格 */}
      {result?.success && imageUrls.length > 0 && (
        <div className={`grid gap-2 mt-2 ${imageUrls.length === 1 ? 'grid-cols-1' : 'grid-cols-2'}`}>
          {imageUrls.map((url, idx) => {
            const safe = safeHref(url);
            return (
              <div key={idx} className="rounded overflow-hidden border border-surface-2">
                {safe ? (
                  <a href={safe} target="_blank" rel="noopener noreferrer nofollow">
                    <img
                      src={safe}
                      alt={`生成图片 ${idx + 1}`}
                      className="w-full h-auto object-cover cursor-pointer hover:opacity-90 transition-opacity"
                      loading="lazy"
                    />
                  </a>
                ) : (
                  <div className="px-2 py-1 text-xs text-ink-faint">
                    [图片 URL 不安全，无法显示]
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* 成功但无图片 */}
      {result?.success && imageUrls.length === 0 && (
        <div className="text-ink-faint dark:text-ink-muted text-xs italic py-2">
          未生成图片
        </div>
      )}
    </div>
  );
};

export default ImageGenRenderer;
```

- [ ] **Step 2: Register ImageGenRenderer in ToolCallRenderer**

修改 `frontend/src/components/Chat/ToolCallRenderer.tsx`：

在文件顶部 import 区域追加：

```typescript
import { ImageGenRenderer } from './ToolRenderers/ImageGenRenderer';
```

修改 DEFAULT_BUILTINS 常量：

```typescript
const DEFAULT_BUILTINS: Record<string, React.ComponentType<ToolRendererProps>> = {
  web_search: WebSearchRenderer,
  db_query: DbQueryRenderer,
  image_gen: ImageGenRenderer,
};
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: 0 errors on modified files

- [ ] **Step 4: Run frontend tests**

Run: `cd frontend && npm run test`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Chat/ToolRenderers/ImageGenRenderer.tsx frontend/src/components/Chat/ToolCallRenderer.tsx
git commit -m "feat(frontend): add ImageGenRenderer for image generation results"
```

---

### Task 9: 集成测试 + 文档

**Files:**
- Create: `backend/tests/harness/test_image_gen_integration.py`
- Create: `docs/harness/image-gen-guide.md`

**Interfaces:**
- Consumes: All of Task 1-8
- Produces: End-to-end test + developer guide

- [ ] **Step 1: Write integration test**

```python
# backend/tests/harness/test_image_gen_integration.py
"""image_gen 端到端集成测试

使用 mock provider + mock gateway 验证完整流程：
用户 prompt → prompt 润色 → provider 调用 → 结果组装 → 事件发送
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.harness.tools.image_gen import ImageGenTool
from app.services.harness.image_provider.base import ImageGenResult
from app.services.harness.tool_protocol import ToolContext


@pytest.fixture
def mock_ctx():
    ctx = MagicMock(spec=ToolContext)
    ctx.user_id = "user-1"
    ctx.conversation_id = "conv-1"
    ctx.agent_id = "agent-1"
    ctx.agent = MagicMock(
        default_model_id="model-uuid-1",
        fallback_model_ids=["model-uuid-2"],
    )
    ctx.event_emitter = AsyncMock()
    ctx.llm_gateway = AsyncMock()
    ctx.llm_gateway.generate.return_value = {
        "content": "a beautiful cat on a table, high quality",
        "usage": {"total_tokens": 30},
    }
    ctx.db = MagicMock()
    ctx.oss_service = MagicMock()
    return ctx


class TestImageGenIntegration:
    @pytest.mark.asyncio
    async def test_full_text2img_flow(self, mock_ctx):
        """完整 text2img 流程"""
        tool = ImageGenTool()

        mock_provider = AsyncMock()
        mock_provider.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/cat.png"],
            model_used="wanx-v1",
            revised_prompt="a beautiful cat on a table, high quality",
            elapsed_seconds=3.0,
        )

        with patch.object(tool, "_resolve_provider_chain", return_value=[("wanx-v1", mock_provider)]):
            result = await tool.execute(
                {"operation": "text2img", "prompt": "一只漂亮的猫坐在桌子上", "size": "1024x1024", "n": 1},
                mock_ctx,
            )

        # 验证结果
        assert result.success is True
        assert len(result.attachments) == 1
        assert result.attachments[0].type == "image"
        assert result.metadata["model_used"] == "wanx-v1"

        # 验证 prompt 润色被调用
        mock_ctx.llm_gateway.generate.assert_called_once()

        # 验证 image_generated 事件被发送
        mock_ctx.event_emitter.assert_called_once()
        event = mock_ctx.event_emitter.call_args[0][0]
        assert event.type == "image_generated"
        assert "https://oss.example.com/cat.png" in event.payload["urls"]

    @pytest.mark.asyncio
    async def test_full_flow_with_fallback(self, mock_ctx):
        """带 fallback 的完整流程"""
        tool = ImageGenTool()

        from app.services.harness.image_provider.base import ImageGenError

        primary = AsyncMock()
        primary.text2img.side_effect = ImageGenError("rate limit", retryable=True)

        secondary = AsyncMock()
        secondary.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/cat-fallback.png"],
            model_used="hailuo-v1",
        )

        with patch.object(tool, "_resolve_provider_chain", return_value=[("wanx-v1", primary), ("hailuo-v1", secondary)]):
            result = await tool.execute(
                {"operation": "text2img", "prompt": "一只猫"},
                mock_ctx,
            )

        assert result.success is True
        assert result.metadata["model_used"] == "hailuo-v1"
        assert result.attachments[0].url == "https://oss.example.com/cat-fallback.png"

    @pytest.mark.asyncio
    async def test_prompt_refine_degrades_gracefully(self, mock_ctx):
        """prompt 润色失败时降级到原始 prompt"""
        tool = ImageGenTool()
        mock_ctx.llm_gateway.generate.side_effect = Exception("LLM down")

        mock_provider = AsyncMock()
        mock_provider.text2img.return_value = ImageGenResult(
            image_urls=["https://oss.example.com/cat.png"],
            model_used="wanx-v1",
        )

        with patch.object(tool, "_resolve_provider_chain", return_value=[("wanx-v1", mock_provider)]):
            result = await tool.execute(
                {"operation": "text2img", "prompt": "一只猫"},
                mock_ctx,
            )

        assert result.success is True
        # provider 被调用（没有因为 prompt 润色失败而阻塞）
        mock_provider.text2img.assert_called_once()
```

- [ ] **Step 2: Run integration tests**

Run: `cd backend && python -m pytest tests/harness/test_image_gen_integration.py -v`
Expected: ALL PASS (3 tests)

- [ ] **Step 3: Write developer guide**

```markdown
# docs/harness/image-gen-guide.md

# 图像生成工具开发指南

## 概述

`image_gen` BuiltinTool 提供 4 种图像生成操作，通过 `ImageModelProvider` 抽象支持多家 provider。

## 架构

```
image_gen BuiltinTool
├── Prompt 润色 (refine_image_prompt)
├── Provider Registry (resolve_provider)
│   ├── TongyiWanxiangProvider (qwen_image)
│   ├── HailuoProvider (minimax_image)
│   └── DoubaoSeedProvider (doubao_seedream)
└── Fallback 链 (Agent.fallback_model_ids)
```

## 添加新 Provider

1. 在 `backend/app/services/harness/image_provider/` 下创建新文件
2. 实现 `ImageModelProvider` 抽象类的 4 个操作方法 + `validate_config`
3. 在模块末尾调用 `register_provider("your_provider_type", YourProvider)`
4. 确保 `LLMProvider.provider_type` 与新类型匹配
5. 添加单元测试（mock httpx，验证参数映射和错误分类）

## 模型配置

在 Admin → 模型管理 中：
1. 创建 `LLMProvider`（provider_type 对应图像 provider 类型）
2. 创建 `LLMModel`（category="image_gen"，关联到上面的 Provider）
3. 在 Agent 配置中设置 `default_model_id` 为该 LLMModel

## 错误处理

- `retryable=True`: 超时/限流/5xx → 自动 fallback 到下一个 provider
- `retryable=False`: 鉴权失败/参数错误 → 不 fallback，直接返回错误

## 前端渲染

`ImageGenRenderer` 自动渲染图像生成结果，包括：
- 操作类型 badge
- 模型标签
- 润色后 prompt（可折叠）
- 图片网格（点击放大）

安全：图片 URL 经 `safeHref` 校验，仅允许 http/https scheme。
```

- [ ] **Step 4: Run full harness test suite**

Run: `cd backend && python -m pytest tests/harness/ -v --tb=short`
Expected: ALL PASS (包括所有既有测试 + 新增测试)

- [ ] **Step 5: Commit**

```bash
git add backend/tests/harness/test_image_gen_integration.py docs/harness/image-gen-guide.md
git commit -m "feat(harness): add image_gen integration tests + developer guide"
```

---

## Self-Review Checklist

- [x] **Spec coverage**: §4 (ImageModelProvider) → Tasks 1-4; §5 (image_gen BuiltinTool) → Tasks 5-6; §3 architecture → Tasks 7-8; §10 testing → Task 9; frontend ImageGenRenderer → Task 8
- [x] **Placeholder scan**: No TBD/TODO found. All code blocks complete.
- [x] **Type consistency**: `ImageGenParams`, `ImageGenResult`, `ImageGenError` used consistently across all tasks. `resolve_provider()` signature matches between Task 1 and Task 6. `refine_image_prompt()` signature matches between Task 5 and Task 6. `ToolRendererProps` consistent between Task 8 and Phase 1 renderers.
