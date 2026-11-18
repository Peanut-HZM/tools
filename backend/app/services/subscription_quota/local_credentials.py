"""本机 CLI 凭据自动发现（用于「已登录即可查询」的供应商）

与 cc-switch 一致：CLI 已经登录过的套餐，不必再手工填一遍 Key。

只做**只读**读取；发现到的凭据以「临时账号」形式参与查询，不落库。
用户也可以手动添加同名供应商（多个账号并存）。

注意：ZCode 的凭据是 `enc:v2:os:<keyId>:...` 形式的自有密文，
无法在不逆向其密钥派生的前提下解开，因此这里只报告「存在但需要手动填 Key」。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.services.subscription_quota.accounts import QuotaAccount
from app.services.subscription_quota.credentials import read_kimi

logger = logging.getLogger(__name__)

#: 本地凭据账号的 id 前缀（前端据此识别为「自动发现」）
LOCAL_ACCOUNT_PREFIX = "local:"


@dataclass
class LocalCredentialNote:
    provider_id: str
    name: str
    status: str  # available | needs_manual_key | absent
    message: str


def discover_local_accounts() -> list[QuotaAccount]:
    """返回可用的本地凭据虚拟账号（不落库、不返回明文到前端）"""
    accounts: list[QuotaAccount] = []

    # Kimi Code：~/.kimi-code/credentials/kimi-code.json 就是 Kimi For Coding 的 OAuth JWT
    try:
        cred = read_kimi()
    except Exception as exc:  # 读取失败不影响其它供应商
        logger.warning("读取 Kimi 本地凭据异常: %s", exc)
        cred = None

    if cred is not None and cred.token:
        accounts.append(
            QuotaAccount(
                id=f"{LOCAL_ACCOUNT_PREFIX}kimi",
                user_id="",
                provider_id="kimi",
                label="Kimi Code（本机登录）",
                api_key=cred.token,
                extra={"region": "cn", "api_key": cred.token},
                enabled=True,
            )
        )

    return accounts


def local_credential_notes() -> list[LocalCredentialNote]:
    """告诉前端哪些供应商有本地凭据可用 / 需要手动填 Key"""
    notes: list[LocalCredentialNote] = []

    kimi = next((a for a in discover_local_accounts() if a.provider_id == "kimi"), None)
    notes.append(
        LocalCredentialNote(
            provider_id="kimi",
            name="Kimi For Coding",
            status="available" if kimi else "absent",
            message="已从本机 Kimi Code 登录自动识别" if kimi else "未检测到本机 Kimi 登录",
        )
    )

    # ZCode：凭据存在但为自有加密格式
    try:
        from pathlib import Path

        from app.config.config import REAL_HOME

        zcode_cred = Path(REAL_HOME) / ".zcode" / "v2" / "credentials.json"
        if zcode_cred.exists():
            notes.append(
                LocalCredentialNote(
                    provider_id="zhipu",
                    name="智谱 GLM（ZCode）",
                    status="needs_manual_key",
                    message="检测到 ZCode 登录，但其凭据是 ZCode 自有加密格式，无法直接读取；"
                    "请在 ZCode 里复制 API Key 后手动添加",
                )
            )
    except Exception as exc:
        logger.debug("检查 ZCode 凭据失败: %s", exc)

    return notes
