"""skill_delete BuiltinTool — 删除 Agent 技能

P2-② Memory procedural

行为：
- 按 name 删除技能；不存在返回 error
- 严格按 (agent_id, user_id) 隔离

可用性：
- 仅当 Agent.memory_procedural_enabled == True 时启用
"""
import logging

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.base import BuiltinTool
from app.services.harness.tools.skill_save import _to_uuid, _check_procedural_enabled

logger = logging.getLogger(__name__)


class SkillDeleteTool(BuiltinTool):
    """删除技能工具"""

    name = "skill_delete"
    display_name = "删除技能"
    description = "删除指定名称的技能（仅在用户明确要求删除时使用）。"
    parameters_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "要删除的技能名"},
        },
        "required": ["name"],
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "deleted": {"type": "boolean"},
        },
    }

    def is_available(self, ctx: ToolContext) -> bool:
        """仅当 Agent.memory_procedural_enabled 为 True 时启用。"""
        return _check_procedural_enabled(ctx)

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        if not isinstance(args, dict):
            return ToolResult.error("参数格式错误")

        name = str(args.get("name") or "").strip()
        if not name:
            return ToolResult.error("name 不能为空")

        db = getattr(ctx, "db", None)
        if db is None:
            return ToolResult.error("数据库连接不可用")
        agent_uuid = _to_uuid(getattr(ctx, "agent_id", None))
        user_uuid = _to_uuid(getattr(ctx, "user_id", None))
        if agent_uuid is None:
            return ToolResult.error("agent_id 缺失或无效")
        if user_uuid is None:
            return ToolResult.error("user_id 缺失或无效")

        try:
            from app.services.harness.skill_service import SkillService

            svc = SkillService(db)
            ok = await svc.delete(agent_uuid, user_uuid, name)
            if not ok:
                return ToolResult.error(f"技能 {name} 不存在")
            logger.info("技能已删除: agent=%s name=%s", agent_uuid, name)
            return ToolResult.json({"name": name, "deleted": True})
        except Exception as e:
            logger.error("skill_delete 失败: %s", type(e).__name__, exc_info=True)
            return ToolResult.error(f"删除技能失败: {type(e).__name__}")
