"""
Aliyun OSS Provider implementation for StorageService
"""
import oss2
import logging
from typing import BinaryIO
from app.config.config import settings
from .base import StorageProvider, StorageError, NotFoundError, AccessDeniedError

logger = logging.getLogger(__name__)


class AliyunOssProvider(StorageProvider):
    """Aliyun OSS storage provider using oss2 SDK"""

    def __init__(self):
        auth = oss2.Auth(
            settings.ALIYUN_OSS_ACCESS_KEY_ID,
            settings.ALIYUN_OSS_ACCESS_KEY_SECRET,
        )
        self._bucket = oss2.Bucket(
            auth, settings.ALIYUN_OSS_ENDPOINT, settings.ALIYUN_OSS_BUCKET_NAME
        )
        self._endpoint = settings.ALIYUN_OSS_ENDPOINT
        self._bucket_name = settings.ALIYUN_OSS_BUCKET_NAME

    @property
    def client(self):
        """Expose underlying oss2.Bucket for compatibility checks"""
        return self._bucket

    @property
    def bucket_name(self) -> str:
        return self._bucket_name

    @property
    def base_url(self) -> str:
        return f"https://{self._bucket_name}.{self._endpoint}"

    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        size: int,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        if metadata:
            for k, v in metadata.items():
                headers[f"x-oss-meta-{k}"] = v
        self._bucket.put_object(object_name, data, headers=headers)
        return f"{self.base_url}/{object_name}"

    def delete_file(self, object_name: str) -> bool:
        self._bucket.delete_object(object_name)
        return True

    def list_files(
        self, prefix: str = "", max_keys: int = 100
    ) -> list[dict]:
        iterator = oss2.ObjectIterator(self._bucket, prefix=prefix, max_keys=max_keys)
        result = []
        for obj in iterator:
            result.append(
                {
                    "key": obj.key,
                    "size": obj.size or 0,
                    "last_modified": obj.last_modified,
                    "content_type": obj.content_type or "",
                }
            )
        return result

    def get_object(self, object_name: str) -> BinaryIO:
        result = self._bucket.get_object(object_name)
        return result

    def head_object(self, object_name: str) -> dict | None:
        try:
            meta = self._bucket.head_object(object_name)
            return {
                "size": int(meta.headers.get("Content-Length", 0)),
                "content_type": meta.headers.get("Content-Type", ""),
                "etag": meta.headers.get("ETag", "").strip('"'),
                "last_modified": meta.headers.get("Last-Modified", ""),
            }
        except oss2.exceptions.NoSuchKey:
            return None

    def sign_url(self, method: str, object_name: str, expires: int = 3600) -> str:
        return self._bucket.sign_url(method, object_name, expires)

    def ensure_bucket_exists(self) -> None:
        if not self._bucket.bucket_name:
            raise StorageError("Aliyun OSS bucket name is not configured")
        # Aliyun OSS: bucket is implicitly created when first used,
        # but we verify connectivity by calling list_objects with max_keys=0
        try:
            self._bucket.get_bucket_info()
        except oss2.exceptions.NoSuchBucket:
            raise StorageError(
                f"Bucket {self._bucket_name} does not exist. "
                "Please create it in Aliyun console first."
            )
