"""
安全模块 - API Key 加密/解密
使用 AES-256-GCM 算法

主密钥管理（key-in-DB，根治多环境密钥不一致）：
    主密钥不再来自各环境 .env 的 DB_ENCRYPTION_KEY，而是存放在共享数据库
    app_secrets 表（key_id='llm_master_key'），首次使用时自动生成。
    任何能连接同一数据库的环境都会取到同一把主密钥，密文天然互通。
    特殊场景（测试 / 显式固定密钥）可通过 TOOLBOX_APP_SECRET_HEX 指定，
    详见 app/core/app_secrets.py。

密文格式：
    v1:<base64(iv[12] + ciphertext + tag)>
    带版本前缀便于将来密钥轮换；读取时兼容无前缀的历史密文（用当前
    主密钥解密，解不开由调用方处理）。
"""

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import os

from app.core.app_secrets import get_or_create_secret

# 主密钥在 app_secrets 表中的 key_id
LLM_MASTER_KEY_ID = "llm_master_key"

# 密文版本前缀
_VERSION_PREFIX = "v1:"


def _load_master_key() -> bytes:
    """加载主密钥（app_secrets 懒加载，进程内缓存）"""
    key = get_or_create_secret(LLM_MASTER_KEY_ID, 32)
    if len(key) != 32:
        raise RuntimeError("llm_master_key 长度异常，应为 32 字节")
    return key


def encrypt_api_key(plaintext_api_key: str) -> str:
    """
    使用 AES-256-GCM 加密 API Key

    Args:
        plaintext_api_key: 明文 API Key

    Returns:
        "v1:" 前缀 + base64 编码的加密字符串 (iv + ciphertext + tag)
    """
    iv = os.urandom(12)
    aesgcm = AESGCM(_load_master_key())
    plaintext_bytes = plaintext_api_key.encode("utf-8")
    ciphertext = aesgcm.encrypt(iv, plaintext_bytes, None)
    # iv (12 bytes) + ciphertext (includes tag)
    return _VERSION_PREFIX + base64.b64encode(iv + ciphertext).decode("utf-8")


def decrypt_api_key(encrypted_api_key: str) -> str:
    """
    解密 API Key

    Args:
        encrypted_api_key: "v1:" 前缀（可选）+ base64 编码的加密字符串

    Returns:
        明文 API Key
    """
    data = encrypted_api_key
    if data.startswith(_VERSION_PREFIX):
        data = data[len(_VERSION_PREFIX):]

    encrypted_data = base64.b64decode(data.encode("utf-8"))
    # 提取 iv (前12字节)
    iv = encrypted_data[:12]
    ciphertext = encrypted_data[12:]

    aesgcm = AESGCM(_load_master_key())
    plaintext_bytes = aesgcm.decrypt(iv, ciphertext, None)
    return plaintext_bytes.decode("utf-8")
