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
    monkeypatch.setattr(settings, "MINIO_ENDPOINT", "minio.example.com")
    provider, _ = _build_provider_with_fake_minio(monkeypatch)
    url = provider.sign_url("GET", "cross_share/test/file.txt", expires=3600)
    assert url.startswith("https://minio.example.com/")
    assert "127.0.0.1" not in url
    assert "sig=GET" in url


def test_sign_url_put_returns_public_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "MINIO_ENDPOINT", "minio.example.com")
    provider, _ = _build_provider_with_fake_minio(monkeypatch)
    url = provider.sign_url("PUT", "cross_share/test/file.txt", expires=3600)
    assert url.startswith("https://minio.example.com/")
    assert "127.0.0.1" not in url
    assert "sig=PUT" in url


def test_internal_client_still_uses_api_endpoint(monkeypatch):
    provider, _ = _build_provider_with_fake_minio(monkeypatch)
    expected_internal = settings.MINIO_API_ENDPOINT or settings.MINIO_ENDPOINT
    assert provider._client.endpoint == expected_internal
