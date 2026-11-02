"""
客户端设备标识解析

用途：同一用户可能在多台设备上使用本应用，各设备对「显示偏好」
（如数据库工具的可见连接/可见数据库）的设置应互不影响、各自回显。

机制：
1. 前端首次访问时生成一个随机 UUID，存到 localStorage（key 见前端常量）
2. 之后每次请求都通过 `X-Device-Id` 请求头带上
3. 后端按 (user_id, device_id) 维度存取该用户的偏好

安全约束：
- device_id 只做「同一用户下区分设备」的用途，不做鉴权；
  任意客户端都能伪造，故不能把它当成权限凭据。
- 缺失/非法 device_id 时回退为空串（走历史兜底行），不报错。
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 客户端设备标识请求头
DEVICE_ID_HEADER = "X-Device-Id"

# device_id 最大长度（与数据库列长度一致）
MAX_DEVICE_ID_LENGTH = 128

# 允许的字符集：UUID / 十六进制 / 短横线 / 下划线
_ALLOWED_CHARS = set(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "-_"
)


def normalize_device_id(raw: Optional[str]) -> str:
    """规范化设备标识。

    - None / 空 → 返回空串（表示「未提供设备标识」，走历史兜底行）
    - 超长 → 截断到 MAX_DEVICE_ID_LENGTH
    - 含非法字符 → 过滤掉；过滤后为空则返回空串
    """
    if not raw:
        return ""

    value = str(raw).strip()
    if not value:
        return ""

    if len(value) > MAX_DEVICE_ID_LENGTH:
        value = value[:MAX_DEVICE_ID_LENGTH]

    filtered = "".join(ch for ch in value if ch in _ALLOWED_CHARS)
    if filtered != value:
        logger.warning("设备标识包含非法字符，已过滤")

    return filtered


def resolve_device_id(raw: Optional[str]) -> str:
    """解析请求携带的设备标识（对外统一入口）。"""
    return normalize_device_id(raw)
