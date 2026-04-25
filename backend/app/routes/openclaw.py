"""
OpenClaw AI 对话路由
提供 SSE 流式对话接口和会话管理
"""

import json
import logging
import asyncio
from typing import Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.openclaw_service import openclaw_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/openclaw", tags=["openclaw"])

_active_chats: Dict[str, asyncio.Event] = {}


class ChatRequest(BaseModel):
    message: str
    session_key: str = "main"


class HistoryRequest(BaseModel):
    session_key: str = "main"
    limit: int = 50


class AbortRequest(BaseModel):
    session_key: str = "main"


@router.post("/chat")
async def chat_stream(request: ChatRequest):
    """流式对话接口（SSE）"""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    if len(request.message) > 4000:
        raise HTTPException(status_code=400, detail="消息内容过长（最大 4000 字符）")
    if not openclaw_service.is_connected():
        raise HTTPException(status_code=502, detail="OpenClaw 服务未连接")

    abort_event = asyncio.Event()
    chat_id = f"{request.session_key}:{id(request)}"
    _active_chats[chat_id] = abort_event

    async def generate():
        try:
            async for chunk in openclaw_service.send_chat(
                session_key=request.session_key,
                message=request.message,
                abort_flag=abort_event,
            ):
                yield chunk
        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
        finally:
            _active_chats.pop(chat_id, None)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/abort")
async def abort_chat(request: AbortRequest):
    """中止生成"""
    if not openclaw_service.is_connected():
        raise HTTPException(status_code=502, detail="OpenClaw 服务未连接")

    aborted = False
    for chat_id, abort_event in list(_active_chats.items()):
        if chat_id.startswith(f"{request.session_key}:"):
            abort_event.set()
            aborted = True
            break

    if not aborted:
        return {"ok": False, "message": "没有找到活跃的生成任务"}

    return {"ok": True, "aborted": True}


@router.post("/history")
async def get_history(request: HistoryRequest):
    """获取会话历史"""
    if not openclaw_service.is_connected():
        raise HTTPException(status_code=502, detail="OpenClaw 服务未连接")
    try:
        messages = await openclaw_service.chat_history(
            session_key=request.session_key, limit=request.limit,
        )
        return {"messages": messages}
    except Exception as e:
        logger.error(f"获取历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_session(session_key: str = "main"):
    """重置会话"""
    if not openclaw_service.is_connected():
        raise HTTPException(status_code=502, detail="OpenClaw 服务未连接")
    try:
        result = await openclaw_service.reset_session(session_key)
        return result
    except Exception as e:
        logger.error(f"重置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """获取 OpenClaw 状态"""
    connected = openclaw_service.is_connected()
    return {"connected": connected}
