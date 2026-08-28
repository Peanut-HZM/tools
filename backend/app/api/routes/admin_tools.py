"""admin/tools API — 工具管理

参考 spec §8.4

端点：
- GET  /api/v1/admin/tools          列表（type / search 过滤 + 分页）
- POST /api/v1/admin/tools          注册新工具（name 唯一性校验）
- GET  /api/v1/admin/tools/builtin  内置工具清单（只读）
- GET  /api/v1/admin/tools/{id}     工具详情
- PUT  /api/v1/admin/tools/{id}     更新工具
- DELETE /api/v1/admin/tools/{id}   删除工具
"""
import logging
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from app.api.dependencies import get_db, get_current_user
from app.models.harness_models import Tool
from app.schemas.harness_schemas import (
    ToolCreate,
    ToolListView,
    ToolUpdate,
    ToolView,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/tools", tags=["admin-tools"])

# 可更新字段白名单（防止 mass assignment）
_UPDATABLE_FIELDS = frozenset({
    "display_name",
    "description",
    "config",
    "parameters_schema",
    "returns_schema",
    "is_available_condition",
    "rate_limit_per_minute",
    "is_active",
})


def require_admin(current_user: dict = Depends(get_current_user)):
    """管理员权限校验"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


def _validate_http_config(config: dict) -> None:
    """校验 HTTP 工具 config，防止 SSRF（admin 侧的输入校验）"""
    url = config.get("url")
    if not url or not isinstance(url, str):
        raise HTTPException(status_code=400, detail="HTTP 工具 config 必须包含 url 字段")
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        raise HTTPException(status_code=400, detail="HTTP 工具 url 仅支持 http/https")


def _get_builtin_tools():
    """获取内置工具实例（延迟导入避免循环依赖）"""
    from app.services.harness.tools.web_search import WebSearchTool
    from app.services.harness.tools.db_query import DbQueryTool

    return [WebSearchTool(), DbQueryTool()]


def _tool_to_view(tool: Tool) -> ToolView:
    """将 ORM Tool 转换为 ToolView（手动映射以处理 UUID / metadata_ 别名）"""
    return ToolView(
        id=str(tool.id),
        name=tool.name,
        display_name=tool.display_name,
        description=tool.description,
        type=tool.type,
        config=tool.config or {},
        parameters_schema=tool.parameters_schema or {},
        returns_schema=tool.returns_schema,
        is_available_condition=tool.is_available_condition or {},
        rate_limit_per_minute=tool.rate_limit_per_minute,
        is_active=tool.is_active,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
    )


@router.get("", response_model=ToolListView)
def list_tools(
    type: Optional[str] = Query(None, pattern="^(builtin|http|mcp|plugin)$"),
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: DBSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """工具列表（支持 type / search 过滤 + 分页）"""
    q = db.query(Tool)
    if type:
        q = q.filter(Tool.type == type)
    if search:
        q = q.filter(
            Tool.name.ilike(f"%{search}%") | Tool.display_name.ilike(f"%{search}%")
        )

    total = q.count()
    items = q.order_by(Tool.created_at.desc()).offset(skip).limit(limit).all()
    return ToolListView(items=[_tool_to_view(t) for t in items], total=total)


@router.post("", response_model=ToolView, status_code=201)
def create_tool(
    payload: ToolCreate,
    db: DBSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """注册工具（name 全局唯一）"""
    # HTTP 工具需校验 config.url scheme
    if payload.type == "http":
        _validate_http_config(payload.config)

    if db.query(Tool).filter(Tool.name == payload.name).first():
        raise HTTPException(
            status_code=400, detail=f"tool name '{payload.name}' already exists"
        )

    tool = Tool(
        name=payload.name,
        display_name=payload.display_name,
        description=payload.description,
        type=payload.type,
        config=payload.config,
        parameters_schema=payload.parameters_schema,
        returns_schema=payload.returns_schema,
        is_available_condition=payload.is_available_condition,
        rate_limit_per_minute=payload.rate_limit_per_minute,
        metadata_=payload.metadata_ or {},
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)
    logger.info(f"Tool created: {tool.name} (id={tool.id})")
    return _tool_to_view(tool)


@router.get("/builtin")
def list_builtin_tools(_admin: dict = Depends(require_admin)):
    """内置工具清单（只读，从代码注册获取）"""
    builtins = _get_builtin_tools()
    return {
        "items": [
            {
                "name": t.name,
                "display_name": t.display_name,
                "description": t.description,
                "parameters_schema": t.parameters_schema,
                "source": "builtin",
            }
            for t in builtins
        ]
    }


@router.get("/{tool_id}", response_model=ToolView)
def get_tool(tool_id: str, db: DBSession = Depends(get_db), _admin: dict = Depends(require_admin)):
    """工具详情"""
    tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="tool not found")
    return _tool_to_view(tool)


@router.put("/{tool_id}", response_model=ToolView)
def update_tool(
    tool_id: str,
    payload: ToolUpdate,
    db: DBSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """更新工具（仅更新传入字段）"""
    tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="tool not found")

    # Pydantic v2: model_dump(exclude_unset=True) 替代 dict(exclude_unset=True)
    update_data = payload.model_dump(exclude_unset=True)
    # 白名单过滤，防止 mass assignment
    for key, value in update_data.items():
        if key in _UPDATABLE_FIELDS:
            setattr(tool, key, value)

    db.commit()
    db.refresh(tool)
    logger.info(f"Tool updated: {tool.name} (id={tool.id})")
    return _tool_to_view(tool)


@router.delete("/{tool_id}", status_code=204)
def delete_tool(tool_id: str, db: DBSession = Depends(get_db), _admin: dict = Depends(require_admin)):
    """删除工具"""
    tool = db.query(Tool).filter(Tool.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="tool not found")
    db.delete(tool)
    db.commit()
    logger.info(f"Tool deleted: {tool.name} (id={tool_id})")
