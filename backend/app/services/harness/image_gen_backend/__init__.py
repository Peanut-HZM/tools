"""图像生成后端工厂 + 执行器

支持 3 种模式：
- dify: 旧版 ImageGenService
- harness: 新版 ImageGenTool
- dual: 双写对比（primary=Harness, secondary=Dify）

通过 settings.IMAGE_GEN_BACKEND 切换。
"""
from .factory import ImageGenBackendFactory, ImageGenExecutor
from .executors import (
    DifyImageGenExecutor,
    HarnessImageGenExecutor,
    DualImageGenExecutor,
)

__all__ = [
    "ImageGenBackendFactory",
    "ImageGenExecutor",
    "DifyImageGenExecutor",
    "HarnessImageGenExecutor",
    "DualImageGenExecutor",
]
