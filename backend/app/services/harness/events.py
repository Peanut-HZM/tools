"""Event 类型定义 + SSE 序列化

参考 spec §7.4
"""
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, List, Optional


@dataclass
class Event:
    """Agent 执行过程中的事件

    通过 SSE 推给前端，前端按 type 分发渲染。
    """

    type: str
    payload: dict
    timestamp: float = field(default_factory=time.time)

    # ---- 工厂方法 ----

    @classmethod
    def turn_start(cls, conversation_id: str, agent: dict) -> "Event":
        return cls(type="turn_start", payload={"conversation_id": conversation_id, "agent": agent})

    @classmethod
    def text_delta(cls, text: str) -> "Event":
        return cls(type="text_delta", payload={"text": text})

    @classmethod
    def text_complete(cls, text: str) -> "Event":
        return cls(type="text_complete", payload={"text": text})

    @classmethod
    def thinking_delta(cls, text: str) -> "Event":
        return cls(type="thinking_delta", payload={"text": text})

    @classmethod
    def tool_call_start(cls, call) -> "Event":
        return cls(
            type="tool_call_start",
            payload={"id": call.id, "name": call.name, "arguments": call.arguments},
        )

    @classmethod
    def tool_call_progress(cls, call_id: str, progress: Any) -> "Event":
        return cls(type="tool_call_progress", payload={"id": call_id, "progress": progress})

    @classmethod
    def tool_result(cls, call, result) -> "Event":
        return cls(
            type="tool_result",
            payload={
                "id": call.id,
                "name": call.name,
                "success": result.success,
                "content_type": result.content_type,
                "content": result.content,
                "attachments": [asdict(a) for a in result.attachments],
                "error": result.error_message,
            },
        )

    @classmethod
    def image_generated(cls, urls: List[str], metadata: dict) -> "Event":
        return cls(type="image_generated", payload={"urls": urls, "metadata": metadata})

    @classmethod
    def video_generated(cls, url: str, metadata: dict) -> "Event":
        return cls(type="video_generated", payload={"url": url, "metadata": metadata})

    @classmethod
    def handoff(cls, from_agent: dict, to_agent: dict, reason: str) -> "Event":
        return cls(
            type="handoff",
            payload={"from_agent": from_agent, "to_agent": to_agent, "reason": reason},
        )

    @classmethod
    def guardrail_triggered(cls, guardrail_name: str, reason: str, stage: str) -> "Event":
        return cls(
            type="guardrail_triggered",
            payload={"guardrail_name": guardrail_name, "reason": reason, "stage": stage},
        )

    @classmethod
    def memory_retrieved(cls, facts: List[str]) -> "Event":
        return cls(type="memory_retrieved", payload={"facts": facts})

    @classmethod
    def error(cls, message: str, recoverable: bool = False) -> "Event":
        return cls(type="error", payload={"message": message, "recoverable": recoverable})

    @classmethod
    def done(cls, final_text: str, usage: Optional[dict] = None) -> "Event":
        payload: dict = {"final_text": final_text}
        if usage:
            payload["usage"] = usage
        return cls(type="done", payload=payload)

    @classmethod
    def custom(cls, name: str, **payload_kwargs) -> "Event":
        return cls(type="custom", payload={"name": name, **payload_kwargs})

    # ---- SSE 序列化 ----

    def to_sse(self) -> str:
        """转换为 SSE 格式

        格式：
            event: <type>\\n
            data: <json>\\n
            \\n
        """
        data = {"timestamp": self.timestamp, **self.payload}
        return f"event: {self.type}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
