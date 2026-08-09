# MinIO 预签名 URL 改用公网 endpoint 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 cross-share 下载文件时签名 URL 指向内网 `127.0.0.1:9000` 的问题，改为用公网 endpoint 生成预签名 URL。

**Architecture:** 在 `MinioProvider` 中新增一个专用于 presign 的公网 client（`endpoint=MINIO_ENDPOINT`，`secure=MINIO_SECURE`），`sign_url` 的 GET/PUT 分支改用它；内网 `self._client` 保留用于数据操作（上传/读取/删除/列表/bucket 管理）。同时删除 `cross_share.get_oss_download_url` 中事后改 `http->https` 的 hack。

**Tech Stack:** Python 3.14, FastAPI, minio SDK, pytest

## Global Constraints

- 遵循 spec：`docs/superpowers/specs/2026-08-08-minio-presign-public-endpoint-design.md`
- 内网 `self._client` 不得用于 presign；公网 `self._public_client` 仅用于 presign（不实际连接）
- S3 v4 签名的 `host` 不可事后替换（会破坏签名）
- nginx 已配置 `proxy_set_header Host $http_host`（无需改 nginx，spec 已验证）
- 测试用 mock，不依赖真实 MinIO 连接
- 后端测试运行方式：`cd backend && .venv/Scripts/python.exe -m pytest tests/<file> -v`

---

### Task 1: MinioProvider 新增公网 client 并改写 sign_url

**Files:**
- Modify: `backend/app/services/storage/minio_provider.py`（`__init__` 第 18-33 行、`sign_url` 第 121-133 行）
- Test: `backend/tests/test_minio_provider_presign.py`（create）

**Interfaces:**
- Consumes: `settings.MINIO_ENDPOINT`、`settings.MINIO_ACCESS_KEY`、`settings.MINIO_SECRET_KEY`、`settings.MINIO_SECURE`、`settings.MINIO_API_ENDPOINT`、`settings.MINIO_BUCKET_NAME`
- Produces: `MinioProvider._public_client`（`Minio` 实例，公网 endpoint）；`MinioProvider.sign_url(method, object_name, expires) -> str` 返回基于公网 endpoint 的预签名 URL

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_minio_provider_presign.py`：

```python
"""MinioProvider 预签名 URL 使用公网 endpoint 的单元测试。"""
from app.config.config import settings


def _build_provider_with_fake_minio(monkeypatch):
    """用 FakeMinio 构造 MinioProvider，避免真实连接。捕获两个 client 的 endpoint。"""
    captured = {"endpoints": []}

    class FakeMinio:
        def __init__(self, endpoint, **kwargs):
            captured["endpoints"].append(endpoint)
            self.endpoint = endpoint
            self._secure = kwargs.get("secure", True)

        def bucket_exists(self, *args, **kwargs):
            return True

        def set_bucket_policy(self, *args, **kwargs):
            pass

        def presigned_get_object(self, bucket, obj, expires=None):
            scheme = "https" if self._secure else "http"
            return f"{scheme}://{self.endpoint}/{bucket}/{obj}?sig=GET"

        def presigned_put_object(self, bucket, obj, expires=None):
            scheme = "https" if self._secure else "http"
            return f"{scheme}://{self.endpoint}/{bucket}/{obj}?sig=PUT"

    import app.services.storage.minio_provider as mod
    monkeypatch.setattr(mod, "Minio", FakeMinio)
    provider = mod.MinioProvider()
    return provider, captured


def test_public_client_uses_public_endpoint(monkeypatch):
    provider, captured = _build_provider_with_fake_minio(monkeypatch)
    assert provider._public_client.endpoint == settings.MINIO_ENDPOINT
    assert settings.MINIO_ENDPOINT in captured["endpoints"]


def test_sign_url_get_returns_public_endpoint(monkeypatch):
    provider, _ = _build_provider_with_fake_minio(monkeypatch)
    url = provider.sign_url("GET", "cross_share/test/file.txt", expires=3600)
    assert url.startswith("https://minio.peanuthzm.com.cn/")
    assert "127.0.0.1" not in url
    assert "sig=GET" in url


def test_sign_url_put_returns_public_endpoint(monkeypatch):
    provider, _ = _build_provider_with_fake_minio(monkeypatch)
    url = provider.sign_url("PUT", "cross_share/test/file.txt", expires=3600)
    assert url.startswith("https://minio.peanuthzm.com.cn/")
    assert "127.0.0.1" not in url
    assert "sig=PUT" in url


