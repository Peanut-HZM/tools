"""memory_search BuiltinTool — 语义搜索长期记忆

参考 spec §6.5 内置工具清单 + Phase 3 Plan-1B。

行为：
- 必填 query（搜索关键词或自然语言描述）；可选 top_k（默认 5）
- 返回与 query 最相关的记忆条目列表，按向量相似度排序
- 当 Agent 配置了 embedding_provider 时使用向量检索；否则降级为关键词搜索
- 严格按 (agent_id, user_id) 隔离，不同用户/Agent 不能互相检索

可用性：
- 仅当 Agent.memory_long_term_enabled == True 时启用

错误处理：
- query 为空：返回 error
- DB/embedding 异常：返回 error（包含脱敏后的异常类型名）
- embedding API 不可用：自动降级为关键词搜索（由 MemoryService 处理）
"""
import logging
import uuid
from typing import Any, Dict, Optional

from app.services.harness.tool_protocol import ToolContext, ToolResult
from app.services.harness.tools.base import BuiltinTool

logger = logging.getLogger(__name__)


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


class MemorySearchTool(BuiltinTool):
    """语义搜索 Agent 长期记忆工具"""

    name = "memory_search"
    display_name = "记忆搜索"
    description = (
        "语义搜索当前 Agent 的长期记忆，返回与查询最相关的记忆条目。"
        "支持自然语言描述或关键词。"
        "记录按 agent 和 user 自动隔离。"
    )
    parameters_schema = {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词或自然语言描述",
            },
            "top_k": {
                "type": "integer",
                "description": "返回条数（默认 5）",
                "default": 5,
                "minimum": 1,
            },
        },
    }
    returns_schema = {
        "type": "object",
        "properties": {
            "records": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "value": {},
                        "score": {"type": "number"},
                        "summary": {"type": "string"},
                    },
                },
            },
            "count": {"type": "integer"},
        },
        "description": (
            "搜索结果：records 为按相关度排序的记忆条目数组；"
            "count 为返回条目数。"
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
                "memory_search.is_available 查询异常: %s", type(e).__name__
            )
            return False

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult:
        # 1. 参数格式校验
        if not isinstance(args, dict):
            return ToolResult.error("参数格式错误")

        # 2. 必填 query
        raw_query = args.get("query")
        if not isinstance(raw_query, str) or not raw_query.strip():
            return ToolResult.error("query 不能为空")

        # 3. 可选 top_k（默认 5，必须是正整数）
        raw_top_k = args.get("top_k", 5)
        if not isinstance(raw_top_k, int) or isinstance(raw_top_k, bool) or raw_top_k < 1:
            top_k = 5
        else:
            top_k = raw_top_k

        # 4. 上下文校验
        db = getattr(ctx, "db", None)
        if db is None:
            return ToolResult.error("数据库连接不可用")

        agent_uuid = _to_uuid(getattr(ctx, "agent_id", None))
        user_uuid = _to_uuid(getattr(ctx, "user_id", None))
        if agent_uuid is None:
            return ToolResult.error("agent_id 缺失或无效")
        if user_uuid is None:
            return ToolResult.error("user_id 缺失或无效")

        # 5. 执行检索（向量优先，降级关键词）
        try:
            from app.services.harness.memory_service import MemoryService
            from app.services.harness.embeddings.factory import (
                create_embedding_provider,
            )

            # 读取 Agent embedding 配置；未配置时 MemoryService 自动降级为关键词
            agent_cfg = self._resolve_agent_config(db, agent_uuid)
            provider = None
            if agent_cfg.get("embedding_provider"):
                try:
                    provider = create_embedding_provider(agent_cfg)
                except Exception as e:
                    # provider 创建失败不阻塞检索；MemoryService 收到 None provider
                    # 会自动降级为关键词搜索
                    logger.warning(
                        "memory_search embedding provider 创建失败，降级为关键词搜索: %s",
                        type(e).__name__,
                    )
                    provider = None

            svc = MemoryService(db=db, embedding_provider=provider)
            results = await svc.search(
                agent_uuid,
                user_uuid,
                raw_query.strip(),
                top_k=top_k,
            )

            # 6. 构造返回结果（脱敏后的精简结构）
            records = [
                {
                    "key": r.key,
                    "value": r.value,
                    "score": round(float(r.score), 4),
                    "summary": r.summary,
                }
                for r in results
            ]
            return ToolResult.json({"records": records, "count": len(records)})

        except Exception as e:
            # 异常脱敏：日志只含异常类型名
            logger.error(
                "memory_search 执行失败: %s",
                type(e).__name__,
                exc_info=True,
            )
            return ToolResult.error(f"记忆搜索失败: {type(e).__name__}")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _to_uuid(value: Any) -> Optional[uuid.UUID]:
        """类内 UUID 解析（保留与 memory_read/write 风格一致）。"""
        return _to_uuid(value)

    @staticmethod
    def _resolve_agent_config(db, agent_uuid: uuid.UUID) -> Dict[str, Any]:
        """读取 Agent.memory_long_term_config（dict），失败回退空 dict。

        用于读取 embedding_provider / embedding_model / embedding_api_key 等配置。
        异常时不阻塞主流程，仅返回空 dict 让 MemoryService 降级为关键词搜索。
        """
        try:
            from app.models.agent import Agent

            agent = (
                db.query(Agent)
                .filter(Agent.id == agent_uuid)
                .first()
            )
            if agent is None:
                return {}
            cfg = getattr(agent, "memory_long_term_config", None)
            return cfg if isinstance(cfg, dict) else {}
        except Exception as e:
            logger.warning(
                "memory_search 读取 Agent embedding 配置失败: %s",
                type(e).__name__,
            )
            return {}