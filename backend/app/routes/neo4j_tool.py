"""Neo4j 浏览器工具 —— 连接 CRUD + 连通性测试接口。

设计要点：
- 连接按 user_id 隔离，越权访问统一返回 404（不暴露资源存在性）。
- 密码 Fernet 加密落库（app.services.neo4j.crypto），响应与日志永不出现密码/密文。
- test 接口用同步 driver 做一次性连通性探测，异常映射为友好中文。
图数据接口由 Task 3/4 在本文件追加。
"""
import asyncio
import inspect
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.middleware import auth_middleware
from app.models import get_db
from app.models.neo4j_models import (
    Neo4jConnection,
    Neo4jConnectionCreate,
    Neo4jConnectionResponse,
    Neo4jConnectionUpdate,
)
from app.services.neo4j import crypto as neo4j_crypto
from app.services.neo4j import driver_manager as neo4j_driver_manager
from app.services.neo4j import query_builder as neo4j_query_builder
from app.services.neo4j import schema_service as neo4j_schema_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/neo4j-tool", tags=["neo4j-tool"])


async def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """代理到 app.middleware.auth_middleware.get_current_user_id。

    测试通过 monkeypatch 替换 auth_middleware 模块内函数，Depends 在
    请求期动态解析，包装代理保证 monkeypatch 始终生效。
    """
    return await _resolve_current_user_id(authorization)


async def _resolve_current_user_id(authorization: Optional[str]) -> str:
    # monkeypatch 可能替换为同步 lambda，两种形态都兼容
    result = auth_middleware.get_current_user_id(authorization)
    if inspect.isawaitable(result):
        return await result
    return result


# ---------------------------------------------------------------------------
# 依赖函数
# ---------------------------------------------------------------------------
def get_owned_connection(
    db: Session, user_id: str, conn_id: str
) -> Neo4jConnection:
    """按 ID + user_id 双条件查询连接；查不到或越权统一抛 404。

    不区分「不存在」与「他人资源」，避免暴露资源存在性。
    """
    conn = (
        db.query(Neo4jConnection)
        .filter(Neo4jConnection.id == conn_id, Neo4jConnection.user_id == user_id)
        .first()
    )
    if conn is None:
        raise HTTPException(status_code=404, detail="连接不存在或无权访问")
    return conn


def decrypt_conn_password(conn: Neo4jConnection) -> str:
    """解密连接密码；crypto 未配置或解密失败抛 503。"""
    try:
        return neo4j_crypto.decrypt_password(conn.encrypted_password)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


def _open_test_driver(uri: str, username: str, password: str, database: Optional[str] = None):
    """打开一个同步 Neo4j driver（仅用于连通性测试，调用方负责 close）。"""
    from neo4j import GraphDatabase

    kwargs = {}
    if database:
        kwargs["database"] = database
    return GraphDatabase.driver(uri, auth=(username, password), **kwargs)


def _map_test_error(exc: Exception) -> str:
    """把 neo4j 异常映射为友好中文错误信息（不泄露密码与凭据段）。"""
    # 延迟导入：neo4j 包为 Task 5 统一纳入依赖，异常类型仅在真实驱动时报出
    try:
        from neo4j.exceptions import AuthError, ServiceUnavailable, OSErrorError
    except Exception:  # noqa: BLE001 - 驱动不可用时无法分类，走兜底文案
        AuthError = ServiceUnavailable = OSErrorError = ()  # type: ignore

    if isinstance(exc, AuthError):
        return "用户名或密码错误"
    if isinstance(exc, ServiceUnavailable):
        return "无法连接到数据库，请检查地址与网络"
    if isinstance(exc, OSErrorError):
        return "连接超时"
    text = str(exc) or type(exc).__name__
    # 兜底：屏蔽可能包含凭据的异常原文，只保留异常类型
    return f"连接失败：{type(exc).__name__}" if text else "连接失败"


