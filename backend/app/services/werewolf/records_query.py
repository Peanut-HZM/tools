"""对局记录查询服务（回放数据）"""
import logging

from sqlalchemy import desc

from app.models.base import SessionLocal
from app.models.werewolf import WerewolfGameRecord, WerewolfGameRecordPlayer

logger = logging.getLogger(__name__)

LIST_COLUMNS = ("id", "room_id", "board_name", "player_count", "winner",
                "day_count", "duration_seconds", "created_at")


def list_records(limit: int = 20, offset: int = 0) -> dict:
    """对局记录列表（不含 timeline，控制体积）"""
    db = SessionLocal()
    try:
        query = db.query(WerewolfGameRecord).order_by(desc(WerewolfGameRecord.id))
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
    """对局记录详情（含回放时间线与玩家明细）"""
    db = SessionLocal()
    try:
        r = db.query(WerewolfGameRecord).get(record_id)
        if r is None:
            return None
        players = db.query(WerewolfGameRecordPlayer).filter_by(record_id=record_id).all()
        return {
            "record": {
                "id": r.id, "room_id": r.room_id, "board_name": r.board_name,
                "player_count": r.player_count, "winner": r.winner,
                "day_count": r.day_count, "duration_seconds": r.duration_seconds,
                "config": r.config, "timeline": r.timeline,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            },
            "players": [{
                "user_id": p.user_id, "nickname": p.nickname, "role": p.role,
                "alive_at_end": p.alive_at_end, "is_winner": p.is_winner,
            } for p in players],
        }
    finally:
        db.close()
