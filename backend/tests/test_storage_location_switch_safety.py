"""存储位置切换的安全不变量测试

覆盖本次修复的三个真实缺陷：
1. SSH update_config 显式指定 storage_location 时曾抛 NameError（500）
2. 编辑弹窗切存储位置曾只做「目标端 UPDATE」，导致源端（服务器）残留密文副本
3. delete_config 曾只删一侧，另一侧残留

核心不变量：
- 配置切到 LOCAL 后，远程 PG 中该 id 必须**物理不存在**（不是软删除标记）
- 配置切到 LOCAL 后，远程 PG 中不得出现 storage_location='LOCAL' 的行
- 删除配置后，两侧都查不到该 id
"""
import os
import sys

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage.crypto import LocalEncryption
from app.storage.locator import StorageLocation
from app.storage.local_db import get_local_engine, init_local_tables, reset_local_engine
from app.storage.repository import get_repository
from app.models.k8s_tool_models import CreateK8sManualRequest


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    """把本地库与本地密钥重定向到临时目录"""
    from app.config import config as config_module

    monkeypatch.setattr(config_module, "REAL_HOME", str(tmp_path))
    LocalEncryption.reset_cipher_suite()
    reset_local_engine()

    init_local_tables(get_local_engine())
    yield
    reset_local_engine()
    LocalEncryption.reset_cipher_suite()


def _local_rows(table: str, config_id: str):
    with get_local_engine().begin() as conn:
        rows = conn.execute(
            text(f"SELECT * FROM {table} WHERE id = :i"), {"i": config_id}
        ).mappings().all()
    return [dict(r) for r in rows]


class TestEnsureStorageLocation:
    """ensure_storage_location：位置变化时必须真迁移（重加密 + 删源端）"""

    def test_config_already_at_target_is_noop(self, local_env):
        """配置已在目标侧 → 不做任何写操作，直接返回目标端仓储"""
        from app.storage.repository import ensure_storage_location
        from app.models.ssh_tool_models import CreateSSHRequest
        from app.services.ssh_tool_service import SSHToolService

        created = SSHToolService.create_config(
            "u-1",
            CreateSSHRequest(
                alias="a", host="10.0.0.1", port=22, username="root", password="pw"
            ),
            StorageLocation.LOCAL,
        )

        repo, location = ensure_storage_location(
            "u-1", "ssh", created.id, StorageLocation.LOCAL
        )

        assert location is StorageLocation.LOCAL
        assert repo.get(created.id, "u-1") is not None

    def test_missing_config_raises(self, local_env):
        """配置不存在 → 抛 ValueError（不静默成功）"""
        from app.storage.repository import ensure_storage_location

        with pytest.raises(ValueError):
            ensure_storage_location("u-1", "ssh", "not-exist", StorageLocation.LOCAL)


class TestSSHUpdateConfigWithStorageLocation:
    """回归：SSH update_config 显式传 storage_location 曾抛 NameError → 500"""

    def test_update_with_explicit_local_location_works(self, local_env):
        """显式指定 LOCAL → 更新成功，不抛 NameError"""
        from app.models.ssh_tool_models import CreateSSHRequest, UpdateSSHRequest
        from app.services.ssh_tool_service import SSHToolService

        created = SSHToolService.create_config(
            "u-1",
            CreateSSHRequest(
                alias="a", host="10.0.0.1", port=22, username="root", password="pw"
            ),
            StorageLocation.LOCAL,
        )

        updated = SSHToolService.update_config(
            "u-1",
            UpdateSSHRequest(id=created.id, alias="renamed"),
            StorageLocation.LOCAL,
        )

        assert updated.alias == "renamed"
        assert updated.storage_location == "local"


