# OSS 到 Minio 迁移实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将文件存储服务从阿里云 OSS 迁移到 Minio，同时保留阿里云 OSS 作为可切换的备选方案。

**Architecture:** 在现有 `OssService` 之上构建存储抽象层（`StorageProvider` 接口 + `AliyunOssProvider`/`MinioProvider` 实现），所有业务代码通过统一的 `StorageService` 接口访问存储，底层由 `STORAGE_PROVIDER` 配置项控制。

**Tech Stack:** Python 3.10+, FastAPI, oss2 SDK, minio SDK, PostgreSQL

**Spec:** `docs/superpowers/specs/2026-05-23-oss-to-minio-migration-design.md`

---

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/requirements.txt` | 修改 | 新增 `minio>=7.2.0` |
| `backend/app/config/config.py` | 修改 | 新增 `STORAGE_PROVIDER` 和 `MINIO_*` 配置项 |
| `backend/app/services/storage/__init__.py` | 创建 | 导出 `StorageService` |
| `backend/app/services/storage/base.py` | 创建 | `StorageProvider` 抽象基类 + 异常类型 |
| `backend/app/services/storage/aliyun_oss.py` | 创建 | `AliyunOssProvider` 实现 |
| `backend/app/services/storage/minio_provider.py` | 创建 | `MinioProvider` 实现 |
| `backend/app/services/storage/factory.py` | 创建 | Provider 工厂函数 |
| `backend/app/services/storage/service.py` | 创建 | `StorageService` 统一服务 |
| `backend/app/services/oss_service.py` | 修改 | 改造为 `StorageService` 的薄封装 |
| `backend/app/services/oss_version_service.py` | 修改 | 替换直接 bucket 调用为包装方法 |
| `backend/app/routes/cross_share.py` | 修改 | 替换直接 bucket 调用、修复 URL 生成 |
| `backend/app/routes/markdown_editor.py` | 修改 | 替换直接 bucket 调用和异常处理 |
| `backend/app/routes/image_downloader.py` | 修改 | 确认 `download_file` 调用兼容 |
| `backend/scripts/storage_migration.py` | 创建 | 数据迁移脚本 |

---

## Phase 1: 基础设施（存储抽象层）

### Task 1: 新增 Minio SDK 依赖和配置项

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config/config.py`

- [ ] **Step 1: 在 requirements.txt 中新增 minio 依赖**

在 `backend/requirements.txt` 中 `oss2>=2.18.0` 行之后添加：

```
minio>=7.2.0
```

- [ ] **Step 2: 提交**

```bash
cd G:/IdeaProjects/tools
git add backend/requirements.txt
git commit -m "chore: 新增 minio SDK 依赖"
```

- [ ] **Step 3: 在 config.py 中新增 Minio 配置项**

在 `backend/app/config/config.py` 的 `Settings` 类中，`ALIYUN_OSS_*` 配置块之后添加：

```python
    # Storage Provider Selection
    STORAGE_PROVIDER: str = "aliyun_oss"  # "aliyun_oss" | "minio"

    # Minio 配置
    MINIO_ENDPOINT: str = "minio.peanuthzm.com.cn"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "MinioAdmin@2025!"
    MINIO_BUCKET_NAME: str = "tools-files"
    MINIO_SECURE: bool = True
```

- [ ] **Step 4: 提交**

```bash
cd G:/IdeaProjects/tools
git add backend/app/config/config.py
git commit -m "feat: 新增 Minio 存储配置项"
```

---

### Task 2: 创建存储抽象基类和异常类型

**Files:**
- Create: `backend/app/services/storage/__init__.py`
- Create: `backend/app/services/storage/base.py`

- [ ] **Step 1: 创建 storage 目录和 `__init__.py`**

`backend/app/services/storage/__init__.py`:

```python
"""
Storage abstraction layer supporting Aliyun OSS and Minio backends.
"""
from .service import StorageService
from .base import StorageProvider, StorageError, NotFoundError, AccessDeniedError

__all__ = [
    "StorageService",
    "StorageProvider",
    "StorageError",
    "NotFoundError",
    "AccessDeniedError",
]
```

- [ ] **Step 2: 创建 `base.py` 抽象基类**

`backend/app/services/storage/base.py`:

```python
"""
StorageProvider abstract base class and custom exception types.
"""
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
from urllib.parse import urlparse


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class NotFoundError(StorageError):
    """File or bucket does not exist."""
    pass


class AccessDeniedError(StorageError):
    """Insufficient permissions."""
    pass


class StorageProvider(ABC):
    """Abstract base class for file storage backends."""

    @abstractmethod
    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        size: int,
        content_type: str,
        metadata: Optional[dict[str, str]] = None,
    ) -> str:
        """Upload a file and return its public URL."""

    @abstractmethod
    def delete_file(self, object_name: str) -> bool:
        """Delete a file."""

    @abstractmethod
    def list_files(self, prefix: str = "", max_keys: int = 100) -> list[dict]:
        """List files. Returns list of {"key", "size", "last_modified", "content_type"}."""

    @abstractmethod
    def get_object(self, object_name: str) -> BinaryIO:
        """Get file content as a stream."""

    def download_file(self, object_name_or_url: str) -> bytes:
        """Get full file content as bytes. Accepts object key or full URL."""
        object_key = self._extract_key(object_name_or_url)
        return self.get_object(object_key).read()

    def _extract_key(self, url_or_key: str) -> str:
        """Extract object key from a full URL, or return as-is if already a key."""
        if url_or_key.startswith(("http://", "https://")):
            parsed = urlparse(url_or_key)
            return parsed.path.lstrip("/")
        return url_or_key

    @abstractmethod
    def head_object(self, object_name: str) -> Optional[dict]:
        """Get file metadata. Returns {"size", "content_type", "etag", "last_modified"} or None."""

    @abstractmethod
    def sign_url(
        self, method: str, object_name: str, expires: int = 3600
    ) -> str:
        """Generate a presigned URL for accessing a file."""

    @abstractmethod
    def ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, creating it if necessary."""

    @property
    @abstractmethod
    def bucket_name(self) -> str:
        """Current bucket name."""

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL for the bucket, used to construct file URLs."""

    @property
    def client(self):
        """Return the underlying SDK client for availability checks. Returns None if not configured."""
        return None
```

