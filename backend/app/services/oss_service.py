"""
OssService - Backward compatibility wrapper around StorageService
All existing callers continue to work unchanged.
"""
import logging
from typing import Optional, BinaryIO, List, Dict, Any

from .storage import StorageService

logger = logging.getLogger(__name__)


class OssService:
    """向后兼容层：保持原有 API 不变，内部委托给 StorageService"""

    def __init__(self):
        self._storage = StorageService()

    @property
    def bucket(self):
        """兼容属性：返回当前 provider 的底层客户端对象，
        仅用于 `if not oss_service.bucket` 可用性检查，不可用于直接调用方法"""
        return self._storage._provider.client

    def is_available(self) -> bool:
        """检查存储服务是否可用（推荐替代 `if not oss_service.bucket` 的新方式）"""
        return self._storage._provider is not None

    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        size: int,
        content_type: str,
        uploaded_by: str = "system",
        metadata: dict[str, str] | None = None,
    ) -> Optional[str]:
        return self._storage.upload_file(
            object_name, data, size, content_type, uploaded_by, metadata
        )

    def delete_file(self, object_name: str) -> bool:
        return self._storage.delete_file(object_name)

    def list_files_db(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        return self._storage.list_files_db(limit, offset)

    def list_files(self, prefix: str = "", max_keys: int = 100) -> list:
        return self._storage.list_files(prefix, max_keys)

    def get_object(self, object_name: str) -> BinaryIO:
        return self._storage.get_object(object_name)

    def download_file(self, object_name_or_url: str) -> bytes:
        return self._storage.download_file(object_name_or_url)

    def sign_url(
        self, method: str, object_name: str, expires: int = 3600
    ) -> str:
        return self._storage.sign_url(method, object_name, expires)

    def head_object(self, object_name: str) -> dict | None:
        return self._storage.head_object(object_name)


# Singleton instance — all existing imports continue to work
oss_service = OssService()
