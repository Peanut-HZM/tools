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

    # ZCode：凭据是自有加密格式，但可以按 ZCode 自己的实现解密出智谱 access token
    try:
        from app.services.subscription_quota.zcode_credentials import read_zcode_token

        zcode = read_zcode_token()
    except Exception as exc:
        logger.warning("读取 ZCode 本地凭据异常: %s", exc)
        zcode = None

    if zcode is not None and zcode.token:
        accounts.append(
            QuotaAccount(
                id=f"{LOCAL_ACCOUNT_PREFIX}zcode",
                user_id="",
                provider_id="zhipu",
                label="智谱 GLM（ZCode 登录）",
                api_key=zcode.token,
                extra={"region": "cn", "api_key": zcode.token},
                enabled=True,
            )
        )

    # ZCode provider_config.json 里的明文 Key（服务账户也能读到）
    try:
        from app.services.subscription_quota.zcode_provider_config import read_provider_keys

        provider_keys = read_provider_keys()
    except Exception as exc:
        logger.warning("读取 ZCode provider 配置异常: %s", exc)
        provider_keys = []

    existing = {a.provider_id for a in accounts}
    for item in provider_keys:
        if item.provider_id in existing:
            continue
        extra: dict = {"region": item.region, "api_key": item.api_key}
        if item.provider_id == "opendesign":
            # OpenDesign 用 control_key 字段名
            extra["control_key"] = item.api_key
        if item.base_url:
            extra["base_url"] = item.base_url
        accounts.append(
            QuotaAccount(
                id=f"{LOCAL_ACCOUNT_PREFIX}zcode-{item.provider_id}",
                user_id="",
                provider_id=item.provider_id,
                label=item.label,
                api_key=item.api_key,
                extra=extra,
                enabled=True,
            )
        )
        existing.add(item.provider_id)

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

    # ZCode：按 ZCode 自己的加密实现解密凭据
    try:
        from app.services.subscription_quota.zcode_credentials import read_zcode_token

        zcode = read_zcode_token()
    except Exception as exc:
        logger.warning("读取 ZCode 凭据异常: %s", exc)
        zcode = None

    if zcode is not None and zcode.token:
        notes.append(
            LocalCredentialNote(
                provider_id="zhipu",
                name="智谱 GLM（ZCode）",
                status="available",
                message="已从本机 ZCode 登录自动识别（智谱 GLM 额度已就绪）",
            )
        )
    elif zcode is not None and zcode.status == "unsupported":
        notes.append(
            LocalCredentialNote(
                provider_id="zhipu",
                name="智谱 GLM（ZCode）",
                status="needs_manual_key",
                message=zcode.message or "无法读取 ZCode 加密凭据，请手动填写 API Key",
            )
        )

    return notes
