---
author: Peanut
created_at: 2026-05-23
purpose: 设计文件存储服务从阿里云 OSS 迁移到 Minio 的完整方案，包括存储抽象层、数据迁移脚本和切换流程
---

# 文件存储服务迁移到 Minio 设计文档

## 1. 背景与目标

将项目的文件存储服务从阿里云 OSS 迁移到 Minio，同时保留阿里云 OSS 作为可切换的备选方案。

**约束条件：**
- Minio 地址：`https://minio.peanuthzm.com.cn/`
- 鉴权：用户名 `admin`，密码 `MinioAdmin@2025!`
- Bucket 自动创建（代码检测不存在则创建）
- 阿里云 OSS 配置必须保留，支持通过配置项切换
- 旧 OSS 文件需要迁移到 Minio（服务器中转方式）
- 迁移过程需支持断点续传、数据校验

## 2. 当前架构分析

### 2.1 核心服务

| 文件 | 作用 |
|------|------|
| `backend/app/services/oss_service.py` | OssService 类，封装 oss2 SDK 的上传/删除/列表操作，同时维护 PostgreSQL `oss_files` 表 |
| `backend/app/routes/oss.py` | `/api/oss/upload` 和 `/api/oss/files/{filename}` DELETE 路由 |
| `backend/app/config/config.py` | 配置项：`ALIYUN_OSS_ACCESS_KEY_ID`、`ALIYUN_OSS_ACCESS_KEY_SECRET`、`ALIYUN_OSS_ENDPOINT`、`ALIYUN_OSS_BUCKET_NAME` |

### 2.2 直接引用 `oss_service.bucket` 的文件（需改造）

以下文件直接调用 `oss_service.bucket` 的底层 SDK 方法，需改为调用 `oss_service` 的包装方法：

| 文件 | 使用的 bucket 方法 |
|------|-------------------|
| `oss_version_service.py` | `bucket.put_object(key, data, headers=metadata)` (版本元数据), `bucket.head_object`, `bucket.get_object`, `bucket.delete_object`, `oss2.ObjectIterator` |
| `routes/cross_share.py` | `bucket.sign_url`, `bucket.put_object`, `bucket.delete_object`, `bucket.get_object` |
| `routes/markdown_editor.py` | `bucket.get_object`, `oss2.ObjectIterator` |
| `routes/image_downloader.py` | `oss_service.download_file`（该方法不存在，需新增） |

**使用已包装方法的文件（无需改造调用方式，只需 StorageService 迁移后 API 保持一致）：**

| 文件 | 使用的方法 |
|------|-----------|
| `converter_service.py` | `oss_service.upload_file` |
| `image_downloader_service.py` | `oss_service.upload_file` |

### 2.3 现有依赖

- `oss2>=2.18.0`（阿里云 OSS SDK）
- 需要新增 `minio>=7.2.0`（Minio Python SDK）

## 3. 方案设计

### 3.1 架构

```
┌──────────────────────────────────────────┐
│         业务代码 (10+ 个文件)              │
│  oss_version, converter, cross_share...   │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│          StorageService (新)              │
│  统一接口: upload/delete/list/get/head    │
│  内部委托给 active provider                │
│  + DB 记录管理 (从 oss_service 迁移)       │
└───────────┬──────────────┬───────────────┘
            │              │
            ▼              ▼
┌──────────────────┐  ┌───────────────────┐
│ AliyunOssProvider│  │   MinioProvider   │
│ (封装 oss2 SDK)  │  │  (封装 minio SDK) │
└──────────────────┘  └───────────────────┘
```

### 3.2 新建目录结构

```
backend/app/services/storage/
├── __init__.py           # 导出 StorageService
├── base.py               # StorageProvider 抽象基类
├── aliyun_oss.py         # AliyunOssProvider 实现
├── minio.py              # MinioProvider 实现
├── factory.py            # create_provider() 工厂函数 + 自动 Bucket 创建
└── service.py            # StorageService 统一服务类
```

### 3.3 存储异常类型 (`base.py`)

```python
class StorageError(Exception):
    """存储操作异常基类"""
    pass

class NotFoundError(StorageError):
    """文件或 Bucket 不存在"""
    pass

class AccessDeniedError(StorageError):
    """权限不足"""
    pass
```

每个 Provider 的实现中捕获原生 SDK 异常并转换为上述抽象异常：
- Aliyun: `oss2.exceptions.NoSuchKey` → `NotFoundError`
- Minio: `minio.error.S3Error` (code=NoSuchKey/AccessDenied) → 对应抽象异常

调用方改造：`except oss2.exceptions.NoSuchKey` → `except storage.NotFoundError`

### 3.4 存储提供者抽象基类 (`base.py`)

