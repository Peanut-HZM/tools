"""
敏感信息脱敏工具（新增于数据加密整改）

用途：
    写入「执行历史 / 错误信息 / 结果预览」等**需要保留可读性**的场景时，
    在落库前把其中的凭据遮蔽，避免明文密钥进入数据库。

设计原则：
    * 只做「遮蔽」，不做「删除」——保留记录结构，保留排障价值
    * 规则分两类：
        1) 形态类（已知供应商密钥格式）——保留前缀便于定位来源，遮蔽主体
        2) 键值类（password/api_key/token=...）——整个值遮蔽
    * 关键词边界用 \\b，避免 token_count / access_key_id 之类被误伤

遮蔽标记统一为 [REDACTED]，形态类额外保留前缀。
"""
import re
from typing import Any

REDACTED = "[REDACTED]"

# ---------------------------------------------------------------------------
# 1) 形态类：已知供应商 / 协议密钥格式
#    (正则, 保留的前缀长度)
# ---------------------------------------------------------------------------
_TOKEN_PATTERNS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{16,}"), 8),        # Anthropic
    (re.compile(r"sk-[A-Za-z0-9_\-]{20,}"), 3),            # 含横线的长 key（如 sk-proj-...）
    (re.compile(r"sk-[A-Za-z0-9]{13,}"), 3),               # 通用短/长 key（不含横线）
    (re.compile(r"gsk_[A-Za-z0-9]{20,}"), 4),               # OpenAI 新格式
    (re.compile(r"dop_v1_[A-Za-z0-9]{20,}"), 7),           # 阿里云百炼
    (re.compile(r"AKIA[0-9A-Z]{16}"), 4),                  # AWS AccessKeyId
    (re.compile(r"ASIA[0-9A-Z]{16}"), 4),                  # AWS 临时凭证
    (re.compile(r"LTAI[0-9A-Za-z]{12,}"), 4),               # 阿里云
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), 11),     # GitHub fine-grained
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), 4),        # GitHub
    (re.compile(r"glpat-[A-Za-z0-9_\-]{16,}"), 6),         # GitLab
    (re.compile(r"npm_[A-Za-z0-9]{30,}"), 4),              # npm
    (re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"), 9),     # Slack
    (re.compile(r"xapp-[0-9]-[A-Za-z0-9\-]{10,}"), 6),     # Slack app
    (re.compile(r"AIza[0-9A-Za-z_\-]{30,}"), 4),           # Google
    (re.compile(r"SG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}"), 3),  # SendGrid
    (re.compile(r"ocl_[A-Za-z0-9]{16,}"), 4),              # OpenClaw token
    (re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"), 3),  # JWT
]

# ---------------------------------------------------------------------------
# 2) 键值类：敏感键名 + 分隔符 + 值
# ---------------------------------------------------------------------------
_SECRET_KEYS = (
    r"password|passwd|pwd|passphrase|secret|secret_key|secretkey|"
    r"api[_\-]?key|apikey|access[_\-]?key|accesskey|"
    r"private[_\-]?key|privatekey|"
    r"token|refresh[_\-]?token|session[_\-]?token|"
    r"auth[_\-]?token|authtoken|access[_\-]?token|"
    r"bearer[_\-]?token|signing[_\-]?key|"
    r"credential|credentials|"
    r"client[_\-]?secret|session[_\-]?key"
)

_SECRET_KEY_RE = re.compile(rf"^(?:{_SECRET_KEYS})$", re.IGNORECASE)

# JSON 形态：  "password": "value"   /   'password': 'value'
_RE_JSON_KV = re.compile(
    rf"""(["'])({_SECRET_KEYS})(["'])\s*:\s*(["'])(?:\\.|(?!\4).)*\4""",
    re.IGNORECASE,
)

# 赋值形态（带引号值）： password = 'value'  /  password: "value"
_RE_ASSIGN_QUOTED = re.compile(
    rf"""(\b(?:{_SECRET_KEYS})\b)(\s*(?:=|:)\s*)(["'])(?:\\.|(?!\3).)*\3""",
    re.IGNORECASE,
)

# 赋值形态（无引号值）： password = value
_RE_ASSIGN_BARE = re.compile(
    rf"""(\b(?:{_SECRET_KEYS})\b)(\s*(?:=|:)\s*)([^\s,;)\]}}'"`]+)""",
    re.IGNORECASE,
)

# PostgreSQL 建用户语法： CREATE USER x WITH PASSWORD 'abc'
_RE_PG_PASSWORD = re.compile(
    rf"""(\bPASSWORD\b)(\s+)(["'])(?:\\.|(?!\3).)*\3""",
    re.IGNORECASE,
)

# 连接串凭据： scheme://user:password@host
_RE_URL_CRED = re.compile(
    r"""([a-zA-Z][a-zA-Z0-9+.\-]*://[^:/@\s"']+:)([^@/\s"']+)(@)""",
)

# 授权头： Authorization: Bearer xxx / Authorization: Basic xxx / 裸 Bearer xxx
# 说明：authorization 不放在 _SECRET_KEYS 中，避免通用赋值规则先抢走 "Bearer" 这个
# scheme 值而留下真正的凭据裸露；授权头统一由本规则处理。
_RE_AUTH_HEADER = re.compile(
    r"""(\b(?:Authorization)\b\s*[:=]\s*)((?:Bearer|Basic|Digest)\s+)?([A-Za-z0-9_\-\.=+/]{8,})"""
    r"""|(\b(?:Bearer|Basic)\b\s+)([A-Za-z0-9_\-\.=+/]{8,})""",
    re.IGNORECASE,
)

# PEM 私钥块（整块遮蔽）
_RE_PEM = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.DOTALL,
)

