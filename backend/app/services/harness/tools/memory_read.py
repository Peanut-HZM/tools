"""memory_read BuiltinTool — 读取 Agent 长期记忆

参考 spec §6.5 内置工具清单。

行为：
- 不传 key：列出当前 (agent_id, user_id) 命名空间下所有记忆条目，按 updated_at 倒序
- 传 key：精确读取该 key 的值
  - 存在：返回 {key, value, summary, updated_at}
  - 不存在：返回 {key, value: null}
- 严格按 (agent_id, user_id) 隔离，不同用户/Agent 不能互相读取

可用性：
- 仅当 Agent.memory_long_term_enabled == True 时启用
"""
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.base import BuiltinTool

logger = logging.getLogger(__name__)

# key 字段最大长度（与 AgentMemoryLongTerm.key 列保持一致）
_MAX_KEY_LENGTH = 200


def _to_uuid(value: Any) -> Optional[uuid.UUID]:
    """将字符串或 UUID 转换为 UUID 对象，转换失败返回 None。"""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


class MemoryReadTool(BuiltinTool):
    """读取 Agent 长期记忆工具"""

    name = "memory_read"
    display_name = "读取长期记忆"
    description = (
        "从当前 Agent 的长期记忆中读取条目。"
        "传入 key 获取单条记录（不存在则 value=null）；"
        "不传 key 列出当前命名空间下全部记录，按更新时间倒序。"
        "记录按 agent 和 user 自动隔离。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "要读取的记忆键名（不传则返回全部记录）",
                "maxLength": _MAX_KEY_LENGTH,
            },
        },
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "value": {},
            "summary": {"type": "string"},
            "updated_at": {"type": "string"},
        },
        "description": (
            "单条读取时返回单个对象；"
            "列表读取时返回 {records: [...]} 对象数组"
        ),
    }

    # ------------------------------------------------------------------
    # 可用性
    # ------------------------------------------------------------------

    def is_available(self, ctx: ToolContext) -> bool:
        """仅当 Agent.memory_long_term_enabled 为 True 时启用。

        查询异常时返回 False（保守拒绝），异常类型记日志（脱敏）。
        """
        agent_id = getattr(ctx, "agent_id", None)
        db = getattr(ctx, "db", None)
        if agent_id is None or db is None:
            return False

        agent_uuid = _to_uuid(agent_id)
        if agent_uuid is None:
            return False

        try:
            # 延迟导入避免模块加载阶段循环依赖
            from app.models.agent import Agent

            agent = (
                db.query(Agent)
                .filter(Agent.id == agent_uuid)
                .first()
            )
            if agent is None:
                return False
            return bool(getattr(agent, "memory_long_term_enabled", False))
        except Exception as e:
            # 异常日志脱敏：仅记录异常类型名，不含参数/详情
            logger.warning(
                "memory_read.is_available 查询异常: %s", type(e).__name__
            )
            return False

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        # 1. 参数校验
        if not isinstance(args, dict):
            return ToolResult.error("参数格式错误")

        raw_key = args.get("key")
        if raw_key is not None:
            if not isinstance(raw_key, str):
                return ToolResult.error("key 必须为字符串")
            key = raw_key.strip()
            if not key:
                return ToolResult.error("key 不能为空")
            if len(key) > _MAX_KEY_LENGTH:
                return ToolResult.error(
                    f"key 长度超过限制（{_MAX_KEY_LENGTH}）"
                )
        else:
            key = None

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

        # 3. 查询
        try:
            from app.models.agent_memory import AgentMemoryLongTerm

            if key is not None:
                row: Optional[AgentMemoryLongTerm] = (
                    db.query(AgentMemoryLongTerm)
                    .filter(
                        AgentMemoryLongTerm.agent_id == agent_uuid,
                        AgentMemoryLongTerm.user_id == user_uuid,
                        AgentMemoryLongTerm.key == key,
                    )
                    .first()
                )
                payload: Any = (
                    self._serialize_row(row, fallback_key=key)
                )
                return ToolResult.json(payload)

            # 无 key：按 updated_at 倒序列出全部
            rows: List[AgentMemoryLongTerm] = (
                db.query(AgentMemoryLongTerm)
                .filter(
                    AgentMemoryLongTerm.agent_id == agent_uuid,
                    AgentMemoryLongTerm.user_id == user_uuid,
                )
                .order_by(AgentMemoryLongTerm.updated_at.desc())
                .all()
            )
            payload = {
                "records": [self._serialize_row(r) for r in rows],
                "count": len(rows),
            }
            return ToolResult.json(payload)

        except Exception as e:
            # 异常脱敏：日志只含异常类型名
            logger.error(
                "memory_read 查询异常: %s", type(e).__name__, exc_info=True
            )
            return ToolResult.error(f"读取长期记忆失败: {type(e).__name__}")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_row(
        row: Optional["AgentMemoryLongTerm"],
        fallback_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """将 ORM 行序列化为 dict。

        row 为 None 时返回带 value=null 的占位对象。
        """
        if row is None:
            return {
                "key": fallback_key,
                "value": None,
                "summary": None,
                "updated_at": None,
            }
        updated_at = getattr(row, "updated_at", None)
        return {
            "key": row.key,
            "value": row.value,
            "summary": row.summary,
            "updated_at": updated_at.isoformat() if updated_at else None,
        }
