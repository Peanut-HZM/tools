"""Session — 运行时会话上下文

参考 spec §7.3

Session 是 Runtime 概念（内存中的活动状态），Conversation 是 DB 持久化概念。
Phase 1：1:1 映射。
"""
import logging
from typing import Any, Dict, List, Optional

from app.models.message import Message
from app.services.harness.llm_bridge import LLMResponse
from app.services.harness.tool_protocol import ToolCall, ToolResult

logger = logging.getLogger(__name__)


# harness 角色 → ORM sender_type 的映射
# Message ORM 只有 user / agent 两个枚举值；tool / system 消息在 ORM 层面归到 agent。
ROLE_TO_SENDER_TYPE = {
    "user": "user",
    "assistant": "agent",
    "tool": "agent",
    "system": "agent",
}


class Session:
    """运行时会话上下文

    Session 是 Runtime 概念（内存中的活动状态）
    Conversation 是存储概念（DB 持久化）
    Phase 1：1:1 映射
    """

    def __init__(self, conversation, agent):
        self.conversation = conversation
        self.agent = agent
        self.messages: List = []
        self.scratch_state: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = dict(conversation.metadata or {})
        self._dirty_messages: List = []  # 待持久化的新消息

    async def load(self):
        """从 DB 加载消息历史。

        兼容 SQLAlchemy 1.x 风格 (.query) 与 2.x 风格 (select + execute) 两种查询方式。
        """
        from sqlalchemy import select

        if hasattr(Message, "query") and Message.query is not None:
            # SQLAlchemy 1.x 风格
            self.messages = list(
                Message.query.filter_by(conversation_id=self.conversation.id)
                .order_by(Message.sent_at)
                .all()
            )
        else:
            # SQLAlchemy 2.x 风格：调用方需提供 db session
            db = getattr(self, "_db", None)
            if db is None:
                logger.warning(
                    "Session.load: SQLAlchemy 2.x 模式下未注入 db，跳过加载"
                )
                return
            stmt = (
                select(Message)
                .where(Message.conversation_id == self.conversation.id)
                .order_by(Message.sent_at)
            )
            self.messages = list(db.execute(stmt).scalars().all())

    # ---- 消息操作 ----

    def _new_message(self, role: str, **orm_fields):
        """构造一条 Message 实例。

        - 把 harness 角色（user/assistant/tool/system）映射到 ORM sender_type
        - 把 role 写成 Python 属性，方便上层（runtime / tests）直接读取
        """
        sender_type = ROLE_TO_SENDER_TYPE.get(role, "agent")
        msg = Message(
            conversation_id=self.conversation.id,
            sender_type=sender_type,
            **orm_fields,
        )
        msg.role = role
        return msg

    def append_user_message(self, content: str):
        """追加用户消息"""
        msg = self._new_message("user", content=content)
        self.messages.append(msg)
        self._dirty_messages.append(msg)
        return msg

    def append_assistant_message(self, response: LLMResponse):
        """追加 assistant 消息"""
        msg = self._new_message(
            "assistant",
            content=response.text_part,
            tool_calls=[tc.to_dict() for tc in response.tool_calls] if response.tool_calls else None,
        )
        if response.thinking_part:
            msg.metadata = {"thinking": response.thinking_part}
        self.messages.append(msg)
        self._dirty_messages.append(msg)
        return msg

    def append_tool_message(self, call: ToolCall, result: ToolResult):
        """追加 tool 消息"""
        msg = self._new_message(
            "tool",
            content=result.to_llm_text(),
            tool_call_id=call.id,
            tool_name=call.name,
            attachments=[
                {"type": a.type, "url": a.url, "name": a.name}
                for a in result.attachments
            ] if result.attachments else None,
        )
        self.messages.append(msg)
        self._dirty_messages.append(msg)
        return msg

    def append_system_message(self, content: str):
        """追加 system 消息"""
        msg = self._new_message("system", content=content)
        self.messages.append(msg)
        self._dirty_messages.append(msg)
        return msg

    # ---- 持久化 ----

    def persist(self, db):
        """批量持久化到 DB（sync 版本，便于测试）。

        Phase 1：仅 add + commit；Phase 3 可在此处接入 session-scope 合并、批量 flush。
        """
        for msg in self._dirty_messages:
            # MagicMock 的 __contains__ 返回 False，因此 mock 下所有消息都会 add
            if msg not in db:
                db.add(msg)
        db.commit()
        self._dirty_messages.clear()

    async def apersist(self, db):
        """async 持久化（与 persist 同义，phase 1 保留 async API）"""
        self.persist(db)

    # ---- Checkpoint ----

    async def write_checkpoint(self, db, step_index: int, phase: str):
        """写 checkpoint（轻量版）

        Phase 1：只记录 messages_ref（最后一条消息的 id）+ agent_state。
        Phase 3：可在此处做完整快照（消息列表 / scratch_state / memory 引用）。
        """
        from app.models.harness_models import SessionCheckpoint

        last_msg_id = self.messages[-1].id if self.messages else None
        cp = SessionCheckpoint(
            conversation_id=self.conversation.id,
            step_index=step_index,
            phase=phase,
            messages_ref=last_msg_id,
            agent_state=self.scratch_state.copy(),
        )
        db.add(cp)
        db.commit()
