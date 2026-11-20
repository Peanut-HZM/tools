"""Neo4j 浏览器工具 —— 连接 CRUD + 连通性测试接口。

设计要点：
- 连接按 user_id 隔离，越权访问统一返回 404（不暴露资源存在性）。
- 密码 Fernet 加密落库（app.services.neo4j.crypto），响应与日志永不出现密码/密文。
- test 接口用同步 driver 做一次性连通性探测，异常映射为友好中文。
图数据接口由 Task 3/4 在本文件追加。
"""
import inspect
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
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
    """删除连接（先校验归属，越权 404）。"""
    conn = get_owned_connection(db, user_id, conn_id)
    db.delete(conn)
    db.commit()
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
