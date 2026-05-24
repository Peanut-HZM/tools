"""
OssService：兼容旧调用方的存储服务门面。

模块导入时不应因为外部存储配置异常导致整个后端启动失败；依赖 OSS 的
具体接口在调用时再返回不可用错误或空结果。
"""

import logging
from typing import Any, BinaryIO, Optional

from .storage import StorageService

logger = logging.getLogger(__name__)


class OssService:
    """向后兼容层：保持原有 API 不变，内部委托给 StorageService。"""

    def __init__(self):
        self._storage: StorageService | None = None
        self._init_error: Exception | None = None
        self._initialize_storage()

    def _initialize_storage(self) -> None:
        """初始化存储服务；失败时不阻塞整个后端启动。"""
        try:
            self._storage = StorageService()
            self._init_error = None
        except Exception as exc:
            self._storage = None
            self._init_error = exc
            logger.error(
                "存储服务初始化失败，依赖 OSS 的功能将暂时不可用: %s",
                exc,
                exc_info=True,
            )

    def _require_storage(self) -> StorageService:
        """获取可用存储服务；不可用时抛出明确异常。"""
        if self._storage is None:
            raise RuntimeError(f"存储服务不可用: {self._init_error}")
        return self._storage

    @property
    def bucket(self):
        """兼容属性：返回底层客户端，仅用于可用性检查。"""
        if self._storage is None:
            return None
        return self._storage._provider.client

    def is_available(self) -> bool:
        """检查存储服务是否可用。"""
        return self._storage is not None and self._storage._provider is not None

    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        size: int,
        content_type: str,
        uploaded_by: str = "system",
        metadata: dict[str, str] | None = None,
    ) -> Optional[str]:
        if not self.is_available():
            logger.error("上传文件失败，存储服务不可用: %s", object_name)
            return None
        return self._require_storage().upload_file(
            object_name, data, size, content_type, uploaded_by, metadata
        )

    def delete_file(self, object_name: str) -> bool:
        if not self.is_available():
            logger.error("删除文件失败，存储服务不可用: %s", object_name)
            return False
        return self._require_storage().delete_file(object_name)

    def list_files_db(
        self, limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        if not self.is_available():
            logger.warning("列出文件记录失败，存储服务不可用")
            return []
        return self._require_storage().list_files_db(limit, offset)

    def list_files(self, prefix: str = "", max_keys: int = 100) -> list:
        if not self.is_available():
            logger.warning("列出存储文件失败，存储服务不可用")
            return []
        return self._require_storage().list_files(prefix, max_keys)

    def get_object(self, object_name: str) -> BinaryIO:
        return self._require_storage().get_object(object_name)

    def download_file(self, object_name_or_url: str) -> bytes:
        return self._require_storage().download_file(object_name_or_url)

    def sign_url(
        self, method: str, object_name: str, expires: int = 3600
    ) -> str:
        return self._require_storage().sign_url(method, object_name, expires)

    def head_object(self, object_name: str) -> dict | None:
        if not self.is_available():
            logger.warning("获取文件元数据失败，存储服务不可用: %s", object_name)
            return None
        return self._require_storage().head_object(object_name)


# 单例实例：保留现有导入方式。
oss_service = OssService()
