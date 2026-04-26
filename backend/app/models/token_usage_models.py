"""Token Usage Records 数据库模型 — 多设备、按日期/模型维度的 Token 消耗统计"""

from sqlalchemy import (
    Column,
    String,
    BigInteger,
    Integer,
    Date,
    DateTime,
    Text,
    UniqueConstraint,
    Index,
    Numeric,
    func,
)

from app.models.base import Base


class TokenUsageRecord(Base):
    __tablename__ = "token_usage_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    device_id = Column(String(128), nullable=False, index=True)
    record_date = Column(Date, nullable=False, index=True)
    source = Column(String(32), nullable=False)  # 'claude' | 'opencode'
    model = Column(String(128), nullable=False)
    input_tokens = Column(BigInteger, nullable=False, default=0)
    output_tokens = Column(BigInteger, nullable=False, default=0)
    cache_creation_tokens = Column(BigInteger, nullable=False, default=0)
    cache_read_tokens = Column(BigInteger, nullable=False, default=0)
    total_tokens = Column(BigInteger, nullable=False, default=0)
    total_cost = Column(Numeric(12, 4), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "device_id", "record_date", "source", "model"),
        Index("idx_token_usage_query", "user_id", "record_date", "source", "device_id"),
    )


class TokenUsageSyncLog(Base):
    __tablename__ = "token_usage_sync_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    device_id = Column(String(128), nullable=False)
    source = Column(String(32), nullable=False)
    sync_date = Column(Date, nullable=False)
    status = Column(String(32), nullable=False)  # 'success' | 'failed' | 'partial'
    records_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "device_id", "source", "sync_date"),
    )
