"""后端注册表"""

from __future__ import annotations

from app.services.image_gen.base import IImageGenerationBackend


class BackendNotConfiguredError(Exception):
    """请求的后端未注册"""


class BackendRegistry:
    """按名称注册/查找 IImageGenerationBackend"""

    _REGISTRY: dict[str, IImageGenerationBackend] = {}

    @classmethod
    def register(cls, name: str, backend: IImageGenerationBackend) -> None:
        cls._REGISTRY[name] = backend

    @classmethod
    def get(cls, name: str) -> IImageGenerationBackend:
        if name not in cls._REGISTRY:
            raise BackendNotConfiguredError(f"后端未配置: {name}")
        return cls._REGISTRY[name]
