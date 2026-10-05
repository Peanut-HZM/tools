"""狼人杀对局记录模型（仅结算结果落库，运行时房间状态不落库）"""
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class WerewolfGameRecord(Base):
    __tablename__ = "werewolf_game_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(String(16), nullable=False, index=True)
    board_name = Column(String(64), nullable=False)
    player_count = Column(Integer, nullable=False)
    winner = Column(String(16), nullable=False)          # VILLAGER / WEREWOLF
    day_count = Column(Integer, nullable=False, default=1)
    duration_seconds = Column(Integer, nullable=False, default=0)
    config = Column(JSON, nullable=False, default=dict)  # 板子角色与对局配置
    created_at = Column(DateTime, server_default=func.now())

    players = relationship("WerewolfGameRecordPlayer", back_populates="record",
                           cascade="all, delete-orphan", lazy="joined")


class WerewolfGameRecordPlayer(Base):
    __tablename__ = "werewolf_game_record_players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("werewolf_game_records.id"),
                       nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    nickname = Column(String(64), nullable=False)
    role = Column(String(16), nullable=False)
    alive_at_end = Column(Boolean, nullable=False, default=False)
    is_winner = Column(Boolean, nullable=False, default=False)

    record = relationship("WerewolfGameRecord", back_populates="players")
