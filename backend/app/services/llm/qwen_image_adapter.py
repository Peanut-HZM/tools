"""通义万相图像生成适配器（DashScope）

支持两类模型：
- qwen-image-* 系列：走 multimodal-generation 同步端点
- wanx-* 等旧模型：走 text2image 异步端点 + 轮询
"""

from __future__ import annotations

import asyncio
import logging
from typing import ClassVar, Optional

import httpx

from app.services.llm.exceptions import RecoverableFailure, UnrecoverableFailure
from app.services.llm.image_gen_base import ImageGenAdapter

logger = logging.getLogger(__name__)


class QwenImageAdapter(ImageGenAdapter):
    """通义万相适配器"""

    provider_type: str = "qwen_image"
    SUPPORTED_OPERATIONS: ClassVar[frozenset[str]] = frozenset(
        {"text2img", "img2img", "inpaint", "upload_edit"}
    )

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "", **kw):
        self._api_key = api_key
        base = (base_url or "https://dashscope.aliyuncs.com").rstrip("/")
        # 兼容多种 base_url 写法：
        # - https://dashscope.aliyuncs.com           → 原生入口
        # - https://dashscope.aliyuncs.com/api/v1    → 已含 API 路径
        # - https://xxx/compatible-mode/v1           → OpenAI 兼容入口（要剥离才能拼 /api/v1）
        for suffix in ("/api/v1", "/compatible-mode/v1"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                break
        self._base_url = base
        self._model = model

    # ------------------------------------------------------------------
    # 路由
    # ------------------------------------------------------------------

    async def _do_generate(self, operation, prompt, **kw):
        """根据模型名选择对应端点"""
        if self._model.startswith("qwen-image"):
            return await self._generate_multimodal(prompt, **kw)
        return await self._generate_async_task(prompt, **kw)

    # ------------------------------------------------------------------
    # qwen-image-*：同步 multimodal-generation
    # ------------------------------------------------------------------

    async def _generate_multimodal(self, prompt: str, **kw) -> list[bytes]:
        url = f"{self._base_url}/api/v1/services/aigc/multimodal-generation/generation"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        size = kw.get("size") or "1024*1024"
        # DashScope multimodal 使用 * 分隔宽高，但兼容 x 写法
        if "x" in size and "*" not in size:
            size = size.replace("x", "*")
        body = {
            "model": self._model,
            "input": {
                "messages": [
                    {"role": "user", "content": [{"text": prompt}]}
                ]
            },
            "parameters": {"size": size, "n": kw.get("n", 1)},
        }

        async with httpx.AsyncClient(timeout=180) as client:
            try:
                resp = await client.post(url, json=body, headers=headers)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise RecoverableFailure(str(e))

            self._classify_status(resp)

            data = resp.json()
            choices = data.get("output", {}).get("choices", [])
            urls: list[str] = []
            for choice in choices:
                for item in choice.get("message", {}).get("content", []):
                    if "image" in item:
                        urls.append(item["image"])
            if not urls:
                raise RecoverableFailure(f"no image url in response: {data}")

            images: list[bytes] = []
            for u in urls:
                try:
                    r = await client.get(u)
                    r.raise_for_status()
                    images.append(r.content)
                except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
                    raise RecoverableFailure(f"download failed: {e}")
            return images

    # ------------------------------------------------------------------
    # wanx-* 等：异步 text2image + 轮询
    # ------------------------------------------------------------------

    async def _generate_async_task(self, prompt: str, **kw) -> list[bytes]:
        url = f"{self._base_url}/api/v1/services/aigc/text2image/image-synthesis"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "X-DashScope-Async": "enable",
        }
        size = kw.get("size") or "1024*1024"
        if "x" in size and "*" not in size:
            size = size.replace("x", "*")
        body = {
            "model": self._model,
            "input": {"prompt": prompt},
            "parameters": {"size": size, "n": kw.get("n", 1)},
        }

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(url, json=body, headers=headers)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise RecoverableFailure(str(e))

            self._classify_status(resp)

        task_id = resp.json().get("output", {}).get("task_id")
        if not task_id:
            raise RecoverableFailure("no task_id in response")

        # 轮询任务状态
        async with httpx.AsyncClient(timeout=30) as client:
            for _ in range(60):  # 最多 60 次 * 5s = 300s
                status_url = f"{self._base_url}/api/v1/tasks/{task_id}"
                try:
                    s_resp = await client.get(status_url, headers=headers)
                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    raise RecoverableFailure(f"poll network error: {e}")

                # 轮询端点也需按状态码分类，避免 401/403 被当作可恢复错误
                if s_resp.status_code in (401, 403):
                    raise UnrecoverableFailure(f"poll auth failed: {s_resp.text}")
                if s_resp.status_code == 429:
                    raise RecoverableFailure(f"poll rate limited: {s_resp.text}")
                if s_resp.status_code >= 500:
                    raise RecoverableFailure(f"poll server error: {s_resp.status_code}")
                if s_resp.status_code >= 400:
                    raise UnrecoverableFailure(f"poll bad request: {s_resp.text}")

                s_data = s_resp.json()
                task_status = s_data.get("output", {}).get("task_status")
                if task_status == "SUCCEEDED":
                    results = s_data.get("output", {}).get("results", [])
                    urls = [r["url"] for r in results if "url" in r]
                    if not urls:
                        raise RecoverableFailure("no urls in result")
                    images = []
                    for u in urls:
                        try:
                            r = await client.get(u)
                            r.raise_for_status()
                            images.append(r.content)
                        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
                            raise RecoverableFailure(f"download failed: {e}")
                    return images
                if task_status in ("FAILED", "CANCELED"):
                    raise RecoverableFailure(f"task {task_status}")
                await asyncio.sleep(5)

        raise RecoverableFailure("task timeout")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_status(resp: httpx.Response) -> None:
        if resp.status_code in (401,):
            raise UnrecoverableFailure(f"auth failed: {resp.text}")
        # 403 可能是：①账号被禁（不可恢复）；②该 API key 不支持当前模型/调用方式（可恢复）
        # 简单判断：body 含 "AccessDenied" 或 "support" 等字样视为可恢复
        if resp.status_code == 403:
            if any(kw in resp.text for kw in ("AccessDenied", "support", "not found", "InvalidParameter")):
                raise RecoverableFailure(f"access denied (recoverable): {resp.text}")
            raise UnrecoverableFailure(f"auth failed: {resp.text}")
        if resp.status_code == 404:
            raise RecoverableFailure(f"model not found: {resp.text}")
        if resp.status_code == 429:
            raise RecoverableFailure(f"rate limited: {resp.text}")
        if resp.status_code >= 500:
            raise RecoverableFailure(f"server error: {resp.status_code}")
        if resp.status_code >= 400:
            logger.warning("[qwen_image] bad request body=%s", resp.text[:500])
            raise RecoverableFailure(f"bad request: {resp.text}")

    async def test_connection(self) -> tuple[bool, str]:
        """连接测试（DashScope 无轻量端点，直接返回 ok）"""
        return (True, "ok")
