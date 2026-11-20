"""Neo4j 连接密码的 Fernet 加解密。

密钥从环境变量 NEO4J_CRYPTO_KEY 读取（Fernet 32-byte urlsafe base64）。
密钥缺失时 is_configured() 为 False，加解密抛 RuntimeError ——
对应设计文档：不自动随机生成 key，避免重启后无法解密已有数据。
"""
import os
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_ENV_KEY = "NEO4J_CRYPTO_KEY"
_fernet: Fernet | None = None
_fernet_loaded = False


def _load() -> Fernet:
    global _fernet, _fernet_loaded
    if not _fernet_loaded:
        _fernet_loaded = True
        raw = os.getenv(_ENV_KEY)
        if raw:
            try:
                _fernet = Fernet(raw.encode())
            except Exception:  # noqa: BLE001 - 非法 key 统一视为未配置
                logger.error("NEO4J_CRYPTO_KEY 不是合法的 Fernet key，Neo4j 密码加解密不可用")
                _fernet = None
    if _fernet is None:
        raise RuntimeError("NEO4J_CRYPTO_KEY 未配置或非法，Neo4j 连接密码不可用")
    return _fernet


def is_configured() -> bool:
    try:
        _load()
        return True
    except RuntimeError:
        return False


def encrypt_password(plain: str) -> str:
    return _load().encrypt(plain.encode()).decode()


def decrypt_password(cipher: str) -> str:
    try:
        return _load().decrypt(cipher.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("密码密文无法解密（密钥可能已更换），请重新录入密码") from exc