```python
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
            # 提取 URL 中域名之后的部分
            from urllib.parse import urlparse
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
```

### 3.5 Minio Provider 实现要点

- SDK: `minio` (`pip install minio>=7.2.0`)
- Endpoint 处理：去除协议前缀（`https://minio.peanuthzm.com.cn/` → `minio.peanuthzm.com.cn`）
- `secure=True` 对应 HTTPS
- `sign_url` → `presigned_get_object` (GET) / `presigned_put_object` (PUT)
- `list_files` → `list_objects` 迭代
- `get_object` → `get_object`，返回类文件对象
- `head_object` → `stat_object`
- `ensure_bucket_exists` → 先 `bucket_exists()` 判断，不存在则 `make_bucket()`
- **Bucket 访问策略**：创建 Bucket 后必须设置公开读策略，使文件可通过 URL 直接访问：
  ```python
  policy = {
      "Version": "2012-10-17",
      "Statement": [{
          "Effect": "Allow",
          "Principal": {"AWS": "*"},
          "Action": ["s3:GetObject"],
          "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
      }]
  }
  client.set_bucket_policy(bucket_name, json.dumps(policy))
  ```
- 文件 URL 生成：`https://minio.peanuthzm.com.cn/{bucket_name}/{object_name}`

### 3.6 Aliyun OSS Provider 实现要点

- 从现有 `OssService` 提取逻辑
- SDK: `oss2`（已有依赖）
- URL 生成：`https://{bucket_name}.{endpoint}/{object_name}`
- `sign_url` → `bucket.sign_url(method, key, expires)`
- `list_files` → `oss2.ObjectIterator`
- 其余方法直接从现有代码迁移

### 3.7 工厂函数 (`factory.py`)

```python
def create_provider() -> StorageProvider:
    """根据 settings.STORAGE_PROVIDER 创建对应的 Provider"""
    provider_type = settings.STORAGE_PROVIDER.lower()
    if provider_type == "minio":
        return MinioProvider(...)
    elif provider_type == "aliyun_oss":
        return AliyunOssProvider(...)
    else:
        raise ValueError(f"Unknown storage provider: {provider_type}")
```

### 3.8 StorageService 统一服务 (`service.py`)

将现有 `OssService` 的所有能力迁移到 `StorageService`：

| 方法 | 实现 |
|------|------|
| `upload_file(object_name, data, size, content_type, uploaded_by, metadata)` | 委托 provider.upload_file + 保存 DB 记录 + metadata 透传 |
| `delete_file(object_name)` | 委托 provider.delete_file + 删除 DB 记录 |
| `list_files_db(limit, offset)` | 查询 `oss_files` 表（不变） |
| `list_files(prefix, max_keys)` | 委托 provider.list_files |
| `get_object(object_name)` | 委托 provider.get_object |
| `download_file(object_name_or_url)` | 委托 provider.download_file（返回 bytes，支持完整 URL 或 object_key） |
| `sign_url(method, object_name, expires)` | 委托 provider.sign_url |
| `head_object(object_name)` | 委托 provider.head_object |
| `is_available()` | 检查 provider 是否可用（替代 `if not oss_service.bucket`） |

### 3.9 向后兼容层 (`oss_service.py` 改造)

现有 `OssService` 改为 `StorageService` 的薄封装：

```python
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

    def upload_file(self, object_name: str, data: BinaryIO, size: int,
                    content_type: str, uploaded_by: str = "system",
                    metadata: dict[str, str] | None = None) -> Optional[str]:
        return self._storage.upload_file(object_name, data, size, content_type,
                                         uploaded_by, metadata)

    def delete_file(self, object_name: str) -> bool:
        return self._storage.delete_file(object_name)

    def list_files_db(self, limit: int = 100, offset: int = 0) -> list:
        return self._storage.list_files_db(limit, offset)

    def list_files(self, prefix: str = "", max_keys: int = 100) -> list:
        return self._storage.list_files(prefix, max_keys)

    def get_object(self, object_name: str) -> BinaryIO:
        return self._storage.get_object(object_name)

    def download_file(self, object_name_or_url: str) -> bytes:
        return self._storage.download_file(object_name_or_url)

    def sign_url(self, method: str, object_name: str, expires: int = 3600) -> str:
        return self._storage.sign_url(method, object_name, expires)

    def head_object(self, object_name: str) -> dict | None:
        return self._storage.head_object(object_name)
```

### 3.10 可用性检查与直接调用文件改造

#### 3.10.1 可用性检查替换

以下代码中 `if not oss_service.bucket` 的可用性检查（共 15 处）可保持不变（`bucket` 属性返回 provider.client，不可用时返回 None），但建议逐步替换为 `if not oss_service.is_available()`：

