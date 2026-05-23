"""
Provider factory — creates the active StorageProvider based on config
"""
import logging
from app.config.config import settings
from .base import StorageProvider

logger = logging.getLogger(__name__)


def create_provider() -> StorageProvider:
    """根据 settings.STORAGE_PROVIDER 创建对应的 Provider"""
    provider_type = settings.STORAGE_PROVIDER.lower()
    if provider_type == "minio":
        from .minio_provider import MinioProvider
        logger.info("Creating MinioProvider")
        return MinioProvider()
    elif provider_type == "aliyun_oss":
        from .aliyun_oss import AliyunOssProvider
        logger.info("Creating AliyunOssProvider")
        return AliyunOssProvider()
    else:
        raise ValueError(f"Unknown storage provider: {provider_type}")
