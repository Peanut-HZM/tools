"""Provider Registry — 从 LLMProvider.provider_type 路由到 ImageModelProvider 实现

参考 spec §4.2
"""
import logging
from typing import Dict, Optional, Type

from app.services.harness.image_provider.base import ImageGenError, ImageModelProvider

logger = logging.getLogger(__name__)

# provider_type → 实现类映射
# 延迟导入避免循环依赖，在 resolve_provider() 中填充
_PROVIDER_MAP: Dict[str, Type[ImageModelProvider]] = {}


def _ensure_providers_loaded():
    """确保所有 provider 实现已注册到 _PROVIDER_MAP

    首次调用时导入各 provider 模块触发注册。
    """
    if _PROVIDER_MAP:
        return
    # 导入各 provider 模块（它们会在模块级别注册到 _PROVIDER_MAP）
    try:
        from app.services.harness.image_provider import tongyi  # noqa: F401
    except ImportError:
        logger.debug("tongyi provider 未加载")
    try:
        from app.services.harness.image_provider import hailuo  # noqa: F401
    except ImportError:
        logger.debug("hailuo provider 未加载")
    try:
        from app.services.harness.image_provider import doubao  # noqa: F401
    except ImportError:
        logger.debug("doubao provider 未加载")


def register_provider(provider_type: str, cls: Type[ImageModelProvider]):
    """注册 provider 实现（由 provider 模块在导入时调用）"""
    _PROVIDER_MAP[provider_type] = cls


# 复用现有的 API key 解密逻辑
def decrypt_api_key(encrypted: str) -> str:
    """解密 API key

    复用项目现有的 AES-256-GCM 解密工具。
    """
    from app.core.security import decrypt_api_key as _decrypt
    return _decrypt(encrypted)


def resolve_provider(llm_provider, oss_client=None) -> ImageModelProvider:
    """从 LLMProvider 实例解析到具体 ImageModelProvider 实现

    Args:
        llm_provider: LLMProvider ORM 实例（需有 provider_type, base_url, api_key_encrypted）
        oss_client: OSS 客户端实例（用于上传图片）

    Returns:
        ImageModelProvider 实例

    Raises:
        ImageGenError: provider_type 未注册
    """
    _ensure_providers_loaded()

    cls = _PROVIDER_MAP.get(llm_provider.provider_type)
    if cls is None:
        raise ImageGenError(
            f"图像 Provider 不支持: {llm_provider.provider_type}，"
            f"已注册: {list(_PROVIDER_MAP.keys())}"
        )

    api_key = decrypt_api_key(llm_provider.api_key_encrypted)

    return cls(
        base_url=llm_provider.base_url,
        api_key=api_key,
        oss_client=oss_client,
    )
