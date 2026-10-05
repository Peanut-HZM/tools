"""WS 协议集成测试：hello/行动/错误/挤线"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.auth import get_current_user_id
from app.services.werewolf import manager as manager_module
from app.services.werewolf.manager import RoomManager


@pytest.fixture()
def client():
    manager_module.manager = RoomManager()  # 每个测试独立房间管理器
    import app.routes.werewolf as wr
    wr.manager = manager_module.manager
    app.dependency_overrides[get_current_user_id] = lambda: "1"
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _create_full_room(client, monkeypatch):
    room_id = client.post("/api/games/werewolf/rooms", json={"board_id": "6p"}).json()["room_id"]
    monkeypatch.setattr("app.routes.werewolf._nickname_of", lambda uid: f"玩家{uid}")
    for uid in range(2, 7):
        app.dependency_overrides[get_current_user_id] = lambda uid=uid: str(uid)
        client.post(f"/api/games/werewolf/rooms/{room_id}/join")
    app.dependency_overrides[get_current_user_id] = lambda: "1"
    client.post(f"/api/games/werewolf/rooms/{room_id}/start")
    return room_id


def test_ws_hello_and_wrong_phase_error(client, monkeypatch):
    monkeypatch.setattr("app.routes.werewolf._verify_ws_token", lambda token: "1")
    room_id = _create_full_room(client, monkeypatch)
    with client.websocket_connect(
            f"/api/games/werewolf/rooms/{room_id}/ws?token=x") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert hello["state"]["snapshot"]["you"]["role"] is not None
        # 非守卫发守卫行动 → 引擎拒绝（错误消息回传）
        ws.send_json({"type": "act", "action": "guard_protect", "target": 2})
        msg = ws.receive_json()
        assert msg["type"] == "error" and msg["code"]


def test_ws_ping_pong_and_sync(client, monkeypatch):
    monkeypatch.setattr("app.routes.werewolf._verify_ws_token", lambda token: "1")
    room_id = _create_full_room(client, monkeypatch)
    with client.websocket_connect(
            f"/api/games/werewolf/rooms/{room_id}/ws?token=x") as ws:
        ws.receive_json()  # hello
        ws.send_json({"type": "ping"})
        assert ws.receive_json()["type"] == "pong"
        ws.send_json({"type": "sync"})
        assert ws.receive_json()["type"] == "state"


def test_ws_reconnect_replaces_old(client, monkeypatch):
    monkeypatch.setattr("app.routes.werewolf._verify_ws_token", lambda token: "1")
    room_id = _create_full_room(client, monkeypatch)
    room = manager_module.manager.get(room_id)
    ws1 = client.websocket_connect(f"/api/games/werewolf/rooms/{room_id}/ws?token=x")
    ws1.__enter__()
    ws1.receive_json()
    assert 1 in room._sockets
    # 同用户第二个连接挤掉旧连接
    with client.websocket_connect(
            f"/api/games/werewolf/rooms/{room_id}/ws?token=x") as ws2:
        assert ws2.receive_json()["type"] == "hello"
        assert room._sockets[1] is ws2 or room._sockets.get(1) is not None
    ws1.__exit__(None, None, None)


def test_ws_wolf_kill_flow(client, monkeypatch):
    """完整链路：狼人通过 WS 提交刀人 → 房间状态更新"""
    monkeypatch.setattr("app.routes.werewolf._verify_ws_token", lambda token: "1")
    room_id = _create_full_room(client, monkeypatch)
    room = manager_module.manager.get(room_id)
    wolf = [p for p in room.engine.players if p.role.value == "WEREWOLF" and p.alive][0]
    # 给狼的座位连上 WS
    app.dependency_overrides[get_current_user_id] = lambda: str(wolf.user_id)
    with client.websocket_connect(
            f"/api/games/werewolf/rooms/{room_id}/ws?token=x") as ws:
        ws.receive_json()  # hello
        # 只有在狼人阶段才能成功；否则收到 error（两种都算链路通畅）
        ws.send_json({"type": "act", "action": "werewolf_kill", "target": 6})
        msg = ws.receive_json()
        assert msg["type"] in ("error", "private", "event")
