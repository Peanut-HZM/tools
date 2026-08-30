"""VideoModelProvider 抽象接口 + 数据结构

镜像 image_provider/base.py 的设计：
- VideoGenParams: 视频生成参数
- VideoGenResult: 视频生成结果
- VideoGenError: 可重试/不可重试错误分类
- VideoModelProvider: 抽象基类
"""
import ipaddress
import logging
import socket
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# 复用 image_provider 的 SSRF 防护网络黑名单
from app.services.harness.image_provider.base import (  # noqa: F401
    _BLOCKED_NETWORKS,
    _resolve_and_check_ip,
)


@dataclass
class VideoGenParams:
    """视频生成参数"""
    resolution: str = "768P"           # 480P / 768P / 2K
    duration: int = 5                  # 秒数 (4-15)
    ratio: str = "16:9"               # 宽高比
    model_name: str = ""               # 来自 LLMModel.model_name
    request_params: dict = field(default_factory=dict)


@dataclass
class VideoGenResult:
    """视频生成结果"""
    video_url: str                     # 生成的视频 URL（OSS）
    model_used: str                    # 实际使用的模型标识
    revised_prompt: str = ""           # provider 润色后的 prompt
    task_id: str = ""                  # 上游任务 ID（调试用）
    elapsed_seconds: float = 0.0


class VideoGenError(Exception):
    """视频生成错误

    retryable=True: 超时/限流/5xx → 触发 fallback 链
    retryable=False: 鉴权失败/参数错误/余额不足 → 不重试
    """
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class VideoModelProvider(ABC):
    """视频生成 Provider 抽象接口

    当前仅支持 text2video；后续可扩展 img2video。
    """

    def __init__(self, base_url: str, api_key: str, oss_client=None):
        self.base_url = base_url
        self.api_key = api_key
        self.oss_client = oss_client

    @abstractmethod
    async def text2video(self, prompt: str, params: VideoGenParams) -> VideoGenResult:
        """文生视频"""

    @abstractmethod
    def validate_config(self) -> None:
        """校验 provider 配置是否可用"""
