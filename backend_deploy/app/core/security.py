"""
安全模块 - API Key 加密/解密
使用 AES-256-GCM 算法
"""

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import os
from app.config.config import settings


# 使用现有的数据库加密密钥
# 如果不存在则使用默认密钥（仅开发环境）
MASTER_KEY_HEX = settings.DB_ENCRYPTION_KEY
if not MASTER_KEY_HEX:
    raise ValueError("DB_ENCRYPTION_KEY configuration is required")

# 转换密钥为 bytes（如果密钥是 base64 编码，先解码）
try:
    # 尝试作为 hex 解码
    MASTER_KEY = bytes.fromhex(MASTER_KEY_HEX)
except ValueError:
    # 如果不是 hex，尝试作为 base64 解码
    MASTER_KEY = base64.b64decode(MASTER_KEY_HEX)

# 确保密钥长度为 32 字节
if len(MASTER_KEY) != 32:
    # 使用 SHA256 哈希密钥到 32 字节
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"product-manager-agent-salt",
        iterations=100000,
    )
    MASTER_KEY = kdf.derive(MASTER_KEY)


def encrypt_api_key(plaintext_api_key: str) -> str:
    """
    使用 AES-256-GCM 加密 API Key

    Args:
        plaintext_api_key: 明文 API Key

    Returns:
        base64 编码的加密字符串 (iv + ciphertext + tag)
    """
    # 生成随机 IV (12 bytes for GCM)
    iv = os.urandom(12)

    # 创建 AESGCM 实例
    aesgcm = AESGCM(MASTER_KEY)

    # 加密数据
    plaintext_bytes = plaintext_api_key.encode("utf-8")
    ciphertext = aesgcm.encrypt(iv, plaintext_bytes, None)

    # iv (12 bytes) + ciphertext (includes tag)
    encrypted_data = iv + ciphertext

    # 返回 base64 编码的字符串
    return base64.b64encode(encrypted_data).decode("utf-8")


def decrypt_api_key(encrypted_api_key: str) -> str:
    """
    解密 API Key

    Args:
        encrypted_api_key: base64 编码的加密字符串

    Returns:
        明文 API Key
    """
    # 解码 base64
    encrypted_data = base64.b64decode(encrypted_api_key.encode("utf-8"))

    # 提取 iv (前12字节)
    iv = encrypted_data[:12]
    ciphertext = encrypted_data[12:]

    # 创建 AESGCM 实例
    aesgcm = AESGCM(MASTER_KEY)

    # 解密
    plaintext_bytes = aesgcm.decrypt(iv, ciphertext, None)

    return plaintext_bytes.decode("utf-8")
