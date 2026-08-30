"""file_list BuiltinTool — 列出工作区文件

P2-③ 多模态沙箱
递归列出 (agent_id, user_id) 工作区内的文件，上限 200 条。
可用性：仅当 Agent.sandbox_enabled == True 时启用。
"""
import logging

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.base import BuiltinTool
from app.services.harness.tools.file_read import _agent_user_uuids, _check_sandbox_enabled
from app.services.harness.workspace import PathEscapeError, WorkspaceFileError, WorkspaceService

logger = logging.getLogger(__name__)


class FileListTool(BuiltinTool):
    """列出工作区文件工具"""

    name = "file_list"
    display_name = "列出文件"
    description = "列出当前工作区中的文件（相对路径与大小），最多 200 条。"
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "子目录相对路径（不传则列出整个工作区）",
            },
        },
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "size_bytes": {"type": "integer"},
                    },
                },
            },
            "count": {"type": "integer"},
        },
    }

    def is_available(self, ctx: ToolContext) -> bool:
        return _check_sandbox_enabled(ctx)

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        if not isinstance(args, dict):
            return ToolResult.error("参数格式错误")
        path = str(args.get("path") or "").strip()

        agent_uuid, user_uuid = _agent_user_uuids(ctx)
        if agent_uuid is None or user_uuid is None:
            return ToolResult.error("agent_id/user_id 缺失或无效")

        try:
            svc = WorkspaceService()
            files = svc.list_files(str(agent_uuid), str(user_uuid), path)
            return ToolResult.json({"files": files, "count": len(files)})
        except PathEscapeError as e:
            return ToolResult.error(str(e))
        except WorkspaceFileError as e:
            return ToolResult.error(str(e))
        except Exception as e:
            logger.error("file_list 失败: %s", type(e).__name__, exc_info=True)
            return ToolResult.error(f"列出文件失败: {type(e).__name__}")
