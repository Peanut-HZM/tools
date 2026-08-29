"""McpClient 安全单元测试 — SSRF 防护 + 日志脱敏

覆盖 validate_url() 和 sanitize_url() 的安全性。
"""
import pytest
from unittest.mock import patch

from app.services.harness.mcp_client import (
    McpClient,
    McpConnectionError,
    validate_url,
    sanitize_url,
    _check_ip_blocked,
)


# ---------- sanitize_url ----------

class TestSanitizeUrl:
    """sanitize_url 日志脱敏"""

    def test_removes_userinfo(self):
        assert sanitize_url("http://user:pass@host:3000/path") == "http://host:3000"

    def test_removes_password_only(self):
        assert sanitize_url("http://user@host:3000/path") == "http://host:3000"

    def test_preserves_scheme_and_port(self):
        assert sanitize_url("https://example.com:8080") == "https://example.com:8080"

    def test_no_userinfo_passthrough(self):
        assert sanitize_url("http://example.com/path") == "http://example.com"

    def test_invalid_url_returns_safe_fallback(self):
        # urlsplit 一般不会抛异常，但极端情况应安全返回
        result = sanitize_url("")
        assert isinstance(result, str)

    def test_ipv6_host(self):
        result = sanitize_url("http://[::1]:3000/path")
        assert "[::1]:3000" in result


# ---------- validate_url — scheme ----------

