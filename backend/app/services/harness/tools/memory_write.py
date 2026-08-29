"""memory_write BuiltinTool — 写入/更新 Agent 长期记忆

参考 spec §6.5 内置工具清单。

行为：
- 必填 key + value（value 必须是 dict）；可选 summary
- 相同 (agent_id, user_id, key) → UPSERT（action=created 或 updated）
- 限制：
  - 单条 value JSON 序列化后 ≤ 10KB
  - 每 (agent_id, user_id) 最多 N 条（默认 100，可由 Agent.memory_long_term_config.max_entries 调整）
  - 更新已有条目不触发 max_entries
- 严格按 (agent_id, user_id) 隔离，不同用户/Agent 不能互相覆盖

可用性：
- 仅当 Agent.memory_long_term_enabled == True 时启用
"""
import json
import logging
import uuid
from typing import Any, Dict, Optional

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.base import BuiltinTool

logger = logging.getLogger(__name__)

# key 字段最大长度（与 AgentMemoryLongTerm.key 列保持一致）
_MAX_KEY_LENGTH = 200
# summary 字段最大长度
_MAX_SUMMARY_LENGTH = 500
# value 序列化后最大字节数
_MAX_VALUE_BYTES = 10 * 1024  # 10KB
# 默认每 (agent, user) 命名空间最大条目数
_DEFAULT_MAX_ENTRIES = 100


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


class MemoryWriteTool(BuiltinTool):
    """写入 Agent 长期记忆工具"""

    name = "memory_write"
    display_name = "写入长期记忆"
    description = (
        "向当前 Agent 的长期记忆写入或更新一条记录。"
        "必填 key（记忆键名）和 value（JSON 对象内容）；可选 summary（摘要）。"
        "相同 key 会被覆盖（UPSERT 语义）；新条目数量受上限约束。"
        "记录按 agent 和 user 自动隔离。"
    )
    parameters_schema = {
        "type": "object",
        "required": ["key", "value"],
        "properties": {
            "key": {
                "type": "string",
                "description": "要写入的记忆键名",
                "maxLength": _MAX_KEY_LENGTH,
            },
            "value": {
                "type": "object",
                "description": "记忆内容（JSON 对象，单条 ≤10KB）",
            },
            "summary": {
                "type": "string",
                "description": "可选摘要（≤500 字符）",
                "maxLength": _MAX_SUMMARY_LENGTH,
            },
        },
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["created", "updated"]},
            "key": {"type": "string"},
        },
        "description": "写入结果：action 表示新建或更新",
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
                "memory_write.is_available 查询异常: %s", type(e).__name__
            )
            return False

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        # 1. 参数格式校验
        if not isinstance(args, dict):
            return ToolResult.error("参数格式错误")

        # 2. 必填字段
        if "key" not in args or "value" not in args:
            return ToolResult.error("缺少必填参数 key 和 value")

        raw_key = args.get("key")
        raw_value = args.get("value")
        raw_summary = args.get("summary")

        # 3. key 类型与长度
        if not isinstance(raw_key, str):
            return ToolResult.error("key 必须为字符串")
        key = raw_key.strip()
        if not key:
            return ToolResult.error("key 不能为空")
        if len(key) > _MAX_KEY_LENGTH:
            return ToolResult.error(
                f"key 长度超过限制（{_MAX_KEY_LENGTH}）"
            )

        # 4. value 类型：必须是 dict
        if not isinstance(raw_value, dict):
            return ToolResult.error("value 必须是 JSON 对象")

        # 5. summary 类型与长度（截断超长摘要）
        summary: Optional[str]
        if raw_summary is None:
            summary = None
        elif not isinstance(raw_summary, str):
            return ToolResult.error("summary 必须为字符串")
        elif len(raw_summary) > _MAX_SUMMARY_LENGTH:
            # 静默截断，避免因过长摘要导致整次写入失败
            summary = raw_summary[:_MAX_SUMMARY_LENGTH]
        else:
            summary = raw_summary

        # 6. 上下文校验
        db = getattr(ctx, "db", None)
        if db is None:
            return ToolResult.error("数据库连接不可用")

        agent_uuid = _to_uuid(getattr(ctx, "agent_id", None))
        user_uuid = _to_uuid(getattr(ctx, "user_id", None))
        if agent_uuid is None:
            return ToolResult.error("agent_id 缺失或无效")
        if user_uuid is None:
            return ToolResult.error("user_id 缺失或无效")

        # 7. value 大小校验（JSON 序列化后字节数）
        try:
            value_json = json.dumps(raw_value, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.warning(
                "memory_write value JSON 序列化失败: %s", type(e).__name__
            )
            return ToolResult.error("value 无法序列化为 JSON")
        if len(value_json.encode("utf-8")) > _MAX_VALUE_BYTES:
            return ToolResult.error(
                f"value 大小不得超过 {_MAX_VALUE_BYTES // 1024}KB"
            )

        # 8. UPSERT
        try:
            from app.models.agent_memory import AgentMemoryLongTerm

            existing = (
                db.query(AgentMemoryLongTerm)
                .filter(
                    AgentMemoryLongTerm.agent_id == agent_uuid,
                    AgentMemoryLongTerm.user_id == user_uuid,
                    AgentMemoryLongTerm.key == key,
                )
                .first()
            )

            if existing is not None:
                # 更新已有条目 → 不触发 max_entries
                existing.value = raw_value
                existing.summary = summary
                action = "updated"
            else:
                # 新建条目 → 检查 max_entries
                max_entries = self._resolve_max_entries(db, agent_uuid)
                current_count = (
                    db.query(AgentMemoryLongTerm)
                    .filter(
                        AgentMemoryLongTerm.agent_id == agent_uuid,
                        AgentMemoryLongTerm.user_id == user_uuid,
                    )
                    .count()
                )
                if current_count >= max_entries:
                    return ToolResult.error(
                        f"记忆条目已达上限（{max_entries} 条），"
                        "请先删除旧条目或使用现有 key 更新"
                    )
                record = AgentMemoryLongTerm(
                    agent_id=agent_uuid,
                    user_id=user_uuid,
                    key=key,
                    value=raw_value,
                    summary=summary,
                )
                db.add(record)
                action = "created"

            db.commit()
            return ToolResult.json({"action": action, "key": key})

        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            # 异常脱敏：日志只含异常类型名
            logger.error(
                "memory_write 提交失败: %s", type(e).__name__, exc_info=True
            )
            return ToolResult.error(f"写入长期记忆失败: {type(e).__name__}")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_max_entries(db, agent_uuid: uuid.UUID) -> int:
        """从 Agent.memory_long_term_config 解析 max_entries，失败回退默认值。

        异常时返回默认值（保守不阻塞写入）。
        """
        try:
            from app.models.agent import Agent

            agent = (
                db.query(Agent)
                .filter(Agent.id == agent_uuid)
                .first()
            )
            if agent is None:
                return _DEFAULT_MAX_ENTRIES
            cfg = getattr(agent, "memory_long_term_config", None)
            if isinstance(cfg, dict) and "max_entries" in cfg:
                value = cfg["max_entries"]
                if isinstance(value, int) and value > 0:
                    return value
            return _DEFAULT_MAX_ENTRIES
        except Exception as e:
            logger.warning(
                "memory_write 读取 Agent 配置失败: %s", type(e).__name__
            )
            return _DEFAULT_MAX_ENTRIES