"""Neo4j Cypher 只读执行器。

双层只读保障：
1. 关键字白名单：语句必须以只读关键字开头（MATCH/RETURN/WITH/CALL/SHOW/
   DESCRIBE/EXPLAIN/OPTIONAL MATCH/UNWIND），且全语句不得出现写关键字
   （CREATE/MERGE/DELETE/DETACH/SET/REMOVE/FOREACH/LOAD CSV/DROP/GRANT/REVOKE）。
   词法扫描先把字符串字面量（单/双引号）与反引号标识符替换为占位符，
   避免字面量内的写关键字被误伤，扫完无需还原（只做检测）。
2. driver 兜底：session 以 default_access_mode=READ 打开。

LIMIT 强制：顶层 RETURN 无 LIMIT 时在语句尾部追加，返回改写后语句与标记。
值序列化：Node/Relationship/Path 按设计文档 §6.5 表转 dict，其余递归处理。
错误映射（路由层）：只读违规→400；语法错误→400 透 Neo4j 描述；超时→408。
"""
import logging
import re
import time
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 只读校验
# ---------------------------------------------------------------------------
# 允许作为语句开头的只读关键字（大写，按长度降序匹配，保证 OPTIONAL MATCH 优先）
_READONLY_START_KEYWORDS = [
    "OPTIONAL MATCH",
    "MATCH",
    "RETURN",
    "WITH",
    "CALL",
    "SHOW",
    "DESCRIBE",
    "EXPLAIN",
    "UNWIND",
]

# 全语句禁止出现的写关键字（大写）
_WRITE_KEYWORDS = [
    "CREATE",
    "MERGE",
    "DELETE",
    "DETACH",
    "SET",
    "REMOVE",
    "FOREACH",
    "LOAD CSV",
    "DROP",
    "GRANT",
    "REVOKE",
]

