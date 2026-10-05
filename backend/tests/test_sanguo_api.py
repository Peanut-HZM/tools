"""三国杀 API/房间/WS 集成验收"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.auth import get_current_user_id
from app.services.sanguo import manager as manager_module
from app.services.sanguo.manager import SanguoManager


@pytest.fixture()
def client():
    manager_module.manager = SanguoManager()
    import app.routes.sanguo as sg
    sg.manager = manager_module.manager
    app.dependency_overrides[get_current_user_id] = lambda: "1"
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def as_user(client, uid):
    app.dependency_overrides[get_current_user_id] = lambda: uid


def create_and_full(client, n=4):
    room_id = client.post("/api/games/sanguo/rooms").json()["room_id"]
    for uid in range(2, n + 1):
        as_user(client, str(uid))
        client.post(f"/api/games/sanguo/rooms/{room_id}/join")
    as_user(client, "1")
    return room_id


class TestHttp:
    def test_heroes_list(self, client):
        res = client.get("/api/games/sanguo/heroes")
        assert res.status_code == 200
        heroes = res.json()["heroes"]
        assert len(heroes) == 8

    def test_create_join_start_flow(self, client):
        room_id = create_and_full(client)
        assert client.post(f"/api/games/sanguo/rooms/{room_id}/start").status_code == 200
        view = client.get(f"/api/games/sanguo/rooms/{room_id}").json()
        assert view["status"] == "PLAYING"
        assert view["snapshot"]["you"]["hand"]  # 主公有手牌
        assert view["snapshot"]["you"]["role"]  # 自己身份可见

    def test_join_full_409(self, client):
        room_id = create_and_full(client)
        as_user(client, "88")
        assert client.post(f"/api/games/sanguo/rooms/{room_id}/join").status_code == 409

    def test_join_started_409(self, client):
        room_id = create_and_full(client)
        client.post(f"/api/games/sanguo/rooms/{room_id}/start")
        as_user(client, "88")
        assert client.post(f"/api/games/sanguo/rooms/{room_id}/join").status_code == 409

    def test_start_not_full_400(self, client):
        room_id = client.post("/api/games/sanguo/rooms").json()["room_id"]
        as_user(client, "2")
        client.post(f"/api/games/sanguo/rooms/{room_id}/join")
        as_user(client, "1")
        res = client.post(f"/api/games/sanguo/rooms/{room_id}/start")
        assert res.status_code == 400

    def test_start_requires_host(self, client):
        room_id = create_and_full(client)
        as_user(client, "2")
        assert client.post(f"/api/games/sanguo/rooms/{room_id}/start").status_code == 403

    def test_dismiss_requires_host_then_gone(self, client):
        room_id = create_and_full(client)
        as_user(client, "2")
        assert client.post(f"/api/games/sanguo/rooms/{room_id}/dismiss").status_code == 403
        as_user(client, "1")
        assert client.post(f"/api/games/sanguo/rooms/{room_id}/dismiss").status_code == 200
        assert client.get(f"/api/games/sanguo/rooms/{room_id}").status_code == 404

    def test_snapshot_requires_membership(self, client):
        room_id = create_and_full(client)
        as_user(client, "99")
        assert client.get(f"/api/games/sanguo/rooms/{room_id}").status_code == 403

    def test_auth_required(self, client):
        app.dependency_overrides.pop(get_current_user_id, None)
        assert client.get("/api/games/sanguo/rooms/123456").status_code == 401
        assert client.post("/api/games/sanguo/rooms").status_code == 401

    def test_missing_room_404(self, client):
        assert client.get("/api/games/sanguo/rooms/000001").status_code == 404


class TestRecords:
    def test_records_list_and_detail(self, client):
        from app.services.sanguo.record import save_game_record
        rid = save_game_record({
            "room_id": "444555", "board_name": "4人身份局", "player_count": 4,
            "winner": "REBEL", "turn_count": 3, "duration_seconds": 240,
            "config": {"heroes": ["刘备", "关羽", "张飞", "赵云"]},
            "timeline": {"timeline": [{"seq": 1, "kind": "event", "text": "对局开始"}]},
        })
        res = client.get("/api/games/sanguo/records")
        assert res.status_code == 200
        assert any(r["id"] == rid for r in res.json()["records"])
        res2 = client.get(f"/api/games/sanguo/records/{rid}")
        assert res2.status_code == 200
        assert res2.json()["record"]["winner"] == "REBEL"
        assert res2.json()["record"]["timeline"]["timeline"]

    def test_record_404(self, client):
        assert client.get("/api/games/sanguo/records/99999999").status_code == 404
