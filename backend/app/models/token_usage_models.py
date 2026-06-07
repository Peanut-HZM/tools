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
    source_raw = Column(String(128), nullable=True)
    tool_id = Column(String(64), nullable=True, index=True)
    tool_name = Column(String(128), nullable=True)
    model = Column(String(128), nullable=False)
    model_display_name = Column(String(128), nullable=True)
    device_name = Column(String(128), nullable=True)
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
        Index(
            "idx_token_usage_dimensions",
            "user_id",
            "record_date",
            "tool_id",
            "device_id",
            "model",
        ),
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


class DeviceRegistry(Base):
    """设备注册表 — 管理设备 ID 与显示名称的映射"""
    __tablename__ = "device_registry"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    device_id = Column(String(128), nullable=False)
    display_name = Column(String(128), nullable=True)  # 用户自定义名称
    default_display_name = Column(String(128), nullable=True)  # 注册时捕获的原始设备名
    device_fingerprint = Column(String(256), nullable=True)
    fingerprint_version = Column(Integer, nullable=False, default=0)
    id_type = Column(String(16), nullable=False, default="uuid")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "device_id"),
        Index("idx_device_registry_fingerprint", "user_id", "device_fingerprint"),
    )


class DeviceIdAlias(Base):
    """设备 ID 别名映射 — 用于复用/合并同一物理设备的多个 UUID"""
    __tablename__ = "device_id_alias"

    alias_device_id = Column(String(128), primary_key=True)
    canonical_device_id = Column(String(128), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_device_alias_user", "user_id", "canonical_device_id"),
    )


class DeviceMergeLog(Base):
    """设备合并日志 — 记录手动合并/复用操作"""
    __tablename__ = "device_merge_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    source_device_id = Column(String(128), nullable=False)
    target_device_id = Column(String(128), nullable=False)
    merged_at = Column(DateTime(timezone=True), server_default=func.now())
    record_count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_device_merge_log_user", "user_id", "merged_at"),
    )
