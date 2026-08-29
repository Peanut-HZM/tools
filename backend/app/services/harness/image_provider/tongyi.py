"""通义万相 (Tongyi Wanxiang) Provider

通过阿里云 DashScope API 调用通义万相图像生成。
参考文档：https://help.aliyun.com/zh/dashscope/developer-reference/tongyi-wanxiang

provider_type: qwen_image
"""
import asyncio
import logging
import time
from urllib.parse import urlparse

import httpx

from app.services.harness.image_provider.base import (
    ImageGenError,
    ImageGenParams,
    ImageGenResult,
    ImageModelProvider,
    _resolve_and_check_ip,
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
        """文生图"""
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
        try:
            resp = await self._http_post(
                f"{self.base_url}/services/aigc/text2image/image-synthesis",
                json=body,
                headers=self._build_headers(async_call=True),
            )
        except httpx.TimeoutException as e:
            raise ImageGenError("DashScope 请求超时", retryable=True)
        except httpx.HTTPError:
            raise ImageGenError("DashScope 网络错误", retryable=True)

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
        """图生图"""
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

        try:
            resp = await self._http_post(
                f"{self.base_url}/services/aigc/image2image/image-synthesis",
                json=body,
                headers=self._build_headers(async_call=True),
            )
        except httpx.TimeoutException as e:
            raise ImageGenError("DashScope 请求超时", retryable=True)
        except httpx.HTTPError:
            raise ImageGenError("DashScope 网络错误", retryable=True)
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
        """局部重绘"""
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

        try:
            resp = await self._http_post(
                f"{self.base_url}/services/aigc/image-inpaint/image-synthesis",
                json=body,
                headers=self._build_headers(async_call=True),
            )
        except httpx.TimeoutException as e:
            raise ImageGenError("DashScope 请求超时", retryable=True)
        except httpx.HTTPError:
            raise ImageGenError("DashScope 网络错误", retryable=True)
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
        """上传编辑（指令式）"""
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

        try:
            resp = await self._http_post(
                f"{self.base_url}/services/aigc/image-edit/image-synthesis",
                json=body,
                headers=self._build_headers(async_call=True),
            )
        except httpx.TimeoutException as e:
            raise ImageGenError("DashScope 请求超时", retryable=True)
        except httpx.HTTPError:
            raise ImageGenError("DashScope 网络错误", retryable=True)
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
        """校验 provider 配置是否可用"""
        if not self.api_key:
            raise ImageGenError("通义万相 api_key 未配置")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _build_headers(self, async_call: bool = False) -> dict:
        """构造 HTTP 请求头"""
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
        """检查 HTTP 响应状态码，抛出分类错误

        retryable: 5xx / 429 (rate limit) / timeout
        fatal: 4xx (except 429)

        注意：异常消息中只包含 status_code，不截取 response body，
        避免上游在错误响应中 echo 敏感信息（如 Authorization header、内部路径）。
        详细 body 仅写入 logger。
        """
        if 200 <= resp.status_code < 300:
            return
        # 将详细响应写入日志，便于排查，但不暴露给调用方
        logger.warning("DashScope 返回错误 HTTP %s: %s", resp.status_code, resp.text[:200])
        # retryable: 5xx / 429 (rate limit)
        if resp.status_code >= 500 or resp.status_code == 429:
            raise ImageGenError(
                f"DashScope HTTP {resp.status_code}",
                retryable=True,
            )
        # fatal: 4xx (except 429)
        raise ImageGenError(
            f"DashScope HTTP {resp.status_code}",
            retryable=False,
        )

    async def _poll_task(self, task_id: str, max_attempts: int = 60, interval: float = 2.0) -> list:
        """轮询异步任务状态直到完成

        Returns:
            生成的图片 URL 列表
        """
        url = f"{self.base_url}/tasks/{task_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        for _ in range(max_attempts):
            # 轮询 GET 使用较短超时（10s），避免单次请求卡住导致整体轮询阻塞
            resp = await self._http_get(url, headers=headers, timeout=10.0)
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

        # URL scheme 校验，避免非法协议
        if not url.startswith(("http://", "https://")):
            logger.warning("拒绝非 HTTP URL: %s", url[:100])
            return url

        # SSRF 防护：DNS 解析（含 AAAA 记录）+ 内网 IP 检查，统一使用 base 中的集中实现
        parsed = urlparse(url)
        hostname = parsed.hostname
        if hostname and not _resolve_and_check_ip(hostname):
            logger.warning("拒绝内网或解析失败的 URL: %s", url[:100])
            return url

        try:
            # follow_redirects=False 防止重定向绕过 SSRF
            async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
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
            # 下载/上传失败，降级返回原始 URL；不泄漏异常细节
            logger.warning("下载/上传图片失败: %s", type(e).__name__)
            return url


# 注册到 provider registry
register_provider("qwen_image", TongyiWanxiangProvider)
