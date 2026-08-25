"""OpenAI DALL-E 3 图像生成适配器

DALL-E 3 不支持参考图（img2img/inpaint/upload_edit 抛 OperationNotSupportedError）。
"""

from __future__ import annotations

from typing import ClassVar, Optional

import httpx

from app.services.llm.exceptions import RecoverableFailure, UnrecoverableFailure
from app.services.llm.image_gen_base import ImageGenAdapter


class OpenAIImageAdapter(ImageGenAdapter):
    """OpenAI 图像适配器"""

    provider_type: str = "openai_image"
    SUPPORTED_OPERATIONS: ClassVar[frozenset[str]] = frozenset({"text2img"})

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "", **kw):
        self._api_key = api_key
        base = (base_url or "https://api.openai.com").rstrip("/")
        # 避免 base_url 已含 /v1 时拼接出重复路径
        if base.endswith("/v1"):
            base = base[: -len("/v1")]
        self._base_url = base
        self._model = model

    async def _do_generate(self, operation, prompt, **kw):
        """调用 OpenAI images/generations API"""
        url = f"{self._base_url}/v1/images/generations"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        body = {
            "model": self._model,
            "prompt": prompt,
            "n": kw.get("n", 1),
            "size": kw.get("size", "1024x1024"),
        }

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                resp = await client.post(url, json=body, headers=headers)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise RecoverableFailure(str(e))

        if resp.status_code == 401:
            raise UnrecoverableFailure(f"auth failed: {resp.text}")
        if resp.status_code == 403:
            raise RecoverableFailure(f"access denied (recoverable): {resp.text}")
        if resp.status_code == 404:
            raise RecoverableFailure(f"model not found: {resp.text}")
        if resp.status_code == 429:
            raise RecoverableFailure(f"rate limited: {resp.text}")
        if resp.status_code >= 500:
            raise RecoverableFailure(f"server error: {resp.status_code}")
        if resp.status_code >= 400:
            raise UnrecoverableFailure(f"bad request: {resp.text}")

        data = resp.json()
        urls = [item["url"] for item in data.get("data", []) if "url" in item]
        if not urls:
            raise RecoverableFailure("no url in response")

        # 下载图片二进制
        async with httpx.AsyncClient(timeout=60) as client:
            images = []
            for u in urls:
                try:
                    r = await client.get(u)
                    r.raise_for_status()
                    images.append(r.content)
                except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
                    raise RecoverableFailure(f"download failed: {e}")
        return images

    async def test_connection(self) -> tuple[bool, str]:
        """连接测试（占位）"""
        return (True, "ok")