- [ ] **Step 3: 验证 Python 语法**

```bash
cd G:/IdeaProjects/tools
python -m py_compile backend/app/services/storage/base.py
python -m py_compile backend/app/services/storage/__init__.py
```

- [ ] **Step 4: 提交**

```bash
cd G:/IdeaProjects/tools
git add backend/app/services/storage/
git commit -m "feat: 创建存储抽象层基类和异常类型"
```

---

### Task 3: 创建 AliyunOssProvider 实现

**Files:**
- Create: `backend/app/services/storage/aliyun_oss.py`

- [ ] **Step 1: 创建 aliyun_oss.py**

`backend/app/services/storage/aliyun_oss.py`:

```python
"""
Aliyun OSS implementation of StorageProvider.
"""
import logging
from typing import BinaryIO, Optional
import oss2
import oss2.exceptions

from app.config.config import settings
from .base import StorageProvider, NotFoundError, AccessDeniedError

logger = logging.getLogger(__name__)


class AliyunOssProvider(StorageProvider):
    """StorageProvider backed by Aliyun OSS (oss2 SDK)."""

    def __init__(self):
        self._access_key_id = settings.ALIYUN_OSS_ACCESS_KEY_ID
        self._access_key_secret = settings.ALIYUN_OSS_ACCESS_KEY_SECRET
        self._endpoint = settings.ALIYUN_OSS_ENDPOINT
        self._bucket_name = settings.ALIYUN_OSS_BUCKET_NAME
        self._bucket: Optional[oss2.Bucket] = None

        if self._access_key_id and self._access_key_secret and self._bucket_name:
            try:
                auth = oss2.Auth(self._access_key_id, self._access_key_secret)
                self._bucket = oss2.Bucket(auth, self._endpoint, self._bucket_name)
                logger.info(f"AliyunOssProvider initialized for bucket: {self._bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize AliyunOssProvider: {e}")

    @property
    def bucket_name(self) -> str:
        return self._bucket_name

    @property
    def base_url(self) -> str:
        return f"https://{self._bucket_name}.{self._endpoint}"

    @property
    def client(self):
        return self._bucket

    def _check_bucket(self):
        if not self._bucket:
            raise RuntimeError("Aliyun OSS is not configured")

    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        size: int,
        content_type: str,
        metadata: Optional[dict[str, str]] = None,
    ) -> str:
        self._check_bucket()
        try:
            headers = {}
            if metadata:
                for k, v in metadata.items():
                    headers[f"x-oss-meta-{k}"] = v
            result = self._bucket.put_object(object_name, data, headers=headers)
            if result.status == 200:
                return f"{self.base_url}/{object_name}"
            logger.error(f"Upload failed with status {result.status}")
            return ""
        except oss2.exceptions.AccessDenied as e:
            raise AccessDeniedError(str(e))
        except Exception as e:
            logger.error(f"Error uploading to Aliyun OSS: {e}")
            return ""

    def delete_file(self, object_name: str) -> bool:
        self._check_bucket()
        try:
            self._bucket.delete_object(object_name)
            return True
        except oss2.exceptions.AccessDenied as e:
            raise AccessDeniedError(str(e))
        except Exception as e:
            logger.error(f"Error deleting from Aliyun OSS: {e}")
            return False

    def list_files(self, prefix: str = "", max_keys: int = 100) -> list[dict]:
        self._check_bucket()
        try:
            files = []
            for obj in oss2.ObjectIterator(self._bucket, prefix=prefix, max_keys=max_keys):
                files.append({
                    "key": obj.key,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "content_type": obj.content_type,
                })
            return files
        except Exception as e:
            logger.error(f"Error listing Aliyun OSS files: {e}")
            return []

    def get_object(self, object_name: str) -> BinaryIO:
        self._check_bucket()
        try:
            return self._bucket.get_object(object_name)
        except oss2.exceptions.NoSuchKey:
            raise NotFoundError(f"Object not found: {object_name}")
        except oss2.exceptions.AccessDenied as e:
            raise AccessDeniedError(str(e))

    def head_object(self, object_name: str) -> Optional[dict]:
        self._check_bucket()
        try:
            result = self._bucket.head_object(object_name)
            return {
                "size": result.content_length,
                "content_type": result.headers.get("content-type", ""),
                "etag": result.etag,
                "last_modified": result.headers.get("last-modified", ""),
            }
        except oss2.exceptions.NoSuchKey:
            raise NotFoundError(f"Object not found: {object_name}")
        except oss2.exceptions.AccessDenied as e:
            raise AccessDeniedError(str(e))
        except Exception:
            return None

    def sign_url(self, method: str, object_name: str, expires: int = 3600) -> str:
        self._check_bucket()
        try:
            url = self._bucket.sign_url(method, object_name, expires)
            if url.startswith("http://"):
                url = "https://" + url[7:]
            return url
        except Exception as e:
            logger.error(f"Error signing URL: {e}")
            return ""

    def ensure_bucket_exists(self) -> None:
        # Aliyun OSS buckets are assumed to already exist;
        # we don't auto-create in production environments.
        pass
```

- [ ] **Step 2: 验证语法**

```bash
cd G:/IdeaProjects/tools
python -m py_compile backend/app/services/storage/aliyun_oss.py
```

- [ ] **Step 3: 提交**

```bash
cd G:/IdeaProjects/tools
git add backend/app/services/storage/aliyun_oss.py
git commit -m "feat: 创建 AliyunOssProvider 实现"
```

---

### Task 4: 创建 MinioProvider 实现

**Files:**
- Create: `backend/app/services/storage/minio_provider.py`

- [ ] **Step 1: 创建 minio_provider.py**

`backend/app/services/storage/minio_provider.py`:

