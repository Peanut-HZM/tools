"""ZCode 本地凭据读取（只读，解密仅在本进程内存中）

ZCode 把凭据加密存进 `~/.zcode/v2/credentials.json`，格式：

    enc:v2:os:<fingerprint>:<iv_b64url>.<tag_b64url>.<ciphertext_b64url>

其中 `fingerprint = sha256(aesKey).hex()[:24]`，`aesKey` 是系统凭据管理器里
（Windows Credential Manager / macOS Keychain / Linux keyring）名为
`sha256(<credentials.json 绝对路径>).hex() + ".ZCode Credential Encryption"`
的条目，32 字节，base64url 编码后存入。

本模块严格对齐该实现（见 ZCode `createSystemCredentialCipher` 的 `seal` /
`open` 两个函数），只做**读取与解密**，绝不写入或刷新。

解密出的 token 只在本进程内存中用于查询额度，绝不返回给前端。
"""

from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CRED_TYPE_GENERIC = 1
_KEYRING_SUFFIX = ".ZCode Credential Encryption"
_PREFIX = "enc:v2:os:"


def _b64u_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# --------------------------------------------------------------------------
# Windows Credential Manager
# --------------------------------------------------------------------------


if sys.platform == "win32":
    from ctypes import wintypes

    class _CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]


def _read_windows_credential(target: str) -> Optional[bytes]:
    if sys.platform != "win32":
        return None
    try:
        advapi = ctypes.windll.advapi32
        ptr = ctypes.POINTER(_CREDENTIAL)()
        if not advapi.CredReadW(target, _CRED_TYPE_GENERIC, 0, ctypes.byref(ptr)):
            return None
        try:
            cred = ptr.contents
            if not cred.CredentialBlobSize:
                return b""
            return ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
        finally:
            advapi.CredFree(ptr)
    except Exception as exc:
        logger.debug("读取 Windows 凭据失败: %s", exc)
        return None


def _read_macos_keychain(service: str) -> Optional[bytes]:
    if sys.platform != "darwin":
        return None
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True,
            timeout=5,
        )
        if out.returncode != 0:
            return None
        return out.stdout.strip()
    except Exception as exc:
        logger.debug("读取 macOS Keychain 失败: %s", exc)
        return None


# --------------------------------------------------------------------------
# 解密
# --------------------------------------------------------------------------


@dataclass
class ZCodeSecret:
    """解密结果（token 仅在本进程内存中使用）"""

    token: Optional[str] = None
    status: str = "not_found"  # valid | not_found | unsupported | error
    message: Optional[str] = None


def _credentials_path() -> Path:
    from app.config.config import REAL_HOME

    return Path(REAL_HOME) / ".zcode" / "v2" / "credentials.json"


def _keyring_service_name(cred_path: Path) -> str:
    """ZCode 在系统凭据管理器里用的条目名：sha256(绝对路径) + 固定后缀"""
    digest = hashlib.sha256(str(cred_path).encode()).hexdigest()
    return f"{digest}{_KEYRING_SUFFIX}"


def _load_aes_key(cred_path: Path) -> Optional[bytes]:
    """从系统凭据管理器取出 32 字节 AES key。"""
    service = _keyring_service_name(cred_path)

    raw: Optional[bytes] = None
    if sys.platform == "win32":
        # Credential Manager 的 target 带 LegacyGeneric: 前缀
        raw = _read_windows_credential(f"LegacyGeneric:target={service}")
        if raw is None:
            raw = _read_windows_credential(service)
    elif sys.platform == "darwin":
        raw = _read_macos_keychain(service)
    else:
        return None

    if not raw:
        return None
    text = raw.decode("utf-8", errors="ignore").strip()
    try:
        key = _b64u_decode(text)
    except Exception:
        key = raw
    return key if len(key) == 32 else None


def _decrypt_value(value: str, key: bytes) -> Optional[str]:
    """解开 `enc:v2:os:<fp>:<iv>.<tag>.<ct>`"""
    if not value.startswith(_PREFIX):
        return None
    try:
        body = value[len(_PREFIX) :]
        _fingerprint, payload = body.split(":", 1)
        iv_s, tag_s, ct_s = payload.split(".")
        iv = _b64u_decode(iv_s)
        tag = _b64u_decode(tag_s)
        ct = _b64u_decode(ct_s)
    except (ValueError, TypeError):
        return None
    if len(iv) != 12 or len(tag) != 16:
        return None
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        plain = AESGCM(key).decrypt(iv, ct + tag, None)
    except Exception as exc:
        logger.debug("ZCode 凭据解密失败: %s", type(exc).__name__)
        return None
    try:
        return plain.decode("utf-8")
    except UnicodeDecodeError:
        return None


def read_zcode_token(field: str = "oauth:bigmodel:access_token") -> ZCodeSecret:
    """读取并解密 ZCode 的某个凭据字段。

    * `oauth:bigmodel:access_token` → 智谱 GLM 额度查询可用（Bearer）
    * `zcodejwttoken` → ZCode 自己的 JWT（zcode-plan 接口需要额外参数，暂不用于额度）
    """
    cred_path = _credentials_path()
    if not cred_path.exists():
        return ZCodeSecret(status="not_found", message=f"未找到 {cred_path}")

    try:
        data = json.loads(cred_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ZCodeSecret(status="error", message=f"读取 ZCode 凭据失败: {exc}")

    value = data.get(field)
    if not isinstance(value, str) or not value:
        return ZCodeSecret(status="not_found", message=f"ZCode 凭据里没有 {field}")

    if not value.startswith(_PREFIX):
        # 明文（旧版本），直接使用
        return ZCodeSecret(token=value, status="valid")

    key = _load_aes_key(cred_path)
    if key is None:
        return ZCodeSecret(
            status="unsupported",
            message="无法从系统凭据管理器取出 ZCode 加密密钥"
            "（需要 ZCode 已登录且当前用户可访问凭据管理器）",
        )

    token = _decrypt_value(value, key)
    if not token:
        return ZCodeSecret(status="error", message="ZCode 凭据解密失败（密钥指纹不匹配）")
    return ZCodeSecret(token=token, status="valid")


def zcode_available() -> tuple[bool, str]:
    """给前端的状态说明：本机是否能用 ZCode 凭据查额度。"""
    result = read_zcode_token()
    if result.status == "valid":
        return True, "已从本机 ZCode 登录自动识别（智谱 GLM 额度）"
    if result.status == "not_found":
        return False, "未检测到 ZCode 登录"
    return False, result.message or "ZCode 凭据不可用"
