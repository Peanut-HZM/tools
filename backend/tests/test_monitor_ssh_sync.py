"""SSH 配置 → 监控服务器自动同步

覆盖需求：「性能监控需要自动同步 SSH 工具配置的服务器过来」。

关键不变量：
1. SSH 新增 → 建监控服务器（记 source_ssh_id）
2. 重复同步幂等 —— 不重复建、不改已有
3. SSH 侧改名 → 监控侧跟随更新
4. SSH 侧删除 → 监控侧标记 disabled（不物理删）
5. 凭据解密失败（历史密钥问题）→ 单条跳过并给出可操作原因，不影响其它条
6. 本机节点 / 手动添加的服务器完全不受同步影响
"""

import pytest

from app.services.monitor import server_service as svc


class _FakeCursor:
    def __init__(self, store):
        self._store = store
        self._result = []

    def execute(self, sql, params=None):
        s = " ".join(sql.split()).lower()
        if s.startswith("select") and "monitor_servers" in s and "source_ssh_id is not null" in s:
            uid = params[0]
            self._result = [
                dict(r) for r in self._store
                if r["user_id"] == uid and not r.get("deleted") and r.get("source_ssh_id")
            ]
        elif s.startswith("update") and "monitor_servers" in s:
            if "status = 'disabled'" in s:
                target_id = params[0]          # WHERE id = %s AND user_id = %s
            else:
                target_id = params[-2]         # ... WHERE id = %s AND user_id = %s
            for r in self._store:
                if r["id"] == target_id:
                    if "name = %s" in s:
                        r.update(name=params[0], host=params[1], port=params[2], username=params[3])
                    elif "status = 'disabled'" in s:
                        r["status"] = "disabled"
        else:
            self._result = []

    def fetchall(self):
        return self._result

    def close(self):
        pass


@pytest.fixture
def fake_db(monkeypatch):
    """用内存列表替代表存储"""
    store: list[dict] = []
    monkeypatch.setattr(svc, "get_pooled_db_connection", lambda: type("C", (), {
        "cursor": lambda self=None: _FakeCursor(store),
        "commit": lambda self=None: None,
    })())
    monkeypatch.setattr(svc, "release_db_connection", lambda c: None)
    return store


class _Cfg:
    def __init__(self, cid, alias, host="1.2.3.4", port=22, username="root"):
        self.id = cid
        self.alias = alias
        self.host = host
        self.port = port
        self.username = username


@pytest.fixture
def ssh_source(monkeypatch):
    """可变的 SSH 配置源"""
    state = {"configs": []}

    class _Svc:
        @staticmethod
        def get_configs(user_id):
            return state["configs"]

    monkeypatch.setattr(
        "app.services.ssh_tool_service.SSHToolService", _Svc, raising=False
    )
    return state


def test_sync_creates_new_servers(fake_db, ssh_source, monkeypatch):
    ssh_source["configs"] = [_Cfg("ssh-1", "web-1"), _Cfg("ssh-2", "web-2")]
    created = []

    def _import(uid, ssh_id):
        created.append(ssh_id)
        fake_db.append({
            "id": f"srv-{ssh_id}", "user_id": uid, "name": ssh_id,
            "host": "1.2.3.4", "port": 22, "username": "root",
            "source_ssh_id": ssh_id, "status": "online", "deleted": False,
        })
        return {"id": f"srv-{ssh_id}"}

    monkeypatch.setattr(svc.MonitorServerService, "import_from_ssh", staticmethod(_import))

    res = svc.MonitorServerService.sync_from_ssh("u1")
    assert res["sshTotal"] == 2
    assert res["created"] == 2
    assert sorted(created) == ["ssh-1", "ssh-2"]


def test_sync_is_idempotent(fake_db, ssh_source, monkeypatch):
    """重复同步不得重复建服务器"""
    ssh_source["configs"] = [_Cfg("ssh-1", "web-1")]
    fake_db.append({
        "id": "srv-1", "user_id": "u1", "name": "web-1", "host": "1.2.3.4",
        "port": 22, "username": "root", "source_ssh_id": "ssh-1",
        "status": "online", "deleted": False,
    })
    called = []
    monkeypatch.setattr(
        svc.MonitorServerService, "import_from_ssh",
        staticmethod(lambda uid, sid: called.append(sid)),
    )

    res = svc.MonitorServerService.sync_from_ssh("u1")
    assert res["created"] == 0
    assert res["unchanged"] == 1
    assert called == []


def test_sync_updates_renamed_ssh_config(fake_db, ssh_source, monkeypatch):
    """SSH 侧改名 → 监控侧跟随"""
    ssh_source["configs"] = [_Cfg("ssh-1", "web-renamed", host="9.9.9.9")]
    fake_db.append({
        "id": "srv-1", "user_id": "u1", "name": "web-old", "host": "1.2.3.4",
        "port": 22, "username": "root", "source_ssh_id": "ssh-1",
        "status": "online", "deleted": False,
    })
    monkeypatch.setattr(
        svc.MonitorServerService, "import_from_ssh",
        staticmethod(lambda uid, sid: pytest.fail("改名不应走新建路径")),
    )

    res = svc.MonitorServerService.sync_from_ssh("u1")
    assert res["updated"] == 1
    row = fake_db[0]
    assert row["name"] == "web-renamed"
    assert row["host"] == "9.9.9.9"


def test_sync_disables_server_when_ssh_removed(fake_db, ssh_source, monkeypatch):
    """SSH 配置删除 → 监控侧 disabled，不物理删（保留历史指标）"""
    ssh_source["configs"] = []
    fake_db.append({
        "id": "srv-1", "user_id": "u1", "name": "web-gone", "host": "1.2.3.4",
        "port": 22, "username": "root", "source_ssh_id": "ssh-gone",
        "status": "online", "deleted": False,
    })

    res = svc.MonitorServerService.sync_from_ssh("u1")
    assert res["disabled"] == 1
    assert fake_db[0]["status"] == "disabled"


def test_sync_skips_undecryptable_ssh_config(fake_db, ssh_source, monkeypatch):
    """凭据解不开时单条跳过并给出可操作原因，不影响其它条"""
    ssh_source["configs"] = [_Cfg("ssh-bad", "legacy"), _Cfg("ssh-ok", "healthy")]

    def _import(uid, ssh_id):
        if ssh_id == "ssh-bad":
            from cryptography.fernet import InvalidToken

            raise InvalidToken()
        fake_db.append({
            "id": "srv-ok", "user_id": uid, "name": "healthy", "host": "1.2.3.4",
            "port": 22, "username": "root", "source_ssh_id": ssh_id,
            "status": "online", "deleted": False,
        })
        return {"id": "srv-ok"}

    monkeypatch.setattr(svc.MonitorServerService, "import_from_ssh", staticmethod(_import))

    res = svc.MonitorServerService.sync_from_ssh("u1")
    assert res["created"] == 1
    failed = [i for i in res["items"] if i["action"] == "failed"]
    assert len(failed) == 1
    assert "重新填写密码" in failed[0]["reason"]
