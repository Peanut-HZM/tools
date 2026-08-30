"""skill_save BuiltinTool — 保存/更新 Agent 技能

P2-② Memory procedural

行为：
- 按 name UPSERT 技能（更新时 use_count 保留）
- 严格按 (agent_id, user_id) 隔离

可用性：
- 仅当 Agent.memory_procedural_enabled == True 时启用
"""
import logging
import uuid
from typing import Optional

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.base import BuiltinTool

logger = logging.getLogger(__name__)

# name 字段最大长度（与 AgentProceduralMemory.name 列一致）
_MAX_NAME_LENGTH = 100


def _to_uuid(value) -> Optional[uuid.UUID]:
    """将字符串或 UUID 转换为 UUID 对象，转换失败返回 None。"""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _check_procedural_enabled(ctx: ToolContext) -> bool:
    """查询 Agent.memory_procedural_enabled；异常时保守返回 False。"""
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
        return bool(getattr(agent, "memory_procedural_enabled", False))
    except Exception as e:
        # 异常日志脱敏：仅记录异常类型名
        logger.warning("技能工具门控查询异常: %s", type(e).__name__)
        return False


class SkillSaveTool(BuiltinTool):
    """保存/更新技能工具"""

    name = "skill_save"
    display_name = "保存技能"
    description = (
        "把当前验证有效的操作流程/方法保存为命名技能，供以后复用。"
        "name 为简短标识（英文/拼音），trigger 描述何时使用，content 为完整步骤。"
        "同名保存会更新已有技能（使用次数保留）。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "技能名（≤100 字符）",
                "maxLength": _MAX_NAME_LENGTH,
            },
            "trigger": {"type": "string", "description": "何时使用该技能（触发条件）"},
            "content": {"type": "string", "description": "技能完整内容（步骤/规则）"},
            "importance": {
                "type": "number",
                "description": "重要度 0-1，默认 0.5",
                "minimum": 0,
                "maximum": 1,
            },
        },
        "required": ["name", "trigger", "content"],
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "saved": {"type": "boolean"},
        },
    }

    def is_available(self, ctx: ToolContext) -> bool:
        """仅当 Agent.memory_procedural_enabled 为 True 时启用。"""
        return _check_procedural_enabled(ctx)

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        # 1. 参数校验
        if not isinstance(args, dict):
            return ToolResult.error("参数格式错误")

        name = str(args.get("name") or "").strip()
        trigger = str(args.get("trigger") or "").strip()
        content = str(args.get("content") or "").strip()
        if not name:
            return ToolResult.error("name 不能为空")
        if len(name) > _MAX_NAME_LENGTH:
            return ToolResult.error(f"name 长度超过限制（{_MAX_NAME_LENGTH}）")
        if not trigger:
            return ToolResult.error("trigger 不能为空")
        if not content:
            return ToolResult.error("content 不能为空")

        importance = args.get("importance", 0.5)
        try:
            importance = float(importance)
        except (TypeError, ValueError):
            return ToolResult.error("importance 必须为数字")
        if not (0.0 <= importance <= 1.0):
            return ToolResult.error("importance 必须在 0-1 之间")

        # 2. 上下文校验
        db = getattr(ctx, "db", None)
        if db is None:
            return ToolResult.error("数据库连接不可用")
        agent_uuid = _to_uuid(getattr(ctx, "agent_id", None))
        user_uuid = _to_uuid(getattr(ctx, "user_id", None))
        if agent_uuid is None:
            return ToolResult.error("agent_id 缺失或无效")
        if user_uuid is None:
            return ToolResult.error("user_id 缺失或无效")

        # 3. 保存
        try:
            from app.services.harness.skill_service import SkillService

            svc = SkillService(db)
            await svc.save(agent_uuid, user_uuid, name, trigger, content, importance)
            logger.info("技能已保存: agent=%s name=%s", agent_uuid, name)
            return ToolResult.json({"name": name, "saved": True})
        except Exception as e:
            logger.error("skill_save 失败: %s", type(e).__name__, exc_info=True)
            return ToolResult.error(f"保存技能失败: {type(e).__name__}")