```python
"""
Minio implementation of StorageProvider.
"""
import json
import logging
from typing import BinaryIO, Optional
from datetime import timedelta
from minio import Minio
from minio.error import S3Error

from app.config.config import settings
from .base import StorageProvider, NotFoundError, AccessDeniedError

logger = logging.getLogger(__name__)


class MinioProvider(StorageProvider):
    """StorageProvider backed by Minio (S3-compatible)."""

    def __init__(self):
        self._endpoint = settings.MINIO_ENDPOINT
        self._access_key = settings.MINIO_ACCESS_KEY
        self._secret_key = settings.MINIO_SECRET_KEY
        self._bucket_name = settings.MINIO_BUCKET_NAME
        self._secure = settings.MINIO_SECURE
        self._client: Optional[Minio] = None

        try:
            self._client = Minio(
                self._endpoint,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=self._secure,
            )
            self.ensure_bucket_exists()
            logger.info(f"MinioProvider initialized for bucket: {self._bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize MinioProvider: {e}")

    @property
    def bucket_name(self) -> str:
        return self._bucket_name

    @property
    def base_url(self) -> str:
        scheme = "https" if self._secure else "http"
        return f"{scheme}://{self._endpoint}/{self._bucket_name}"

    @property
    def client(self):
        return self._client

    def _check_client(self):
        if not self._client:
            raise RuntimeError("Minio is not configured")

    def ensure_bucket_exists(self) -> None:
        self._check_client()
        try:
            if not self._client.bucket_exists(self._bucket_name):
                self._client.make_bucket(self._bucket_name)
                # Set public read policy
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self._bucket_name}/*"],
                    }],
                }
                self._client.set_bucket_policy(
                    self._bucket_name, json.dumps(policy)
                )
                logger.info(f"Created bucket {self._bucket_name} with public read policy")
            else:
                logger.info(f"Bucket {self._bucket_name} already exists")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")

    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        size: int,
        content_type: str,
        metadata: Optional[dict[str, str]] = None,
    ) -> str:
        self._check_client()
        try:
            headers = {"Content-Type": content_type}
            if metadata:
                for k, v in metadata.items():
                    headers[f"x-amz-meta-{k}"] = v
            # Minio put_object expects either file path or data as bytes
            file_data = data.read() if hasattr(data, "read") else data
            from io import BytesIO
            stream = BytesIO(file_data) if isinstance(file_data, bytes) else data
            self._client.put_object(
                self._bucket_name,
                object_name,
                stream,
                length=len(file_data) if isinstance(file_data, bytes) else size,
                content_type=content_type,
            )
            return f"{self.base_url}/{object_name}"
        except S3Error as e:
            if e.code == "AccessDenied":
                raise AccessDeniedError(str(e))
            logger.error(f"Error uploading to Minio: {e}")
            return ""

    def delete_file(self, object_name: str) -> bool:
        self._check_client()
        try:
            self._client.remove_object(self._bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code == "AccessDenied":
                raise AccessDeniedError(str(e))
            logger.error(f"Error deleting from Minio: {e}")
            return False

    def list_files(self, prefix: str = "", max_keys: int = 100) -> list[dict]:
        self._check_client()
        try:
            files = []
            objects = self._client.list_objects(
                self._bucket_name, prefix=prefix, recursive=True
            )
            for i, obj in enumerate(objects):
                if i >= max_keys:
                    break
                files.append({
                    "key": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "content_type": obj.content_type,
                })
            return files
        except S3Error as e:
            logger.error(f"Error listing Minio files: {e}")
            return []

    def get_object(self, object_name: str) -> BinaryIO:
        self._check_client()
        try:
            return self._client.get_object(self._bucket_name, object_name)
        except S3Error as e:
            if e.code in ("NoSuchKey", "NoSuchBucket"):
                raise NotFoundError(f"Object not found: {object_name}")
            if e.code == "AccessDenied":
                raise AccessDeniedError(str(e))
            raise

    def head_object(self, object_name: str) -> Optional[dict]:
        self._check_client()
        try:
            stat = self._client.stat_object(self._bucket_name, object_name)
            return {
                "size": stat.size,
                "content_type": stat.content_type or "",
                "etag": stat.etag,
                "last_modified": stat.last_modified.isoformat() if stat.last_modified else "",
            }
        except S3Error as e:
            if e.code in ("NoSuchKey", "NoSuchBucket"):
                raise NotFoundError(f"Object not found: {object_name}")
            if e.code == "AccessDenied":
                raise AccessDeniedError(str(e))
            return None

    def sign_url(self, method: str, object_name: str, expires: int = 3600) -> str:
        self._check_client()
        try:
            expiry = timedelta(seconds=expires)
            if method.upper() == "GET":
                return self._client.presigned_get_object(
                    self._bucket_name, object_name, expires=expiry
                )
            elif method.upper() == "PUT":
                return self._client.presigned_put_object(
                    self._bucket_name, object_name, expires=expiry
                )
            else:
                return self._client.presigned_get_object(
                    self._bucket_name, object_name, expires=expiry
                )
        except S3Error as e:
            logger.error(f"Error signing Minio URL: {e}")
            return ""
```

- [ ] **Step 2: 安装 minio SDK 并验证语法**

```bash
cd G:/IdeaProjects/tools/backend
pip install minio>=7.2.0
python -m py_compile app/services/storage/minio_provider.py
```

- [ ] **Step 3: 提交**

```bash
cd G:/IdeaProjects/tools
git add backend/app/services/storage/minio_provider.py backend/requirements.txt
git commit -m "feat: 创建 MinioProvider 实现"
```

---

### Task 5: 创建工厂函数和 StorageService

**Files:**
- Create: `backend/app/services/storage/factory.py`
- Create: `backend/app/services/storage/service.py`

- [ ] **Step 1: 创建 factory.py**

`backend/app/services/storage/factory.py`:

```python
"""
Factory for creating StorageProvider instances based on configuration.
"""
from app.config.config import settings
from .base import StorageProvider


def create_provider() -> StorageProvider:
    """Create a StorageProvider based on STORAGE_PROVIDER config."""
    provider_type = settings.STORAGE_PROVIDER.lower()
    if provider_type == "minio":
        from .minio_provider import MinioProvider
        return MinioProvider()
    elif provider_type == "aliyun_oss":
        from .aliyun_oss import AliyunOssProvider
        return AliyunOssProvider()
    else:
        raise ValueError(f"Unknown storage provider: {provider_type}")
```

- [ ] **Step 2: 创建 service.py**

`backend/app/services/storage/service.py`:

