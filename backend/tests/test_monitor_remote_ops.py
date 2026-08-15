"""
按需远程操作测试 - mock 命令输出，验证解析逻辑
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.monitor import remote_ops

SSH_SERVER = {"id": "srv-1", "user_id": "u1", "server_type": "ssh", "name": "web1",
              "host": "10.0.0.1", "port": 22, "username": "root", "password": "pw",
              "private_key": None, "passphrase": None, "group_name": None,
              "status": "enabled", "last_error": None, "last_seen_at": None}

LOCAL_SERVER = {"id": "srv-local", "user_id": "u1", "server_type": "local", "name": "本机",
                "host": "", "port": 22, "username": "", "password": None,
                "private_key": None, "passphrase": None, "group_name": None,
                "status": "enabled", "last_error": None, "last_seen_at": None}

DF_OUTPUT = """Filesystem     1024-blocks      Used Available Capacity Mounted on
/dev/vda1        20971520   4194304  16777216      20% /
"""

PS_OUTPUT = """1|root|Ss|0.0|0.1|100000|200000|1|00:12:34|/sbin/init
1234|root|S|5.5|2.0|500000|900000|8|02:00:00|/usr/bin/python3 /opt/app/main.py
5678|www|R|95.0|10.0|2000000|3000000|20|00:01:00|node /app/server.js
"""

SVC_OUTPUT = """nginx.service loaded active running The nginx HTTP and reverse proxy server
mysql.service loaded active exited MySQL Community Server
cron.service loaded not-running Regular background program processing daemon
"""

SVC_FILES_OUTPUT = """nginx.service enabled
mysql.service disabled
cron.service enabled
"""


def test_parse_df():
    rows = remote_ops._parse_df_output(DF_OUTPUT)
    assert len(rows) == 1
    assert rows[0]["device"] == "/dev/vda1"
    assert rows[0]["percent"] == 20.0
    assert rows[0]["total"] == 20971520 * 1024


def test_parse_ps():
    processes = remote_ops._parse_ps_output(PS_OUTPUT)
    assert len(processes) == 3
    assert processes[0]["pid"] == 1
    assert processes[1]["cpu_percent"] == 5.5
    assert processes[1]["command_line"].startswith("/usr/bin/python3")
    assert processes[2]["project_type"] == "Node.js"


def test_parse_services():
    services = remote_ops._parse_services_output(SVC_OUTPUT, SVC_FILES_OUTPUT)
    assert len(services) == 3
    nginx = services[0]
    assert nginx["name"] == "nginx.service"
    assert nginx["state"] == "running"
    assert nginx["enabled"] is True
    assert services[1]["enabled"] is False


def test_get_partitions_local(monkeypatch):
    """本机通过 subprocess 执行 df"""
    # mock _run_local_command 返回 stdout 字符串（与实现返回值类型一致）
    monkeypatch.setattr(remote_ops, "_run_local_command", lambda *a, **k: DF_OUTPUT)
    rows = asyncio.run(remote_ops.get_partitions(LOCAL_SERVER))
    assert rows[0]["device"] == "/dev/vda1"


def test_service_action_success(monkeypatch):
    async def fake_run(server, cmd, timeout=10):
        return ""
    monkeypatch.setattr(remote_ops, "_run_on_server", fake_run)
    result = asyncio.run(remote_ops.service_action(SSH_SERVER, "nginx.service", "restart"))
    assert result["success"] is True


def test_service_action_failure(monkeypatch):
    from app.services.monitor.ssh_client import SSHCommandError

    async def fake_run(server, cmd, timeout=10):
        raise SSHCommandError("需要 root 权限")
    monkeypatch.setattr(remote_ops, "_run_on_server", fake_run)
    result = asyncio.run(remote_ops.service_action(SSH_SERVER, "nginx.service", "restart"))
    assert result["success"] is False
    assert "root" in result["message"]


def test_check_privileges_sudo_ok(monkeypatch):
    async def fake_run(server, cmd, timeout=10):
        return "EXIT:0"
    monkeypatch.setattr(remote_ops, "_run_on_server", fake_run)
    result = asyncio.run(remote_ops.check_privileges(SSH_SERVER))
    assert result["sudo_available"] is True
