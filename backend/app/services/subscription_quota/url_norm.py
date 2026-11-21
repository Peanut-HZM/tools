"""base_url 归一化（订阅去重键的唯一实现）

设计依据：`specs/agent-subscription-bridge-design.md` §4.3

规则（与文档逐条对应）：
1. 去首尾空白；空值 → ``official``
2. 解析失败（非 http/https URL）→ 小写原文
3. scheme/host 小写；去默认端口（:80 / :443）
4. 去 query、fragment、userinfo
5. 路径去末尾 ``/``
6. 去末尾单个版本段（``v1`` / ``v1beta`` / ``v1alpha`` / ``v2`` …），
   只去最后一段且必须匹配 ``^v\\d+(beta|alpha)?$``
7. 重新拼回 ``scheme://host[:port]/path``

不做「跨路径合并」：``/anthropic`` 与 ``/v1`` 是不同端点（宁可不合并，不可错合并）。
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

#: 空 base_url（官方直连）的归一值
OFFICIAL = "official"

_VERSION_SEGMENT = re.compile(r"^v\d+(beta|alpha)?$")

_DEFAULT_PORTS = {"http": "80", "https": "443"}


def normalize_base_url(url: str | None) -> str:
    """把订阅调用地址归一成去重键用字符串（幂等：f(f(x)) == f(x)）"""
    raw = (url or "").strip()
    if not raw:
        return OFFICIAL

    try:
        parts = urlsplit(raw)
    except ValueError:
        return raw.lower()

    scheme = (parts.scheme or "").lower()
    if scheme not in ("http", "https") or not parts.netloc:
        # 非 URL（例如中文说明、模型名）→ 小写原文，保证稳定可比
        return raw.lower()

    host = (parts.hostname or "").lower()
    if not host:
        return raw.lower()

    port = parts.port
    if port is not None and str(port) == _DEFAULT_PORTS.get(scheme):
        port = None

    netloc = host
    if ":" in host:  # IPv6 字面量
        netloc = f"[{host}]"
    if port is not None:
        netloc = f"{netloc}:{port}"

    segments = [seg for seg in parts.path.split("/") if seg]
    if segments and _VERSION_SEGMENT.match(segments[-1].lower()):
        segments = segments[:-1]
    path = "/" + "/".join(segments) if segments else ""

    return f"{scheme}://{netloc}{path}"