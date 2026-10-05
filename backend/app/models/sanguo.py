"""三国杀对局记录模型"""
from sqlalchemy import JSON, Column, DateTime, Integer, String, func

from app.models.base import Base


class SanguoGameRecord(Base):
    __tablename__ = "sanguo_game_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(String(16), nullable=False, index=True)
    board_name = Column(String(64), nullable=False, default="4人身份局")
    player_count = Column(Integer, nullable=False)
    winner = Column(String(16), nullable=False)       # LORD / REBEL / SPY
    turn_count = Column(Integer, nullable=False, default=1)
    duration_seconds = Column(Integer, nullable=False, default=0)
    config = Column(JSON, nullable=False, default=dict)
    timeline = Column(JSON, nullable=True)            # 对局过程回放
    created_at = Column(DateTime, server_default=func.now())
