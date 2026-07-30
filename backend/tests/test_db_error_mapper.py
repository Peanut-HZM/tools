"""数据库连接错误中文映射单元测试"""
import pytest
from app.utils.db_error_mapper import map_connection_error


class TestMapConnectionError:
    """map_connection_error 各错误码的匹配测试"""

    def test_timeout_timed_out(self):
        code, msg = map_connection_error(
            "(pymysql.err.OperationalError) (2003, \"Can't connect to MySQL server on '10.0.0.1' (timed out)\")"
        )
        assert code == "CONNECTION_TIMEOUT"
        assert "超时" in msg

    def test_timeout_generic(self):
        code, _ = map_connection_error("connect_timeout expired")
        assert code == "CONNECTION_TIMEOUT"

    def test_connection_refused(self):
        code, msg = map_connection_error(
            "Connection refused (0x0000274D/10061)"
        )
        assert code == "CONNECTION_REFUSED"
        assert "拒绝" in msg

    def test_cant_connect(self):
        code, _ = map_connection_error(
            "Can't connect to MySQL server on 'localhost'"
        )
        assert code == "CONNECTION_REFUSED"

    def test_host_not_found(self):
        code, msg = map_connection_error(
            "Name or service not known"
        )
        assert code == "HOST_NOT_FOUND"
        assert "主机" in msg or "地址" in msg

    def test_host_not_found_getaddrinfo(self):
        code, _ = map_connection_error(
            "getaddrinfo failed: Temporary failure in name resolution"
        )
        assert code == "HOST_NOT_FOUND"

    def test_host_not_found_macos(self):
        code, _ = map_connection_error(
            "nodename nor servname provided, or not known"
        )
        assert code == "HOST_NOT_FOUND"

    def test_access_denied_mysql(self):
        code, msg = map_connection_error(
            "Access denied for user 'root'@'localhost' (using password: YES)"
        )
        assert code == "ACCESS_DENIED"
        assert "拒绝" in msg or "密码" in msg

    def test_access_denied_pg(self):
        code, _ = map_connection_error(
            'FATAL:  password authentication failed for user "postgres"'
        )
        assert code == "ACCESS_DENIED"

    def test_database_not_found(self):
        code, msg = map_connection_error(
            "Unknown database 'nonexistent_db'"
        )
        assert code == "DATABASE_NOT_FOUND"
        assert "不存在" in msg

    def test_database_not_found_pg(self):
        code, _ = map_connection_error(
            'database "nonexistent" does not exist'
        )
        assert code == "DATABASE_NOT_FOUND"

    def test_ssl_error(self):
        code, msg = map_connection_error(
            "SSL connection error: certificate verify failed"
        )
        assert code == "SSL_ERROR"
        assert "SSL" in msg or "证书" in msg

    def test_too_many_connections(self):
        code, _ = map_connection_error(
            "Too many connections (max_connections=100)"
        )
        assert code == "TOO_MANY_CONNECTIONS"

    def test_network_error_broken_pipe(self):
        code, msg = map_connection_error(
            "Broken pipe - server closed the connection unexpectedly"
        )
        # 注意："server closed" 应优先匹配 NETWORK_ERROR
        assert code == "NETWORK_ERROR"
        assert "网络" in msg or "连接" in msg

    def test_network_error_connection_lost(self):
        code, _ = map_connection_error(
            "Lost connection to MySQL server during query"
        )
        assert code == "NETWORK_ERROR"

    def test_network_error_connection_reset(self):
        code, _ = map_connection_error(
            "Connection reset by peer"
        )
        assert code == "NETWORK_ERROR"

    def test_network_error_connection_closed_bare(self):
        """裸 'connection closed'（不含 server）应映射为 NETWORK_ERROR，不落入 UNKNOWN_ERROR"""
        code, _ = map_connection_error("connection closed")
        assert code == "NETWORK_ERROR"

    def test_unknown_error_fallback(self):
        code, msg = map_connection_error(
            "Some completely unknown error happened"
        )
        assert code == "UNKNOWN_ERROR"
        # UNKNOWN_ERROR 的 msg 使用原始错误字符串
        assert "Some completely unknown error happened" in msg

    def test_case_insensitive(self):
        """大小写不敏感"""
        code, _ = map_connection_error("CONNECTION REFUSED")
        assert code == "CONNECTION_REFUSED"

    def test_priority_timeout_before_network(self):
        """timeout 优先于 network_error（避免 'timeout' 被 network_error 的泛匹配吞掉）"""
        code, _ = map_connection_error(
            "Operation timed out after 30000 ms"
        )
        assert code == "CONNECTION_TIMEOUT"
