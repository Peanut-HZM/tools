"""服务定位映射服务单元测试"""
from datetime import datetime

import pytest
from unittest.mock import patch, MagicMock

from app.services.k8s_service_mapping_service import K8sServiceMappingService

TABLE_READY = "app.services.k8s_service_mapping_service._table_ready"


@pytest.fixture
def mock_db():
    # 注意：不在此断言 release_db_connection 被调用——source 非法等参数校验
    # 在触 DB 前就抛 ValueError，属于合法路径
    with patch("app.services.k8s_service_mapping_service.get_pooled_db_connection") as mock_get, \
         patch("app.services.k8s_service_mapping_service.release_db_connection"):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        mock_get.return_value = conn
        yield cursor, conn


@pytest.fixture(autouse=True)
def skip_ensure_table():
    with patch(TABLE_READY, True):
        yield


def test_ensure_table_idempotent_ddl(mock_db):
    with patch(TABLE_READY, False):
        cursor, _ = mock_db
        K8sServiceMappingService._ensure_table()
        ddl = str(cursor.execute.call_args_list[0][0][0])
        assert "CREATE TABLE IF NOT EXISTS k8s_service_mappings" in ddl
        assert "UNIQUE (user_id, project_key)" in ddl


def test_save_mapping_rejects_bad_source(mock_db):
    cursor, _ = mock_db
    with pytest.raises(ValueError):
        K8sServiceMappingService.save_mapping(
            "u1", "gmdos-svc", "c1", "desk-dev", None, None, "x", source="hack")


def test_save_mapping_upsert(mock_db):
    cursor, _ = mock_db
    cursor.fetchone.return_value = {
        "id": "m1", "user_id": "u1", "project_key": "gmdos-svc", "cluster_id": "c1",
        "namespace": "desk-dev", "deployment": "gmdos-admin-svc", "container": None,
        "evidence": "Jenkinsfile: docker build gmdos-admin", "source": "jenkinsfile",
        "created_at": datetime(2026, 10, 14, 10, 0), "updated_at": datetime(2026, 10, 14, 10, 0),
    }
    row = K8sServiceMappingService.save_mapping(
        "u1", "gmdos-svc", "c1", "desk-dev", "gmdos-admin-svc", None,
        "Jenkinsfile: docker build gmdos-admin", source="jenkinsfile")
    sql = str(cursor.execute.call_args[0][0])
    assert "ON CONFLICT (user_id, project_key) DO UPDATE" in sql   # 幂等 UPSERT
    assert row["project_key"] == "gmdos-svc"


def test_lookup_returns_none_when_missing(mock_db):
    cursor, _ = mock_db
    cursor.fetchone.return_value = None
    assert K8sServiceMappingService.lookup_mapping("u1", "nope") is None


def test_lookup_joins_cluster_name_and_scopes_user(mock_db):
    cursor, _ = mock_db
    cursor.fetchone.return_value = {
        "project_key": "gmdos-svc", "cluster_id": "c1", "cluster_name": "gmdos-dev",
        "namespace": "desk-dev", "deployment": "gmdos-admin-svc", "container": None,
        "evidence": "e", "source": "traversal", "updated_at": datetime(2026, 10, 14, 10, 0),
    }
    row = K8sServiceMappingService.lookup_mapping("u1", "gmdos-svc")
    sql, params = cursor.execute.call_args[0]
    assert "cluster_name" in sql and "LEFT JOIN k8s_connections" in sql
    assert params[0] == "u1"          # 按用户隔离
    assert row["cluster_name"] == "gmdos-dev"
