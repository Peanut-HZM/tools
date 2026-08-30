"""admin/mcp/servers API — MCP Server 管理

Phase 3-Plan-1A: MCP 工具支持核心骨架

端点：
- GET    /api/admin/mcp/servers          列表
- POST   /api/admin/mcp/servers          创建
- GET    /api/admin/mcp/servers/{id}     详情
- PUT    /api/admin/mcp/servers/{id}     更新
- DELETE /api/admin/mcp/servers/{id}     删除
- POST   /api/admin/mcp/servers/{id}/test  测试连接
- POST   /api/admin/mcp/servers/{id}/sync  同步工具到 ToolRegistry
"""
import json
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.api.dependencies import get_db, get_current_user
from app.models.mcp_server import McpServer
from app.schemas.mcp_server import (
    McpServerCreate,
    McpServerUpdate,
    McpServerResponse,
    McpServerTestResponse,
)
from app.services.harness.mcp_server_manager import get_mcp_server_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/mcp/servers", tags=["admin-mcp-servers"])


def require_admin(current_user: dict = Depends(get_current_user)):
    """管理员权限校验"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


def _validate_transport_config(transport: str, command: dict | None) -> None:
    """P2-①c: 按 transport 校验配置完整性。

    - sse / http：server_url 必填由 schema 保证；URL 安全校验在 connect 时做
    - stdio：command 必须为非空 dict 且含非空 command 键
    """
    if transport == "stdio":
        if not isinstance(command, dict) or not str(command.get("command") or "").strip():
            raise HTTPException(
                status_code=400,
                detail='stdio transport 需要 command 配置: {"command": "...", "args": [...], "env": {...}}',
            )


@router.get("", response_model=list[McpServerResponse])
def list_servers(
    db: DBSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """列出所有 MCP servers"""
    servers = db.query(McpServer).order_by(McpServer.created_at.desc()).all()
    return servers


@router.post("", response_model=McpServerResponse, status_code=201)
def create_server(
    data: McpServerCreate,
    db: DBSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """创建 MCP server"""
    # 检查 name 唯一性
    existing = db.query(McpServer).filter(McpServer.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Server name '{data.name}' already exists")

    # P2-①c: 按 transport 校验配置完整性
    _validate_transport_config(data.transport, data.command)

    server = McpServer(
        name=data.name,
        server_url=data.server_url,
        transport=data.transport,
        headers_json=json.dumps(data.headers) if data.headers else None,
        command_json=json.dumps(data.command, ensure_ascii=False)
        if data.transport == "stdio" and data.command
        else None,
        timeout_seconds=data.timeout_seconds,
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    logger.info(f"MCP server created: {server.name} (id={server.id}, transport={server.transport})")
    return server


@router.get("/{server_id}", response_model=McpServerResponse)
def get_server(
    server_id: UUID,
    db: DBSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """获取 MCP server 详情"""
    server = db.query(McpServer).filter(McpServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.put("/{server_id}", response_model=McpServerResponse)
def update_server(
    server_id: UUID,
    data: McpServerUpdate,
    db: DBSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """更新 MCP server"""
    server = db.query(McpServer).filter(McpServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if data.name is not None:
        server.name = data.name
    if data.server_url is not None:
        server.server_url = data.server_url
    if data.headers is not None:
        server.headers_json = json.dumps(data.headers)
    if data.command is not None:
        # P2-①c: transport 不可改，仅 stdio server 支持替换 command 配置
        if server.transport != "stdio":
            raise HTTPException(status_code=400, detail="仅 stdio 类型的 server 支持 command 配置")
        _validate_transport_config(server.transport, data.command)
        server.command_json = json.dumps(data.command, ensure_ascii=False)
    if data.timeout_seconds is not None:
        server.timeout_seconds = data.timeout_seconds
    if data.is_active is not None:
        server.is_active = data.is_active

    server.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(server)
    logger.info(f"MCP server updated: {server.name} (id={server.id}, transport={server.transport})")
    return server


@router.delete("/{server_id}", status_code=204)
def delete_server(
    server_id: UUID,
    db: DBSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """删除 MCP server"""
    server = db.query(McpServer).filter(McpServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    db.delete(server)
    db.commit()
    logger.info(f"MCP server deleted: id={server_id}")


@router.post("/{server_id}/test", response_model=McpServerTestResponse)
async def test_server(
    server_id: UUID,
    db: DBSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """测试 MCP server 连接 + 拉取工具列表"""
    server = db.query(McpServer).filter(McpServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    manager = get_mcp_server_manager()
    result = await manager.sync_server(server)

    # 更新状态
    if result["success"]:
        server.last_connected_at = datetime.utcnow()
        server.last_error = None
        server.tools_count = result["tools_count"]
    else:
        server.last_error = result.get("error", "Unknown error")

    db.commit()

    return McpServerTestResponse(
        success=result["success"],
        tools=result.get("tools", []),
        error=result.get("error"),
    )


@router.post("/{server_id}/sync")
async def sync_server(
    server_id: UUID,
    db: DBSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """同步工具到 ToolRegistry"""
    server = db.query(McpServer).filter(McpServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    manager = get_mcp_server_manager()
    result = await manager.sync_server(server)

    if result["success"]:
        server.last_connected_at = datetime.utcnow()
        server.last_error = None
        server.tools_count = result["tools_count"]
        db.commit()

    return result
