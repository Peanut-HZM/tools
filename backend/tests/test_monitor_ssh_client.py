# backend/tests/test_monitor_ssh_client.py
"""
SSH 连接池测试 - mock paramiko 客户端
"""
import os
import sys
import asyncio
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.services.monitor import ssh_client
from app.services.monitor.ssh_client import SSHConnectionPool, SSHCommandError

SERVER = {
    "id": "srv-1", "server_type": "ssh", "host": "10.0.0.1", "port": 22,
    "username": "root", "password": "pw", "private_key": None, "passphrase": None,
}


class FakeChannel:
    """模拟 paramiko 通道（支持超时设置与退出码）"""
    def __init__(self, out=b"", err=b"", code=0):
        self.out = out
        self.err = err
        self.code = code
        self.timeout = None

    def settimeout(self, t):
        self.timeout = t

    def recv_exit_status(self):
        return self.code


class FakeStdout:
    def __init__(self, channel):
        self.channel = channel

    def read(self):
        if self.channel.timeout is None:
            raise TimeoutError("simulated read timeout")
        return self.channel.out


class FakeStderr:
    def __init__(self, channel):
        self.channel = channel

    def read(self):
        return self.channel.err


def make_fake_client(out=b"OK\n", err=b"", code=0):
    client = MagicMock()
    channel = FakeChannel(out=out, err=err, code=code)
    stdout = FakeStdout(channel)
    stderr = FakeStderr(channel)
    client.exec_command.return_value = (MagicMock(), stdout, stderr)
    transport = MagicMock()
    transport.set_keepalive = MagicMock()
    client.get_transport.return_value = transport
    return client


def test_run_command_success(monkeypatch):
    fake_client = make_fake_client(out=b"hello")
    monkeypatch.setattr(ssh_client.paramiko, "SSHClient", lambda: fake_client)
    p = SSHConnectionPool()
    result = asyncio.run(p.run_command(SERVER, "echo hello", timeout=10))
    assert result == "hello"
    assert fake_client.exec_command.called


def test_run_command_nonzero_exit_raises(monkeypatch):
    fake_client = make_fake_client(out=b"", err=b"permission denied", code=1)
    monkeypatch.setattr(ssh_client.paramiko, "SSHClient", lambda: fake_client)
    p = SSHConnectionPool()
    with pytest.raises(SSHCommandError):
        asyncio.run(p.run_command(SERVER, "bad-command", timeout=10))


def test_connection_reuse(monkeypatch):
    """同一服务器第二次执行应复用连接（只 connect 一次）"""
    fake_client = make_fake_client(out=b"x")
    monkeypatch.setattr(ssh_client.paramiko, "SSHClient", lambda: fake_client)
    p = SSHConnectionPool()
    asyncio.run(p.run_command(SERVER, "cmd1"))
    asyncio.run(p.run_command(SERVER, "cmd2"))
    assert fake_client.connect.call_count == 1


def test_reconnect_after_failure(monkeypatch):
    """连接失效时自动重连一次"""
    calls = {"n": 0}

    def side_effect(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("conn lost")
        return None

    fake_client = make_fake_client(out=b"ok")
    fake_client.connect.side_effect = side_effect
    monkeypatch.setattr(ssh_client.paramiko, "SSHClient", lambda: fake_client)
    p = SSHConnectionPool()
    result = asyncio.run(p.run_command(SERVER, "cmd"))
    assert result == "ok"
    assert calls["n"] == 2


def test_close_idle_connections(monkeypatch):
    fake_client = make_fake_client(out=b"x")
    monkeypatch.setattr(ssh_client.paramiko, "SSHClient", lambda: fake_client)
    p = SSHConnectionPool()
    asyncio.run(p.run_command(SERVER, "cmd"))
    assert len(p._pool) == 1
    closed = p.close_idle_connections(max_idle_seconds=0)
    assert closed == 1
    assert len(p._pool) == 0
