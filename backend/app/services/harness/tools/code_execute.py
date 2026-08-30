"""code_execute BuiltinTool — 工作区内执行 Python 代码（轻量沙箱）

P2-③ 多模态沙箱
执行模型：`sys.executable -I -c code` 子进程，cwd=工作区，超时 kill，
stdout/stderr 各截断 10KB。-I 隔离模式（无 user site / 忽略 PYTHONPATH），
仅标准库可用。

安全边界（明示）：进程级隔离，无网络/文件系统强隔离；
生产强隔离需求应替换为容器执行器（见 spec §5）。
可用性：仅当 Agent.sandbox_enabled == True 时启用。
"""
import logging
import subprocess
import sys

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.base import BuiltinTool
from app.services.harness.tools.file_read import _agent_user_uuids, _check_sandbox_enabled
from app.services.harness.workspace import WorkspaceService

logger = logging.getLogger(__name__)

# stdout/stderr 截断上限（字符）
_MAX_OUTPUT_CHARS = 10 * 1024
# timeout_seconds 允许范围
_MIN_TIMEOUT = 1
_MAX_TIMEOUT = 30
# 支持的语言（v1 仅 python）
_SUPPORTED_LANGUAGES = ("python",)


def _truncate_output(text: str) -> str:
    """超限截断并追加尾注"""
    if len(text) <= _MAX_OUTPUT_CHARS:
        return text
    return text[:_MAX_OUTPUT_CHARS] + "\n[truncated]"


class CodeExecuteTool(BuiltinTool):
    """工作区代码执行工具"""

    name = "code_execute"
    display_name = "执行代码"
    description = (
        "在当前工作区中执行 Python 代码（仅标准库），返回 stdout/stderr/退出码。"
        "代码以工作区为当前目录，可用相对路径读写工作区文件。"
        "非零退出码不是失败——stderr 中的错误信息可用于自我修正。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "要执行的 Python 代码"},
            "language": {
                "type": "string",
                "description": "语言，当前仅支持 python",
                "enum": list(_SUPPORTED_LANGUAGES),
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "超时秒数（默认 15，上限 30）",
                "minimum": 1,
                "maximum": 30,
            },
        },
        "required": ["code"],
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "stdout": {"type": "string"},
            "stderr": {"type": "string"},
            "exit_code": {"type": ["integer", "null"]},
            "timed_out": {"type": "boolean"},
        },
    }

    def is_available(self, ctx: ToolContext) -> bool:
        return _check_sandbox_enabled(ctx)

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        if not isinstance(args, dict):
            return ToolResult.error("参数格式错误")
        code = args.get("code")
        if not isinstance(code, str) or not code.strip():
            return ToolResult.error("code 不能为空")

        language = str(args.get("language") or "python").strip().lower()
        if language not in _SUPPORTED_LANGUAGES:
            return ToolResult.error(f"不支持的语言: {language}（当前仅支持 python）")

        try:
            timeout_seconds = int(args.get("timeout_seconds", 15))
        except (TypeError, ValueError):
            return ToolResult.error("timeout_seconds 必须为整数")
        # 钳制到允许范围（防御性：超过上限按上限执行）
        timeout_seconds = max(_MIN_TIMEOUT, min(timeout_seconds, _MAX_TIMEOUT))

        agent_uuid, user_uuid = _agent_user_uuids(ctx)
        if agent_uuid is None or user_uuid is None:
            return ToolResult.error("agent_id/user_id 缺失或无效")

        # 工作区作为子进程 cwd（uuid 字符串无路径分隔符，直接拼接安全）
        svc = WorkspaceService()
        try:
            workdir = svc.workspace_dir(str(agent_uuid), str(user_uuid))
        except Exception as e:
            logger.error("code_execute 工作区创建失败: %s", type(e).__name__)
            return ToolResult.error("工作区不可用")

        logger.info(
            "code_execute 开始: agent=%s timeout=%ss code_len=%d",
            agent_uuid, timeout_seconds, len(code),
        )
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-c", code],
                cwd=str(workdir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
            return ToolResult.json({
                "stdout": _truncate_output(proc.stdout or ""),
                "stderr": _truncate_output(proc.stderr or ""),
                "exit_code": proc.returncode,
                "timed_out": False,
            })
        except subprocess.TimeoutExpired as e:
            # 超时：进程已被 kill，返回已捕获的部分输出
            stdout = e.stdout or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            stderr = e.stderr or ""
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            logger.warning(
                "code_execute 超时被终止: agent=%s timeout=%ss", agent_uuid, timeout_seconds
            )
            return ToolResult.json({
                "stdout": _truncate_output(stdout),
                "stderr": _truncate_output(stderr) + "\n[execution timed out]",
                "exit_code": None,
                "timed_out": True,
            })
        except Exception as e:
            logger.error("code_execute 失败: %s", type(e).__name__, exc_info=True)
            return ToolResult.error(f"代码执行失败: {type(e).__name__}")
