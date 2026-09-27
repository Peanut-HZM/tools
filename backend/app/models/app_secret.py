"""
应用级密钥表

存放跨环境必须一致的应用密钥（如 LLM API Key 的主加密密钥）。
背景：主密钥此前放在各环境 .env 的 DB_ENCRYPTION_KEY 中，而密文存放在
共享数据库 —— 多设备/多部署各自持钥，先写入的密文在其他环境永远解不开。
主密钥入库后，密钥跟着数据库走，任何能连接同一数据库的环境天然拿到同一把钥匙。

密钥一旦生成不应修改（修改等于销毁所有用它加密的数据）；如需轮换，
应新增 key_id 并重加密存量密文。
"""
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func

from .base import Base


class AppSecret(Base):
    """应用级密钥表（key-value，key_id 唯一）"""

    __tablename__ = "app_secrets"

    key_id = Column(String(64), primary_key=True)
    # hex 编码的随机字节串（如 32 字节 = 64 字符）
    secret_value = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )

    def __repr__(self):
        return f"<AppSecret(key_id={self.key_id})>"