class TestValidateUrlScheme:
    """scheme 必须为 http 或 https"""

    def test_rejects_file_scheme(self):
        with pytest.raises(McpConnectionError, match="scheme"):
            validate_url("file:///etc/passwd")

    def test_rejects_gopher_scheme(self):
        with pytest.raises(McpConnectionError, match="scheme"):
            validate_url("gopher://internal/...")

    def test_rejects_ftp_scheme(self):
        with pytest.raises(McpConnectionError, match="scheme"):
            validate_url("ftp://example.com/file")

    def test_rejects_empty_scheme(self):
        with pytest.raises(McpConnectionError, match="scheme"):
            validate_url("//example.com/path")

    def test_accepts_http(self):
        # mock DNS 以避免真实网络调用
        with patch("app.services.harness.mcp_client.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
            validate_url("http://example.com")  # 不应抛异常

    def test_accepts_https(self):
        with patch("app.services.harness.mcp_client.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
            validate_url("https://example.com")  # 不应抛异常


# ---------- validate_url — userinfo ----------

class TestValidateUrlUserinfo:
    """拒绝 user:pass@host 模式"""

    def test_rejects_user_pass(self):
        with pytest.raises(McpConnectionError, match="userinfo"):
            validate_url("http://user:pass@example.com")

    def test_rejects_user_only(self):
        with pytest.raises(McpConnectionError, match="userinfo"):
            validate_url("http://admin@example.com")


# ---------- validate_url — SSRF (IP ranges) ----------

class TestValidateUrlSSRF:
    """拒绝内网/环回/链路本地地址"""

    def _mock_dns(self, ip: str):
        """辅助函数：mock DNS 返回指定 IP"""
        return patch("app.services.harness.mcp_client.socket.getaddrinfo",
                      return_value=[(2, 1, 6, "", (ip, 0))])

    def test_rejects_loopback_127(self):
        with pytest.raises(McpConnectionError, match="blocked"):
            validate_url("http://127.0.0.1:3000")

    def test_rejects_loopback_127_other(self):
        with pytest.raises(McpConnectionError, match="blocked"):
            validate_url("http://127.0.0.2")

    def test_rejects_ipv6_loopback(self):
        with pytest.raises(McpConnectionError, match="blocked"):
            validate_url("http://[::1]:3000")

    def test_rejects_link_local(self):
        with pytest.raises(McpConnectionError, match="blocked"):
            validate_url("http://169.254.169.254/latest/meta-data/")

    def test_rejects_ipv6_link_local(self):
        with pytest.raises(McpConnectionError, match="blocked"):
            validate_url("http://[fe80::1]")

    def test_rejects_rfc1918_10(self):
        with pytest.raises(McpConnectionError, match="blocked"):
            validate_url("http://10.0.0.1")

    def test_rejects_rfc1918_172(self):
        with pytest.raises(McpConnectionError, match="blocked"):
            validate_url("http://172.16.0.1")

    def test_rejects_rfc1918_192(self):
        with pytest.raises(McpConnectionError, match="blocked"):
            validate_url("http://192.168.1.1")

    def test_rejects_ula_ipv6(self):
        with pytest.raises(McpConnectionError, match="blocked"):
            validate_url("http://[fc00::1]")

    def test_rejects_dns_rebinding_to_loopback(self):
        """DNS rebinding: hostname 解析到 127.0.0.1"""
        with self._mock_dns("127.0.0.1"):
            with pytest.raises(McpConnectionError, match="blocked"):
                validate_url("http://spoofed.example.com")

    def test_rejects_dns_rebinding_to_private(self):
        """DNS rebinding: hostname 解析到内网 IP"""
        with self._mock_dns("10.0.0.1"):
            with pytest.raises(McpConnectionError, match="blocked"):
                validate_url("http://spoofed.example.com")

    def test_accepts_public_ip(self):
        """公网 IP 应被允许"""
        with self._mock_dns("93.184.216.34"):
            validate_url("http://example.com")  # 不应抛异常

    def test_accepts_public_ipv6(self):
        with patch("app.services.harness.mcp_client.socket.getaddrinfo",
                    return_value=[(10, 1, 6, "", ("2606:2800:220:1:248:1893:25c8:1946", 0))]):
            validate_url("http://example.com")  # 不应抛异常


# ---------- validate_url — allow_private_hosts ----------

class TestValidateUrlAllowPrivate:
    """allow_private_hosts=True 应允许内网地址"""

    def test_allows_loopback(self):
        validate_url("http://127.0.0.1:3000", allow_private_hosts=True)

    def test_allows_private_10(self):
        validate_url("http://10.0.0.1", allow_private_hosts=True)

    def test_allows_link_local(self):
        validate_url("http://169.254.169.254", allow_private_hosts=True)

    def test_still_rejects_bad_scheme(self):
        """即使 allow_private_hosts=True，scheme 校验仍然生效"""
        with pytest.raises(McpConnectionError, match="scheme"):
            validate_url("file:///etc/passwd", allow_private_hosts=True)

    def test_still_rejects_userinfo(self):
        """即使 allow_private_hosts=True，userinfo 校验仍然生效"""
        with pytest.raises(McpConnectionError, match="userinfo"):
            validate_url("http://user:pass@127.0.0.1", allow_private_hosts=True)


# ---------- validate_url — hostname ----------

class TestValidateUrlHostname:
    """hostname 必须存在"""

    def test_rejects_empty_hostname(self):
        with pytest.raises(McpConnectionError, match="hostname"):
            validate_url("http:///path")


# ---------- McpClient 集成 ----------

class TestMcpClientIntegration:
    """McpClient.__init__ 调用 validate_url"""

    def test_constructor_rejects_ssrf(self):
        with pytest.raises(McpConnectionError):
            McpClient(server_url="http://127.0.0.1:3000")

    def test_constructor_allows_private(self):
        client = McpClient(
            server_url="http://localhost:3000",
            allow_private_hosts=True,
        )
        assert client.server_url == "http://localhost:3000"

    def test_constructor_rejects_file_scheme(self):
        with pytest.raises(McpConnectionError):
            McpClient(server_url="file:///etc/passwd")


# ---------- _check_ip_blocked ----------

class TestCheckIpBlocked:
    """底层 IP 检查函数"""

    def test_loopback_blocked(self):
        import ipaddress
        assert _check_ip_blocked(ipaddress.ip_address("127.0.0.1"))

    def test_public_not_blocked(self):
        import ipaddress
        assert not _check_ip_blocked(ipaddress.ip_address("8.8.8.8"))

    def test_ipv4_mapped_ipv6_blocked(self):
        """IPv4 映射的 IPv6 地址应提取 IPv4 检查"""
        import ipaddress
        # ::ffff:127.0.0.1
        ip = ipaddress.ip_address("::ffff:127.0.0.1")
        assert _check_ip_blocked(ip)
