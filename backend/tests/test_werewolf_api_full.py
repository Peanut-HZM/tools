"""HTTP API 全场景验收：正常路径 + 全部错误路径"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.auth import get_current_user_id
from app.services.werewolf import manager as manager_module
from app.services.werewolf.manager import RoomManager


@pytest.fixture()
def client():
    manager_module.manager = RoomManager()
    import app.routes.werewolf as wr
    wr.manager = manager_module.manager
    app.dependency_overrides[get_current_user_id] = lambda: "1"
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def as_user(uid):
    app.dependency_overrides[get_current_user_id] = lambda: uid


def make_room(client, board="6p"):
    return client.post("/api/games/werewolf/rooms", json={"board_id": board}).json()["room_id"]


def full_join(client, room_id, count=6):
    for uid in range(2, count + 1):
        as_user(str(uid))
        client.post(f"/api/games/werewolf/rooms/{room_id}/join")
    as_user("1")


# ---------- 认证 ----------
def test_all_endpoints_require_auth(client):
    app.dependency_overrides.pop(get_current_user_id, None)
    assert client.get("/api/games/werewolf/boards").status_code == 401
    assert client.post("/api/games/werewolf/rooms", json={"board_id": "6p"}).status_code == 401
    assert client.get("/api/games/werewolf/rooms/123456").status_code == 401


# ---------- 创建与校验 ----------
def test_create_rejects_unknown_board(client):
    assert client.post("/api/games/werewolf/rooms", json={"board_id": "99p"}).status_code == 422


def test_create_rejects_no_board_specified(client):
    assert client.post("/api/games/werewolf/rooms", json={}).status_code == 422


def test_create_custom_board_with_warnings_ok(client):
    res = client.post("/api/games/werewolf/rooms",
                      json={"custom_roles": {"WEREWOLF": 2, "WITCH": 1, "VILLAGER": 4},
                            "board_name": "7人无预言家"})
    assert res.status_code == 200
    view = client.get(f"/api/games/werewolf/rooms/{res.json()['room_id']}").json()
    assert view["board"]["name"] == "7人无预言家"
    assert view["board"]["player_count"] == 7


@pytest.mark.parametrize("roles", [
    {"WEREWOLF": 1, "VILLAGER": 4},                # 5 人不足
    {"WEREWOLF": 1, "VILLAGER": 12},               # 13 人超限
    {"VILLAGER": 6},                                # 无狼
    {"WEREWOLF": 1, "SEER": 2, "VILLAGER": 4},     # 预言家超 1
    {"WEREWOLF": 1, "WITCH": 3, "VILLAGER": 3},    # 女巫超 1
    {"FOO": 1, "VILLAGER": 6},                      # 未知角色
    {"WEREWOLF": -1, "VILLAGER": 8},                # 负数
])
def test_create_custom_board_rejects_invalid(client, roles):
    assert client.post("/api/games/werewolf/rooms",
                       json={"custom_roles": roles}).status_code == 422


def test_create_rejects_bad_speech_seconds(client):
    assert client.post("/api/games/werewolf/rooms",
                       json={"board_id": "6p", "speech_seconds": 10}).status_code == 422
    assert client.post("/api/games/werewolf/rooms",
                       json={"board_id": "6p", "witch_self_rescue": "sometimes"}
                       ).status_code == 422


# ---------- 加入/离开 ----------
def test_join_full_room_rejected(client):
    room_id = make_room(client)
    full_join(client, room_id)
    as_user("88")
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/join").status_code == 409


def test_join_started_room_rejected(client):
    room_id = make_room(client)
    full_join(client, room_id)
    client.post(f"/api/games/werewolf/rooms/{room_id}/start")
    as_user("88")
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/join").status_code == 409


def test_join_twice_is_idempotent(client):
    room_id = make_room(client)
    as_user("2")
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/join").status_code == 200
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/join").status_code == 200
    as_user("1")
    assert len(client.get(f"/api/games/werewolf/rooms/{room_id}").json()["members"]) == 2


def test_join_invalid_room_id_format_404(client):
    as_user("2")
    assert client.post("/api/games/werewolf/rooms/abc123/join").status_code == 404


def test_leave_missing_room_404(client):
    as_user("2")
    assert client.post("/api/games/werewolf/rooms/000001/leave").status_code == 404


# ---------- 权限 ----------
def test_kick_requires_host_and_valid_target(client):
    room_id = make_room(client)
    as_user("2")
    client.post(f"/api/games/werewolf/rooms/{room_id}/join")
    as_user("2")
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/kick",
                       json={"user_id": "3"}).status_code == 403  # 非房主
    as_user("1")
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/kick",
                       json={"user_id": "1"}).status_code == 403  # 踢自己
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/kick",
                       json={"user_id": "999"}).status_code == 200  # 踢不存在的人幂等
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/kick",
                       json={"user_id": "2"}).status_code == 200


def test_config_requires_host(client):
    room_id = make_room(client)
    as_user("2")
    client.post(f"/api/games/werewolf/rooms/{room_id}/join")
    as_user("2")
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/config",
                       json={"speech_seconds": 90}).status_code == 403


def test_dismiss_requires_host_then_room_gone(client):
    room_id = make_room(client)
    as_user("2")
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/dismiss").status_code == 403
    as_user("1")
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/dismiss").status_code == 200
    assert client.get(f"/api/games/werewolf/rooms/{room_id}").status_code == 404
    as_user("2")
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/join").status_code == 404


# ---------- 开始/重开 ----------
def test_replay_requires_host_and_finished_game(client):
    room_id = make_room(client)
    full_join(client, room_id)
    client.post(f"/api/games/werewolf/rooms/{room_id}/start")
    as_user("2")
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/replay").status_code == 403
    as_user("1")
    assert client.post(f"/api/games/werewolf/rooms/{room_id}/replay").status_code == 403  # 未结束


def test_start_missing_room_404(client):
    assert client.post("/api/games/werewolf/rooms/000001/start").status_code == 404


# ---------- 快照权限 ----------
def test_snapshot_forbidden_for_non_member_when_playing(client):
    room_id = make_room(client)
    full_join(client, room_id)
    client.post(f"/api/games/werewolf/rooms/{room_id}/start")
    as_user("99")
    assert client.get(f"/api/games/werewolf/rooms/{room_id}").status_code == 403