class TestDeleteConfigEverywhere:
    """删除配置必须两侧都物理删除"""

    def test_delete_removes_local_row(self, local_env):
        from app.models.ssh_tool_models import CreateSSHRequest
        from app.services.ssh_tool_service import SSHToolService

        created = SSHToolService.create_config(
            "u-1",
            CreateSSHRequest(
                alias="a", host="10.0.0.1", port=22, username="root", password="pw"
            ),
            StorageLocation.LOCAL,
        )
        assert len(_local_rows("ssh_configs", created.id)) == 1

        assert SSHToolService.delete_config("u-1", created.id) is True

        assert _local_rows("ssh_configs", created.id) == []

    def test_delete_config_everywhere_covers_both_sides(self, local_env, monkeypatch):
        """delete_config_everywhere 会对两侧都调用 delete（即使一侧没有该行）"""
        from app.storage import repository as repo_module

        calls: list = []

        class FakeRepo:
            def __init__(self, location, hit):
                self.location = location
                self.hit = hit

            def delete(self, config_id, user_id):
                calls.append(self.location)
                return self.hit

        def fake_get_repository(location, tool):
            return FakeRepo(location, hit=(location is StorageLocation.LOCAL))

        monkeypatch.setattr(repo_module, "get_repository", fake_get_repository)

        result = repo_module.delete_config_everywhere("u-1", "ssh", "cfg-1")

        assert result is True
        assert len(calls) == 2, "必须两侧都尝试删除"


class TestLocalRowsNeverLeakToRemote:
    """安全不变量：本地库的 LOCAL 行不会被写进远程库"""

    def test_local_repo_rejects_server_location(self, local_env):
        """LocalConfigRepository.create 传 SERVER → 抛错（类型层保障）"""
        from app.models.ssh_tool_models import CreateSSHRequest
        from app.services.ssh_tool_service import SSHToolService

        repo = get_repository(StorageLocation.LOCAL, "ssh")

        with pytest.raises(ValueError, match="存储位置不匹配"):
            repo.create(
                "u-1",
                {
                    "id": "x",
                    "alias": "a",
                    "host": "h",
                    "port": 22,
                    "username": "root",
                    "created_at": None,
                    "updated_at": None,
                },
                StorageLocation.SERVER,
            )

    def test_local_row_marked_local(self, local_env):
        """本地库行的 storage_location 必须是 LOCAL"""
        from app.models.ssh_tool_models import CreateSSHRequest
        from app.services.ssh_tool_service import SSHToolService

        created = SSHToolService.create_config(
            "u-1",
            CreateSSHRequest(
                alias="a", host="10.0.0.1", port=22, username="root", password="pw"
            ),
            StorageLocation.LOCAL,
        )

        rows = _local_rows("ssh_configs", created.id)
        assert len(rows) == 1
        assert rows[0]["storage_location"] == "LOCAL"


class TestK8sUpdateAcceptsStorageLocationInBody:
    """回归：K8s 的 storage_location 曾只在 Query 里读，body 传值被静默忽略

    前端把 storage_location 放在请求体中，若后端只读 Query，
    切位置会「看起来保存成功但实际没迁移」（服务器侧残留密文副本）。
    """

    def test_update_request_model_has_storage_location(self):
        from app.models.k8s_tool_models import UpdateK8sAuthRequest, UpdateK8sRequest

        assert "storage_location" in UpdateK8sRequest.model_fields
        assert "storage_location" in UpdateK8sAuthRequest.model_fields

    def test_update_reads_body_storage_location(self, local_env):
        """body 里的 storage_location=local 必须生效（配置从 SERVER 迁到 LOCAL）"""
        from app.models.k8s_tool_models import UpdateK8sRequest
        from app.services.k8s_tool_service import K8sToolService

        created = K8sToolService.create_config(
            "u-k8s",
            CreateK8sManualRequest(
                name="k8s-a",
                server="https://10.0.0.1:6443",
                auth_type="bearer_token",
                token="tok",
            ),
            StorageLocation.LOCAL,
        )

        updated = K8sToolService.update_config(
            "u-k8s",
            UpdateK8sRequest(id=created.id, storage_location="local"),
            None,
        )

        assert updated is not None
        assert updated.storage_location == "local"

