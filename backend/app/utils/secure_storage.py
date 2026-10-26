"""
统一安全存储工具（新增于数据加密整改）

目标：
    为「非 LLM 主密钥链路」的敏感数据提供统一的「密文入库 / 明文读取」能力，
    与 app/core/security.py（LLM API Key，master_key=llm_master_key）、
    app/utils/encryption.py（Fernet，key 存 system_settings.db_encryption_key）
    并存但语义独立，避免各模块各自造轮子。

密文格式：
    enc:v1:<base64(Fernet密文)>
    前缀 enc:v1: 是权威标记 —— 判定「是否密文」只看前缀，不靠 try/except 猜测，
    因此不存在「解密失败就悄悄返回原文」这类兜底行为：
      * 带前缀且解密成功 → 返回明文
      * 带前缀且解密失败 → 抛 SecureStorageError（真实报错，绝不吞掉）
      * 无前缀            → 视为历史明文数据，原样返回（明确的兼容分支）

主密钥：
    存放在 app_secrets 表（key_id='secure_storage_master_key'），
    与 app/core/app_secrets.py 的 key-in-DB 机制一致，多环境天然一致。
"""
import base64
import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# 密文版本前缀（权威标记）
CIPHER_PREFIX = "enc:v1:"

# 主密钥在 app_secrets 表中的 key_id
MASTER_KEY_ID = "secure_storage_master_key"


class SecureStorageError(Exception):
    """安全存储异常（密文损坏 / 密钥不匹配 / 密钥长度异常）"""


def _get_cipher() -> Fernet:
    """获取 Fernet 实例（主密钥 key-in-DB，进程内缓存由 app_secrets 负责）"""
    from app.core.app_secrets import get_or_create_secret

    key = get_or_create_secret(MASTER_KEY_ID, 32)
    if len(key) != 32:
        raise SecureStorageError(f"主密钥长度异常：期望 32 字节，实际 {len(key)} 字节")
    return Fernet(base64.urlsafe_b64encode(key))


def is_encrypted(value: str) -> bool:
    """判断字符串是否为本模块产出的密文（只看前缀）"""
    return bool(value) and value.startswith(CIPHER_PREFIX)


def encrypt_text(plain_text: str) -> str:
    """
    加密文本并加上 enc:v1: 前缀

    Args:
        plain_text: 明文（None/空串原样返回，不产生密文）

    Returns:
        enc:v1:<base64密文>
    """
    if plain_text is None:
        return plain_text
    if plain_text == "":
        return plain_text
    cipher = _get_cipher()
    token = cipher.encrypt(plain_text.encode("utf-8"))
    return CIPHER_PREFIX + base64.urlsafe_b64encode(token).decode("utf-8")


def decrypt_text(stored: str) -> str:
    """
    解密文本

    Args:
        stored: 库中取出的原始值

    Returns:
        明文；无 enc:v1: 前缀时视为历史明文数据原样返回

    Raises:
        SecureStorageError: 带前缀但解密失败（密钥不匹配 / 密文损坏）
    """
    if not stored:
        return stored
    if not stored.startswith(CIPHER_PREFIX):
        # 历史明文数据（加密功能上线前写入），明确兼容分支
        return stored

    payload = stored[len(CIPHER_PREFIX):]
    try:
        raw = base64.urlsafe_b64decode(payload.encode("utf-8"))
    except Exception as e:
        raise SecureStorageError(f"密文 base64 解码失败：{e}") from e

    try:
        cipher = _get_cipher()
        plain = cipher.decrypt(raw)
    except InvalidToken as e:
        raise SecureStorageError(
            "密文解密失败：主密钥与该密文不匹配（可能是密钥被改动或数据跨环境写入），请重新保存该配置"
        ) from e
    except SecureStorageError:
        raise
    except Exception as e:
        raise SecureStorageError(f"密文解密失败：{e}") from e

    return plain.decode("utf-8")
