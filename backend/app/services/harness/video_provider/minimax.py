"""MiniMax 视频生成 Provider (H3 / H3-Max)

API 文档：https://platform.minimaxi.com/docs/api-reference/video-generation-v2-create

调用流程（异步轮询）：
1. POST {base_url}/v2/video_generation → 获取 task_id
2. GET {base_url}/v2/query/video_generation?task_id=xxx → 轮询直到 succeeded/failed
3. 下载视频 → 上传到自有 OSS → 返回 OSS URL

provider_type: minimax_video

API Key 复用策略：
  VideoGenTool 在执行时通过 find_minimax_api_key() 从数据库查找
  已有的 MiniMax 供应商（如 minimax_image / openai+minimaxi.com），
  复用其 API Key，避免用户重复配置。
"""
import logging
import time
import uuid
from urllib.parse import urlparse

import httpx

from app.services.harness.video_provider.base import (
    VideoGenError,
    VideoGenParams,
    VideoGenResult,
    VideoModelProvider,
    _resolve_and_check_ip,
)
from app.services.harness.video_provider.registry import register_provider

logger = logging.getLogger(__name__)

# 请求超时
_CREATE_TIMEOUT = 30.0
_POLL_TIMEOUT = 15.0
_DOWNLOAD_TIMEOUT = 120.0

# 轮询参数
_POLL_INTERVAL = 5        # 秒
_POLL_MAX_ATTEMPTS = 120  # 最多 10 分钟


