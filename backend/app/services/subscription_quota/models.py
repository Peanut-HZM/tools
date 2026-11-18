"""订阅额度统一数据模型

字段与 cc-switch 的 ``SubscriptionQuota`` 一一对应（Rust serde camelCase），
方便对照上游实现排查问题。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


class CredentialStatus:
    """凭据状态（对应 cc-switch ``CredentialStatus``）"""

    VALID = "valid"
    EXPIRED = "expired"
    #: 访问令牌过期，但刷新令牌还在——CLI 下次运行时会自己换新，不算登录失效
    REFRESH_PENDING = "refresh_pending"
    NOT_FOUND = "not_found"
    PARSE_ERROR = "parse_error"


@dataclass
class QuotaTier:
    """单个限速窗口（5 小时 / 每周 / 每月 等）或余额项

    * 窗口型：``utilization`` 为**已用**百分比 0–100
    * 余额型：``utilization`` 恒为 0，金额放在 ``balance_amount`` / ``balance_unit``
    """

    name: str
    utilization: float
    resets_at: Optional[str] = None
    #: 可选：窗口已用金额（USD），仅部分供应商返回
    used_value_usd: Optional[float] = None
    #: 可选：窗口上限金额（USD）
    max_value_usd: Optional[float] = None
    #: 余额型专用：金额与币种
    balance_amount: Optional[float] = None
    balance_unit: Optional[str] = None

    def to_dict(self) -> dict:
        data = {
            "name": self.name,
            "utilization": self.utilization,
            "resetsAt": self.resets_at,
        }
        if self.used_value_usd is not None:
            data["usedValueUsd"] = self.used_value_usd
        if self.max_value_usd is not None:
            data["maxValueUsd"] = self.max_value_usd
        if self.balance_amount is not None:
            data["balanceAmount"] = self.balance_amount
        if self.balance_unit is not None:
            data["balanceUnit"] = self.balance_unit
        return data


@dataclass
class SubscriptionQuota:
    """一家供应商的套餐额度查询结果"""

    tool: str
    credential_status: str = CredentialStatus.NOT_FOUND
    credential_message: Optional[str] = None
    success: bool = False
    tiers: list[QuotaTier] = field(default_factory=list)
    #: 套餐显示名（如「Pro 200」「Allegretto」），查不到时为 None
    plan_name: Optional[str] = None
    error: Optional[str] = None
    queried_at: Optional[int] = None
    #: 用户自定义标签（多账号区分）
    label: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "credentialStatus": self.credential_status,
            "credentialMessage": self.credential_message,
            "success": self.success,
            "tiers": [tier.to_dict() for tier in self.tiers],
            "planName": self.plan_name,
            "error": self.error,
            "queriedAt": self.queried_at,
            "label": self.label,
        }

    # ---------- 构造辅助（对应 cc-switch 的 not_found / error） ----------

    @classmethod
    def not_found(cls, tool: str) -> "SubscriptionQuota":
        return cls(tool=tool, credential_status=CredentialStatus.NOT_FOUND)

    @classmethod
    def failure(
        cls,
        tool: str,
        status: str,
        message: str,
        *,
        credential_message: Optional[str] = None,
    ) -> "SubscriptionQuota":
        return cls(
            tool=tool,
            credential_status=status,
            credential_message=credential_message if credential_message is not None else message,
            success=False,
            error=message,
            queried_at=now_millis(),
        )


def now_millis() -> int:
    return int(time.time() * 1000)


def millis_to_iso(ms: Optional[int]) -> Optional[str]:
    """毫秒时间戳 → ISO 8601（UTC）。无法解析时返回 None。"""
    if ms is None:
        return None
    try:
        from datetime import datetime, timezone

        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, OSError, OverflowError):
        return None
