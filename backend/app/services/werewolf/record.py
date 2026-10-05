"""对局结算落库"""
import logging

from app.models.base import SessionLocal
from app.models.werewolf import WerewolfGameRecord, WerewolfGameRecordPlayer

logger = logging.getLogger(__name__)


def save_game_record(summary: dict) -> int:
    """对局结束一次性写入记录表，返回 record_id"""
    db = SessionLocal()
    try:
        rec = WerewolfGameRecord(
            room_id=summary["room_id"], board_name=summary["board_name"],
            player_count=summary["player_count"], winner=summary["winner"],
            day_count=summary["day_count"],
            duration_seconds=summary["duration_seconds"],
            config=summary["config"],
        )
        db.add(rec)
        db.flush()
        for pl in summary["players"]:
            db.add(WerewolfGameRecordPlayer(record_id=rec.id, **pl))
        db.commit()
        logger.info("[werewolf] 对局落库成功 record_id=%s room=%s winner=%s",
                    rec.id, summary["room_id"], summary["winner"])
        return rec.id
    except Exception:
        db.rollback()
        logger.exception("[werewolf] 对局落库失败 room=%s", summary.get("room_id"))
        raise
    finally:
        db.close()
