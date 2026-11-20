"""Schema 概览查询服务。

返回结构（设计文档 §6.1）：
{
  "labels": [{"name": "Person", "count": 1234, "estimated": false, "sampleProperties": ["name","born"]}],
  "relationshipTypes": [{"name": "ACTED_IN", "count": 2345}],
  "propertyKeys": ["name", "born", "title"]
}

- 每 Label 精确计数（count(n)）超过 5s 超时 → 降级为采样 100 条估算（estimated=True）
- sampleProperties：按 elementId 升序取该 Label 前 5 条节点，合并属性键后按字母序截断至前 10 个
- 空数据契约：某 Label 节点数为 0 时仍返回 {"name", "count": 0, "estimated": false, "sampleProperties": []}
"""
import asyncio
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# 每 Label 计数查询的超时时间（秒）
_COUNT_TIMEOUT_SECONDS = 5.0
# 采样估算时的样本量
_SAMPLE_SIZE = 100
# sampleProperties 的采样节点数与截断长度
_SAMPLE_PROPERTIES_NODE_COUNT = 5
_SAMPLE_PROPERTIES_MAX_KEYS = 10


async def get_schema(driver, database: str) -> Dict[str, Any]:
    """获取 Neo4j 实例的 schema 概览（labels / relationshipTypes / propertyKeys）。"""
    from neo4j.api import READ_ACCESS

    labels_out: List[Dict[str, Any]] = []
    relationship_types: List[Dict[str, Any]] = []
    property_keys: List[str] = []

    async with driver.session(database=database, default_access_mode=READ_ACCESS) as session:
        # 1. 全量 Label 列表（Neo4j 5 SHOW LABELS）
        result = await session.run("SHOW LABELS")
        records = [r async for r in result]
        label_names = sorted(r["label"] for r in records)

        # 2. 全量关系类型列表
        result = await session.run("SHOW RELATIONSHIP TYPES")
        records = [r async for r in result]
        rel_type_names = sorted(r["relationshipType"] for r in records)

        # 3. 全量属性键
        try:
            result = await session.run("SHOW PROPERTY KEYS")
            records = [r async for r in result]
            property_keys = sorted(r["propertyKey"] for r in records)
        except Exception as exc:  # noqa: BLE001 - 老版本无 SHOW PROPERTY KEYS，从采样兜底
            logger.warning("SHOW PROPERTY KEYS 失败，改由采样属性合并: %s", type(exc).__name__)
            property_keys = []

        # 4. 每 Label 计数 + sampleProperties
        for label in label_names:
            entry = await _describe_label(session, label)
            labels_out.append(entry)
            # propertyKeys 兜底：合并各 Label 的 sampleProperties
            if not property_keys:
                for k in entry["sampleProperties"]:
                    if k not in property_keys:
                        property_keys.append(k)

        # 5. 每关系类型计数
        for rel_type in rel_type_names:
            count = await _count_relationships(session, rel_type)
            relationship_types.append({"name": rel_type, "count": count})

    property_keys = sorted(set(property_keys))
    return {
        "labels": labels_out,
        "relationshipTypes": relationship_types,
        "propertyKeys": property_keys,
    }


async def _describe_label(session, label: str) -> Dict[str, Any]:
    """单个 Label 的 count（含超时降级）+ sampleProperties。"""
    from app.services.neo4j.query_builder import _assert_safe_name

    _assert_safe_name(label, "Label")

    # 精确计数，超时降级为采样估算
    count, estimated = await _count_label_nodes(session, label)
    sample_properties = await _sample_label_properties(session, label)

    return {
        "name": label,
        "count": count,
        "estimated": estimated,
        "sampleProperties": sample_properties,
    }


async def _count_label_nodes(session, label: str) -> tuple[int, bool]:
    """返回 (count, estimated)。超时/异常时采样估算并标记 estimated=True。"""
    cypher = f"MATCH (n:{label}) RETURN count(n) AS c"
    try:
        result = await asyncio.wait_for(
            _collect_single(session, cypher, "c"), timeout=_COUNT_TIMEOUT_SECONDS
        )
        return int(result), False
    except asyncio.TimeoutError:
        logger.warning("Label %s 计数超时，降级为采样估算", label)
    except Exception as exc:  # noqa: BLE001 - 单类失败不阻断整体 schema
        logger.warning("Label %s 计数失败，降级为采样估算: %s", label, type(exc).__name__)

    # 采样估算：取前 SAMPLE_SIZE 条，能取满说明真实数量 >= 样本量
    # fallback 同样套超时并捕获异常，保证「降级估算、永不抛」语义
    sample_cypher = f"MATCH (n:{label}) RETURN n LIMIT {_SAMPLE_SIZE}"
    try:
        records = await asyncio.wait_for(
            _collect_all(session, sample_cypher), timeout=_COUNT_TIMEOUT_SECONDS
        )
        return len(records), True
    except asyncio.TimeoutError:
        logger.warning("Label %s 采样估算也超时，返回 count=0 estimated=True", label)
        return 0, True
    except Exception as exc:  # noqa: BLE001 - 二次失败仍不阻断整体 schema
        logger.warning("Label %s 采样估算失败: %s", label, type(exc).__name__)
        return 0, True


async def _sample_label_properties(session, label: str) -> List[str]:
    """按 elementId 升序取前 5 条节点，合并属性键后按字母序截断至前 10 个。"""
    cypher = (
        f"MATCH (n:{label}) RETURN n "
        f"ORDER BY elementId(n) LIMIT {_SAMPLE_PROPERTIES_NODE_COUNT}"
    )
    try:
        records = await asyncio.wait_for(_collect_all(session, cypher), timeout=_COUNT_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.warning("Label %s sampleProperties 采样超时，返回空列表", label)
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Label %s sampleProperties 采样失败: %s", label, type(exc).__name__)
        return []

    keys: set[str] = set()
    for record in records:
        node = record["n"]
        keys.update(dict(node).keys())
    return sorted(keys)[:_SAMPLE_PROPERTIES_MAX_KEYS]


async def _count_relationships(session, rel_type: str) -> int:
    from app.services.neo4j.query_builder import _assert_safe_name

    _assert_safe_name(rel_type, "关系类型")
    cypher = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS c"
    try:
        result = await asyncio.wait_for(
            _collect_single(session, cypher, "c"), timeout=_COUNT_TIMEOUT_SECONDS
        )
        return int(result)
    except Exception as exc:  # noqa: BLE001 - 单类型失败返回 0 并记录
        logger.warning("关系类型 %s 计数失败: %s", rel_type, type(exc).__name__)
        return 0


async def _collect_single(session, cypher: str, key: str):
    """执行查询并取第一条记录的 key 字段。"""
    result = await session.run(cypher)
    records = [r async for r in result]
    return records[0][key] if records else None


async def _collect_all(session, cypher: str):
    """执行查询并收集全部记录。"""
    result = await session.run(cypher)
    return [r async for r in result]
