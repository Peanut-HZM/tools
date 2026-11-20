"""Cypher 查询构建器（纯函数，全部参数化）。

所有函数返回 (cypher, params) 二元组，调用方负责在只读事务中执行。
设计契约见 docs/superpowers/specs/2026-11-20-neo4j-explorer-design.md §6。
"""
from typing import Any, Dict, List, Optional, Tuple


def build_sample_query(
    labels: List[str],
    rel_types: List[str],
    node_limit_per_label: int,
    rel_limit: int,
) -> Tuple[str, Dict[str, Any]]:
    """构建采样查询：每 Label 取前 node_limit_per_label 个节点（按 elementId 升序），
    并返回已采样节点之间的内部关系（最多 rel_limit 条）。

    - labels 为空时退化为全图节点采样（无 Label 过滤）。
    - rel_types 非空时只保留指定类型的关系。
    """
    params: Dict[str, Any] = {}

    # 每个 Label 一个子查询，UNION 合并（利用 elementId 有序快速返回，不随机扫全表）
    union_parts = []
    for label in labels or [None]:
        label_expr = f":{_assert_safe_name(label, 'Label')}" if label else ""
        union_parts.append(
            f"MATCH (n{label_expr}) RETURN n ORDER BY elementId(n) LIMIT {int(node_limit_per_label)}"
        )
    union_cypher = "\nUNION\n".join(union_parts)

    if rel_types:
        type_filter = ":" + "|".join(
            _assert_safe_name(t, "关系类型") for t in rel_types
        )
    else:
        type_filter = ""

    cypher = (
        f"CALL {{\n{union_cypher}\n}}\n"
        "WITH collect(DISTINCT n) AS sampled\n"
        f"MATCH (a)-[r{type_filter}]->(b)\n"
        "WHERE elementId(a) IN [x IN sampled | elementId(x)]\n"
        "  AND elementId(b) IN [x IN sampled | elementId(x)]\n"
        f"RETURN sampled, r LIMIT {int(rel_limit)}"
    )
    return cypher, params


def build_expand_query(
    node_id: str,
    direction: str,
    rel_types: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[str, Dict[str, Any]]:
    """构建邻居展开查询，同时返回 total（用 count 子查询）。

    - direction: both | in | out
    - rel_types: None/空列表表示不过滤类型
    """
    if direction not in ("both", "in", "out"):
        raise ValueError(f"非法的方向参数: {direction!r}")

    if rel_types:
        type_filter = ":" + "|".join(
            _assert_safe_name(t, "关系类型") for t in rel_types
        )
    else:
        type_filter = ""

    if direction == "in":
        pattern = f"(m)-[r{type_filter}]->(n)"
    elif direction == "out":
        pattern = f"(n)-[r{type_filter}]->(m)"
    else:  # both
        pattern = f"(n)-[r{type_filter}]-(m)"

    # 主查询只取邻居数据；total 由 build_expand_count_query 单独查询（超时降级 null）
    cypher = (
        "MATCH (n) WHERE elementId(n) = $node_id\n"
        f"MATCH {pattern}\n"
        "RETURN n, r, m\n"
        "ORDER BY elementId(r)\n"
        "SKIP $offset LIMIT $limit"
    )
    params: Dict[str, Any] = {
        "node_id": node_id,
        "offset": int(offset),
        "limit": int(limit),
    }
    return cypher, params


def build_expand_count_query(
    node_id: str,
    direction: str,
    rel_types: Optional[List[str]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """邻居总数统计查询（调用方负责超时控制，超时返回 total=None）。

    复用 build_expand_query 的校验与 pattern 逻辑：direction 与 rel_types
    在这里只做透传，由 build_expand_query 统一做白名单校验。
    """
    # 先跑一遍主查询逻辑做校验（返回值弃用），避免重复校验代码
    build_expand_query(node_id, direction, rel_types, limit=1, offset=0)

    if rel_types:
        type_filter = ":" + "|".join(
            _assert_safe_name(t, "关系类型") for t in rel_types
        )
    else:
        type_filter = ""

    if direction == "in":
        pattern = f"(m)-[r{type_filter}]->(n)"
    elif direction == "out":
        pattern = f"(n)-[r{type_filter}]->(m)"
    else:  # both
        pattern = f"(n)-[r{type_filter}]-(m)"

    cypher = (
        "MATCH (n) WHERE elementId(n) = $node_id\n"
        f"MATCH {pattern}\n"
        "RETURN count(r) AS total"
    )
    params: Dict[str, Any] = {"node_id": node_id}
    return cypher, params


def build_search_query(q: str, limit: int = 20) -> Tuple[str, Dict[str, Any]]:
    """跨属性模糊搜索：任意属性值的字符串形式包含 q 即命中。"""
    cypher = (
        "MATCH (n)\n"
        "WHERE any(k IN keys(n) | toString(n[k]) CONTAINS $q)\n"
        "RETURN n\n"
        "ORDER BY elementId(n)\n"
        "LIMIT $limit"
    )
    params: Dict[str, Any] = {"q": q, "limit": int(limit)}
    return cypher, params


def _assert_safe_name(name: str, kind: str) -> str:
    """Cypher 标识符白名单校验（动态片段无法参数化，防止注入）。"""
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"非法的{kind}名: {name!r}")
    return name
