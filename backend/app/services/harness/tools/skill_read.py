"""skill_read BuiltinTool — 读取 Agent 技能（索引或完整内容）

P2-② Memory procedural

行为：
- 不传 name：返回启用技能索引 [{name, trigger, use_count}]（渐进披露的发现入口）
- 传 name：返回完整内容 {name, trigger, content, use_count}，并 use_count += 1（读即计数）
- 禁用技能返回 error

可用性：
- 仅当 Agent.memory_procedural_enabled == True 时启用
"""
import logging
from typing import Optional

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.base import BuiltinTool
from app.services.harness.tools.skill_save import _to_uuid, _check_procedural_enabled

logger = logging.getLogger(__name__)


class SkillReadTool(BuiltinTool):
    """读取技能工具"""

    name = "skill_read"
    display_name = "读取技能"
    description = (
        "读取 Agent 技能。不传 name 返回可用技能索引（名称+触发条件）；"
        "传 name 返回该技能的完整内容。当任务匹配技能触发条件时应先读取再遵循执行。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "技能名（不传则返回索引）"},
        },
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "trigger": {"type": "string"},
            "content": {"type": "string"},
            "use_count": {"type": "integer"},
        },
        "description": "完整读取返回单个对象；索引读取返回 {records: [...]}",
    }

    def is_available(self, ctx: ToolContext) -> bool:
        """仅当 Agent.memory_procedural_enabled 为 True 时启用。"""
        return _check_procedural_enabled(ctx)

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        if not isinstance(args, dict):
            return ToolResult.error("参数格式错误")

        raw_name = args.get("name")
        if raw_name is not None:
            if not isinstance(raw_name, str):
                return ToolResult.error("name 必须为字符串")
            name = raw_name.strip()
            if not name:
                return ToolResult.error("name 不能为空")
        else:
            name = None

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

            # 完整读取
            if name is not None:
                row = await svc.get(agent_uuid, user_uuid, name)
                if row is None:
                    return ToolResult.error(f"技能 {name} 不存在")
                if not row.is_enabled:
                    return ToolResult.error(f"技能 {name} 已禁用")
                # 读即计数（best-effort，失败不影响返回）
                await svc.increment_use_count(agent_uuid, user_uuid, name)
                return ToolResult.json({
                    "name": row.name,
                    "trigger": row.trigger,
                    "content": row.content,
                    "use_count": (row.use_count or 0) + 1,
                })

            # 索引读取
            rows = await svc.list_enabled(agent_uuid, user_uuid)
            return ToolResult.json({
                "records": [
                    {"name": r.name, "trigger": r.trigger, "use_count": r.use_count}
                    for r in rows
                ],
                "count": len(rows),
            })
        except Exception as e:
            logger.error("skill_read 失败: %s", type(e).__name__, exc_info=True)
            return ToolResult.error(f"读取技能失败: {type(e).__name__}")
