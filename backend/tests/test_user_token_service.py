"""个人 API Token 服务单元测试（mock pooled connection，参照 test_k8s_tool_service.py 模式）"""
from datetime import datetime

import pytest
from unittest.mock import patch, MagicMock

from app.services.user_token_service import UserTokenService, TOKEN_PREFIX


@pytest.fixture
def mock_db():
    """Mock 数据库连接（与 test_k8s_tool_service.mock_db 相同模式）"""
    with patch("app.services.user_token_service.get_pooled_db_connection") as mock_get, \
         patch("app.services.user_token_service.release_db_connection") as mock_release:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        mock_get.return_value = conn
        yield cursor, conn
        mock_release.assert_called_with(conn)


@pytest.fixture(autouse=True)
def table_ready():
    """默认跳过建表（_ensure_table 含 3 条 DDL），业务 SQL 即 execute 第 0 条调用"""
    with patch("app.services.user_token_service._table_ready", True):
        yield


def test_ensure_table_idempotent_ddl(mock_db):
    with patch("app.services.user_token_service._table_ready", False):
        cursor, _ = mock_db
        UserTokenService._ensure_table()
        ddl = str(cursor.execute.call_args_list[0][0][0])
        assert "CREATE TABLE IF NOT EXISTS user_api_tokens" in ddl


def test_generate_token_returns_plain_once(mock_db):
    """创建返回明文 token，且明文只出现在返回值、DB 只收哈希"""
    cursor, _ = mock_db
    cursor.fetchone.return_value = {"created_at": "2026-10-14 10:00:00"}
    resp, plain = UserTokenService.generate_token("u1", "claude-code", expires_days=30)
    assert plain.startswith(TOKEN_PREFIX) and len(plain) > 40
    assert resp.token == plain          # 明文仅在创建响应里
    assert resp.token_prefix == plain[:12]
    insert_sql = str(cursor.execute.call_args_list[0][0][0])
    assert "INSERT INTO user_api_tokens" in insert_sql
    assert "token_hash" in insert_sql
    # 传给 execute 的参数中不能出现明文 token（只允许哈希与前缀）
    params = cursor.execute.call_args_list[0][0][1]
    assert plain not in params


def test_hash_is_sha256_deterministic():
    import hashlib
    assert UserTokenService._hash_token("pat_abc") == hashlib.sha256(b"pat_abc").hexdigest()


def test_validate_token_rejects_bad_format():
    assert UserTokenService.validate_token("") is None
    assert UserTokenService.validate_token("not-a-pat") is None


def test_validate_token_ok_updates_last_used(mock_db):
    cursor, _ = mock_db
    plain = "pat_validtoken123"
    cursor.fetchone.return_value = {"user_id": "u1", "expires_at": None, "revoked_at": None}
    assert UserTokenService.validate_token(plain) == "u1"
    select_sql = str(cursor.execute.call_args_list[0][0][0])
    assert "token_hash" in select_sql and "revoked_at" in select_sql
    update_sql = str(cursor.execute.call_args_list[-1][0][0])
    assert "last_used_at" in update_sql


def test_validate_token_revoked(mock_db):
    cursor, _ = mock_db
    cursor.fetchone.return_value = {"user_id": "u1", "expires_at": None,
                                    "revoked_at": datetime(2026, 10, 13)}
    assert UserTokenService.validate_token("pat_x") is None


def test_validate_token_expired(mock_db):
    cursor, _ = mock_db
    cursor.fetchone.return_value = {"user_id": "u1",
                                    "expires_at": datetime(2026, 1, 1),
                                    "revoked_at": None}
    assert UserTokenService.validate_token("pat_x") is None


def test_validate_token_not_found(mock_db):
    cursor, _ = mock_db
    cursor.fetchone.return_value = None
    assert UserTokenService.validate_token("pat_x") is None


def test_list_tokens_filters_by_user(mock_db):
    cursor, _ = mock_db
    cursor.fetchall.return_value = []
    UserTokenService.list_tokens("u1")
    sql = str(cursor.execute.call_args_list[0][0][0])
    assert "user_id = %s" in sql
    assert "revoked" in sql


def test_revoke_token_scoped_to_user(mock_db):
    cursor, _ = mock_db
    cursor.rowcount = 1
    assert UserTokenService.revoke_token("u1", "tok1") is True
    call = cursor.execute.call_args_list[0]
    sql, params = call[0][0], call[0][1]
    assert "user_id = %s" in sql and "revoked_at" in sql
    assert "u1" in params and "tok1" in params


def test_revoke_token_not_found(mock_db):
    cursor, _ = mock_db
    cursor.rowcount = 0
    assert UserTokenService.revoke_token("u1", "missing") is False
