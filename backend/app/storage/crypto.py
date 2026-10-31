"""
本地文件密钥加密器

与服务器 EncryptionUtils 完全分离：
- 服务器 EncryptionUtils 的密钥存在数据库 system_settings 表
- 本地 LocalEncryption 的密钥存在本机 ~/.toolbox/encryption.key

两把密钥物理隔离，密文即便被复制到另一端也无法解密。
算法同为 Fernet，便于理解与迁移。
"""
import base64
import hashlib
import logging
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.storage.paths import get_local_key_path

logger = logging.getLogger(__name__)


class LocalEncryption:
    """本地文件密钥加密器（密钥不出本机）"""

    _cipher_suite = None

    @classmethod
    def _read_or_create_key(cls) -> str:
        """读取本机密钥；不存在则生成并原子写入"""
        key_path = get_local_key_path()

        if key_path.exists():
            key = key_path.read_text(encoding="utf-8").strip()
            if key:
                return key

        key = secrets.token_hex(32)
        cls._write_key_atomic(key_path, key)
        logger.info("已生成本地加密密钥：%s", key_path)
        return key

    @staticmethod
    def _write_key_atomic(path: Path, key: str) -> None:
        """原子写入密钥文件。

        Windows 上 os.rename() 对已存在的目标文件会抛 FileExistsError
        （POSIX 是静默覆盖），故需按 os.name 分支处理。
        """
        tmp = path.with_suffix(".tmp")
        tmp.write_text(key, encoding="utf-8")

        if os.name == "nt" and path.exists():
            path.unlink()

        os.rename(tmp, path)
        try:
            path.chmod(0o600)  # POSIX 收紧权限；Windows 上为 no-op
        except OSError:
            pass

    @classmethod
    def _get_cipher_suite(cls):
        if cls._cipher_suite is None:
            key = cls._read_or_create_key()
            try:
                cls._cipher_suite = Fernet(key)
            except ValueError:
                # 非标准 Fernet key 时用 SHA-256 派生（与服务器 EncryptionUtils 同策略）
                digest = hashlib.sha256(key.encode("utf-8")).digest()
                cls._cipher_suite = Fernet(base64.urlsafe_b64encode(digest))
        return cls._cipher_suite

    @classmethod
    def reset_cipher_suite(cls) -> None:
        """重置密钥缓存（密钥变更或测试隔离时调用）"""
        cls._cipher_suite = None

    @classmethod
    def encrypt(cls, plain_text: str) -> str:
        """加密字符串"""
        if not plain_text:
            return ""
        cipher_suite = cls._get_cipher_suite()
        return cipher_suite.encrypt(plain_text.encode("utf-8")).decode("utf-8")

    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        """解密字符串。密钥不匹配时抛 InvalidToken —— 禁止返回假明文。"""
        if not encrypted_text:
            return ""
        cipher_suite = cls._get_cipher_suite()
        try:
            return cipher_suite.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            logger.error("本地密文解密失败（密钥不匹配或数据损坏）")
            raise ValueError(
                "本地加密密钥不可用，请检查 ~/.toolbox/encryption.key"
            ) from exc
