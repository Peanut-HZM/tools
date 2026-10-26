"""
敏感信息脱敏工具（app.utils.sensitive_redactor）单元测试

覆盖范围：
  ✓ 形态类密钥遮蔽（各供应商格式）
  ✓ 键值类遮蔽（JSON / SQL 赋值 / SQL VALUES / PG PASSWORD 语法）
  ✓ 连接串凭据遮蔽
  ✓ 授权头遮蔽
  ✓ PEM 私钥整块遮蔽
  ✓ 误伤防护（token_count / access_key_id / password_hash 等不得被遮蔽）
  ✓ redact_structure 递归脱敏
"""

import pytest

from app.utils.sensitive_redactor import (
    REDACTED,
    redact_sensitive,
    redact_structure,
)


class TestTokenPatterns:
    """形态类密钥"""

    @pytest.mark.parametrize(
        "token",
        [
            "sk-ab395535bxyz1234567890abcdefghij",
            "sk-abc123def4567",
            "sk-ant-api03-abcdefghijklmnopqrstuvwxyz",
            "AKIAIOSFODNN7EXAMPLE",
            "LTAI5tFakeKeyValueForAliyun123",
            "ghp_abcdefghijklmnopqrstuvwxyz0123",
            "glpat-abcdefghijklmnopqrst",
            "xoxb-1234567890-abcdefghijkl",
            "AIzaSyA1234567890abcdefghijklmnopqrstuv",
            "ocl_abcdefghijklmnopqrstuvwx",
            "gsk_abcdefghijklmnopqrstuvwxyz01",
        ],
    )
    def test_token_is_masked(self, token):
        out = redact_sensitive(f"value = {token}")
        assert token not in out
        assert REDACTED in out

    def test_prefix_is_kept_for_troubleshooting(self):
        out = redact_sensitive("sk-ab395535bxyz1234567890abcdefghij")
        assert out.startswith("sk-")
        assert "ab395535bxyz" not in out

    def test_jwt_is_masked(self):
        jwt = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0"
            ".dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        )
        out = redact_sensitive(f"Authorization: Bearer {jwt}")
        assert jwt not in out


class TestKeyValuePatterns:
    """键值类凭据"""

    @pytest.mark.parametrize(
        "text",
        [
            "SELECT * FROM t WHERE api_key = 'secret-value'",
            "SELECT * FROM t WHERE apiKey = 'secret-value'",
            "SELECT * FROM t WHERE token = 'secret-value'",
            'UPDATE t SET password = "secret-value"',
            '{"password": "secret-value"}',
            '{"apiKey": "secret-value"}',
            '{"access_key": "secret-value"}',
        ],
    )
    def test_value_is_masked(self, text):
        out = redact_sensitive(text)
        assert "secret-value" not in out
        assert REDACTED in out

    def test_insert_values_position(self):
        text = "INSERT INTO users (username, password) VALUES ('bob', 'hunter2')"
        out = redact_sensitive(text)
        assert "hunter2" not in out
        assert "'bob'" in out  # 非敏感列的值保留

    def test_insert_values_only_sensitive_column(self):
        text = "INSERT INTO cfg (api_key) VALUES ('sk-abcdefghijklmnopqrst')"
        out = redact_sensitive(text)
        assert "sk-abcdefghijklmnopqrst" not in out

    def test_postgres_password_literal(self):
        out = redact_sensitive("CREATE USER app WITH PASSWORD 'pgpass123';")
        assert "pgpass123" not in out

    def test_url_credentials(self):
        out = redact_sensitive("psql postgresql://admin:s3cr3tpw@10.0.0.1:5432/db")
        assert "s3cr3tpw" not in out
        assert "admin" in out  # 用户名保留
        assert "10.0.0.1" in out

    def test_authorization_header(self):
        out = redact_sensitive("Authorization: Bearer abcdefghijklmnop")
        assert "abcdefghijklmnop" not in out
        assert "Authorization" in out

    def test_pem_private_key_block(self):
        text = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEowIBAAKCAQEA\n"
            "-----END RSA PRIVATE KEY-----"
        )
        out = redact_sensitive(text)
        assert "MIIEowIBAAKCAQEA" not in out
        assert "PRIVATE KEY" not in out


class TestFalsePositiveProtection:
    """误伤防护：普通业务字段不得被遮蔽"""

    @pytest.mark.parametrize(
        "text",
        [
            "SELECT id FROM users WHERE token_count > 100",
            "SELECT id FROM llm_user_quota WHERE token_period = 'daily'",
            "SELECT id FROM orders WHERE status = 'password_reset'",
            "SELECT id FROM messages WHERE total_tokens > 1000",
            "SELECT id FROM t WHERE name = 'secretary'",
            "UPDATE users SET password_hash = '$2b$12$abcdefghijklmnop'",
            "SELECT id FROM cfg WHERE access_key_id = 5",
            "ALTER TABLE hr.user_sync_sub_task ADD COLUMN id bigint",
        ],
    )
    def test_normal_sql_is_untouched(self, text):
        assert redact_sensitive(text) == text

    def test_short_word_after_sk_is_untouched(self):
        # 'sk-' 只有 3 字符的普通标识符片段不应被当成密钥
        text = "SELECT * FROM task WHERE task_sync_status = 1"
        assert redact_sensitive(text) == text


class TestRedactStructure:
    """结构化数据递归脱敏"""

    def test_sensitive_key_whole_value_masked(self):
        data = {"user": "bob", "password": "p@ssw0rd"}
        out = redact_structure(data)
        assert out["password"] == REDACTED
        assert out["user"] == "bob"

    def test_nested_list_and_dict(self):
        data = {"rows": [{"note": "key sk-abcdefghijklmnopqrst"}]}
        out = redact_structure(data)
        assert "sk-abcdefghijklmnopqrst" not in out["rows"][0]["note"]

    def test_non_string_passthrough(self):
        assert redact_structure(123) == 123
        assert redact_structure(None) is None
        assert redact_structure(True) is True


class TestEdgeCases:
    def test_empty_and_none(self):
        assert redact_sensitive("") == ""
        assert redact_sensitive(None) is None

    def test_plain_text_unchanged(self):
        assert redact_sensitive("SELECT 1") == "SELECT 1"
