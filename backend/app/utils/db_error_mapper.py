"""数据库连接错误分类映射工具

将原始异常字符串映射为 (error_code, zh_message) 二元组，
供路由层和服务层复用，统一向前端传递结构化的错误信息。
"""
import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# 错误码 → 中文描述（兜底文案）
_ERROR_CODE_ZH: dict[str, str] = {
    "CONNECTION_TIMEOUT": "连接超时，请检查主机地址和端口是否正确，或网络是否可达",
    "CONNECTION_REFUSED": "连接被拒绝，目标服务器可能未启动或端口未监听",
    "HOST_NOT_FOUND": "无法解析主机地址，请检查主机名是否正确",
    "ACCESS_DENIED": "访问被拒绝，用户名或密码可能错误，或该用户无权连接此数据库",
    "DATABASE_NOT_FOUND": "指定的数据库不存在",
    "SSL_ERROR": "SSL/TLS 连接失败，请检查 SSL 配置或证书路径",
    "TOO_MANY_CONNECTIONS": "连接数过多，服务器已达最大连接数限制",
    "NETWORK_ERROR": "网络异常，连接中断或服务器关闭了连接",
    "UNKNOWN_ERROR": "连接失败",
}

# 按优先级排列（越具体的越靠前）。
# 每个条目：(error_code, [关键字列表])
# 匹配时对 raw_error 做大小写不敏感的关键字子串匹配，任一关键字命中即视为该错误码
_RULES: list[tuple[str, list[str]]] = [
    (
        "CONNECTION_TIMEOUT",
        ["timed out", "timeout", "connect_timeout", "operation timed out"],
    ),
    (
        "CONNECTION_REFUSED",
        ["connection refused", "actively refused", "can't connect", "cannot connect"],
    ),
    (
        "HOST_NOT_FOUND",
        [
            "name or service not known",
            "getaddrinfo failed",
            "nodename nor servname provided",
            "unknown host",
            "temporary failure in name resolution",
        ],
    ),
    (
        "ACCESS_DENIED",
        [
            "access denied",
            "authentication failed",
            "invalid credentials",
            "login failed",
            "password authentication failed",
            "using password",
        ],
    ),
    (
        "DATABASE_NOT_FOUND",
        [
            "unknown database",
            # 匹配 "database "xxx" does not exist" 或 "database xxx does not exist"
            r"database .+ does not exist",
        ],
    ),
    (
        "SSL_ERROR",
        ["ssl", "certificate verify failed", "tls"],
    ),
    (
        "TOO_MANY_CONNECTIONS",
        ["too many connections", "max_connections", "connection limit"],
    ),
    (
        "NETWORK_ERROR",
        [
            "connection lost",
            "connection closed",
            "broken pipe",
            "connection reset",
            "server closed",
            "lost connection",
            "econnreset",
            "econnrefused",
        ],
    ),
]

# 预编译正则（大小写不敏感）
_COMPILED_RULES: list[tuple[str, list[re.Pattern[str]]]] = [
    (code, [re.compile(kw, re.IGNORECASE) for kw in keywords])
    for code, keywords in _RULES
]


def map_connection_error(raw_error: str) -> Tuple[str, str]:
    """将原始异常字符串映射为 (error_code, zh_message)。

    匹配规则按优先级从上到下，首个命中即返回。
    全部未命中时返回 ("UNKNOWN_ERROR", 原始错误字符串)。
    """
    lowered = raw_error.lower()
    for code, patterns in _COMPILED_RULES:
        for pattern in patterns:
            if pattern.search(lowered):
                return code, _ERROR_CODE_ZH[code]

    logger.debug("未匹配到已知错误模式，返回 UNKNOWN_ERROR: %s", raw_error[:200])
    return "UNKNOWN_ERROR", raw_error
