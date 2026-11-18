"""本机 CLI 凭据发现与读取（只读）

统一从各 CLI 已有的登录凭据文件里读出 access token / api key，
**从不写入、刷新或上传**。

路径解析必须基于 ``REAL_HOME``：``app.config.config`` 在非桌面模式会把
``HOME`` 覆盖成缓存目录（见 CLAUDE.md「用户目录访问必须使用真实家目录」）。
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.services.subscription_quota.models import CredentialStatus

logger = logging.getLogger(__name__)


def real_home() -> Path:
    """返回用户真实家目录（不受 HOME 覆盖影响）。"""
    from app.config.config import REAL_HOME

    return Path(REAL_HOME)


def _env_path(env_name: str, default_rel: str) -> Path:
    """环境变量优先的路径（展开 ~ 时基于真实家目录）。"""
    raw = os.environ.get(env_name)
    if raw:
        if raw.startswith("~"):
            return real_home() / raw[2:] if raw.startswith("~/") else real_home()
        return Path(raw)
    return real_home() / default_rel


@dataclass
class Credential:
    """读到的凭据（仅在服务端内存中短暂存在，绝不返回给前端）"""

    token: Optional[str] = None
    status: str = CredentialStatus.NOT_FOUND
    message: Optional[str] = None
    #: 各供应商专属的附加字段（如 Codex 的 account_id）
    extras: dict = None

    def __post_init__(self) -> None:
        if self.extras is None:
            self.extras = {}


def _read_json(path: Path) -> tuple[Optional[dict], Optional[str]]:
    """读取 JSON 文件，返回 (对象, 错误信息)。不抛异常。"""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        return None, f"读取凭据文件失败: {exc}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"凭据文件不是合法 JSON: {exc}"
    if not isinstance(data, dict):
        return None, "凭据文件结构异常（顶层不是对象）"
    return data, None


def _expired(expires_at) -> bool:
    """判断过期时间（支持秒 / 毫秒时间戳与 ISO 字符串）。"""
    import time

    now_s = time.time()
    if expires_at is None:
        return False
    if isinstance(expires_at, (int, float)):
        value = float(expires_at)
        # 毫秒级时间戳大于 1e12
        if value > 1e12:
            value /= 1000.0
        return value < now_s
    if isinstance(expires_at, str) and expires_at:
        from datetime import datetime, timezone

        text = expires_at.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return False
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp() < now_s
    return False


# --------------------------------------------------------------------------
# Claude Code
# --------------------------------------------------------------------------

def read_claude() -> Credential:
    """读取 Claude Code OAuth 凭据（``~/.claude/.credentials.json``）"""
    config_dir = _env_path("CLAUDE_CONFIG_DIR", ".claude")
    path = config_dir / ".credentials.json"
    data, err = _read_json(path)
    if err is not None:
        return Credential(status=CredentialStatus.PARSE_ERROR, message=err)
    if data is None:
        return Credential()

    entry = data.get("claudeAiOauth") or data.get("claude.ai_oauth")
    if not isinstance(entry, dict):
        return Credential(
            status=CredentialStatus.PARSE_ERROR,
            message="凭据中缺少 claudeAiOauth 字段",
        )
    token = entry.get("accessToken")
    if not isinstance(token, str) or not token:
        return Credential(
            status=CredentialStatus.PARSE_ERROR,
            message="accessToken 为空",
        )
    if _expired(entry.get("expiresAt")):
        refresh = entry.get("refreshToken")
        refresh_ok = isinstance(refresh, str) and refresh and not _expired(
            entry.get("refreshTokenExpiresAt")
        )
        # 与 cc-switch 一致：刷新令牌还在就不算登录失效，仍尝试用当前 token 查询
        return Credential(
            token=token,
            status=CredentialStatus.REFRESH_PENDING if refresh_ok else CredentialStatus.EXPIRED,
            message="访问令牌已过期，Claude Code 下次运行时会自动刷新"
            if refresh_ok
            else "OAuth 令牌已过期，请重新登录 Claude Code",
        )
    return Credential(token=token, status=CredentialStatus.VALID)


# --------------------------------------------------------------------------
# Codex (ChatGPT)
# --------------------------------------------------------------------------

def read_codex() -> Credential:
    """读取 Codex OAuth 凭据（``~/.codex/auth.json``，仅 chatgpt 模式可查）"""
    config_dir = _env_path("CODEX_HOME", ".codex")
    path = config_dir / "auth.json"
    data, err = _read_json(path)
    if err is not None:
        return Credential(status=CredentialStatus.PARSE_ERROR, message=err)
    if data is None:
        return Credential()

    if data.get("auth_mode") != "chatgpt":
        return Credential(
            status=CredentialStatus.NOT_FOUND,
            message="Codex 未使用 OAuth 登录模式（API key 模式无法查询订阅额度）",
        )
    tokens = data.get("tokens")
    if not isinstance(tokens, dict):
        return Credential(
            status=CredentialStatus.PARSE_ERROR,
            message="凭据中缺少 tokens 字段",
        )
    token = tokens.get("access_token")
    if not isinstance(token, str) or not token:
        return Credential(status=CredentialStatus.PARSE_ERROR, message="access_token 为空")

    status = CredentialStatus.VALID
    message = None
    last_refresh = data.get("last_refresh")
    if isinstance(last_refresh, str) and last_refresh:
        from datetime import datetime, timezone

        try:
            parsed = datetime.fromisoformat(last_refresh.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - parsed).days > 8:
                status = CredentialStatus.EXPIRED
                message = "Codex 令牌超过 8 天未刷新，可能已失效"
        except ValueError:
            pass

    return Credential(
        token=token,
        status=status,
        message=message,
        extras={"account_id": tokens.get("account_id")},
    )


# --------------------------------------------------------------------------
# Gemini CLI
# --------------------------------------------------------------------------

def read_gemini() -> Credential:
    """读取 Gemini CLI 凭据（``~/.gemini/oauth_creds.json``）"""
    config_dir = _env_path("GEMINI_DIR", ".gemini")
    path = config_dir / "oauth_creds.json"
    data, err = _read_json(path)
    if err is not None:
        return Credential(status=CredentialStatus.PARSE_ERROR, message=err)
    if data is None:
        return Credential()

    token = data.get("access_token")
    if not isinstance(token, str) or not token:
        return Credential(status=CredentialStatus.PARSE_ERROR, message="access_token 为空")

    refresh = data.get("refresh_token")
    if _expired(data.get("expiry_date")):
        return Credential(
            token=token,
            status=CredentialStatus.EXPIRED,
            message="Gemini 访问令牌已过期，请重新登录 Gemini CLI",
            extras={"refresh_token": refresh},
        )
    return Credential(token=token, status=CredentialStatus.VALID, extras={"refresh_token": refresh})


# --------------------------------------------------------------------------
# Kimi Code
# --------------------------------------------------------------------------

def read_kimi() -> Credential:
    """读取 Kimi Code 凭据（``~/.kimi-code/credentials/kimi-code.json``）"""
    root = _env_path("KIMI_DATA_DIR", ".kimi-code")
    candidates = [
        root / "credentials" / "kimi-code.json",
        real_home() / ".kimi-code" / "credentials" / "kimi-code.json",
        real_home() / ".kimi" / "credentials" / "kimi-code.json",
    ]
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        data, err = _read_json(path)
        if err is not None:
            return Credential(status=CredentialStatus.PARSE_ERROR, message=err)
        if data is None:
            continue
        token = data.get("access_token")
        if not isinstance(token, str) or not token:
            continue
        if _expired(data.get("expires_at")):
            return Credential(
                token=token,
                status=CredentialStatus.EXPIRED,
                message="Kimi 访问令牌已过期，请重新登录 Kimi Code",
            )
        return Credential(
            token=token,
            status=CredentialStatus.VALID,
            extras={"scope": data.get("scope")},
        )
    return Credential()


# --------------------------------------------------------------------------
# MiniMax
# --------------------------------------------------------------------------

def read_minimax() -> Credential:
    """读取 MiniMax OAuth 凭据（``~/.minimax/auth/**/auth.json``）"""
    auth_root = real_home() / ".minimax" / "auth"
    if not auth_root.is_dir():
        return Credential()
    files = sorted(auth_root.rglob("auth.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files:
        data, err = _read_json(path)
        if err is not None:
            continue
        if not data:
            continue
        records = data.get("records")
        if not isinstance(records, dict):
            continue
        # 取最近一条记录里仍有效的 accessToken
        for record in records.values():
            if not isinstance(record, dict):
                continue
            token = record.get("accessToken")
            if not isinstance(token, str) or not token:
                continue
            expired = _expired(record.get("expiresAtMs"))
            return Credential(
                token=token,
                status=CredentialStatus.EXPIRED if expired else CredentialStatus.VALID,
                message="MiniMax 访问令牌已过期，请重新登录"
                if expired
                else None,
            )
    return Credential()


# --------------------------------------------------------------------------
# 智谱 GLM（ZCode / bigmodel）
# --------------------------------------------------------------------------

def read_zhipu() -> Credential:
    """读取智谱 GLM 凭据

    来源 1：``~/.zcode/v2/credentials.json`` 的 ``oauth:bigmodel:access_token``
    来源 2：``ZHIPU_API_KEY`` / ``ZHIPUAI_API_KEY`` 环境变量（API key 模式）
    """
    path = real_home() / ".zcode" / "v2" / "credentials.json"
    data, err = _read_json(path)
    if err is None and data:
        token = data.get("oauth:bigmodel:access_token")
        if isinstance(token, str) and token:
            return Credential(token=token, status=CredentialStatus.VALID)
    elif err is not None:
        logger.debug("读取 ZCode 凭据失败: %s", err)

    for env_name in ("ZHIPU_API_KEY", "ZHIPUAI_API_KEY", "BIGMODEL_API_KEY"):
        token = os.environ.get(env_name)
        if token:
            return Credential(token=token, status=CredentialStatus.VALID)
    return Credential()


# --------------------------------------------------------------------------
# 汇总
# --------------------------------------------------------------------------

CREDENTIAL_READERS = {
    "claude": read_claude,
    "codex": read_codex,
    "gemini": read_gemini,
    "kimi": read_kimi,
    "minimax": read_minimax,
    "zhipu": read_zhipu,
}


def detect_credentials() -> dict[str, Credential]:
    """探测所有供应商的本地凭据状态（只返回状态，不含 token）。"""
    result: dict[str, Credential] = {}
    for tool, reader in CREDENTIAL_READERS.items():
        try:
            result[tool] = reader()
        except Exception as exc:  # 单个读取器异常不影响其它供应商
            logger.warning("读取 %s 凭据异常: %s", tool, exc)
            result[tool] = Credential(
                status=CredentialStatus.PARSE_ERROR,
                message=f"读取凭据异常: {type(exc).__name__}",
            )
    return result
