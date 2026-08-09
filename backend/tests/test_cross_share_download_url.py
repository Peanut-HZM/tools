"""get_oss_download_url 不应事后篡改 sign_url 的 scheme（会破坏签名）。"""
from unittest.mock import patch


def test_get_oss_download_url_returns_sign_url_as_is(monkeypatch):
    from app.routes import cross_share
    from app.services.oss_service import oss_service

    monkeypatch.setattr(cross_share.settings, "MINIO_SECURE", True)

    signed = "https://minio.peanuthzm.com.cn/tools-files/x?sig=abc"
    with patch.object(oss_service, "is_available", return_value=True), \
         patch.object(oss_service, "sign_url", return_value=signed):
        url = cross_share.get_oss_download_url("x", expires=3600)
    assert url == signed


def test_get_oss_download_url_does_not_force_https_on_http(monkeypatch):
    """即使 MINIO_SECURE=true，也不应把 http:// 强改 https://。"""
    from app.routes import cross_share
    from app.services.oss_service import oss_service

    monkeypatch.setattr(cross_share.settings, "MINIO_SECURE", True)

    signed = "http://minio.peanuthzm.com.cn/tools-files/y?sig=def"
    with patch.object(oss_service, "is_available", return_value=True), \
         patch.object(oss_service, "sign_url", return_value=signed):
        url = cross_share.get_oss_download_url("y", expires=3600)
    assert url == signed
