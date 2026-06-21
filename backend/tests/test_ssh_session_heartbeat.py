"""
handle_ssh_session 单元测试
覆盖:SSH 失败时 error 推送 / WebSocket 断开后 ssh.close() 被调用 / transport keepalive 设置
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ssh_tool_service import SSHToolService


class FakeWebSocket:
    def __init__(self):
        self.sent = []
        self.closed = False
        self.close_code = None
        self.client_state = MagicMock()
        self.client_state.name = "CONNECTED"

    async def accept(self):
        # handle_ssh_session 入口先 accept
        pass

    async def send_text(self, data):
        self.sent.append(data)

    async def receive_text(self):
        from fastapi import WebSocketDisconnect
        raise WebSocketDisconnect()

    async def close(self, code=1000, reason=""):
        self.closed = True
        self.close_code = code
        self.client_state.name = "DISCONNECTED"


@pytest.mark.asyncio
async def test_ssh_connect_failure_pushes_error_message_then_closes():
    """ssh.connect 抛错 → 后端先发 type=error,再 close"""
    ws = FakeWebSocket()

    fake_config = {
        'id': 'cfg-x', 'host': 'bad-host', 'port': 22, 'username': 'u',
        'password_encrypted': None, 'private_key_encrypted': None, 'passphrase_encrypted': None,
    }

    with patch.object(SSHToolService, '_get_config_record', return_value=fake_config), \
         patch.object(SSHToolService, '_get_column_map', return_value={
             'password': 'password_encrypted',
             'private_key': 'private_key_encrypted',
             'passphrase': 'passphrase_encrypted',
         }), \
         patch('app.services.ssh_tool_service.get_auth_service') as gauth, \
         patch('app.services.ssh_tool_service.EncryptionUtils.decrypt', return_value=None), \
         patch('app.services.ssh_tool_service.paramiko.SSHClient') as SSH:
        auth_svc = MagicMock()
        auth_svc.verify_token_data.return_value = MagicMock(user_id='u1')
        gauth.return_value = auth_svc
        ssh_inst = MagicMock()
        ssh_inst.connect.side_effect = OSError("Connection refused")
        SSH.return_value = ssh_inst

        await SSHToolService.handle_ssh_session(ws, 'cfg-x', 'fake-token')

    # 发了 type=error,message 为通用错误消息(不泄露内部细节)
    error_msgs = [json.loads(m) for m in ws.sent if m.startswith('{')]
    assert any(m.get('type') == 'error' and m.get('message') == 'SSH connection failed' for m in error_msgs)
    # close 被调用
    assert ws.closed


@pytest.mark.asyncio
async def test_websocket_disconnect_triggers_ssh_close():
    """WebSocket 断开后,ssh.close() 必须被调用"""
    ws = FakeWebSocket()

    fake_config = {
        'id': 'cfg-x', 'host': 'h', 'port': 22, 'username': 'u',
        'password_encrypted': None, 'private_key_encrypted': None, 'passphrase_encrypted': None,
    }

    channel = MagicMock()
    # 第一次 recv 抛 timeout(模拟 5s 等待),第二次起直接 TimeoutError
    channel.recv.side_effect = TimeoutError("timed out")
    # exit_status_ready 第一次 False,第二次起 True,让循环有机会退出
    channel.exit_status_ready.side_effect = [False, True]
    channel.settimeout = MagicMock()

    ssh_inst = MagicMock()
    ssh_inst.invoke_shell.return_value = channel
    transport = MagicMock()
    ssh_inst.get_transport.return_value = transport

    async def recv_then_disconnect():
        from fastapi import WebSocketDisconnect
        raise WebSocketDisconnect()
    ws.receive_text = recv_then_disconnect

    with patch.object(SSHToolService, '_get_config_record', return_value=fake_config), \
         patch.object(SSHToolService, '_get_column_map', return_value={
             'password': 'password_encrypted',
             'private_key': 'private_key_encrypted',
             'passphrase': 'passphrase_encrypted',
         }), \
         patch('app.services.ssh_tool_service.get_auth_service') as gauth, \
         patch('app.services.ssh_tool_service.EncryptionUtils.decrypt', return_value=None), \
         patch('app.services.ssh_tool_service.paramiko.SSHClient') as SSH:
        auth_svc = MagicMock()
        auth_svc.verify_token_data.return_value = MagicMock(user_id='u1')
        gauth.return_value = auth_svc
        SSH.return_value = ssh_inst

        # 给一个较短的超时,防止真卡住
        await asyncio.wait_for(
            SSHToolService.handle_ssh_session(ws, 'cfg-x', 'fake-token'),
            timeout=15.0,
        )

    ssh_inst.close.assert_called_once()


@pytest.mark.asyncio
async def test_transport_keepalive_is_set_after_connect():
    """ssh.connect 成功后必须调用 transport.set_keepalive(30),防止 server TCP idle 切断"""
    ws = FakeWebSocket()

    fake_config = {
        'id': 'cfg-x', 'host': 'h', 'port': 22, 'username': 'u',
        'password_encrypted': None, 'private_key_encrypted': None, 'passphrase_encrypted': None,
    }

    channel = MagicMock()
    channel.recv.side_effect = TimeoutError("timed out")
    channel.exit_status_ready.side_effect = [False, True]
    channel.settimeout = MagicMock()

    transport = MagicMock()
    ssh_inst = MagicMock()
    ssh_inst.invoke_shell.return_value = channel
    ssh_inst.get_transport.return_value = transport

    async def recv_then_disconnect():
        await asyncio.sleep(0.05)
        from fastapi import WebSocketDisconnect
        raise WebSocketDisconnect()
    ws.receive_text = recv_then_disconnect

    with patch.object(SSHToolService, '_get_config_record', return_value=fake_config), \
         patch.object(SSHToolService, '_get_column_map', return_value={
             'password': 'password_encrypted',
             'private_key': 'private_key_encrypted',
             'passphrase': 'passphrase_encrypted',
         }), \
         patch('app.services.ssh_tool_service.get_auth_service') as gauth, \
         patch('app.services.ssh_tool_service.EncryptionUtils.decrypt', return_value=None), \
         patch('app.services.ssh_tool_service.paramiko.SSHClient') as SSH:
        auth_svc = MagicMock()
        auth_svc.verify_token_data.return_value = MagicMock(user_id='u1')
        gauth.return_value = auth_svc
        SSH.return_value = ssh_inst

        await asyncio.wait_for(
            SSHToolService.handle_ssh_session(ws, 'cfg-x', 'fake-token'),
            timeout=15.0,
        )

    transport.set_keepalive.assert_called_once_with(30)
    channel.settimeout.assert_called_once_with(5.0)
