"""图像生成后端抽象接口"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BackendContext:
    """后端调用上下文"""

    user_id: uuid.UUID
    operation: str                      # "text2img" | "img2img" | "inpaint" | "upload_edit"
    query: str                          # 用户输入
    conversation_id: Optional[str]      # 上一轮对话 ID，None 表示新对话
    reference_image: Optional[bytes]
    reference_mime: Optional[str]
    mask_image: Optional[bytes]
    mask_mime: Optional[str]
    size: str
    n: int
    strength: Optional[float]
    edit_type: Optional[str]


@dataclass
class BackendResult:
    """后端调用结果"""

    image_urls: list[str] = field(default_factory=list)  # OSS 签名 URL，可能为空
    answer_text: str = ""                                  # 给用户的回复文本
    conversation_id: str = ""                              # 对话 ID（新建或沿用）
    model_used: str = ""                                   # 实际调用的模型
    backend: str = ""                                      # "dify" | "selfdev"


class IImageGenerationBackend(ABC):
    """图像生成后端接口"""

    @abstractmethod
    async def run(self, ctx: BackendContext) -> BackendResult:
        """执行图像生成 + 对话编排"""
