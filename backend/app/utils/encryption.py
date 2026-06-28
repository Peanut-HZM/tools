"""
Author: Peanut
Created: 2026-06-27
Purpose: 加密工具 - 密钥存储在数据库中，确保跨设备部署时密钥一致
"""
from cryptography.fernet import Fernet
from app.config.config import settings
import base64
import hashlib
import logging
import secrets

logger = logging.getLogger(__name__)


class EncryptionUtils:
    _cipher_suite = None
    _key_initialized = False

    @classmethod
    def _get_db_encryption_key(cls) -> str:
        """
        从数据库获取加密密钥。
        如果数据库中还没有密钥，则生成一个并存储。
        密钥来源优先级：数据库 > .env 环境变量
        """
        try:
            from app.config.database import get_pooled_db_connection, release_db_connection

            conn = get_pooled_db_connection()
            try:
                with conn.cursor() as cur:
                    # 确保 system_settings 表存在
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS system_settings (
                            key VARCHAR(255) PRIMARY KEY,
                            value TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """)
                    conn.commit()

                    # 查询是否已有加密密钥
                    cur.execute(
                        "SELECT value FROM system_settings WHERE key = 'db_encryption_key'"
                    )
                    row = cur.fetchone()
                    if row:
                        return row["value"]

                    # 首次运行：生成随机密钥并存储
                    new_key = secrets.token_hex(32)  # 64 字符的十六进制字符串
                    cur.execute(
                        """INSERT INTO system_settings (key, value)
                           VALUES ('db_encryption_key', %s)""",
                        (new_key,),
                    )
                    conn.commit()
                    logger.info("已在数据库中生成并存储新的加密密钥")
                    return new_key
            finally:
                release_db_connection(conn)
        except Exception as e:
            logger.warning(f"从数据库获取加密密钥失败: {e}，回退到 .env 配置")
            # 回退到 .env 中的配置
            return settings.DB_ENCRYPTION_KEY

    @classmethod
    def _get_cipher_suite(cls):
        if cls._cipher_suite is None:
            key = cls._get_db_encryption_key()
            # Fernet key must be 32 url-safe base64-encoded bytes
            try:
                cls._cipher_suite = Fernet(key)
            except ValueError:
                # 如果 key 不是合法的 Fernet key，通过 SHA-256 派生
                m = hashlib.sha256()
                m.update(key.encode("utf-8"))
                derived_key = base64.urlsafe_b64encode(m.digest())
                cls._cipher_suite = Fernet(derived_key)

        return cls._cipher_suite

    @classmethod
    def reset_cipher_suite(cls):
        """重置密钥缓存，用于密钥变更后重新加载"""
        cls._cipher_suite = None

    @classmethod
    def encrypt(cls, plain_text: str) -> str:
        """加密字符串"""
        if not plain_text:
            return ""
        try:
            cipher_suite = cls._get_cipher_suite()
            encrypted_text = cipher_suite.encrypt(plain_text.encode("utf-8"))
            return encrypted_text.decode("utf-8")
        except Exception as e:
            logger.error(f"加密失败: {e}")
            raise

    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        """解密字符串"""
        if not encrypted_text:
            return ""
        try:
            cipher_suite = cls._get_cipher_suite()
            decrypted_text = cipher_suite.decrypt(encrypted_text.encode("utf-8"))
            return decrypted_text.decode("utf-8")
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise
