"""file_write BuiltinTool — 写入工作区文件

P2-③ 多模态沙箱
路径限制在工作区内；单次写入上限 1MB；自动创建父目录。
可用性：仅当 Agent.sandbox_enabled == True 时启用。
"""
import logging

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.base import BuiltinTool
from app.services.harness.tools.file_read import _agent_user_uuids, _check_sandbox_enabled
from app.services.harness.workspace import PathEscapeError, WorkspaceFileError, WorkspaceService

logger = logging.getLogger(__name__)


class FileWriteTool(BuiltinTool):
    """写入工作区文件工具"""

    name = "file_write"
    display_name = "写入文件"
    description = (
        "把内容写入当前工作区的文件（utf-8 文本）。"
        "mode=overwrite 覆盖（默认）或 append 追加；自动创建父目录；单次上限 1MB。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "工作区内相对路径"},
            "content": {"type": "string", "description": "要写入的文本内容"},
            "mode": {
                "type": "string",
                "enum": ["overwrite", "append"],
                "description": "写入模式，默认 overwrite",
            },
        },
        "required": ["path", "content"],
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "size_bytes": {"type": "integer"},
            "mode": {"type": "string"},
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
        if "content" not in args or args.get("content") is None:
            return ToolResult.error("content 不能为空")
        content = str(args.get("content"))
        mode = str(args.get("mode") or "overwrite")

        agent_uuid, user_uuid = _agent_user_uuids(ctx)
        if agent_uuid is None or user_uuid is None:
            return ToolResult.error("agent_id/user_id 缺失或无效")

        try:
            svc = WorkspaceService()
            result = svc.write_file(str(agent_uuid), str(user_uuid), path, content, mode=mode)
            logger.info("工作区文件已写入: agent=%s path=%s mode=%s", agent_uuid, path, mode)
            return ToolResult.json(result)
        except PathEscapeError as e:
            return ToolResult.error(str(e))
        except WorkspaceFileError as e:
            return ToolResult.error(str(e))
        except Exception as e:
            logger.error("file_write 失败: %s", type(e).__name__, exc_info=True)
            return ToolResult.error(f"写入文件失败: {type(e).__name__}")
