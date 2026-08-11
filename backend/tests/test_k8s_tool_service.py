"""K8s 连接配置 Service 单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.k8s_tool_service import K8sToolService
from app.models.k8s_tool_models import CreateK8sManualRequest


@pytest.fixture
def mock_db():
    """Mock 数据库连接，模拟 RealDictCursor 返回 dict 行"""
    with patch("app.services.k8s_tool_service.get_pooled_db_connection") as mock_get, \
         patch("app.services.k8s_tool_service.release_db_connection") as mock_release:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        mock_get.return_value = conn
        yield cursor, conn
        # 验证每次获取的连接最终都被归还
        mock_release.assert_called_with(conn)


def test_ensure_table_creates_table(mock_db):
    """_ensure_table 执行 CREATE TABLE IF NOT EXISTS"""
    cursor, _ = mock_db
    K8sToolService._ensure_table()
    # 收集所有 execute 调用的 SQL 文本
    calls = [str(c) for c in cursor.execute.call_args_list]
    assert any("CREATE TABLE IF NOT EXISTS k8s_connections" in c for c in calls)


def test_create_config_encrypts_secrets(mock_db):
    """创建配置时敏感字段被加密，响应不含明文"""
    cursor, conn = mock_db
    # fetchone 返回刚插入的行（模拟 RealDictCursor dict 行）
    cursor.fetchone.return_value = {
        "id": "test-id",
        "user_id": "u1",
        "name": "test-cluster",
        "source_type": "manual",
        "cluster_name": "cluster",
        "context_name": "ctx",
        "server": "https://k8s:6443",
        "auth_type": "bearer_token",
        "auth_data_encrypted": "encrypted_token",
        "ca_cert_encrypted": None,
        "namespace_filter": "[]",
        "is_metrics_available": False,
        "last_test_at": None,
        "last_test_error": None,
        "created_at": "2026-08-10T00:00:00",
        "updated_at": "2026-08-10T00:00:00",
    }

    request = CreateK8sManualRequest(
        name="test-cluster",
        server="https://k8s:6443",
        auth_type="bearer_token",
        token="my-secret-token",
    )

    with patch("app.services.k8s_tool_service.EncryptionUtils") as mock_enc:
        mock_enc.encrypt.return_value = "encrypted_token"
        result = K8sToolService.create_config("u1", request)

    # 验证加密函数被调用（token JSON 序列化后被加密）
    mock_enc.encrypt.assert_called()
    # 响应标记已配置认证信息
    assert result.has_auth_data is True
    # 响应对象不应含明文 token 字段（Pydantic 模型无此字段）
    assert not hasattr(result, "token")


def test_get_configs_filters_by_user(mock_db):
    """列表查询按 user_id 过滤，且只返回未删除记录"""
    cursor, _ = mock_db
    cursor.fetchall.return_value = []
    K8sToolService.get_configs("user-123")
    sql, params = cursor.execute.call_args[0]
    assert "user_id = %s" in sql
    assert "deleted = FALSE" in sql
    assert params == ("user-123",)


def test_delete_config_soft_delete(mock_db):
    """删除操作是软删除（SET deleted = TRUE），不物理删除行"""
    cursor, _ = mock_db
    cursor.rowcount = 1
    result = K8sToolService.delete_config("u1", "config-id")
    assert result is True
    sql, _ = cursor.execute.call_args[0]
    assert "deleted = TRUE" in sql or "deleted = true" in sql.lower()