class MiniMaxVideoProvider(VideoModelProvider):
    """MiniMax H3 视频生成 Provider

    使用异步任务模式：创建任务 → 轮询状态 → 下载上传。
    base_url 应为 MiniMax API 的基础地址（如 https://api.minimaxi.com）。
    """

    def __init__(self, base_url: str, api_key: str, oss_client=None):
        super().__init__(base_url, api_key, oss_client)

    async def text2video(self, prompt: str, params: VideoGenParams) -> VideoGenResult:
        """文生视频"""
        model = params.model_name or "MiniMax-H3"
        start = time.time()

        # 1. 创建视频生成任务
        task_id = await self._create_task(prompt, params, model)
        logger.info("MiniMax 视频任务已创建 task_id=%s model=%s", task_id, model)

        # 2. 轮询任务状态
        video_url = await self._poll_task(task_id)
        logger.info("MiniMax 视频任务完成 task_id=%s", task_id)

        # 3. 下载视频 → 上传到 OSS
        oss_url = await self._download_and_upload(video_url)

        return VideoGenResult(
            video_url=oss_url,
            model_used=model,
            revised_prompt=prompt,
            task_id=task_id,
            elapsed_seconds=time.time() - start,
        )

    def validate_config(self) -> None:
        if not self.api_key:
            raise VideoGenError("MiniMax Video api_key 未配置")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _build_base_url(self) -> str:
        """构造 API 基础 URL（确保不含 /v1 后缀）"""
        url = self.base_url.rstrip("/")
        # 如果用户填的是 LLM 的 base_url（含 /v1），去掉版本号
        if url.endswith("/v1"):
            url = url[:-3]
        return url

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _create_task(self, prompt: str, params: VideoGenParams, model: str) -> str:
        """POST /v2/video_generation 创建任务，返回 task_id"""
        base_url = self._build_base_url()
        url = f"{base_url}/v2/video_generation"

        body = {
            "model": model,
            "content": [
                {"type": "text", "text": prompt}
            ],
            "resolution": params.resolution,
            "duration": params.duration,
            "ratio": params.ratio,
        }

        try:
            async with httpx.AsyncClient(timeout=_CREATE_TIMEOUT) as client:
                resp = await client.post(url, json=body, headers=self._build_headers())
        except httpx.TimeoutException:
            raise VideoGenError("MiniMax Video 请求超时", retryable=True)
        except httpx.HTTPError:
            raise VideoGenError("MiniMax Video 网络错误", retryable=True)

        self._check_response(resp)
        data = resp.json()
        task_id = data.get("task_id")
        if not task_id:
            logger.warning("MiniMax 创建任务响应异常: %s", str(data)[:200])
            raise VideoGenError("MiniMax 未返回 task_id", retryable=True)
        return str(task_id)

    async def _poll_task(self, task_id: str) -> str:
        """轮询任务状态直到完成，返回视频 URL"""
        base_url = self._build_base_url()
        url = f"{base_url}/v2/query/video_generation"
        headers = self._build_headers()

        for attempt in range(_POLL_MAX_ATTEMPTS):
            try:
                async with httpx.AsyncClient(timeout=_POLL_TIMEOUT) as client:
                    resp = await client.get(url, params={"task_id": task_id}, headers=headers)
            except httpx.TimeoutException:
                logger.warning("轮询超时 attempt=%d task_id=%s", attempt, task_id)
                continue
            except httpx.HTTPError:
                logger.warning("轮询网络错误 attempt=%d task_id=%s", attempt, task_id)
                continue

            if resp.status_code != 200:
                logger.warning("轮询 HTTP %d attempt=%d", resp.status_code, attempt)
                continue

            data = resp.json()
            task_info = data.get("task", data.get("data", data))
            status = task_info.get("status", "")

            if status == "succeeded" or status == "Success":
                # 提取视频 URL
                content = task_info.get("content", {})
                if isinstance(content, list) and content:
                    video_url = content[0].get("url", "")
                elif isinstance(content, dict):
                    video_url = content.get("url", "")
                else:
                    video_url = task_info.get("file_id", "")

                if not video_url:
                    logger.warning("任务成功但未找到视频 URL: %s", str(data)[:300])
                    raise VideoGenError("MiniMax 任务成功但未返回视频 URL", retryable=True)
                return video_url

            if status in ("failed", "Failed", "cancelled", "Canceled"):
                reason = task_info.get("message", "") or task_info.get("status_message", "")
                logger.warning("视频任务失败 task_id=%s status=%s reason=%s", task_id, status, reason)
                raise VideoGenError(f"视频生成失败: {status}", retryable=False)

            # queued / running / Processing → 继续等待
            if attempt % 6 == 0:  # 每 30 秒记录一次状态
                logger.info("视频生成中 task_id=%s status=%s attempt=%d", task_id, status, attempt)

            import asyncio
            await asyncio.sleep(_POLL_INTERVAL)

        raise VideoGenError("视频生成超时（超过 10 分钟）", retryable=True)

    def _check_response(self, resp: httpx.Response) -> None:
        """检查 HTTP 响应状态"""
        if 200 <= resp.status_code < 300:
            return
        logger.warning("MiniMax Video HTTP %s: %s", resp.status_code, resp.text[:200])
        if resp.status_code >= 500 or resp.status_code == 429:
            raise VideoGenError(f"MiniMax Video HTTP {resp.status_code}", retryable=True)
        raise VideoGenError(f"MiniMax Video HTTP {resp.status_code}", retryable=False)

    async def _download_and_upload(self, url: str) -> str:
        """下载视频并上传到 OSS，返回 OSS URL"""
        if not self.oss_client:
            return url

        if not url.startswith(("http://", "https://")):
            logger.warning("拒绝非 HTTP URL: %s", url[:100])
            return url

        # SSRF 防护
        parsed = urlparse(url)
        hostname = parsed.hostname
        if hostname and not _resolve_and_check_ip(hostname):
            logger.warning("拒绝内网 URL: %s", url[:100])
            return url

        try:
            async with httpx.AsyncClient(timeout=_DOWNLOAD_TIMEOUT, follow_redirects=False) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning("下载视频失败 HTTP %s: %s", resp.status_code, url)
                    return url

                key = f"video-gen/{uuid.uuid4().hex}.mp4"
                oss_url = self.oss_client.upload_bytes(key, resp.content, "video/mp4")
                logger.info("视频已上传到 OSS: %s (%d bytes)", key, len(resp.content))
                return oss_url
        except Exception as e:
            logger.warning("下载/上传视频失败: %s", type(e).__name__)
            return url


# 注册到 video provider registry
register_provider("minimax_video", MiniMaxVideoProvider)
