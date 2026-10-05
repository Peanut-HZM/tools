"""HTTP API 集成测试（依赖注入伪造登录用户）"""
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


def test_get_boards(client):
    res = client.get("/api/games/werewolf/boards")
    assert res.status_code == 200
    data = res.json()
    assert len(data["boards"]) == 5
    assert "speech_seconds" in data["presets"]


def test_create_and_get_room(client):
    res = client.post("/api/games/werewolf/rooms", json={"board_id": "6p"})
    assert res.status_code == 200
    room_id = res.json()["room_id"]
    assert len(str(room_id)) == 6
    res2 = client.get(f"/api/games/werewolf/rooms/{room_id}")
    assert res2.status_code == 200
    view = res2.json()
    assert view["status"] == "WAITING" and view["host_id"] == "1"


def test_custom_board_validation(client):
    res = client.post("/api/games/werewolf/rooms",
                      json={"custom_roles": {"WEREWOLF": 1, "VILLAGER": 20}})
    assert res.status_code == 422


def test_join_leave_flow(client):
    room_id = client.post("/api/games/werewolf/rooms", json={"board_id": "6p"}).json()["room_id"]
    app.dependency_overrides[get_current_user_id] = lambda: "2"
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/join").status_code == 200
    view = client.get(f"/api/games/werewolf/rooms/{room_id}").json()
    assert len(view["members"]) == 2
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/leave").status_code == 200
    view = client.get(f"/api/games/werewolf/rooms/{room_id}").json()
    assert len(view["members"]) == 1


def test_join_missing_room_404(client):
    app.dependency_overrides[get_current_user_id] = lambda: "2"
    assert client.post("/api/games/werewolf/rooms/999999/join").status_code == 404


def test_start_requires_host(client):
    room_id = client.post("/api/games/werewolf/rooms", json={"board_id": "6p"}).json()["room_id"]
    for uid in range(2, 7):
        app.dependency_overrides[get_current_user_id] = lambda uid=uid: str(uid)
        client.post(f"/api/games/werewolf/rooms/{room_id}/join")
    app.dependency_overrides[get_current_user_id] = lambda: "3"
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/start").status_code == 403
    app.dependency_overrides[get_current_user_id] = lambda: "1"
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/start").status_code == 200
    assert client.get(f"/api/games/werewolf/rooms/{room_id}").json()["status"] == "PLAYING"


def test_start_insufficient_players(client):
    room_id = client.post("/api/games/werewolf/rooms", json={"board_id": "6p"}).json()["room_id"]
    # 6 人板只有 2 人 → 拒绝开始
    app.dependency_overrides[get_current_user_id] = lambda: "2"
    client.post(f"/api/games/werewolf/rooms/{room_id}/join")
    app.dependency_overrides[get_current_user_id] = lambda: "1"
    res = client.post(f"/api/games/werewolf/rooms/{room_id}/start")
    assert res.status_code == 400


def test_config_update_by_host(client):
    room_id = client.post("/api/games/werewolf/rooms", json={"board_id": "6p"}).json()["room_id"]
    res = client.post(f"/api/games/werewolf/rooms/{room_id}/config",
                      json={"speech_seconds": 90, "witch_self_rescue": "always"})
    assert res.status_code == 200
    view = client.get(f"/api/games/werewolf/rooms/{room_id}").json()
    assert view["settings"]["speech_seconds"] == 90
    assert view["settings"]["witch_self_rescue"] == "always"