# ---------------------------------------------------------------------------
# 连接 CRUD
# ---------------------------------------------------------------------------
@router.get("/connections", response_model=List[Neo4jConnectionResponse])
async def list_connections(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """列出当前用户的全部 Neo4j 连接（不含密码）。"""
    return (
        db.query(Neo4jConnection)
        .filter(Neo4jConnection.user_id == user_id)
        .order_by(Neo4jConnection.created_at.desc())
        .all()
    )


@router.get("/connections/{conn_id}", response_model=Neo4jConnectionResponse)
async def get_connection(
    conn_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """获取单个连接详情（不含密码）。"""
    return get_owned_connection(db, user_id, conn_id)


@router.post("/connections", response_model=Neo4jConnectionResponse)
async def create_connection(
    req: Neo4jConnectionCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """新建 Neo4j 连接；密码加密落库，响应不回传。"""
    try:
        encrypted = neo4j_crypto.encrypt_password(req.password)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    conn = Neo4jConnection(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=req.name,
        uri=req.uri,
        username=req.username,
        encrypted_password=encrypted,
        database=req.database or "neo4j",
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    logger.info("Neo4j 连接已创建: id=%s name=%s user=%s", conn.id, conn.name, user_id)
    return conn


@router.put("/connections/{conn_id}", response_model=Neo4jConnectionResponse)
async def update_connection(
    req: Neo4jConnectionUpdate,
    conn_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """更新连接；password 留空表示不变，其余字段 None 表示不变。"""
    conn = get_owned_connection(db, user_id, conn_id)

    if req.name is not None:
        conn.name = req.name
    if req.uri is not None:
        conn.uri = req.uri
    if req.username is not None:
        conn.username = req.username
    if req.database is not None:
        conn.database = req.database
    if req.password:  # 非空才更新密文
        try:
            conn.encrypted_password = neo4j_crypto.encrypt_password(req.password)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    db.commit()
    db.refresh(conn)
    logger.info("Neo4j 连接已更新: id=%s user=%s", conn.id, user_id)
    return conn


@router.delete("/connections/{conn_id}")
async def delete_connection(
    conn_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """删除连接（先校验归属，越权 404）；同步关闭缓存的 AsyncDriver。"""
    conn = get_owned_connection(db, user_id, conn_id)
    db.delete(conn)
    db.commit()
    await neo4j_driver_manager.driver_manager.close_driver(conn_id)
    logger.info("Neo4j 连接已删除: id=%s user=%s", conn_id, user_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# 连通性测试
# ---------------------------------------------------------------------------
@router.post("/connections/{conn_id}/test")
async def test_connection(
    conn_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """测试连接连通性，返回 ok / server_version / error（均不含密码）。"""
    conn = get_owned_connection(db, user_id, conn_id)
    password = decrypt_conn_password(conn)

    driver = None
    try:
        driver = _open_test_driver(conn.uri, conn.username, password, conn.database)
        driver.verify_connectivity()
        info = driver.get_server_info()
        server_version = getattr(info, "agent", None) or str(info)
        return {"ok": True, "server_version": server_version, "error": None}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - 全部映射为友好中文
        logger.warning(
            "Neo4j 连通性测试失败: id=%s uri=%s err=%s",
            conn.id, conn.uri.split("@")[-1], type(exc).__name__,
        )
        return {"ok": False, "server_version": None, "error": _map_test_error(exc)}
    finally:
        if driver is not None:
            try:
                driver.close()
            except Exception:  # noqa: BLE001 - close 失败不影响结果
                pass


# ---------------------------------------------------------------------------
# 图数据接口（schema / sample / expand / search）
# ---------------------------------------------------------------------------
class GraphSampleRequest(BaseModel):
    """采样请求体：按 Label 采样节点 + 已采样节点间的内部关系。"""
    labels: List[str] = Field(default_factory=list)
    relTypes: List[str] = Field(default_factory=list)
    nodeLimitPerLabel: int = Field(default=200, ge=1, le=1000)
    relLimit: int = Field(default=500, ge=1, le=5000)


class GraphExpandRequest(BaseModel):
    """邻居展开请求体。"""
    nodeId: str
    direction: str = Field(default="both", pattern="^(both|in|out)$")
    relTypes: List[str] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


def _node_to_json(node) -> Dict[str, Any]:
    """Node → 统一图格式节点（id 用 elementId 字符串）。"""
    return {
        "id": node.element_id,
        "labels": list(node.labels),
        "properties": dict(node),
    }


def _rel_to_json(rel) -> Dict[str, Any]:
    """Relationship → 统一图格式关系。"""
    return {
        "id": rel.element_id,
        "type": rel.type,
        "source": rel.start_node.element_id,
        "target": rel.end_node.element_id,
        "properties": dict(rel),
    }


def _build_graph_response(nodes: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
    """按 elementId 去重后组装统一图格式响应。"""
    unique_nodes: Dict[str, Dict[str, Any]] = {}
    for n in nodes:
        unique_nodes[n["id"]] = n
    unique_rels: Dict[str, Dict[str, Any]] = {}
    for r in relationships:
        unique_rels[r["id"]] = r
    return {
        "nodes": list(unique_nodes.values()),
        "relationships": list(unique_rels.values()),
        "truncated": False,
    }


async def _get_graph_driver(conn: Neo4jConnection):
    """按连接配置获取（或创建）缓存的 AsyncDriver。异常映射为友好中文。"""
    password = decrypt_conn_password(conn)
    try:
        return await neo4j_driver_manager.driver_manager.get_driver(
            conn.id, conn.uri, conn.username, password
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - driver 创建失败映射为连接错误
        safe_uri = conn.uri.split("@")[-1]
        logger.warning(
            "Neo4j driver 创建失败: id=%s uri=%s err=%s",
            conn.id, safe_uri, type(exc).__name__,
        )
        raise HTTPException(status_code=502, detail="无法连接到 Neo4j 数据库，请检查配置")


@router.get("/connections/{conn_id}/schema")
async def get_schema(
    conn_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """获取 Neo4j schema 概览：labels（含 count/estimated/sampleProperties）、relationshipTypes、propertyKeys。"""
    from neo4j.api import READ_ACCESS

    conn = get_owned_connection(db, user_id, conn_id)
    driver = await _get_graph_driver(conn)

    try:
        return await neo4j_schema_service.get_schema(driver, conn.database)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - schema 查询失败统一 502
        safe_uri = conn.uri.split("@")[-1]
        logger.warning(
            "Neo4j schema 查询失败: id=%s uri=%s err=%s",
            conn.id, safe_uri, type(exc).__name__,
        )
        raise HTTPException(status_code=502, detail="Neo4j schema 查询失败")


@router.post("/connections/{conn_id}/graph/sample")
async def graph_sample(
    conn_id: str,
    req: GraphSampleRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """按 Label 采样节点 + 已采样节点间的内部关系，返回统一图格式。"""
    from neo4j.api import READ_ACCESS

    conn = get_owned_connection(db, user_id, conn_id)
    driver = await _get_graph_driver(conn)

    cypher, params = neo4j_query_builder.build_sample_query(
        labels=req.labels,
        rel_types=req.relTypes,
        node_limit_per_label=req.nodeLimitPerLabel,
        rel_limit=req.relLimit,
    )

    try:
        async with driver.session(database=conn.database, default_access_mode=READ_ACCESS) as session:
            result = await session.run(cypher, params)
            records = [r async for r in result]

        nodes: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []
        for record in records:
            sampled = record.get("sampled") or []
            rel = record.get("r")
            for node in sampled:
                nodes.append(_node_to_json(node))
            if rel is not None:
                relationships.append(_rel_to_json(rel))

        graph = _build_graph_response(nodes, relationships)
        # 截断标记：任一 Label 采样数达到每 Label 上限，或关系数达到 relLimit
        node_cap_hit = bool(req.labels) and len(graph["nodes"]) >= req.nodeLimitPerLabel
        rel_cap_hit = len(graph["relationships"]) >= req.relLimit
        graph["truncated"] = bool(node_cap_hit or rel_cap_hit)
        return graph
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - 查询失败统一 502
        safe_uri = conn.uri.split("@")[-1]
        logger.warning(
            "Neo4j 采样查询失败: id=%s uri=%s err=%s",
            conn.id, safe_uri, type(exc).__name__,
        )
        raise HTTPException(status_code=502, detail="Neo4j 采样查询失败")


@router.post("/connections/{conn_id}/graph/expand")
async def graph_expand(
    conn_id: str,
    req: GraphExpandRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """展开指定节点的邻居，返回 {"graph": {...}, "total": int|null}。
    total 单独统计，查询超时返回 null（前端显示"继续加载"但不显示具体剩余数量）。
    """
    from neo4j.api import READ_ACCESS

    conn = get_owned_connection(db, user_id, conn_id)
    driver = await _get_graph_driver(conn)

    cypher, params = neo4j_query_builder.build_expand_query(
        node_id=req.nodeId,
        direction=req.direction,
        rel_types=req.relTypes or None,
        limit=req.limit,
        offset=req.offset,
    )
    count_cypher, count_params = neo4j_query_builder.build_expand_count_query(
        node_id=req.nodeId,
        direction=req.direction,
        rel_types=req.relTypes or None,
    )

    try:
        async with driver.session(database=conn.database, default_access_mode=READ_ACCESS) as session:
            result = await session.run(cypher, params)
            records = [r async for r in result]

        # total 单独查询：超时（5s）降级为 None，不影响 graph 数据
        total: Optional[int] = None
        try:
            async with driver.session(database=conn.database, default_access_mode=READ_ACCESS) as session:
                total_result = await asyncio.wait_for(
                    _collect_expand_total(session, count_cypher, count_params),
                    timeout=5.0,
                )
                total = total_result
        except asyncio.TimeoutError:
            logger.warning("Neo4j expand total 统计超时: conn=%s", conn.id)
        except Exception as exc:  # noqa: BLE001 - total 失败不阻断 graph 返回
            logger.warning(
                "Neo4j expand total 统计失败: id=%s err=%s", conn.id, type(exc).__name__
            )

        nodes: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []
        for record in records:
            center = record.get("n")
            rel = record.get("r")
            neighbor = record.get("m")
            if center is not None:
                nodes.append(_node_to_json(center))
            if neighbor is not None:
                nodes.append(_node_to_json(neighbor))
            if rel is not None:
                relationships.append(_rel_to_json(rel))

        graph = _build_graph_response(nodes, relationships)
        return {"graph": graph, "total": total}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - 查询失败统一 502
        safe_uri = conn.uri.split("@")[-1]
        logger.warning(
            "Neo4j 展开查询失败: id=%s uri=%s err=%s",
            conn.id, safe_uri, type(exc).__name__,
        )
        raise HTTPException(status_code=502, detail="Neo4j 展开查询失败")


async def _collect_expand_total(session, cypher: str, params: Dict[str, Any]) -> Optional[int]:
    """执行 total 统计并取首条记录的 total 字段。"""
    result = await session.run(cypher, params)
    records = [r async for r in result]
    if not records:
        return None
    return records[0].get("total")


@router.get("/connections/{conn_id}/nodes/search")
async def nodes_search(
    conn_id: str,
    q: str,
    limit: int = Query(default=20, ge=1, le=500),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """跨属性模糊搜索节点，返回统一图格式（只含节点）。"""
    from neo4j.api import READ_ACCESS

    conn = get_owned_connection(db, user_id, conn_id)
    driver = await _get_graph_driver(conn)

    cypher, params = neo4j_query_builder.build_search_query(q=q, limit=limit)

    try:
        async with driver.session(database=conn.database, default_access_mode=READ_ACCESS) as session:
            result = await session.run(cypher, params)
            records = [r async for r in result]

        nodes = [_node_to_json(record["n"]) for record in records]
        return _build_graph_response(nodes, [])
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - 查询失败统一 502
        safe_uri = conn.uri.split("@")[-1]
        logger.warning(
            "Neo4j 搜索失败: id=%s uri=%s err=%s",
            conn.id, safe_uri, type(exc).__name__,
        )
        raise HTTPException(status_code=502, detail="Neo4j 搜索失败")
