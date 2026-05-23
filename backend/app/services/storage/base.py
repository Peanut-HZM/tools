from abc import ABC, abstractmethod
from io import BytesIO
from typing import BinaryIO
from urllib.parse import urlparse


class StorageError(Exception):
    """存储操作异常基类"""
    pass


class NotFoundError(StorageError):
    """文件或 Bucket 不存在"""
    pass


class AccessDeniedError(StorageError):
    """权限不足"""
    pass


class StorageProvider(ABC):
    """文件存储抽象基类"""

    @abstractmethod
    def upload_file(self, object_name: str, data: BinaryIO,
                    size: int, content_type: str,
                    metadata: dict[str, str] | None = None) -> str:
        """上传文件，返回可公开访问的 URL。metadata 为可选的自定义键值对"""

    @abstractmethod
    def delete_file(self, object_name: str) -> bool:
        """删除文件"""

    @abstractmethod
    def list_files(self, prefix: str = "", max_keys: int = 100) -> list[dict]:
        """列出文件，返回 [{"key", "size", "last_modified", "content_type"}]"""

    @abstractmethod
    def get_object(self, object_name: str) -> BinaryIO:
        """获取文件内容流"""

    def download_file(self, object_name_or_url: str) -> bytes:
        """获取文件完整内容（便捷方法）

        参数可以是 object_key（如 `uploads/user1/file.png`）
        也可以是完整 URL（如 `https://minio.peanuthzm.com.cn/tools-files/uploads/user1/file.png`）
        内部会自动提取 object_key 后调用 get_object().read()"""
        object_key = self._extract_key(object_name_or_url)
        return self.get_object(object_key).read()

    def _extract_key(self, url_or_key: str) -> str:
        """从完整 URL 中提取 object_key，如果已经是 key 则原样返回"""
        if url_or_key.startswith(("http://", "https://")):
            parsed = urlparse(url_or_key)
            return parsed.path.lstrip("/")
        return url_or_key

    @abstractmethod
    def head_object(self, object_name: str) -> dict | None:
        """获取文件元数据 {"size", "content_type", "etag", "last_modified"}"""

    @abstractmethod
    def sign_url(self, method: str, object_name: str, expires: int = 3600) -> str:
        """生成签名访问 URL（用于私有 Bucket）"""

    @abstractmethod
    def ensure_bucket_exists(self) -> None:
        """确保 Bucket 存在，不存在则自动创建"""

    @property
    @abstractmethod
    def bucket_name(self) -> str:
        """当前 Bucket 名称"""

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Bucket 的基础 URL，用于拼接文件访问地址"""
