"""ImageGenExecutor 抽象基类 + 工厂

定义统一的图像生成执行接口，工厂根据配置返回对应执行器。
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from app.config.config import settings

logger = logging.getLogger(__name__)


class ImageGenExecutor(ABC):
    """图像生成执行器抽象基类

    所有执行器必须实现 execute 方法，返回统一的结果结构。
    """

    @abstractmethod
    async def execute(self, args: Dict[str, Any], ctx: Any) -> Dict[str, Any]:
        """执行图像生成

        Args:
            args: 图像生成参数（operation, prompt, size, n 等）
            ctx: 工具上下文（ToolContext）

        Returns:
            统一结果结构：
            {
                "success": bool,
                "image_urls": List[str],
                "error": Optional[str],
                "backend": str,  # "dify" | "harness"
                "elapsed_ms": float,
                "request_id": str,
            }
        """
        ...


class ImageGenBackendFactory:
    """图像生成后端工厂

    根据 settings.IMAGE_GEN_BACKEND 返回对应的执行器实例。
    """

    @staticmethod
    def create(ctx: Any = None) -> ImageGenExecutor:
        """创建执行器

        Args:
            ctx: 工具上下文（可选，Dual 模式下可用于传递）

        Returns:
            ImageGenExecutor 实例

        Raises:
            ValueError: 未知的 backend 配置
        """
        # 延迟导入避免循环依赖
        from .executors import (
            DifyImageGenExecutor,
            HarnessImageGenExecutor,
            DualImageGenExecutor,
        )

        backend = settings.IMAGE_GEN_BACKEND
        logger.info(f"创建图像生成执行器: backend={backend}")

        if backend == "dify":
            return DifyImageGenExecutor()
        elif backend == "harness":
            return HarnessImageGenExecutor()
        elif backend == "dual":
            return DualImageGenExecutor(
                primary=HarnessImageGenExecutor(),
                secondary=DifyImageGenExecutor(),
            )
        else:
            raise ValueError(f"Unknown backend: {backend}")
