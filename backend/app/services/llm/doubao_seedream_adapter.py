"""豆包 Seedream 图像生成适配器（火山 ark API）"""

from __future__ import annotations

from typing import ClassVar, Optional

import httpx

from app.services.llm.exceptions import RecoverableFailure, UnrecoverableFailure
from app.services.llm.image_gen_base import ImageGenAdapter


class DoubaoSeedreamAdapter(ImageGenAdapter):
    """豆包 Seedream 适配器"""

    provider_type: str = "doubao_seedream"
    SUPPORTED_OPERATIONS: ClassVar[frozenset[str]] = frozenset(
        {"text2img", "img2img", "inpaint", "upload_edit"}
    )

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "", **kw):
        self._api_key = api_key
        self._base_url = (base_url or "https://ark.cn-beijing.volces.com").rstrip("/")
        self._model = model

    async def _do_generate(self, operation, prompt, **kw):
        """调用火山 ark API 生成图像"""
        url = f"{self._base_url}/api/v3/images/generations"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        body = {"model": self._model, "prompt": prompt}
        if kw.get("size"):
            body["size"] = kw["size"]
        if kw.get("n"):
            body["n"] = kw["n"]

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                resp = await client.post(url, json=body, headers=headers)
            except httpx.ConnectError as e:
                raise RecoverableFailure(str(e))
            except httpx.TimeoutException as e:
                raise RecoverableFailure(str(e))

        if resp.status_code == 401 or resp.status_code == 403:
            raise UnrecoverableFailure(f"auth failed: {resp.text}")
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
                r = await client.get(u)
                r.raise_for_status()
                images.append(r.content)
        return images

    async def test_connection(self) -> tuple[bool, str]:
        """测试与火山 ark API 的连通性"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.get(
                    f"{self._base_url}/api/v3/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
            return (True, "ok")
        except Exception as e:
            return (False, str(e))