# INSERT INTO tbl (col1, col2) VALUES (v1, v2)
_RE_INSERT = re.compile(
    r"(INSERT\s+INTO\s+[^\s(]+\s*\(([^)]*)\)\s*VALUES\s*\(([^)]*)\))",
    re.IGNORECASE | re.DOTALL,
)


def _split_sql_list(text: str):
    """按顶层逗号切分 SQL 列表项（忽略括号内与引号内的逗号）"""
    items = []
    depth = 0
    quote = None
    buf = []
    i = 0
    while i < len(text):
        ch = text[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and i + 1 < len(text):
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    if buf:
        items.append("".join(buf))
    return [x.strip() for x in items]


def _mask_pattern_value(match: re.Match, keep: int) -> str:
    """形态类遮蔽：保留前缀，其余替换为 [REDACTED]"""
    token = match.group(0)
    prefix = token[:keep]
    return f"{prefix}...{REDACTED}"


def _redact_insert(match: re.Match) -> str:
    """INSERT 语句：按列位置遮蔽敏感列对应的值"""
    whole, cols_raw, vals_raw = match.group(1), match.group(2), match.group(3)
    cols = _split_sql_list(cols_raw)
    vals = _split_sql_list(vals_raw)
    if len(cols) != len(vals):
        # 列数与值数不匹配（表达式列等），不按位置处理，交由其它规则兜底
        return whole

    changed = False
    for idx, col in enumerate(cols):
        if _SECRET_KEY_RE.match(col.strip().strip('"').strip("'")):
            vals[idx] = f"'{REDACTED}'"
            changed = True
    if not changed:
        return whole

    new_cols = ", ".join(cols)
    new_vals = ", ".join(vals)
    return whole[: whole.index("(")] + f"({new_cols}) VALUES ({new_vals})" + whole[whole.rindex(")") + 1:]


def _redact_auth_header(match: re.Match) -> str:
    """授权头遮蔽：保留 scheme，仅遮蔽凭据部分"""
    if match.group(1) is not None:
        scheme = match.group(2) or ""
        return f"{match.group(1)}{scheme}{REDACTED}"
    return f"{match.group(4)}{REDACTED}"


def redact_sensitive(text: str) -> str:
    """
    遮蔽文本中的敏感信息

    Args:
        text: 原始文本（None/空串原样返回）

    Returns:
        脱敏后的文本
    """
    if not text:
        return text
    if not isinstance(text, str):
        return text

    result = text

    # 1) PEM 私钥块：整块遮蔽
    result = _RE_PEM.sub("[REDACTED_PRIVATE_KEY]", result)

    # 2) 连接串凭据：保留 user，遮蔽密码
    result = _RE_URL_CRED.sub(rf"\1{REDACTED}\3", result)

    # 3) INSERT ... (cols) VALUES (vals)：按位置遮蔽敏感列的值
    result = _RE_INSERT.sub(_redact_insert, result)

    # 4) JSON 键值
    result = _RE_JSON_KV.sub(rf'\1\2\3: "{REDACTED}"', result)

    # 5) PostgreSQL PASSWORD 'literal' 语法（先于通用赋值规则处理）
    result = _RE_PG_PASSWORD.sub(rf"\1\2'{REDACTED}'", result)

    # 6) 授权头（先于通用赋值规则，避免 scheme 被误当作值）
    result = _RE_AUTH_HEADER.sub(_redact_auth_header, result)

    # 7) 通用键值赋值（先带引号、后不带引号）
    result = _RE_ASSIGN_QUOTED.sub(rf"\1\2\3{REDACTED}\3", result)
    result = _RE_ASSIGN_BARE.sub(rf"\1\2{REDACTED}", result)

    # 8) 形态类密钥（保留前缀）
    for pattern, keep in _TOKEN_PATTERNS:
        result = pattern.sub(lambda m, _k=keep: _mask_pattern_value(m, _k), result)

    return result


def redact_structure(value: Any) -> Any:
    """
    递归脱敏任意结构（dict / list / str / 标量）

    用于 result_data 这类 JSON 结构化数据：键名命中敏感词则整个值遮蔽，
    字符串值则走形态类脱敏。
    """
    if isinstance(value, str):
        return redact_sensitive(value)
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if isinstance(k, str) and _SECRET_KEY_RE.match(k.strip()):
                out[k] = REDACTED
            else:
                out[k] = redact_structure(v)
        return out
    if isinstance(value, list):
        return [redact_structure(v) for v in value]
    return value
