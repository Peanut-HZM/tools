"""Video Provider Registry — 从 LLMProvider.provider_type 路由到 VideoModelProvider 实现

设计要点：
- provider_type → 实现类映射（延迟导入触发注册）
- API Key 复用：通过 api_key_hash 查找同 Key 的其他供应商，避免重复录入
"""
import logging
from typing import Dict, Optional, Type

from app.services.harness.video_provider.base import VideoGenError, VideoModelProvider

logger = logging.getLogger(__name__)

_PROVIDER_MAP: Dict[str, Type[VideoModelProvider]] = {}


def _ensure_providers_loaded():
    """确保所有 video provider 实现已注册"""
    if _PROVIDER_MAP:
        return
    try:
        from app.services.harness.video_provider import minimax  # noqa: F401
    except ImportError:
        logger.debug("minimax video provider 未加载")


def register_provider(provider_type: str, cls: Type[VideoModelProvider]):
    """注册 video provider 实现"""
    _PROVIDER_MAP[provider_type] = cls


def decrypt_api_key(encrypted: str) -> str:
    """解密 API key"""
    from app.core.security import decrypt_api_key as _decrypt
    return _decrypt(encrypted)


def resolve_provider(llm_provider, oss_client=None) -> VideoModelProvider:
    """从 LLMProvider 实例解析到具体 VideoModelProvider 实现"""
    _ensure_providers_loaded()

    cls = _PROVIDER_MAP.get(llm_provider.provider_type)
    if cls is None:
        raise VideoGenError(
            f"视频 Provider 不支持: {llm_provider.provider_type}，"
            f"已注册: {list(_PROVIDER_MAP.keys())}"
        )

    api_key = decrypt_api_key(llm_provider.api_key_encrypted)

    return cls(
        base_url=llm_provider.base_url,
        api_key=api_key,
        oss_client=oss_client,
    )


def find_minimax_api_key(db) -> Optional[str]:
    """在数据库中查找已有 MiniMax 供应商的 API Key（解密后）

    匹配条件：provider_type 含 "minimax" 或 base_url 含 "minimaxi.com"
    用途：视频生成工具复用图像/LLM 供应商的 API Key，避免用户重复配置。
    """
    from app.models.llm_provider import LLMProvider

    candidates = db.query(LLMProvider).all()
    for p in candidates:
        pt = (p.provider_type or "").lower()
        bu = (p.base_url or "").lower()
        if "minimax" in pt or "minimaxi.com" in bu:
            if p.api_key_encrypted:
                try:
                    return decrypt_api_key(p.api_key_encrypted)
                except Exception as e:
                    logger.warning("解密 MiniMax API Key 失败 provider_id=%s: %s", p.id, type(e).__name__)
    return None
