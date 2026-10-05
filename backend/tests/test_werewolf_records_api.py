"""对局记录查询 API 验收（列表 + 详情含回放时间线）"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.auth import get_current_user_id
from app.services.werewolf import manager as manager_module
from app.services.werewolf.manager import RoomManager
from app.services.werewolf.record import save_game_record


@pytest.fixture()
def client():
    manager_module.manager = RoomManager()
    import app.routes.werewolf as wr
    wr.manager = manager_module.manager
    app.dependency_overrides[get_current_user_id] = lambda: "1"
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_record():
    rid = save_game_record({
        "room_id": "111222", "board_name": "6人新手局", "player_count": 6,
        "winner": "VILLAGER", "day_count": 2, "duration_seconds": 300,
        "config": {"roles": {"WEREWOLF": 2}},
        "timeline": {
            "events": [{"id": 1, "text": "对局开始"}, {"id": 2, "text": "天亮了，昨夜 3 号 死亡"}],
            "speeches": [{"seat": 4, "nickname": "丁", "content": "我是好人", "day": 1}],
            "votes": [{"day": 1, "kind": "vote", "exiled": 3,
                       "detail": [{"voter": 1, "target": 3}]}],
            "timeline": [{"seq": 1, "kind": "event", "text": "对局开始"}],
        },
        "players": [
            {"user_id": "1", "nickname": "甲", "role": "WEREWOLF",
             "alive_at_end": False, "is_winner": False},
            {"user_id": "2", "nickname": "乙", "role": "SEER",
             "alive_at_end": True, "is_winner": True},
        ],
    })
    return rid


def test_list_records(client, seeded_record):
    res = client.get("/api/games/werewolf/records")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    item = next(r for r in data["records"] if r["id"] == seeded_record)
    assert item["board_name"] == "6人新手局"
    assert item["winner"] == "VILLAGER"
    assert item["player_count"] == 6
    # 列表不带 timeline（体积控制）
    assert "timeline" not in item


def test_record_detail_with_timeline(client, seeded_record):
    res = client.get(f"/api/games/werewolf/records/{seeded_record}")
    assert res.status_code == 200
    data = res.json()
    assert data["record"]["room_id"] == "111222"
    assert len(data["record"]["timeline"]["timeline"]) >= 1
    assert len(data["players"]) == 2
    assert data["players"][0]["role"] == "WEREWOLF"


def test_record_detail_404(client):
    assert client.get("/api/games/werewolf/records/99999999").status_code == 404


def test_records_require_auth(client):
    app.dependency_overrides.pop(get_current_user_id, None)
    assert client.get("/api/games/werewolf/records").status_code == 401