# 字符串字面量 / 反引号标识符 → 占位符（扫描用，占位符本身无 Cypher 含义）
_LITERAL_PATTERN = re.compile(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|`[^`]*`")

# LIMIT 检测：语句中任意位置的顶层 RETURN ... LIMIT n（贪婪匹配到结尾）
_LIMIT_AT_RETURN_PATTERN = re.compile(
    r"\bRETURN\b[\s\S]*\bLIMIT\s+\d+\s*;?\s*$", re.IGNORECASE
)


class ReadonlyViolation(Exception):
    """只读校验失败：语句包含写操作或被白名单拒绝。"""


def _strip_literals(cypher: str) -> str:
    """把字符串字面量与反引号标识符替换为占位符，返回用于关键字扫描的安全文本。"""
    return _LITERAL_PATTERN.sub("''", cypher)


def _strip_leading_comments(cypher: str) -> str:
    """去掉语句开头的行注释（// ...）与块注释（/* ... */）及空白，返回首个有效词前的文本。

    只处理开头的注释，语句中间的注释保留（由关键字扫描整体覆盖）。
    """
    text = cypher.lstrip()
    while True:
        if text.startswith("//"):
            newline = text.find("\n")
            if newline == -1:
                return ""
            text = text[newline + 1:].lstrip()
        elif text.startswith("/*"):
            end = text.find("*/")
            if end == -1:
                return ""
            text = text[end + 2:].lstrip()
        else:
            return text


def validate_readonly(cypher: str) -> None:
    """校验语句为只读；违规抛 ReadonlyViolation（中文消息）。

    双层校验：
    1. 开头关键字白名单（忽略前导注释/空白/大小写）；
    2. 全语句扫描写关键字（字面量已替换为占位符，不会误伤）。
    """
    stripped = _strip_leading_comments(cypher)
    if not stripped:
        raise ReadonlyViolation("当前为只读模式，不允许空语句")

    upper = stripped.upper()
    matched = None
    for kw in _READONLY_START_KEYWORDS:
        if upper.startswith(kw):
            matched = kw
            break
    if matched is None:
        raise ReadonlyViolation(
            f"当前为只读模式，不允许写操作：语句必须以 {'/'.join(_READONLY_START_KEYWORDS)} 开头"
        )

    # 全语句扫描写关键字（字面量替换后扫描，避免误伤）
    safe_text = _strip_literals(cypher).upper()
    for kw in _WRITE_KEYWORDS:
        # 词边界匹配：关键字前后不能是标识符字符（避免 SET 误伤 RESET、SETTINGS 等）
        pattern = r"(?<![A-Z0-9_])" + re.escape(kw) + r"(?![A-Z0-9_])"
        if re.search(pattern, safe_text):
            raise ReadonlyViolation(f"当前为只读模式，不允许写操作：检测到关键字 {kw}")


# ---------------------------------------------------------------------------
# LIMIT 强制
# ---------------------------------------------------------------------------
def enforce_limit(cypher: str, default_limit: int) -> Tuple[str, bool]:
    """若顶层 RETURN 无 LIMIT 则追加，返回 (改写后语句, limitAppended)。

    启发式：整体匹配「行首 RETURN ... LIMIT n（可选分号/空白结尾）」。
    复杂语句（CALL 子查询等）启发式失败时安全追加 LIMIT，保证始终有上限。
    """
    if _LIMIT_AT_RETURN_PATTERN.search(cypher):
        return cypher, False
    # 去掉尾部空白与分号后追加 LIMIT，保持语句可执行
    trimmed = cypher.rstrip().rstrip(";").rstrip()
    return f"{trimmed} LIMIT {default_limit}", True


# ---------------------------------------------------------------------------
# 值序列化（设计文档 §6.5 表）
# ---------------------------------------------------------------------------
def serialize_value(value: Any) -> Any:
    """把 Neo4j 值递归序列化为 JSON 可传输结构。

    Node → {"__type":"node","elementId","labels","properties"}
    Relationship → {"__type":"relationship","elementId","type","startElementId","endElementId","properties"}
    Path → {"__type":"path","nodes":[...],"relationships":[...]}
    列表 / Map 递归处理；标量原样；其余类型退化为 str()。
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    # Node：有 element_id 与 labels
    if hasattr(value, "element_id") and hasattr(value, "labels"):
        return {
            "__type": "node",
            "elementId": value.element_id,
            "labels": list(value.labels),
            "properties": {k: serialize_value(v) for k, v in dict(value).items()},
        }

    # Relationship：有 element_id 与 type（无 labels）
    if hasattr(value, "element_id") and hasattr(value, "type"):
        return {
            "__type": "relationship",
            "elementId": value.element_id,
            "type": value.type,
            "startElementId": value.start_element_id,
            "endElementId": value.end_element_id,
            "properties": {k: serialize_value(v) for k, v in dict(value).items()},
        }

    # Path：有 nodes 与 relationships 序列
    if hasattr(value, "nodes") and hasattr(value, "relationships"):
        return {
            "__type": "path",
            "nodes": [serialize_value(n) for n in value.nodes],
            "relationships": [serialize_value(r) for r in value.relationships],
        }

    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]

    if isinstance(value, dict):
        return {str(k): serialize_value(v) for k, v in value.items()}

    # 时间/日期/空间等 neo4j 扩展类型：退化为字符串表示，保证可 JSON 化
    return str(value)


# ---------------------------------------------------------------------------
# 执行
# ---------------------------------------------------------------------------
async def _execute_and_serialize(driver, database: str, cypher: str,
                                 timeout_ms: int) -> Dict[str, Any]:
    """在 READ 事务中执行语句并序列化结果（内部函数，供 run_query 与路由测试复用）。

    返回 {"columns","rows","graph","truncated","elapsedMs"}：
    - columns：首条记录的键列表（无记录为空数组）；
    - rows：每行 {列名: 序列化值}；
    - graph：聚合行内 node/relationship 列，按 elementId 去重；
    - truncated：结果行数达到 limit（调用方传入的 limit 与行数比较）；
    - elapsedMs：执行耗时（毫秒，整数）。
    """
    started = time.monotonic()
    async with driver.session(database=database, default_access_mode="READ") as session:
        async with session.begin_transaction(timeout=timeout_ms / 1000) as tx:
            result = await tx.run(cypher)
            records = [record async for record in result]
            await tx.commit()

    elapsed_ms = int((time.monotonic() - started) * 1000)

    columns: List[str] = list(records[0].keys()) if records else []
    rows: List[Dict[str, Any]] = []
    graph_nodes: Dict[str, Dict[str, Any]] = {}
    graph_rels: Dict[str, Dict[str, Any]] = {}

    for record in records:
        row: Dict[str, Any] = {}
        for key, value in record.items():
            serialized = serialize_value(value)
            row[key] = serialized
            # 聚合 node / relationship 列到 graph（按 elementId 去重）
            if isinstance(serialized, dict):
                if serialized.get("__type") == "node":
                    graph_nodes[serialized["elementId"]] = serialized
                elif serialized.get("__type") == "relationship":
                    graph_rels[serialized["elementId"]] = serialized
                elif serialized.get("__type") == "path":
                    for n in serialized["nodes"]:
                        graph_nodes[n["elementId"]] = n
                    for r in serialized["relationships"]:
                        graph_rels[r["elementId"]] = r
        rows.append(row)

    # truncated 语义：结果行数达到 limit（由调用方根据 limit 判定，此处用 rows 数返回）
    return {
        "columns": columns,
        "rows": rows,
        "graph": {
            "nodes": list(graph_nodes.values()),
            "relationships": list(graph_rels.values()),
        },
        "truncated": False,  # 由 run_query 根据 limit 覆盖
        "elapsedMs": elapsed_ms,
    }


async def run_query(driver, database: str, cypher: str, limit: int,
                    timeout_ms: int) -> Dict[str, Any]:
    """校验只读 + 强制 LIMIT + 执行 + 序列化，返回统一结果结构。

    driver 以 default_access_mode=READ 兜底；写语句在校验阶段即被拒绝，
    不会到达 driver。truncated = 结果行数 >= limit。
    """
    validate_readonly(cypher)
    final_cypher, _ = enforce_limit(cypher, limit)

    result = await _execute_and_serialize(driver, database, final_cypher, timeout_ms)
    result["truncated"] = len(result["rows"]) >= limit
    return result
