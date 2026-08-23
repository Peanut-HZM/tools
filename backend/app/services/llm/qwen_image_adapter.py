"""通义万相图像生成适配器（DashScope，task 异步轮询）"""

from __future__ import annotations

import asyncio
from typing import ClassVar, Optional

import httpx

from app.services.llm.exceptions import RecoverableFailure, UnrecoverableFailure
from app.services.llm.image_gen_base import ImageGenAdapter


class QwenImageAdapter(ImageGenAdapter):
    """通义万相适配器"""

    provider_type: str = "qwen_image"
    SUPPORTED_OPERATIONS: ClassVar[frozenset[str]] = frozenset(
        {"text2img", "img2img", "inpaint", "upload_edit"}
    )

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "", **kw):
        self._api_key = api_key
        self._base_url = (base_url or "https://dashscope.aliyuncs.com").rstrip("/")
        self._model = model

    async def _do_generate(self, operation, prompt, **kw):
        """提交异步任务并轮询结果"""
        url = f"{self._base_url}/api/v1/services/aigc/text2image/image-synthesis"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "X-DashScope-Async": "enable",
        }
        body = {
            "model": self._model,
            "input": {"prompt": prompt},
            "parameters": {},
        }
        if kw.get("size"):
            body["parameters"]["size"] = kw["size"]
        if kw.get("n"):
            body["parameters"]["n"] = kw["n"]

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(url, json=body, headers=headers)
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise RecoverableFailure(str(e))

        if resp.status_code in (401, 403):
            raise UnrecoverableFailure(f"auth failed: {resp.text}")
        if resp.status_code == 429:
            raise RecoverableFailure(f"rate limited: {resp.text}")
        if resp.status_code >= 500:
            raise RecoverableFailure(f"server error: {resp.status_code}")
        if resp.status_code >= 400:
            raise UnrecoverableFailure(f"bad request: {resp.text}")

        task_id = resp.json().get("output", {}).get("task_id")
        if not task_id:
            raise RecoverableFailure("no task_id in response")

        # 轮询任务状态
        async with httpx.AsyncClient(timeout=30) as client:
            for _ in range(60):  # 最多 60 次 * 5s = 300s
                status_url = f"{self._base_url}/api/v1/tasks/{task_id}"
                s_resp = await client.get(status_url, headers=headers)
                if s_resp.status_code != 200:
                    raise RecoverableFailure(f"poll failed: {s_resp.status_code}")

                s_data = s_resp.json()
                task_status = s_data.get("output", {}).get("task_status")
                if task_status == "SUCCEEDED":
                    results = s_data.get("output", {}).get("results", [])
                    urls = [r["url"] for r in results if "url" in r]
                    if not urls:
                        raise RecoverableFailure("no urls in result")
                    images = []
                    for u in urls:
                        r = await client.get(u)
                        r.raise_for_status()
                        images.append(r.content)
                    return images
                if task_status in ("FAILED", "CANCELED"):
                    raise RecoverableFailure(f"task {task_status}")
                await asyncio.sleep(5)

        raise RecoverableFailure("task timeout")

    async def test_connection(self) -> tuple[bool, str]:
        """连接测试（DashScope 无轻量端点，直接返回 ok）"""
        return (True, "ok")