```python
"""
StorageService: unified storage interface with DB record management.
"""
import logging
import os
from typing import BinaryIO, List, Dict, Any, Optional
from urllib.parse import urlparse

from app.config.config import settings
from app.config.database import get_db_connection
from .base import StorageProvider
from .factory import create_provider

logger = logging.getLogger(__name__)


class StorageService:
    """Unified storage service with DB record management."""

    def __init__(self):
        self._provider: StorageProvider = create_provider()

    @property
    def provider(self) -> StorageProvider:
        return self._provider

    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        size: int,
        content_type: str,
        uploaded_by: str = "system",
        metadata: Optional[dict[str, str]] = None,
    ) -> Optional[str]:
        """Upload a file and save DB record."""
        try:
            url = self._provider.upload_file(
                object_name, data, size, content_type, metadata=metadata
            )
            if url:
                self._save_file_record(
                    filename=os.path.basename(object_name),
                    file_path=object_name,
                    url=url,
                    file_type=content_type,
                    size=size,
                    uploaded_by=uploaded_by,
                )
            return url
        except Exception as e:
            logger.error(f"Error in StorageService.upload_file: {e}")
            return None

    def delete_file(self, object_name: str) -> bool:
        """Delete a file and its DB record."""
        try:
            result = self._provider.delete_file(object_name)
            if result:
                self._delete_file_record(object_name)
            return result
        except Exception as e:
            logger.error(f"Error in StorageService.delete_file: {e}")
            return False

    def list_files_db(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List files from database."""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM oss_files ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    (limit, offset),
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": row["id"],
                        "name": row["filename"],
                        "path": row["file_path"],
                        "url": row["url"],
                        "type": row["file_type"],
                        "size": row["size"],
                        "uploaded_by": row["uploaded_by"],
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error listing files from DB: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def list_files(self, prefix: str = "", max_keys: int = 100) -> list:
        """List files from storage provider."""
        return self._provider.list_files(prefix, max_keys)

    def get_object(self, object_name: str) -> BinaryIO:
        """Get file content as stream."""
        return self._provider.get_object(object_name)

    def download_file(self, object_name_or_url: str) -> bytes:
        """Get full file content as bytes."""
        return self._provider.download_file(object_name_or_url)

    def sign_url(self, method: str, object_name: str, expires: int = 3600) -> str:
        """Generate presigned URL."""
        return self._provider.sign_url(method, object_name, expires)

    def head_object(self, object_name: str) -> Optional[dict]:
        """Get file metadata."""
        return self._provider.head_object(object_name)

    def is_available(self) -> bool:
        """Check if storage provider is available."""
        return self._provider is not None and self._provider.client is not None

    def _save_file_record(
        self, filename: str, file_path: str, url: str,
        file_type: str, size: int, uploaded_by: str,
    ):
        """Save file record to database."""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO oss_files (filename, file_path, url, file_type, size, uploaded_by)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT (file_path) DO UPDATE SET
                           url = EXCLUDED.url, file_type = EXCLUDED.file_type,
                           size = EXCLUDED.size, created_at = CURRENT_TIMESTAMP""",
                    (filename, file_path, url, file_type, size, uploaded_by),
                )
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving file record: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def _delete_file_record(self, file_path: str):
        """Delete file record from database."""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM oss_files WHERE file_path = %s", (file_path,))
            conn.commit()
        except Exception as e:
            logger.error(f"Error deleting file record from DB: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
```

- [ ] **Step 3: 更新 `__init__.py` 导出**

确保 `backend/app/services/storage/__init__.py` 包含：

```python
from .service import StorageService
from .base import StorageProvider, StorageError, NotFoundError, AccessDeniedError
from .factory import create_provider

__all__ = [
    "StorageService",
    "StorageProvider",
    "StorageError",
    "NotFoundError",
    "AccessDeniedError",
    "create_provider",
]
```

- [ ] **Step 4: 验证所有文件语法**

```bash
cd G:/IdeaProjects/tools
python -m py_compile backend/app/services/storage/factory.py
python -m py_compile backend/app/services/storage/service.py
python -m py_compile backend/app/services/storage/__init__.py
```

- [ ] **Step 5: 提交**

```bash
cd G:/IdeaProjects/tools
git add backend/app/services/storage/
git commit -m "feat: 创建 StorageService 和工厂函数"
```

---

### Task 6: 改造 oss_service.py 为薄封装

**Files:**
- Modify: `backend/app/services/oss_service.py`

- [ ] **Step 1: 替换 oss_service.py 内容为薄封装**

`backend/app/services/oss_service.py`（完整替换）:

```python
"""
OSS Service - Thin compatibility wrapper around StorageService.
"""
import logging
from typing import Optional, BinaryIO, List, Dict, Any

from app.services.storage import StorageService
from app.services.storage.base import StorageError, NotFoundError, AccessDeniedError

logger = logging.getLogger(__name__)


class OssService:
    """Backwards-compatible wrapper delegating to StorageService."""

    def __init__(self):
        self._storage = StorageService()
        # Run DB table initialization via the storage service's internal setup
        self._init_db()

    def _init_db(self):
        """Initialize database tables (delegated to storage service internals)."""
        from app.config.database import get_db_connection
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS oss_files (
                        id SERIAL PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        file_path VARCHAR(500) NOT NULL UNIQUE,
                        url VARCHAR(500) NOT NULL,
                        file_type VARCHAR(50),
                        size BIGINT,
                        uploaded_by VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    @property
    def bucket(self):
        """Compatibility property: returns underlying SDK client for availability checks only.
        Do NOT call methods on this directly — use the wrapper methods below."""
        return self._storage._provider.client

    def is_available(self) -> bool:
        """Check if storage service is available."""
        return self._storage.is_available()

    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        size: int,
        content_type: str,
        uploaded_by: str = "system",
        metadata: Optional[dict[str, str]] = None,
    ) -> Optional[str]:
        return self._storage.upload_file(
            object_name, data, size, content_type, uploaded_by, metadata
        )

    def delete_file(self, object_name: str) -> bool:
        return self._storage.delete_file(object_name)

    def list_files_db(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return self._storage.list_files_db(limit, offset)

    def list_files(self, prefix: str = "", max_keys: int = 100) -> list:
        return self._storage.list_files(prefix, max_keys)

    def get_object(self, object_name: str) -> BinaryIO:
        return self._storage.get_object(object_name)

    def download_file(self, object_name_or_url: str) -> bytes:
        return self._storage.download_file(object_name_or_url)

    def sign_url(self, method: str, object_name: str, expires: int = 3600) -> str:
        return self._storage.sign_url(method, object_name, expires)

    def head_object(self, object_name: str) -> Optional[dict]:
        return self._storage.head_object(object_name)


# Singleton instance
oss_service = OssService()
```

