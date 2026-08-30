"""file_read BuiltinTool — 读取工作区文件

P2-③ 多模态沙箱
路径限制在 (agent_id, user_id) 工作区内；文本读取 + 截断保护。
可用性：仅当 Agent.sandbox_enabled == True 时启用。
"""
import logging
from typing import Optional

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.base import BuiltinTool
from app.services.harness.tools.skill_save import _to_uuid
from app.services.harness.workspace import PathEscapeError, WorkspaceFileError, WorkspaceService

logger = logging.getLogger(__name__)


def _check_sandbox_enabled(ctx: ToolContext) -> bool:
    """查询 Agent.sandbox_enabled；异常时保守返回 False（与技能门控同构）。"""
    agent_id = getattr(ctx, "agent_id", None)
    db = getattr(ctx, "db", None)
    agent_uuid = _to_uuid(agent_id)
    if agent_id is None or db is None or agent_uuid is None:
        return False
    try:
        from app.models.agent import Agent

        agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
        if agent is None:
            return False
        return bool(getattr(agent, "sandbox_enabled", False))
    except Exception as e:
        logger.warning("沙箱工具门控查询异常: %s", type(e).__name__)
        return False


def _agent_user_uuids(ctx: ToolContext):
    """提取并校验 (agent_uuid, user_uuid)；无效返回 (None, None)"""
    agent_uuid = _to_uuid(getattr(ctx, "agent_id", None))
    user_uuid = _to_uuid(getattr(ctx, "user_id", None))
    return agent_uuid, user_uuid


class FileReadTool(BuiltinTool):
    """读取工作区文件工具"""

    name = "file_read"
    display_name = "读取文件"
    description = (
        "读取当前工作区中的文本文件（utf-8）。传入相对路径；"
        "超长内容会被截断并标注 truncated。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "工作区内相对路径"},
            "max_bytes": {
                "type": "integer",
                "description": "最大读取字节数（默认 64KB，上限 1MB）",
            },
        },
        "required": ["path"],
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
            "truncated": {"type": "boolean"},
            "size_bytes": {"type": "integer"},
        },
    }

    def is_available(self, ctx: ToolContext) -> bool:
        return _check_sandbox_enabled(ctx)

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        if not isinstance(args, dict):
            return ToolResult.error("参数格式错误")
        path = str(args.get("path") or "").strip()
        if not path:
            return ToolResult.error("path 不能为空")

        max_bytes = args.get("max_bytes", 65536)
        try:
            max_bytes = int(max_bytes)
        except (TypeError, ValueError):
            return ToolResult.error("max_bytes 必须为整数")
        if not (1 <= max_bytes <= 1024 * 1024):
            return ToolResult.error("max_bytes 必须在 1-1048576 之间")

        agent_uuid, user_uuid = _agent_user_uuids(ctx)
        if agent_uuid is None or user_uuid is None:
            return ToolResult.error("agent_id/user_id 缺失或无效")

        try:
            svc = WorkspaceService()
            content, truncated = svc.read_file(
                str(agent_uuid), str(user_uuid), path, max_bytes=max_bytes
            )
            return ToolResult.json({
                "path": path,
                "content": content,
                "truncated": truncated,
                "size_bytes": len(content.encode("utf-8")),
            })
        except PathEscapeError as e:
            return ToolResult.error(str(e))
        except WorkspaceFileError as e:
            return ToolResult.error(str(e))
        except Exception as e:
            logger.error("file_read 失败: %s", type(e).__name__, exc_info=True)
            return ToolResult.error(f"读取文件失败: {type(e).__name__}")
