"""订阅去重（唯一实现）

设计依据：``specs/agent-subscription-bridge-design.md`` §5

判定键（默认 ``url_key`` 模式）::

    (user_id, normalize_base_url(base_url), sha256(api_key))

* base_url 相同 + Key 相同 → 同一条订阅，**完全跳过**（不改任何字段）
* base_url 相同 + Key 不同 → 新增（同渠道多把 Key = 多个订阅）
* base_url 不同 + Key 相同 → 新增（两个端点各一份）

``legacy`` 模式（回滚用，``QUOTA_DEDUPE_MODE=legacy``）保留旧行为：
``(provider_id, sha256(api_key))`` 判重，且同 Key 跨供应商全局唯一。

约束：
* 明文 Key 只在内存中参与 sha256，绝不落日志/响应；
* 存量 ``api_key_hash`` 为空的行，用解密函数现算（调用方传入 ``decrypt_fn``），
  解密失败的行不参与判重并计入 ``unreadable``；
* 本模块不做任何数据库写入（纯决策），写库由调用方负责。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional

from app.services.subscription_quota.url_norm import normalize_base_url

logger = logging.getLogger(__name__)

#: 去重模式开关（默认 url_key；回滚可切 legacy）
DEDUPE_MODE_ENV = "QUOTA_DEDUPE_MODE"
_MODE_URL_KEY = "url_key"
_MODE_LEGACY = "legacy"


def dedupe_mode() -> str:
    """当前去重模式（未知值按默认 url_key 处理，避免写错配置导致行为不可预期）"""
    raw = (os.getenv(DEDUPE_MODE_ENV) or "").strip().lower()
    return _MODE_LEGACY if raw == _MODE_LEGACY else _MODE_URL_KEY


def sha256_hex(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def mask_key(plain: str) -> str:
    """掩码格式与 QuotaAccount.masked_key 一致（前 4 + *×8 + 后 4；≤8 位全掩码）"""
    if not plain:
        return ""
    if len(plain) <= 8:
        return "*" * len(plain)
    return f"{plain[:4]}{'*' * 8}{plain[-4:]}"


def item_key(provider_id: str, base_url: str, api_key: str, mode: Optional[str] = None) -> tuple:
    """一条订阅的去重键（调用方与索引必须用同一个 mode）"""
    resolved_mode = mode or dedupe_mode()
    key_hash = sha256_hex(api_key)
    if resolved_mode == _MODE_LEGACY:
        return (_MODE_LEGACY, provider_id, key_hash)
    return (_MODE_URL_KEY, normalize_base_url(base_url), key_hash)


@dataclass(frozen=True)
class DedupeDecision:
    """一条待入库条目的裁决结果"""

    action: str  # create | skip
    reason: Optional[str]  # skip 时为 duplicate；create 时为 None
    label: Optional[str]  # create 时的最终 label
    key: tuple


class ExistingIndex:
    """已存在订阅的判重索引（含 label 占用与 hash 回填登记）"""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.key_index: dict[tuple, str] = {}
        #: row_id → provider_id（命中时回填明细里的「既有归属供应商」）
        self.row_provider: dict[str, str] = {}
        #: (provider_id, label) 占用表：值为该行 hash，无 hash 的行用哨兵
        self.label_index: dict[tuple[str, str], str] = {}
        #: row_id → 现算出的 hash（存量行缺 hash 时登记，命中后由调用方回填）
        self.hash_pending: dict[str, str] = {}
        #: legacy 模式的跨供应商全局去重：hash → provider_id
        self.global_index: dict[str, str] = {}
        self.unreadable: list[str] = []

    # ------------------------------------------------------------------ 构建
    @classmethod
    def from_rows(
        cls,
        rows: Iterable[Any],
        *,
        mode: Optional[str] = None,
        decrypt_fn: Optional[Callable[[str], str]] = None,
    ) -> "ExistingIndex":
        """从数据库行构建索引

        ``rows`` 需提供 ``id / provider_id / base_url_norm / api_key_hash /
        api_key_enc / label`` 字段（SQLAlchemy Row 或 dict 均可）。
        """
        index = cls(mode or dedupe_mode())
        for row in rows:
            mapping = row._mapping if hasattr(row, "_mapping") else row
            row_id = mapping["id"]
            provider_id = mapping["provider_id"] or ""
            stored_hash = (mapping["api_key_hash"] or "") if "api_key_hash" in mapping else ""
            if not stored_hash and mapping.get("api_key_enc") and decrypt_fn is not None:
                try:
                    stored_hash = sha256_hex(decrypt_fn(mapping["api_key_enc"]))
                    index.hash_pending[row_id] = stored_hash
                except Exception:  # 解不开的存量行不参与判重
                    index.unreadable.append(row_id)
                    stored_hash = ""
            if stored_hash:
                base_url = (mapping["base_url_norm"] or "") if "base_url_norm" in mapping else ""
                if not base_url:
                    # 存量行尚未回填 norm：从 base_url / extra_json 现推（保证与回填后一致）
                    raw_url = (mapping.get("base_url") or "") if hasattr(mapping, "get") else ""
                    if not raw_url:
                        try:
                            raw_extra = json.loads(mapping.get("extra_json") or "{}")
                        except (json.JSONDecodeError, TypeError):
                            raw_extra = {}
                        if isinstance(raw_extra, dict):
                            raw_url = str(raw_extra.get("base_url") or "")
                    base_url = normalize_base_url(raw_url)
                key = (
                    (_MODE_LEGACY, provider_id, stored_hash)
                    if index.mode == _MODE_LEGACY
                    else (_MODE_URL_KEY, base_url, stored_hash)
                )
                index.key_index.setdefault(key, row_id)
                index.row_provider[row_id] = provider_id
                if index.mode == _MODE_LEGACY:
                    index.global_index.setdefault(stored_hash, provider_id)
            # label 占位：解不开 hash 的行同样占用 label，避免消歧误判为空闲
            label = (mapping.get("label") if hasattr(mapping, "get") else mapping["label"]) or ""
            index.label_index[(provider_id, label)] = stored_hash or "unknown"
        return index

    # ------------------------------------------------------------------ 裁决
    def decide(
        self,
        *,
        provider_id: str,
        provider_name: str,
        channel: str,
        base_url: str,
        api_key: str,
    ) -> DedupeDecision:
        """判定 create / skip，并给出最终 label（create 时）"""
        key = item_key(provider_id, base_url, api_key, self.mode)
        hit = self.key_index.get(key)
        global_hit = key[2] in self.global_index if self.mode == _MODE_LEGACY else None
        if hit or global_hit:
            return DedupeDecision(action="skip", reason="duplicate", label=None, key=key)
        return DedupeDecision(
            action="create", reason=None, label=self._label(provider_id, provider_name, channel, api_key), key=key
        )

    def register(
        self, *, provider_id: str, key: tuple, row_id: str, label: str, api_key: str
    ) -> None:
        """批内即时可见：同批后续条目立刻能命中，避免重复/重名"""
        self.key_index[key] = row_id
        self.label_index[(provider_id, label)] = key[2]
        if self.mode == _MODE_LEGACY:
            self.global_index.setdefault(key[2], provider_id)

    # ------------------------------------------------------------------ label
    def _label(self, provider_id: str, provider_name: str, channel: str, api_key: str) -> str:
        label = f"{provider_name}-{channel}" if channel else provider_name
        if not self.label_index.get((provider_id, label)):
            return label
        label = f"{label}·{api_key[-4:]}" if len(api_key) >= 4 else f"{label}·{api_key}"
        if not self.label_index.get((provider_id, label)):
            return label
        base, suffix = label, 2
        while self.label_index.get((provider_id, label)):
            label = f"{base}-{suffix}"
            suffix += 1
        return label


def find_duplicate_groups(rows: Iterable[Any], *, mode: Optional[str] = None) -> list[dict]:
    """按去重键分组，返回出现 ≥2 行的分组（重复项报告用）

    ``rows`` 需含 ``id / user_id / provider_id / label / base_url_norm / api_key_hash``。
    """
    resolved_mode = mode or dedupe_mode()
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        mapping = row._mapping if hasattr(row, "_mapping") else row
        key_hash = mapping["api_key_hash"] or ""
        if not key_hash:
            continue
        provider_id = mapping["provider_id"] or ""
        key = (
            (_MODE_LEGACY, provider_id, key_hash)
            if resolved_mode == _MODE_LEGACY
            else (_MODE_URL_KEY, mapping["base_url_norm"] or "", key_hash)
        )
        groups.setdefault(key, []).append(
            {
                "id": mapping["id"],
                "userId": mapping["user_id"],
                "providerId": provider_id,
                "label": mapping["label"] or "",
                "baseUrl": (mapping.get("base_url") if hasattr(mapping, "get") else None) or "",
            }
        )
    duplicates: list[dict] = []
    for key, items in groups.items():
        if len(items) < 2:
            continue
        duplicates.append(
            {
                "baseUrlNorm": key[1] if resolved_mode == _MODE_URL_KEY else "",
                "apiKeyHash": key[2],
                "count": len(items),
                "items": items,
            }
        )
    return duplicates