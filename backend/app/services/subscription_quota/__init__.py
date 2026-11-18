"""订阅套餐额度查询（参考 cc-switch 的 subscription / coding_plan 实现）

只读本机各 CLI 已有的官方登录凭据，查询官方额度接口，返回统一的档位模型。

设计约束：
* **只读**：从不写入、刷新或上传任何凭据
* **不泄露**：响应中绝不包含 access_token / refresh_token / api_key
* **不伪造**：凭据缺失时返回 ``not_found``，查询失败时返回 ``success=False`` 与原始错误

``utilization`` 一律表示**已用**百分比（0–100），与 cc-switch 保持一致，
前端按 ``剩余 = 100 - utilization`` 展示。
"""

from app.services.subscription_quota.models import (
    CredentialStatus,
    QuotaTier,
    SubscriptionQuota,
)
from app.services.subscription_quota.service import (
    KNOWN_TOOLS,
    query_quotas,
)

__all__ = [
    "CredentialStatus",
    "QuotaTier",
    "SubscriptionQuota",
    "KNOWN_TOOLS",
    "query_quotas",
]
