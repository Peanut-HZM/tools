"""K8s 连接配置 Service 单元测试（双存储改造后：走 Repository + 本地 SQLite）"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.k8s_tool_models import CreateK8sManualRequest
from app.storage.crypto import LocalEncryption
from app.storage.locator import StorageLocation
from app.storage.local_db import get_local_engine, init_local_tables, reset_local_engine


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    from app.config import config as config_module

    monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
    LocalEncryption.reset_cipher_suite()
    reset_local_engine()

    init_local_tables(get_local_engine())
    yield
    reset_local_engine()


def _make_request(**overrides):
    payload = {
        "name": "test-cluster",
        "server": "https://k8s:6443",
        "auth_type": "bearer_token",
        "token": "my-secret-token",
    }
    payload.update(overrides)
    return CreateK8sManualRequest(**payload)


def test_create_config_encrypts_secrets(local_env):
    """创建配置时敏感字段被加密落库，响应不含明文"""
    from app.services.k8s_tool_service import K8sToolService
    from sqlalchemy import text

    result = K8sToolService.create_config("u1", _make_request(), StorageLocation.LOCAL)

    # 落库为密文（token 明文不出现在密文里）
    with get_local_engine().begin() as conn:
        cipher = conn.execute(text(
            "SELECT auth_data_encrypted FROM k8s_connections WHERE id = :i"
        ), {"i": result.id}).first()[0]

    assert "my-secret-token" not in cipher
    # 响应标记已配置认证信息
    assert result.has_auth_data is True
    assert result.storage_location == "local"
    # 响应对象不应含明文 token 字段（Pydantic 模型无此字段）
    assert not hasattr(result, "token")


def test_get_configs_merges_and_sorts(local_env):
    """列表合并本地 + 服务器两侧，按 sort_order / name 排序"""
    from app.services.k8s_tool_service import K8sToolService

    K8sToolService.create_config(
        "user-123", _make_request(name="b-cluster"), StorageLocation.LOCAL
    )
    K8sToolService.create_config(
        "user-123", _make_request(name="a-cluster"), StorageLocation.LOCAL
    )

    configs = K8sToolService.get_configs("user-123")

    assert [c.name for c in configs] == ["a-cluster", "b-cluster"]
    # 过滤了其他用户
    assert all(c.user_id == "user-123" for c in configs)


def test_delete_config_removes_row(local_env):
    """删除后配置不再出现在列表与定位结果中"""
    from app.services.k8s_tool_service import K8sToolService

    created = K8sToolService.create_config(
        "u1", _make_request(name="to-delete"), StorageLocation.LOCAL
    )

    assert K8sToolService.delete_config("u1", created.id) is True
    assert K8sToolService.get_config_by_id("u1", created.id) is None
    assert K8sToolService.delete_config("u1", created.id) is False
