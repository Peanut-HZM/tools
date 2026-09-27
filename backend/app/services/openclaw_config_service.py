"""
OpenClaw 配置管理服务
管理 Gateway 连接配置的持久化和热加载

加密密钥（key-in-DB）：与 LLM API Key 主密钥同机制，存放在共享数据库
app_secrets 表（key_id='openclaw_master_key'），首次使用时自动生成，
多环境天然一致。历史密文（旧环境变量 / 硬编码默认密钥加密）解密时自动
降级兼容，重新保存配置后即迁移到新密钥。
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
from cryptography.fernet import Fernet, InvalidToken
from app.config.database import get_pooled_db_connection, release_db_connection

logger = logging.getLogger(__name__)

# 历史遗留密钥来源（仅用于解密旧数据，不再用于加密新数据）
_LEGACY_DEFAULT_KEY = "openclaw-default-key-32bytes!!"


def _fernet_from_str(key_str: str) -> Fernet:
    """由字符串派生 Fernet 实例（与旧版 _get_encryption_key 逻辑一致）"""
    key_bytes = key_str.encode("utf-8")
    if len(key_bytes) < 32:
        key_bytes = key_bytes.ljust(32, b"\0")
    elif len(key_bytes) > 32:
        key_bytes = key_bytes[:32]
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def _get_cipher() -> Fernet:
    """当前密钥的 Fernet 实例（key-in-DB，懒加载）"""
    from app.core.app_secrets import get_or_create_secret

    return Fernet(base64.urlsafe_b64encode(get_or_create_secret("openclaw_master_key", 32)))


def _legacy_ciphers() -> list:
    """历史密钥的 Fernet 实例列表（按优先级：环境变量 → 硬编码默认值）"""
    ciphers = []
    env_key = os.environ.get("OPENCLAW_ENCRYPTION_KEY")
    if env_key:
        ciphers.append(_fernet_from_str(env_key))
    ciphers.append(_fernet_from_str(_LEGACY_DEFAULT_KEY))
    return ciphers


ENCRYPTED_KEYS = {"password"}  # 需要加密的字段


def encrypt_value(value: str) -> str:
    """加密值（始终使用当前 key-in-DB 密钥）"""
    if not value:
        return value
    return _get_cipher().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str) -> str:
    """解密值

    优先用当前 key-in-DB 密钥；失败时降级尝试历史密钥（旧数据平滑迁移），
    并提示重新保存以完成迁移；全部失败时保持旧行为原样返回。
    """
    if not value:
        return value
    try:
        return _get_cipher().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        pass
    except Exception:
        # 可能是未加密的旧数据，直接返回
        return value
    for legacy in _legacy_ciphers():
        try:
            plain = legacy.decrypt(value.encode("utf-8")).decode("utf-8")
            _warn_legacy_once()
            return plain
        except InvalidToken:
            continue
        except Exception:
            break
    logger.error("OpenClaw 配置解密失败（所有已知密钥均不匹配），将原样返回")
    return value


_legacy_warned = False


def _warn_legacy_once():
    """历史密钥命中提示只打一次，避免轮询日志刷屏"""
    global _legacy_warned
    if not _legacy_warned:
        _legacy_warned = True
        logger.warning(
            "OpenClaw 配置使用历史密钥解密成功，请在 OpenClaw 管理页重新保存以迁移到新密钥"
        )


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
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    def get_config(self) -> Dict[str, str]:
        """获取所有配置"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

    def update_config(self, data: Dict[str, str]) -> Dict[str, str]:
        """批量更新配置"""
        conn = None
        try:
            conn = get_pooled_db_connection()
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
                release_db_connection(conn)

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