| 文件 | 行号 | 检查方式 |
|------|------|----------|
| `oss_version_service.py` | 44, 82, 131, 154, 194 | `if not oss_service.bucket` |
| `routes/markdown_editor.py` | 424, 484, 520, 568, 643, 686, 722, 767 | `if not oss_service.bucket` |
| `routes/cross_share.py` | 97, 384, 618 | `if not oss_service.bucket` |

#### 3.10.2 直接 bucket 方法调用改造

以下文件直接使用 `oss_service.bucket.xxx()` 方法，需改为调用 `oss_service` 的包装方法：

| 文件 | 需修改的方法调用 | 替换为 |
|------|----------------|--------|
| `oss_version_service.py` | `bucket.put_object(key, data, headers=metadata)` | `oss_service.upload_file(key, data, size, content_type, metadata=metadata)` |
| `oss_version_service.py` | `bucket.get_object` | `oss_service.get_object` |
| `oss_version_service.py` | `bucket.head_object` | `oss_service.head_object` |
| `oss_version_service.py` | `bucket.delete_object` | `oss_service.delete_file` |
| `oss_version_service.py` | `oss2.ObjectIterator(bucket, prefix)` | `oss_service.list_files(prefix)` |
| `routes/cross_share.py` | `bucket.sign_url('GET', oss_key, expires)` | `oss_service.sign_url('GET', oss_key, expires)` |
| `routes/cross_share.py` | `bucket.put_object(oss_key, io.BytesIO(file_content))` | `oss_service.upload_file(oss_key, io.BytesIO(file_content), size, content_type)` |
| `routes/cross_share.py` | `bucket.delete_object(oss_key)` | `oss_service.delete_file(oss_key)` |
| `routes/cross_share.py` | `bucket.get_object(file.oss_key)` | `oss_service.get_object(file.oss_key)` |
| `routes/cross_share.py` | `get_oss_upload_url(oss_key)` 硬编码阿里云 URL | `f"{oss_service.provider.base_url}/{oss_key}"` |
| `routes/markdown_editor.py` | `bucket.get_object` | `oss_service.get_object` |
| `routes/markdown_editor.py` | `oss2.ObjectIterator` | `oss_service.list_files` |
| `routes/image_downloader.py` | `oss_service.download_file(row.oss_url)`（完整 URL） | `oss_service.download_file(row.oss_url)`（已支持 URL 或 key） |

**注意：**
- `oss_version_service.py` 中 `bucket.put_object(version_path, file_obj, headers=metadata)` 传入自定义元数据头。新的 `StorageProvider.upload_file` 支持可选的 `metadata` 参数，实现中将 dict 转换为 HTTP headers（Aliyun: `x-oss-meta-*`，Minio: `x-amz-meta-*`）。
- `list_files` 返回的数据形状从 `oss2.ObjectIterator` 的对象属性访问（`obj.key`、`obj.size`）变为字典键访问（`item["key"]`、`item["size"]`）。调用方需相应调整。

### 3.11 异常类型迁移

现有代码中直接使用 `oss2.exceptions.NoSuchKey` 的地方需改为 `storage.NotFoundError`：

| 文件 | 原代码 | 替换为 |
|------|--------|--------|
| `routes/markdown_editor.py` | `except oss2.exceptions.NoSuchKey` | `except storage.NotFoundError` |

## 4. 配置项设计

### 4.1 `config.py` 新增配置

```python
# Storage Provider Selection
STORAGE_PROVIDER: str = "aliyun_oss"  # "aliyun_oss" | "minio"

# Minio 配置
MINIO_ENDPOINT: str = "minio.peanuthzm.com.cn"
MINIO_ACCESS_KEY: str = "admin"
MINIO_SECRET_KEY: str = "MinioAdmin@2025!"
MINIO_BUCKET_NAME: str = "tools-files"
MINIO_SECURE: bool = True  # 使用 HTTPS
```

### 4.2 `.env` 新增环境变量

```bash
# 存储提供者选择
STORAGE_PROVIDER=minio

# Minio 配置
MINIO_ENDPOINT=minio.peanuthzm.com.cn
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=MinioAdmin@2025!
MINIO_BUCKET_NAME=tools-files
MINIO_SECURE=true
```

### 4.3 保留的 OSS 配置（不变）

所有 `ALIYUN_OSS_*` 配置项保持不变，用于 `aliyun_oss` provider。

## 5. 数据迁移方案

### 5.1 迁移脚本 (`backend/scripts/storage_migration.py`)

