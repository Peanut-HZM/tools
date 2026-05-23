"""
Minio Provider implementation for StorageService
"""
import json
import logging
from typing import BinaryIO
from minio import Minio
from minio.error import S3Error
from app.config.config import settings
from .base import StorageProvider, StorageError, NotFoundError, AccessDeniedError

logger = logging.getLogger(__name__)


class MinioProvider(StorageProvider):
    """Minio storage provider using minio SDK"""

    def __init__(self):
        self._client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self._endpoint = (
            f"https://{settings.MINIO_ENDPOINT}"
            if settings.MINIO_SECURE
            else f"http://{settings.MINIO_ENDPOINT}"
        )
        self._bucket_name = settings.MINIO_BUCKET_NAME
        self.ensure_bucket_exists()

    @property
    def client(self):
        """Expose underlying minio.Minio client for compatibility checks"""
        return self._client

    @property
    def bucket_name(self) -> str:
        return self._bucket_name

    @property
    def base_url(self) -> str:
        return f"{self._endpoint}/{self._bucket_name}"

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

        # Convert metadata dict to Minio user metadata (x-amz-meta-* prefix)
        minio_metadata = None
        if metadata:
            minio_metadata = {f"x-amz-meta-{k}": v for k, v in metadata.items()}

        self._client.put_object(
            self._bucket_name,
            object_name,
            data,
            length=size,
            content_type=content_type or "application/octet-stream",
            headers=headers,
            metadata=minio_metadata,
        )
        return f"{self.base_url}/{object_name}"

    def delete_file(self, object_name: str) -> bool:
        self._client.remove_object(self._bucket_name, object_name)
        return True

    def list_files(
        self, prefix: str = "", max_keys: int = 100
    ) -> list[dict]:
        objects = self._client.list_objects(
            self._bucket_name, prefix=prefix, recursive=True
        )
        result = []
        count = 0
        for obj in objects:
            if count >= max_keys:
                break
            result.append(
                {
                    "key": obj.object_name,
                    "size": obj.size or 0,
                    "last_modified": obj.last_modified,
                    "content_type": obj.content_type or "",
                }
            )
            count += 1
        return result

    def get_object(self, object_name: str) -> BinaryIO:
        try:
            return self._client.get_object(self._bucket_name, object_name)
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise NotFoundError(f"Object not found: {object_name}") from e
            elif e.code == "AccessDenied":
                raise AccessDeniedError(f"Access denied: {object_name}") from e
            raise StorageError(f"Minio error: {e}") from e

    def head_object(self, object_name: str) -> dict | None:
        try:
            stat = self._client.stat_object(self._bucket_name, object_name)
            return {
                "size": stat.size,
                "content_type": stat.content_type or "",
                "etag": stat.etag.strip('"') if stat.etag else "",
                "last_modified": stat.last_modified,
            }
        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            raise StorageError(f"Minio error: {e}") from e

    def sign_url(self, method: str, object_name: str, expires: int = 3600) -> str:
        from datetime import timedelta

        if method.upper() == "GET":
            return self._client.presigned_get_object(
                self._bucket_name, object_name, expires=timedelta(seconds=expires)
            )
        elif method.upper() == "PUT":
            return self._client.presigned_put_object(
                self._bucket_name, object_name, expires=timedelta(seconds=expires)
            )
        else:
            raise ValueError(f"Unsupported method for presigned URL: {method}")

    def ensure_bucket_exists(self) -> None:
        if not self._client.bucket_exists(self._bucket_name):
            self._client.make_bucket(self._bucket_name)
            logger.info(f"Created Minio bucket: {self._bucket_name}")

        # Set public read policy
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{self._bucket_name}/*"],
                }
            ],
        }
        self._client.set_bucket_policy(
            self._bucket_name, json.dumps(policy)
        )
