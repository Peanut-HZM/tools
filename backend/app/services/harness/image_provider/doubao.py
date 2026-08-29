"""豆包 Seed (ByteDance Seedream) Provider

通过火山引擎视觉 API 调用豆包 Seed 图像生成。
参考文档：https://www.volcengine.com/docs/6791/1347773

与海螺 AI 类似，使用同步 API（无需异步轮询）。
响应格式：data.images[].url
尺寸参数需要 width/height 分开（从 "1024x1024" 解析）。

provider_type: doubao_seedream
"""
import logging
import time
import uuid

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


class DoubaoSeedProvider(ImageModelProvider):
    """豆包 Seed Provider

    火山引擎 API 调用流程（同步）：
    1. POST 图像生成请求
    2. 解析返回的图片 URL
    3. 下载 → 上传到自有 OSS
    4. 返回 OSS URL
    """

    def __init__(self, base_url: str, api_key: str, oss_client=None):
        super().__init__(base_url, api_key, oss_client)
        self._timeout = _DEFAULT_TIMEOUT

    async def text2img(self, prompt: str, params: ImageGenParams) -> ImageGenResult:
        """文生图"""
        model = params.model_name or "seedream-v1"
        start = time.time()

        width, height = self._parse_size(params.size)
        body = {
            "model": model,
            "prompt": prompt,
            "width": width,
            "height": height,
            "n": params.n,
        }
        if params.style:
            body["style"] = params.style

        try:
            resp = await self._http_post(
                f"{self.base_url}/images/generations",
                json=body,
                headers=self._build_headers(),
            )
        except httpx.TimeoutException:
            raise ImageGenError("豆包 Seed 请求超时", retryable=True)
        except httpx.HTTPError:
            raise ImageGenError("豆包 Seed 网络错误", retryable=True)

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
        """图生图"""
        model = params.model_name or "seedream-v1"
        start = time.time()

        width, height = self._parse_size(params.size)
        body = {
            "model": model,
            "prompt": prompt,
            "reference_image": reference_image,
            "width": width,
            "height": height,
            "n": params.n,
        }

        try:
            resp = await self._http_post(
                f"{self.base_url}/images/img2img",
                json=body,
                headers=self._build_headers(),
            )
        except httpx.TimeoutException:
            raise ImageGenError("豆包 Seed 请求超时", retryable=True)
        except httpx.HTTPError:
            raise ImageGenError("豆包 Seed 网络错误", retryable=True)

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
        """局部重绘"""
        model = params.model_name or "seedream-v1"
        start = time.time()

        width, height = self._parse_size(params.size)
        body = {
            "model": model,
            "prompt": prompt,
            "image_url": image_url,
            "mask_url": mask_url,
            "width": width,
            "height": height,
            "n": params.n,
        }

        try:
            resp = await self._http_post(
                f"{self.base_url}/images/inpaint",
                json=body,
                headers=self._build_headers(),
            )
        except httpx.TimeoutException:
            raise ImageGenError("豆包 Seed 请求超时", retryable=True)
        except httpx.HTTPError:
            raise ImageGenError("豆包 Seed 网络错误", retryable=True)

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
        """上传编辑（指令式）"""
        model = params.model_name or "seedream-v1"
        start = time.time()

        width, height = self._parse_size(params.size)
        body = {
            "model": model,
            "image_url": image_url,
            "prompt": instruction,
            "width": width,
            "height": height,
            "n": params.n,
        }

        try:
            resp = await self._http_post(
                f"{self.base_url}/images/edit",
                json=body,
                headers=self._build_headers(),
            )
        except httpx.TimeoutException:
            raise ImageGenError("豆包 Seed 请求超时", retryable=True)
        except httpx.HTTPError:
            raise ImageGenError("豆包 Seed 网络错误", retryable=True)

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
        """校验 provider 配置是否可用"""
        if not self.api_key:
            raise ImageGenError("豆包 Seed api_key 未配置")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_size(size: str) -> tuple:
        """解析 '1024x1024' → (1024, 1024)

        格式异常时回退到默认值 1024x1024。
        """
        try:
            w, h = size.split("x")
            return int(w), int(h)
        except (ValueError, AttributeError):
            return 1024, 1024

    def _build_headers(self) -> dict:
        """构造 HTTP 请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _http_post(self, url: str, **kwargs) -> httpx.Response:
        """HTTP POST（可被测试 mock）"""
        timeout = kwargs.pop("timeout", self._timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.post(url, **kwargs)

    def _check_response(self, resp: httpx.Response) -> None:
        """检查 HTTP 响应状态码，抛出分类错误

        retryable: 5xx / 429 (rate limit)
        fatal: 4xx (except 429)

        注意：异常消息中只包含 status_code，不截取 response body，
        避免上游在错误响应中 echo 敏感信息。详细 body 仅写入 logger。
        """
        if 200 <= resp.status_code < 300:
            return
        # 将详细响应写入日志，便于排查，但不暴露给调用方
        logger.warning("豆包 Seed 返回错误 HTTP %s: %s", resp.status_code, resp.text[:200])
        if resp.status_code >= 500 or resp.status_code == 429:
            raise ImageGenError(
                f"豆包 Seed HTTP {resp.status_code}",
                retryable=True,
            )
        raise ImageGenError(
            f"豆包 Seed HTTP {resp.status_code}",
            retryable=False,
        )

    async def _download_and_upload(self, url: str) -> str:
        """下载图片并上传到自有 OSS，返回 OSS URL

        如果 oss_client 不可用，直接返回原始 URL（降级模式）。
        """
        if not self.oss_client:
            return url

        # URL scheme 校验，避免 SSRF / 非法协议
        if not url.startswith(("http://", "https://")):
            logger.warning("拒绝非 HTTP URL: %s", url[:100])
            return url

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning("下载图片失败 HTTP %s: %s", resp.status_code, url)
                    return url

                key = f"image-gen/{uuid.uuid4().hex}.png"
                oss_url = self.oss_client.upload_bytes(key, resp.content, "image/png")
                return oss_url
        except Exception as e:
            # 下载/上传失败，降级返回原始 URL；不泄漏异常细节
            logger.warning("下载/上传图片失败: %s", type(e).__name__)
            return url


# 注册到 provider registry
register_provider("doubao_seedream", DoubaoSeedProvider)