**功能：**
1. 连接阿里云 OSS 和 Minio 两个服务
2. 从 OSS 遍历所有文件（`ObjectIterator`）
3. 逐个下载 → 上传到 Minio
4. 对比源和目标的文件大小 + ETag/MD5 校验
5. 更新 PostgreSQL `oss_files` 表中的 URL 字段
6. 记录迁移状态到 `migration_state.json` 支持断点续传

**断点续传机制：**
```json
// migration_state.json
{
  "started_at": "2026-05-23T10:00:00",
  "total_files": 1234,
  "migrated_files": 567,
  "failed_files": ["path/to/failed/file1"],
  "last_object_key": "uploads/user123/abc.jpg"
}
```

**运行方式：**
```bash
python backend/scripts/storage_migration.py [--dry-run] [--resume] [--verify]
```

- `--dry-run`：只扫描不迁移，输出预估信息
- `--resume`：从上次中断位置继续
- `--verify`：仅校验不迁移，对比两边文件一致性

### 5.2 URL 格式转换

迁移时需要更新数据库中 `oss_files` 表的 URL 字段：

```python
# 旧格式 (阿里云 OSS):
# https://oss-peanut.oss-cn-beijing.aliyuncs.com/uploads/user1/file.png
# 或 https://oss-peanut.oss-cn-beijing.aliyuncs.com:443/uploads/user1/file.png

# 新格式 (Minio):
# https://minio.peanuthzm.com.cn/tools-files/uploads/user1/file.png

# 转换逻辑：只保留 object_key，拼接新的 base_url
object_key = old_url.split("/", 3)[-1]  # 提取 key
new_url = f"https://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_NAME}/{object_key}"
```

### 5.3 迁移安全特性

- **单文件重试**：失败文件最多重试 3 次，超过后记录到 `failed_files`
- **校验机制**：对比迁移前后的文件大小，MD5 可选
- **数据库更新原子性**：每个文件迁移成功后立即更新 DB URL，避免部分更新
- **日志输出**：每个文件的迁移状态（成功/失败/跳过）输出到控制台和日志文件

## 6. 切换流程

```
步骤 1: 部署新版本代码
        - storage 抽象层已部署
        - STORAGE_PROVIDER=aliyun_oss（保持不变）
        - 验证阿里云 OSS 功能正常

步骤 2: 运行迁移脚本
        python backend/scripts/storage_migration.py --dry-run
        （确认扫描到的文件列表）
        python backend/scripts/storage_migration.py
        （执行实际迁移）

步骤 3: 校验迁移结果
        python backend/scripts/storage_migration.py --verify
        （对比 OSS 和 Minio 文件一致性）

步骤 4: 切换到 Minio
        - 修改 .env: STORAGE_PROVIDER=minio
        - 重启后端服务
        - 验证上传/下载/删除/列表功能正常

步骤 5: 回退方案（如有问题）
        - 修改 .env: STORAGE_PROVIDER=aliyun_oss
        - 重启后端服务
        - 阿里云 OSS 数据未被删除，可随时回退
```

## 7. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| oss2 SDK 在 Minio 上的兼容性问题 | 方案 C 有此风险 | 方案 A 使用独立 SDK（minio），不依赖 oss2 兼容性 |
| 迁移过程中文件丢失 | 数据损坏 | 迁移是复制而非删除，OSS 数据保留；先校验再切换 |
| Minio Bucket 权限问题 | 上传失败 | 代码自动创建 Bucket 时设置合适的访问策略 |
| 大文件迁移超时 | 迁移中断 | 断点续传 + 单文件重试机制 |
| 切换后旧 URL 失效 | 页面图片/文件无法加载 | DB 中 URL 字段在迁移时已更新为 Minio URL |

## 8. 前端影响

前端组件不直接感知存储后端，只通过后端 API 获取文件 URL。迁移后：

- 新上传的文件 URL 变为 Minio 格式
- `oss_files` 表中已有记录的 URL 在迁移时更新
- 前端 `OssUploader.tsx`、`OssManagement.tsx` 等组件无需修改
- 需注意：`OssUploader.tsx` 中有一处硬编码的阿里云上传 URL（`your-oss-bucket.oss-cn-shanghai.aliyuncs.com`），这个 TODO 实现本身就有问题，建议借此机会修复为调用后端 API

## 9. 测试计划

| 测试项 | 验证方式 |
|--------|----------|
| Minio Provider 上传/下载/删除/列表 | 单元测试 |
| Aliyun OSS Provider 功能回归 | 手动测试（切换回 OSS 验证） |
| 迁移脚本 | 使用测试 Bucket 运行 --dry-run 和实际迁移 |
| 切换后文件访问 | 浏览器访问已迁移文件的 URL |
| 回退测试 | 切换回 OSS 验证功能正常 |
