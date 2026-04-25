"""
OpenClaw 配置管理服务
管理 Gateway 连接配置的持久化和热加载
"""
import json
import logging
import uuid
import os
import base64
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from cryptography.fernet import Fernet
from app.config.database import get_db_connection

logger = logging.getLogger(__name__)

# 加密密钥（从环境变量读取或使用固定密钥）
def _get_encryption_key() -> bytes:
    """获取加密密钥，至少 32 字节"""
    key = os.environ.get("OPENCLAW_ENCRYPTION_KEY", "openclaw-default-key-32bytes!!")
    # 确保密钥长度为 32 字节（Fernet 要求）
    key_bytes = key.encode("utf-8")
    if len(key_bytes) < 32:
        key_bytes = key_bytes.ljust(32, b"\0")
    elif len(key_bytes) > 32:
        key_bytes = key_bytes[:32]
    return base64.urlsafe_b64encode(key_bytes)

_cipher = Fernet(_get_encryption_key())

ENCRYPTED_KEYS = {"password"}  # 需要加密的字段


def encrypt_value(value: str) -> str:
    """加密值"""
    if not value:
        return value
    return _cipher.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str) -> str:
    """解密值"""
    if not value:
        return value
    try:
        return _cipher.decrypt(value.encode("utf-8")).decode("utf-8")
    except Exception:
        # 可能是未加密的旧数据，直接返回
        return value


DEFAULT_CONFIGS = {
    "gateway_url": "ws://127.0.0.1:18081",
    "auth_mode": "token",
    "username": "",
    "password": "",
    "token": "",
    "enabled": "true",
}


class OpenClawConfigService:
    """OpenClaw 配置管理服务（单例）"""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS openclaw_configs (
                        id VARCHAR(36) PRIMARY KEY,
                        config_key VARCHAR(50) UNIQUE NOT NULL,
                        config_value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 插入默认配置
                for key, value in DEFAULT_CONFIGS.items():
                    cur.execute(
                        """
                        INSERT INTO openclaw_configs (id, config_key, config_value)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (config_key) DO NOTHING
                        """,
                        (str(uuid.uuid4()), key, value),
                    )
            conn.commit()
            logger.info("OpenClaw configs table initialized")
        except Exception as e:
            logger.error(f"OpenClaw config table initialization failed: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def get_config(self) -> Dict[str, str]:
        """获取所有配置"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT config_key, config_value FROM openclaw_configs")
                rows = cur.fetchall()
                config = {}
                for row in rows:
                    key = row["config_key"]
                    value = row["config_value"]
                    # 解密敏感字段
                    if key in ENCRYPTED_KEYS:
                        value = decrypt_value(value)
                    config[key] = value
                return config
        except Exception as e:
            logger.error(f"Failed to load OpenClaw config: {e}")
            return DEFAULT_CONFIGS.copy()
        finally:
            if conn:
                conn.close()

    def update_config(self, data: Dict[str, str]) -> Dict[str, str]:
        """批量更新配置"""
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                for key, value in data.items():
                    if key in DEFAULT_CONFIGS:
                        # 加密敏感字段
                        store_value = encrypt_value(value) if key in ENCRYPTED_KEYS else value
                        cur.execute(
                            """
                            UPDATE openclaw_configs
                            SET config_value = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE config_key = %s
                            """,
                            (store_value, key),
                        )
                conn.commit()
            logger.info(f"OpenClaw config updated: {list(data.keys())}")
            return self.get_config()
        except Exception as e:
            logger.error(f"Failed to update OpenClaw config: {e}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def is_enabled(self) -> bool:
        """检查功能是否启用"""
        config = self.get_config()
        return config.get("enabled", "true").lower() == "true"


def is_encrypted(value: str) -> bool:
    """检查值是否已加密"""
    if not value:
        return False
    try:
        decrypted = decrypt_value(value)
        return decrypted != value
    except Exception:
        return False


# 全局单例
openclaw_config_service = OpenClawConfigService()
