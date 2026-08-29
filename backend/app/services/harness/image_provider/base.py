"""ImageModelProvider 抽象接口 + 数据结构

参考 spec §4.1
"""
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
