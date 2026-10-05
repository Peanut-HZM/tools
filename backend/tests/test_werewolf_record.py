"""对局记录落库（sqlite 临时库隔离测试）"""
from app.services.werewolf import record


def test_save_game_record(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.models.werewolf  # noqa: F401 确保表注册
    from app.models.base import Base

    engine = create_engine(f"sqlite:///{tmp_path}/t.db")
    from app.models.werewolf import WerewolfGameRecord, WerewolfGameRecordPlayer
    # 只建本模块两张表：Base 全量元数据含 JSONB 模型，sqlite 无法渲染
    Base.metadata.create_all(
        engine,
        tables=[WerewolfGameRecord.__table__, WerewolfGameRecordPlayer.__table__])
    TestSession = sessionmaker(bind=engine)
    monkeypatch.setattr(record, "SessionLocal", TestSession)

    rid = record.save_game_record({
        "room_id": "123456", "board_name": "6人新手局", "player_count": 6,
        "winner": "VILLAGER", "day_count": 2, "duration_seconds": 600,
        "config": {"witch_self_rescue": "never"},
        "timeline": {"events": [{"id": 1, "text": "对局开始"}], "speeches": [],
                     "votes": [], "timeline": [{"seq": 1, "kind": "event",
                                                "text": "对局开始"}]},
        "players": [
            {"user_id": "1", "nickname": "甲", "role": "WEREWOLF",
             "alive_at_end": False, "is_winner": False},
            {"user_id": "2", "nickname": "乙", "role": "SEER",
             "alive_at_end": True, "is_winner": True},
        ],
    })
    assert rid > 0
    with TestSession() as db:
        from app.models.werewolf import WerewolfGameRecord, WerewolfGameRecordPlayer
        rec = db.query(WerewolfGameRecord).get(rid)
        assert rec.winner == "VILLAGER"
        assert rec.players[0].nickname == "甲"
        assert rec.timeline["timeline"][0]["text"] == "对局开始"
        assert db.query(WerewolfGameRecordPlayer).count() == 2