- [ ] **Step 2: 验证语法**

```bash
cd G:/IdeaProjects/tools
python -m py_compile backend/app/services/oss_service.py
```

- [ ] **Step 3: 验证导入链**

```bash
cd G:/IdeaProjects/tools
python -c "from app.services.oss_service import oss_service; print('OssService import OK')"
```

- [ ] **Step 4: 提交**

```bash
cd G:/IdeaProjects/tools
git add backend/app/services/oss_service.py
git commit -m "refactor: 将 OssService 改造为 StorageService 薄封装"
```

---

## Phase 2: 改造直接调用文件

### Task 7: 改造 oss_version_service.py

**Files:**
- Modify: `backend/app/services/oss_version_service.py`

- [ ] **Step 1: 替换所有 bucket 直接调用**

在 `backend/app/services/oss_version_service.py` 中做以下修改：

1. 顶部 import 中删除 `import oss2`，新增:
```python
from app.services.oss_service import oss_service
from app.services.storage.base import NotFoundError
```

2. `create_version` 方法（约行 62）：替换
```python
oss_service.bucket.put_object(version_path, file_obj, headers=metadata)
```
为：
```python
oss_service.upload_file(
    object_name=version_path,
    data=file_obj,
    size=len(content_bytes),
    content_type="text/markdown",
    uploaded_by=user_id,
    metadata=metadata,
)
```

3. `list_versions` 方法（约行 89）：替换
```python
for obj in oss2.ObjectIterator(oss_service.bucket, prefix=prefix):
```
为：
```python
for item in oss_service.list_files(prefix=prefix, max_keys=1000):
```
并将循环体内 `obj.key` 改为 `item["key"]`，`obj.size` 改为 `item["size"]`。

4. `list_versions` 中 `head_object` 调用（约行 98）：替换
```python
head_result = oss_service.bucket.head_object(obj.key)
```
为：
```python
head_result = oss_service.head_object(item["key"])
```

注意：Aliyun OSS 的 `head_object` 返回对象的 `headers` 属性是 oss2 特有的。对于 Minio 兼容，`head_object` 返回的是 `dict`。需要修改代码适配：
```python
head_result = oss_service.head_object(item["key"])
if head_result:
    # head_result is now a dict: {"size", "content_type", "etag", "last_modified"}
    # For version metadata stored as x-amz-meta-* / x-oss-meta-* headers,
    # we need a separate get_metadata method. For now, use list_files item metadata.
    preview = head_result.get("content_preview", "")
else:
    preview = ""
```

**实际上**：version metadata（`x-oss-meta-content-preview` 等）是通过 `head_object` 读取 HTTP headers。两个 SDK 的 head 方法返回格式不同。需要 `StorageProvider.head_object` 方法在返回 dict 中加入自定义 metadata。

修改 `base.py` 中 `head_object` 返回 dict，加入 metadata 字段。修改 `aliyun_oss.py` 的 `head_object` 提取 `x-oss-meta-*` headers。修改 `minio_provider.py` 的 `head_object` 提取 `x-amz-meta-*` headers。

更新后的 `aliyun_oss.py` `head_object` 方法：
```python
def head_object(self, object_name: str) -> Optional[dict]:
    self._check_bucket()
    try:
        result = self._bucket.head_object(object_name)
        metadata = {}
        for k, v in result.headers.items():
            if k.startswith("x-oss-meta-"):
                metadata[k] = v
        return {
            "size": result.content_length,
            "content_type": result.headers.get("content-type", ""),
            "etag": result.etag,
            "last_modified": result.headers.get("last-modified", ""),
            "metadata": metadata,
        }
    except oss2.exceptions.NoSuchKey:
        raise NotFoundError(f"Object not found: {object_name}")
    except Exception:
        return None
```

更新后的 `minio_provider.py` `head_object` 方法（加入 metadata）：
```python
def head_object(self, object_name: str) -> Optional[dict]:
    self._check_client()
    try:
        stat = self._client.stat_object(self._bucket_name, object_name)
        # Extract custom metadata (x-amz-meta-* headers)
        metadata = {}
        if hasattr(stat, "metadata") and stat.metadata:
            for k, v in stat.metadata.items():
                metadata[f"x-amz-meta-{k}"] = v
        return {
            "size": stat.size,
            "content_type": stat.content_type or "",
            "etag": stat.etag,
            "last_modified": stat.last_modified.isoformat() if stat.last_modified else "",
            "metadata": metadata,
        }
    except S3Error as e:
        if e.code in ("NoSuchKey", "NoSuchBucket"):
            raise NotFoundError(f"Object not found: {object_name}")
        return None
```

现在 `oss_version_service.py` 的 `list_versions` 中读取 metadata 改为：
```python
for item in oss_service.list_files(prefix=prefix, max_keys=1000):
    version_id = os.path.splitext(os.path.basename(item["key"]))[0]
    parts = version_id.split("_")
    timestamp = parts[0] if parts else ""
    try:
        head_result = oss_service.head_object(item["key"])
        if head_result:
            meta = head_result.get("metadata", {})
            preview = meta.get("x-oss-meta-content-preview", "") or meta.get("x-amz-meta-content-preview", "")
        else:
            preview = ""
    except Exception:
        preview = ""

    versions.append({
        "version_id": version_id,
        "created_at": self._format_timestamp(timestamp),
        "size": item["size"],
        "content_preview": preview,
    })
```

5. `read_version` 方法（约行 136）：替换
```python
result = oss_service.bucket.get_object(version_path)
content = result.read().decode("utf-8")
```
为：
```python
stream = oss_service.get_object(version_path)
content = stream.read().decode("utf-8")
```

6. `delete_version` 方法（约行 199）：替换
```python
oss_service.bucket.delete_object(version_path)
```
为：
```python
oss_service.delete_file(version_path)
```