def test_internal_client_still_uses_api_endpoint(monkeypatch):
    provider, _ = _build_provider_with_fake_minio(monkeypatch)
    expected_internal = settings.MINIO_API_ENDPOINT or settings.MINIO_ENDPOINT
    assert provider._client.endpoint == expected_internal
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_minio_provider_presign.py -v`
Expected: FAIL -- `MinioProvider` 无 `_public_client` 属性（AttributeError）

- [ ] **Step 3: 实现--新增 _public_client 并改写 sign_url**

修改 `backend/app/services/storage/minio_provider.py`。

在 `__init__` 的 `self._client = Minio(...)` 块之后、`self._public_endpoint = ...` 之前新增：

```python
        self._public_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
```

将 `sign_url` 中 `self._client` 改为 `self._public_client`：

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

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_minio_provider_presign.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/storage/minio_provider.py backend/tests/test_minio_provider_presign.py
git commit -m "fix(storage): MinIO 预签名 URL 改用公网 endpoint

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: 删除 cross_share 的 http->https hack

**Files:**
- Modify: `backend/app/routes/cross_share.py`（`get_oss_download_url` 第 119-126 行）
- Test: `backend/tests/test_cross_share_download_url.py`（create）

**Interfaces:**
- Consumes: Task 1 的 `MinioProvider.sign_url`（现返回公网 https URL）
- Produces: `get_oss_download_url(oss_key, expires)` 直接返回 `sign_url` 结果，不再事后改 scheme

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_cross_share_download_url.py`：

```python
"""get_oss_download_url 不应事后篡改 sign_url 的 scheme（会破坏签名）。"""
from unittest.mock import patch


def test_get_oss_download_url_returns_sign_url_as_is(monkeypatch):
    from app.routes import cross_share
    from app.services import oss_service

    monkeypatch.setattr(cross_share.settings, "MINIO_SECURE", True)

    signed = "https://minio.peanuthzm.com.cn/tools-files/x?sig=abc"
    with patch.object(oss_service, "is_available", return_value=True), \
         patch.object(oss_service, "sign_url", return_value=signed):
        url = cross_share.get_oss_download_url("x", expires=3600)
    assert url == signed


def test_get_oss_download_url_does_not_force_https_on_http(monkeypatch):
    """即使 MINIO_SECURE=true，也不应把 http:// 强改 https://。"""
    from app.routes import cross_share
    from app.services import oss_service

    monkeypatch.setattr(cross_share.settings, "MINIO_SECURE", True)

    signed = "http://minio.peanuthzm.com.cn/tools-files/y?sig=def"
    with patch.object(oss_service, "is_available", return_value=True), \
         patch.object(oss_service, "sign_url", return_value=signed):
        url = cross_share.get_oss_download_url("y", expires=3600)
    assert url == signed
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_cross_share_download_url.py -v`
Expected: 第二个测试 FAIL -- 现有 hack 会把 `http://` 改成 `https://`

- [ ] **Step 3: 实现--删除 hack**

修改 `backend/app/routes/cross_share.py` 的 `get_oss_download_url`，将：

```python
    # 生成签名 URL
    download_url = oss_service.sign_url('GET', oss_key, expires)

    # 根据 Minio 配置决定是否强制 HTTPS
    if settings.MINIO_SECURE and download_url.startswith('http://'):
        download_url = 'https://' + download_url[7:]

    return download_url
```

改为：

```python
    # 生成签名 URL（公网 endpoint client 直接生成 https，无需事后改 scheme）
    download_url = oss_service.sign_url('GET', oss_key, expires)
    return download_url
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_cross_share_download_url.py -v`
Expected: 2 passed

- [ ] **Step 5: 回归测试**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_cross_share_crud.py tests/test_minio_provider_presign.py tests/test_cross_share_download_url.py -v`
Expected: all pass

- [ ] **Step 6: 提交**

```bash
git add backend/app/routes/cross_share.py backend/tests/test_cross_share_download_url.py
git commit -m "fix(cross-share): 删除签名 URL 的 http->https hack

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: 部署验证

**Files:** 无代码改动（手动验证）

- [ ] **Step 1: 部署后端**

Run: `python deploy.py --backend-only`
（或按项目部署流程重启后端服务）

- [ ] **Step 2: 验证下载 URL 指向公网**

访问 `https://tools.peanuthzm.com.cn/tools/cross-share`，对一个文件点击下载，检查浏览器实际请求的 URL：

- host == `minio.peanuthzm.com.cn`（不是 `127.0.0.1`）
- scheme == `https`
- 文件成功下载（签名验证通过）

- [ ] **Step 3: 验证预览**

对同一文件点击预览，确认 302 重定向到 `https://minio.peanuthzm.com.cn/...` 且能正常预览。

- [ ] **Step 4: 如失败排查 nginx host**

若签名验证失败（403），检查 nginx `minio.peanuthzm.com.cn` 配置是否含 `proxy_set_header Host $http_host;`（spec 已确认存在）。
