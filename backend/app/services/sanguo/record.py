"""三国杀对局记录落库与查询（独立表 sanguo_game_records）"""
import logging

from sqlalchemy import desc

from app.models.base import SessionLocal
from app.models.sanguo import SanguoGameRecord

logger = logging.getLogger(__name__)

LIST_COLUMNS = ("id", "room_id", "board_name", "player_count", "winner",
                "turn_count", "duration_seconds", "created_at")


def save_game_record(summary: dict) -> int:
    db = SessionLocal()
    try:
        rec = SanguoGameRecord(
            room_id=summary["room_id"], board_name=summary["board_name"],
            player_count=summary["player_count"], winner=summary["winner"],
            turn_count=summary["turn_count"],
            duration_seconds=summary["duration_seconds"],
            config=summary["config"], timeline=summary.get("timeline"),
        )
        db.add(rec)
        db.commit()
        logger.info("[sanguo] 对局落库成功 id=%s room=%s winner=%s",
                    rec.id, summary["room_id"], summary["winner"])
        return rec.id
    except Exception:
        db.rollback()
        logger.exception("[sanguo] 对局落库失败 room=%s", summary.get("room_id"))
        raise
    finally:
        db.close()


def list_records(limit: int = 20, offset: int = 0) -> dict:
    db = SessionLocal()
    try:
        query = db.query(SanguoGameRecord).order_by(desc(SanguoGameRecord.id))
        total = query.count()
        rows = query.offset(offset).limit(min(limit, 50)).all()
        records = []
        for r in rows:
            item = {col: getattr(r, col) for col in LIST_COLUMNS}
            item["created_at"] = r.created_at.isoformat() if r.created_at else None
            records.append(item)
        return {"total": total, "records": records}
    finally:
        db.close()


def get_record(record_id: int) -> dict | None:
    db = SessionLocal()
    try:
        r = db.query(SanguoGameRecord).get(record_id)
        if r is None:
            return None
        return {"record": {
            "id": r.id, "room_id": r.room_id, "board_name": r.board_name,
            "player_count": r.player_count, "winner": r.winner,
            "turn_count": r.turn_count, "duration_seconds": r.duration_seconds,
            "config": r.config, "timeline": r.timeline,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }}
    finally:
        db.close()