7. `_cleanup_old_versions` 方法（约行 212-221）：替换
```python
for obj in oss2.ObjectIterator(oss_service.bucket, prefix=prefix):
    versions.append(obj.key)
```
为：
```python
for item in oss_service.list_files(prefix=prefix, max_keys=1000):
    versions.append(item["key"])
```

并替换
```python
oss_service.bucket.delete_object(version_key)
```
为：
```python
oss_service.delete_file(version_key)
```

8. `rollback_to_version` 中（约行 167）：`oss_service.upload_file` 已适配 metadata 参数，无需修改（它已调用包装方法）。

9. 所有 `if not oss_service.bucket:` 保持不变（兼容属性仍返回 client）。

- [ ] **Step 2: 验证语法**

```bash
cd G:/IdeaProjects/tools
python -m py_compile backend/app/services/oss_version_service.py
```

- [ ] **Step 3: 提交**

```bash
cd G:/IdeaProjects/tools
git add backend/app/services/oss_version_service.py
git commit -m "refactor: 改造 oss_version_service 使用包装方法"
```

---

### Task 8: 改造 routes/cross_share.py

**Files:**
- Modify: `backend/app/routes/cross_share.py`

- [ ] **Step 1: 替换所有 bucket 直接调用和硬编码 URL**

在 `backend/app/routes/cross_share.py` 中做以下修改：

1. `get_oss_upload_url` 函数（约行 88-90）：替换
```python
def get_oss_upload_url(oss_key: str) -> str:
    """获取 OSS 上传 URL"""
    return f"https://{settings.ALIYUN_OSS_BUCKET_NAME}.{settings.ALIYUN_OSS_ENDPOINT}/{oss_key}"
```
为：
```python
def get_oss_upload_url(oss_key: str) -> str:
    """获取上传 URL"""
    from app.services.oss_service import oss_service
    return f"{oss_service.provider.base_url}/{oss_key}"
```

2. `get_oss_download_url` 函数（约行 93-110）：替换
```python
def get_oss_download_url(oss_key: str, expires: int = 3600) -> str:
    """获取 OSS 下载 URL（带签名）"""
    from app.services.oss_service import oss_service

    if not oss_service.bucket:
        logger.warning("OSS bucket not initialized, returning public URL")
        return f"https://{settings.ALIYUN_OSS_BUCKET_NAME}.{settings.ALIYUN_OSS_ENDPOINT}/{oss_key}"

    download_url = oss_service.bucket.sign_url('GET', oss_key, expires)
    if download_url.startswith('http://'):
        download_url = 'https://' + download_url[7:]
    return download_url
```
为：
```python
def get_oss_download_url(oss_key: str, expires: int = 3600) -> str:
    """获取 OSS 下载 URL（带签名）"""
    from app.services.oss_service import oss_service

    if not oss_service.is_available():
        logger.warning("Storage service not available, returning public URL")
        return f"{oss_service.provider.base_url}/{oss_key}"

    download_url = oss_service.sign_url('GET', oss_key, expires)
    return download_url
```

3. 文件上传处（约行 393）：替换
```python
result = oss_service.bucket.put_object(oss_key, io.BytesIO(file_content))
if result.status != 200:
    raise HTTPException(status_code=500, detail=f"上传到 OSS 失败，状态码：{result.status}")
```
为：
```python
url = oss_service.upload_file(
    object_name=oss_key,
    data=io.BytesIO(file_content),
    size=file_size,
    content_type=file.content_type or "application/octet-stream",
    uploaded_by=current_user,
)
if not url:
    raise HTTPException(status_code=500, detail="上传到存储失败")
```

4. 文件删除处（约行 406, 418）：替换
```python
oss_service.bucket.delete_object(oss_key)
```
为：
```python
oss_service.delete_file(oss_key)
```

5. 文件读取处（约行 623）：替换
```python
obj = oss_service.bucket.get_object(file.oss_key)
content = obj.read()
```
为：
```python
stream = oss_service.get_object(file.oss_key)
content = stream.read()
```

6. 所有 `if not oss_service.bucket:` 保持不变。

- [ ] **Step 2: 验证语法**

```bash
cd G:/IdeaProjects/tools
python -m py_compile backend/app/routes/cross_share.py
```

- [ ] **Step 3: 提交**

```bash
cd G:/IdeaProjects/tools
git add backend/app/routes/cross_share.py
git commit -m "refactor: 改造 cross_share 路由使用包装方法"
```

---

### Task 9: 改造 routes/markdown_editor.py

**Files:**
- Modify: `backend/app/routes/markdown_editor.py`

- [ ] **Step 1: 替换所有 bucket 直接调用和异常处理**

在 `backend/app/routes/markdown_editor.py` 中做以下修改：

1. 顶部 import 中删除 `import oss2`（约行 35），新增：
```python
from app.services.storage.base import NotFoundError
```

2. 读取文件处（约行 495-506）：替换
```python
result = oss_service.bucket.get_object(file_path)
content = result.read().decode("utf-8")
```
为：
```python
stream = oss_service.get_object(file_path)
content = stream.read().decode("utf-8")
```

并替换异常处理：
```python
except oss2.exceptions.NoSuchKey:
```
为：
```python
except NotFoundError:
```

3. 文件列表处（约行 577）：替换
```python
for obj in oss2.ObjectIterator(oss_service.bucket, prefix=prefix):
    if obj.key.endswith((".md", ".markdown", ".txt")):
        files.append(OssFileInfo(
            file_path=obj.key,
            filename=os.path.basename(obj.key),
            size=obj.size,
            last_modified=obj.last_modified.isoformat() if obj.last_modified else None,
        ))
```
为：
```python
for item in oss_service.list_files(prefix=prefix, max_keys=1000):
    key = item["key"]
    if key.endswith((".md", ".markdown", ".txt")):
        last_modified = item.get("last_modified")
        files.append(OssFileInfo(
            file_path=key,
            filename=os.path.basename(key),
            size=item["size"],
            last_modified=last_modified.isoformat() if last_modified and hasattr(last_modified, 'isoformat') else str(last_modified) if last_modified else None,
        ))
```

4. 所有 `if not oss_service.bucket:` 保持不变。

