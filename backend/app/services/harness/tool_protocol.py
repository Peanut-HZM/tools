"""ToolProtocol 接口 + 数据结构

参考 spec §6.1 / §6.2
"""
import json as _json
import time
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncIterator,
    Dict,
    List,
    Optional,
    Protocol,
    runtime_checkable,
)


@dataclass
class Attachment:
    """多模态附件"""

    type: str  # "image" / "file"
    url: str
    mime_type: Optional[str] = None
    name: Optional[str] = None
    size: Optional[int] = None


@dataclass
class ToolResult:
    """工具执行结果标准结构

    参考 spec §6.2
    """

    success: bool
    content: Any
    content_type: str = "text"  # text / image / file / json / error
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    attachments: List[Attachment] = field(default_factory=list)

    @classmethod
    def text(cls, text: str, **kw) -> "ToolResult":
        return cls(success=True, content=text, content_type="text", **kw)

    @classmethod
    def json(cls, data: Any, **kw) -> "ToolResult":
        return cls(success=True, content=data, content_type="json", **kw)

    @classmethod
    def image(cls, url: str, alt: str = "", **kw) -> "ToolResult":
        return cls(
            success=True,
            content=alt or "image",
            content_type="image",
            attachments=[Attachment(type="image", url=url, name=alt)],
            **kw,
        )

    @classmethod
    def error(cls, message: str, **kw) -> "ToolResult":
        return cls(success=False, content="", content_type="error", error_message=message, **kw)

    def to_llm_text(self) -> str:
        """转换为给 LLM 看的文本"""
        if self.content_type == "text":
            return self.content or ""
        if self.content_type == "json":
            return _json.dumps(self.content, ensure_ascii=False, indent=2, default=str)
        if self.content_type == "image":
            urls = [a.url for a in self.attachments if a.type == "image"]
            return f"[image: {', '.join(urls)}]" if urls else "[image]"
        if self.content_type == "error":
            return f"[error: {self.error_message}]"
        return str(self.content)


@dataclass
class ToolCall:
    """一次工具调用请求

    由 LLM 生成，Runtime 解析后分发给工具。
    """

    id: str
    name: str
    arguments: Dict[str, Any]

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "arguments": self.arguments}


@dataclass
class ToolEvent:
    """工具执行过程中的中间事件"""

    type: str  # "progress" / "result" / "error" / "log"
    payload: Any
    timestamp: float = field(default_factory=time.time)


class ToolContext:
    """工具执行上下文

    工具通过此对象访问运行时依赖，避免全局变量。
    """

    def __init__(
        self,
        user_id: str,
        conversation_id: str,
        agent_id: str,
        session=None,  # Session 对象（避免循环导入）
        db=None,  # SQLAlchemy session
        oss_service=None,
        llm_gateway=None,
        event_emitter=None,
        quota_service=None,
        trace_recorder=None,
        cancel_event=None,
        tool_state: Optional[Dict] = None,
    ):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.agent_id = agent_id
        self.session = session
        self.db = db
        self.oss_service = oss_service
        self.llm_gateway = llm_gateway
        self.event_emitter = event_emitter
        self.quota_service = quota_service
        self.trace_recorder = trace_recorder
        self.cancel_event = cancel_event
        self.tool_state = tool_state if tool_state is not None else {}


@runtime_checkable
class ToolProtocol(Protocol):
    """标准工具协议接口

    所有工具（builtin / http / mcp / plugin）都实现此接口。
    """

    name: str
    display_name: str
    description: str
    parameters_schema: dict
    returns_schema: Optional[dict]

    async def initialize(self) -> None: ...

    async def shutdown(self) -> None: ...

    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult: ...

    def execute_stream(self, args: dict, ctx: ToolContext) -> AsyncIterator[ToolEvent]: ...

    def is_available(self, ctx: ToolContext) -> bool: ...

    def to_function_schema(self) -> dict: ...
