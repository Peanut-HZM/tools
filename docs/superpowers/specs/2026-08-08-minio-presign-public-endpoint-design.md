---
purpose: 修复 cross-share 下载文件时签名 URL 指向内网 127.0.0.1:9000 导致浏览器无法下载的问题，改用公网 endpoint 生成预签名 URL
date: 2026-08-08
---

# MinIO 预签名 URL 改用公网 endpoint 设计

## 背景

部署到服务器后，cross-share 页面（https://tools.peanuthzm.com.cn/tools/cross-share）下载文件时报错，浏览器拿到的下载 URL 指向 `https://127.0.0.1:9000/tools-files/...`（MinIO 内网地址），用户本机无法访问。

## 根因

1. `MinioProvider.__init__`（`backend/app/services/storage/minio_provider.py:18-26`）用 `MINIO_API_ENDPOINT`（服务器配置为内网 `127.0.0.1:9000`）初始化 `self._client`。
2. `sign_url`（`minio_provider.py:121-133`）的 `presigned_get_object` 基于 `self._client` 的 endpoint 生成预签名 URL，因此 URL 的 host 就是内网地址 `127.0.0.1:9000`。
3. `get_oss_download_url`（`backend/app/routes/cross_share.py:122-124`）有一段 `http->https` 的 hack：`if settings.MINIO_SECURE and download_url.startswith('http://'): download_url = 'https://' + download_url[7:]`。它只改 scheme 不改 host，而且改 scheme 会破坏 S3 v4 签名（签名基于完整 URL）。

调用链：`cross_share.py:get_download_url` -> `get_oss_download_url` -> `oss_service.sign_url('GET', ...)` -> `storage.service.sign_url` -> `MinioProvider.sign_url` -> `self._client.presigned_get_object`。

S3 v4 签名约束：`host` 是签名的一部分（`SignedHeaders=host`），不能事后替换 URL 的 host，必须用最终访问的 endpoint 来签名。

## 方案

预签名 URL 用**公网 endpoint client** 生成；内网数据操作（上传/读取/删除/列表/bucket 管理）保留内网 client 不变。

### 代码改动

**`backend/app/services/storage/minio_provider.py`**

`__init__` 新增专用于 presign 的公网 client：

```python
self._public_client = Minio(
    settings.MINIO_ENDPOINT,              # 公网域名 minio.peanuthzm.com.cn
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,         # true -> https
)
```

`sign_url` 的 GET/PUT 分支改用 `self._public_client`：

```python
def sign_url(self, method: str, object_name: str, expires: int = 3600) -> str:
    from datetime import timedelta

    if method.upper() == "GET":
        return self._public_client.presigned_get_object(
            self._bucket_name, object_name, expires=timedelta(seconds=expires)
        )
    elif method.upper() == "PUT":
        return self._public_client.presigned_put_object(
            self._bucket_name, object_name, expires=timedelta(seconds=expires)
        )
    else:
        raise ValueError(f"Unsupported method for presigned URL: {method}")
```

内网 `self._client` 保留，`upload_file` / `get_object` / `delete_file` / `list_files` / `head_object` / `ensure_bucket_exists` 等不动。

**`backend/app/routes/cross_share.py`**

删除 `get_oss_download_url` 中 line 122-124 的 `http->https` hack：

```python
    # 生成签名 URL
    download_url = oss_service.sign_url('GET', oss_key, expires)
    return download_url
```

公网 client 直接生成 https，无需且不应事后改 scheme。

### 部署前提（已验证）

nginx `minio.peanuthzm.com.cn` server block 配置：

- `proxy_pass http://127.0.0.1:9000;`
- `proxy_set_header Host $http_host;`

浏览器访问 `https://minio.peanuthzm.com.cn/...` 时，nginx 转发到内网 MinIO 且保留原始 Host header，MinIO 收到的 host 与签名时一致，签名验证通过。无需改 nginx。

## 影响范围

- 下载 `POST /files/{id}/download`（`get_oss_download_url` -> `sign_url('GET')`）
- 预览 `GET /files/{id}/preview`（302 重定向到签名 URL）
- PUT 预签名分支（当前未被调用，一并改用公网 client 保持一致，避免将来踩同坑）
- `aliyun_oss` provider 不受影响（走 OSS SDK 自己的签名逻辑）
- `get_oss_download_url` 的兜底逻辑（storage 不可用时返回 `base_url` 或后端代理 URL）不变

## 测试

### 单元测试

新增/补充 `MinioProvider.sign_url` 测试，断言：

- 返回 URL 的 host == `minio.peanuthzm.com.cn`（不含 `127.0.0.1`）
- scheme == `https`（当 `MINIO_SECURE=true`）
- GET / PUT 都走公网 client

### 部署验证

部署后访问 cross-share 页面下载文件，确认：

- 下载 URL 指向 `https://minio.peanuthzm.com.cn/tools-files/...?X-Amz-...`
- 文件能成功下载（签名验证通过）

## 回滚

仅修改 2 个文件，回滚即：

```bash
git checkout HEAD -- backend/app/services/storage/minio_provider.py backend/app/routes/cross_share.py
```