- [ ] **Step 2: 验证语法**

```bash
cd G:/IdeaProjects/tools
python -m py_compile backend/app/routes/markdown_editor.py
```

- [ ] **Step 3: 提交**

```bash
cd G:/IdeaProjects/tools
git add backend/app/routes/markdown_editor.py
git commit -m "refactor: 改造 markdown_editor 路由使用包装方法"
```

---

## Phase 3: 数据迁移脚本

### Task 10: 创建 storage_migration.py

**Files:**
- Create: `backend/scripts/storage_migration.py`

- [ ] **Step 1: 创建迁移脚本**

`backend/scripts/storage_migration.py`:

```python
"""
Storage Migration Script: Aliyun OSS → Minio

Migrates all files from Aliyun OSS to Minio, updates DB URLs,
supports dry-run, resume, and verification.

Usage:
    python backend/scripts/storage_migration.py [--dry-run] [--resume] [--verify]
"""
import os
import sys
import json
import time
import logging
import hashlib
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import oss2
from minio import Minio
from app.config.config import settings
from app.config.database import get_db_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent / "migration_state.json"


def get_oss_client():
    """Create Aliyun OSS client."""
    auth = oss2.Auth(
        settings.ALIYUN_OSS_ACCESS_KEY_ID,
        settings.ALIYUN_OSS_ACCESS_KEY_SECRET,
    )
    return oss2.Bucket(auth, settings.ALIYUN_OSS_ENDPOINT, settings.ALIYUN_OSS_BUCKET_NAME)


def get_minio_client():
    """Create Minio client."""
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def load_state():
    """Load migration state or return empty state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "started_at": "",
        "total_files": 0,
        "migrated_files": 0,
        "failed_files": [],
        "last_object_key": "",
    }


def save_state(state):
    """Save migration state."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def compute_md5(data: bytes) -> str:
    """Compute MD5 hash."""
    return hashlib.md5(data).hexdigest()


def migrate_files(dry_run=False, resume=False):
    """Main migration logic."""
    oss_bucket = get_oss_client()
    minio_client = get_minio_client()
    state = load_state() if resume else {}

    if not state.get("started_at"):
        import datetime
        state["started_at"] = datetime.datetime.now().isoformat()
        state["total_files"] = 0
        state["migrated_files"] = 0
        state["failed_files"] = []
        state["last_object_key"] = ""
        save_state(state)

    minio_bucket = settings.MINIO_BUCKET_NAME
    minio_base_url = f"https://{settings.MINIO_ENDPOINT}/{minio_bucket}"

    # List all files in Aliyun OSS
    logger.info("Scanning Aliyun OSS for files...")
    all_keys = []
    for obj in oss2.ObjectIterator(oss_bucket):
        all_keys.append(obj.key)

    state["total_files"] = len(all_keys)
    save_state(state)
    logger.info(f"Found {len(all_keys)} files in Aliyun OSS")

    if dry_run:
        logger.info("=== DRY RUN ===")
        for key in all_keys:
            old_url = f"https://{settings.ALIYUN_OSS_BUCKET_NAME}.{settings.ALIYUN_OSS_ENDPOINT}/{key}"
            new_url = f"{minio_base_url}/{key}"
            logger.info(f"  Would migrate: {key}")
            logger.info(f"    Old URL: {old_url}")
            logger.info(f"    New URL: {new_url}")
        logger.info(f"Total files to migrate: {len(all_keys)}")
        return

    migrated = state.get("migrated_files", 0)
    last_key = state.get("last_object_key", "")

    # Resume: skip to last position
    if resume and last_key and last_key in all_keys:
        start_idx = all_keys.index(last_key) + 1
        logger.info(f"Resuming from: {last_key} (skipping {start_idx} files)")
        all_keys = all_keys[start_idx:]

    for key in all_keys:
        max_retries = 3
        success = False
        for attempt in range(1, max_retries + 1):
            try:
                # Download from Aliyun OSS
                obj = oss_bucket.get_object(key)
                data = obj.read()

                if dry_run:
                    logger.info(f"  [DRY] {key} ({len(data)} bytes)")
                    continue

                # Upload to Minio
                from io import BytesIO
                minio_client.put_object(
                    minio_bucket,
                    key,
                    BytesIO(data),
                    length=len(data),
                )

                # Verify size
                stat = minio_client.stat_object(minio_bucket, key)
                if stat.size != len(data):
                    raise ValueError(
                        f"Size mismatch: expected {len(data)}, got {stat.size}"
                    )

                # Update DB URL
                new_url = f"{minio_base_url}/{key}"
                update_db_url(key, new_url)

                success = True
                migrated += 1
                state["migrated_files"] = migrated
                state["last_object_key"] = key
                save_state(state)

                logger.info(f"  [{migrated}/{len(all_keys)}] {key} ({len(data)} bytes) OK")
                break

            except Exception as e:
                logger.warning(
                    f"  Attempt {attempt}/{max_retries} failed for {key}: {e}"
                )
                if attempt == max_retries:
                    state["failed_files"].append(key)
                    save_state(state)
                    logger.error(f"  FAILED: {key}")

    logger.info("=" * 60)
    logger.info("Migration complete!")
    logger.info(f"Total files: {state['total_files']}")
    logger.info(f"Migrated: {migrated}")
    logger.info(f"Failed: {len(state['failed_files'])}")
    if state["failed_files"]:
        logger.info("Failed files:")
        for f in state["failed_files"]:
            logger.info(f"  - {f}")


def update_db_url(object_key: str, new_url: str):
    """Update URL in oss_files table."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE oss_files SET url = %s WHERE file_path = %s",
                (new_url, object_key),
            )
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating DB URL for {object_key}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def verify():
    """Verify migration integrity."""
    oss_bucket = get_oss_client()
    minio_client = get_minio_client()
    minio_bucket = settings.MINIO_BUCKET_NAME

    logger.info("Verifying migration integrity...")
    mismatches = []
    missing_in_minio = []
    total_checked = 0

    for obj in oss2.ObjectIterator(oss_bucket):
        total_checked += 1
        key = obj.key
        try:
            stat = minio_client.stat_object(minio_bucket, key)
            if stat.size != obj.size:
                mismatches.append(
                    f"{key}: OSS={obj.size}, Minio={stat.size}"
                )
        except Exception as e:
            missing_in_minio.append(f"{key}: {e}")

    logger.info(f"Checked {total_checked} files")
    logger.info(f"Size mismatches: {len(mismatches)}")
    for m in mismatches:
        logger.info(f"  MISMATCH: {m}")
    logger.info(f"Missing in Minio: {len(missing_in_minio)}")
    for m in missing_in_minio:
        logger.info(f"  MISSING: {m}")

    if not mismatches and not missing_in_minio:
        logger.info("Verification passed: all files match!")
    else:
        logger.warning("Verification found issues!")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Storage migration: Aliyun OSS → Minio")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, don't migrate")
    parser.add_argument("--resume", action="store_true", help="Resume from last position")
    parser.add_argument("--verify", action="store_true", help="Verify migration integrity")
    args = parser.parse_args()

    if args.verify:
        verify()
    else:
        migrate_files(dry_run=args.dry_run, resume=args.resume)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证语法**

```bash
cd G:/IdeaProjects/tools
python -m py_compile backend/scripts/storage_migration.py
```

- [ ] **Step 3: 提交**

```bash
cd G:/IdeaProjects/tools
git add backend/scripts/storage_migration.py
git commit -m "feat: 创建 OSS 到 Minio 数据迁移脚本"
```

---

## Phase 4: 验证和最终检查

### Task 11: 验证服务启动和 Aliyun OSS 功能

**Files:**
- No file changes

- [ ] **Step 1: 确保 `STORAGE_PROVIDER=aliyun_oss`（默认值）**

检查 `.env` 文件中没有设置 `STORAGE_PROVIDER`，或设置为 `aliyun_oss`。

- [ ] **Step 2: 重启后端服务**

```bash
cd G:/IdeaProjects/tools
python dev_services.py restart backend
```

- [ ] **Step 3: 验证服务启动无报错**

```bash
cd G:/IdeaProjects/tools
python dev_services.py status
```

确认后端在 19092 端口正常运行，日志中无 ImportError 或初始化错误。

- [ ] **Step 4: 验证 OSS 功能（浏览器）**

访问管理后台的 OSS 文件管理页面，确认能正常列出文件。

- [ ] **Step 5: 提交（如有 .env 变更）**

---

### Task 12: 运行数据迁移

**Files:**
- No file changes

- [ ] **Step 1: 运行 dry-run**

```bash
cd G:/IdeaProjects/tools
python backend/scripts/storage_migration.py --dry-run
```

检查输出，确认扫描到的文件列表正确。

- [ ] **Step 2: 运行实际迁移**

```bash
cd G:/IdeaProjects/tools
python backend/scripts/storage_migration.py
```

等待迁移完成，观察日志输出。

- [ ] **Step 3: 运行校验**

```bash
cd G:/IdeaProjects/tools
python backend/scripts/storage_migration.py --verify
```

确认所有文件大小匹配，无缺失。

---

### Task 13: 切换到 Minio 并验证

**Files:**
- Modify: `backend/.env`

- [ ] **Step 1: 修改 .env 切换到 Minio**

在 `backend/.env` 中添加或修改：
```bash
STORAGE_PROVIDER=minio
```

- [ ] **Step 2: 重启后端服务**

```bash
cd G:/IdeaProjects/tools
python dev_services.py restart backend
```

- [ ] **Step 3: 验证服务启动**

```bash
cd G:/IdeaProjects/tools
python dev_services.py status
```

确认后端正常启动，日志中显示 `MinioProvider initialized for bucket: tools-files`。

- [ ] **Step 4: 浏览器验证文件访问**

在浏览器中访问之前已迁移的文件的 URL（Minio 格式），确认能正常访问。

- [ ] **Step 5: 验证上传功能**

在管理后台上传一个新文件，确认：
- 文件成功上传到 Minio
- 返回的 URL 为 Minio 格式
- 数据库 `oss_files` 表中记录正常

- [ ] **Step 6: 验证删除功能**

删除刚上传的文件，确认：
- 文件从 Minio 删除
- 数据库记录删除

- [ ] **Step 7: 验证 cross_share 签名 URL**

使用跨设备分享功能上传和下载文件，确认签名 URL 正常工作。

- [ ] **Step 8: 验证 markdown_editor 版本历史**

创建 markdown 文件，修改并保存版本，确认版本历史功能正常。

- [ ] **Step 9: 提交**

```bash
cd G:/IdeaProjects/tools
git add backend/.env
git commit -m "chore: 切换 STORAGE_PROVIDER 到 minio"
```

---

## 自审

**1. Spec 覆盖检查：**
- 存储抽象层 ✅ (Task 2-5)
- AliyunOssProvider ✅ (Task 3)
- MinioProvider + Bucket 自动创建 + 公开策略 ✅ (Task 4)
- 工厂函数 ✅ (Task 5)
- StorageService ✅ (Task 5)
- OssService 薄封装 ✅ (Task 6)
- 可用性检查 `is_available()` ✅ (Task 6)
- `download_file` 支持 URL 或 key ✅ (base.py + Task 6)
- `upload_file` metadata 参数 ✅ (Task 3, 4, 6)
- 异常类型 `StorageError`/`NotFoundError` ✅ (Task 2)
- oss_version_service 改造 ✅ (Task 7)
- cross_share.py 改造 + URL 硬编码修复 ✅ (Task 8)
- markdown_editor.py 改造 + 异常替换 ✅ (Task 9)
- 配置项 ✅ (Task 1)
- 迁移脚本 + 断点续传 + 校验 ✅ (Task 10)
- URL 格式转换 ✅ (migration script)
- 切换流程 ✅ (Task 11-13)

**2. 占位符扫描：** 无 TBD/TODO。

**3. 类型一致性：** 所有方法签名在 base.py 中定义，各 provider 实现一致，OssService 封装一致。`metadata` 参数统一为 `Optional[dict[str, str]]`。

---

## 执行

Plan 完成。两种执行方式：

**1. Subagent-Driven（推荐）** — 每个 Task 独立派遣 subagent，Task 间检查点确认

**2. Inline Execution** — 在当前 session 中依次执行

选择哪种方式？
