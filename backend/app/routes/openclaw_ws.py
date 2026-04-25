"""
OpenClaw WebSocket 路由
专为小程序端提供流式对话支持
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.openclaw_service import openclaw_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/openclaw", tags=["openclaw-ws"])

# 活跃 WebSocket 会话管理
_active_ws: dict[str, asyncio.Event] = {}


@router.websocket("/chat/ws")
async def chat_websocket(
    websocket: WebSocket,
    session_key: str = "main",
):
    """WebSocket 流式对话（小程序专用）"""
    await websocket.accept()

    ws_id = f"{session_key}:{id(websocket)}"
    abort_event = asyncio.Event()
    _active_ws[ws_id] = abort_event

    try:
        while True:
            # 等待客户端发送消息
            raw = await websocket.receive_text()
            data = json.loads(raw)

            msg_type = data.get("type")

            if msg_type == "message":
                content = data.get("content", "").strip()
                if not content:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "消息内容不能为空"
                    }))
                    continue

                if len(content) > 4000:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "消息内容过长（最大 4000 字符）"
                    }))
                    continue

                if not openclaw_service.is_connected():
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "OpenClaw 服务未连接"
                    }))
                    continue

                # 重置中止标志
                abort_event.clear()

                # 流式转发 OpenClaw 响应
                try:
                    async for chunk in openclaw_service.send_chat(
                        session_key=session_key,
                        message=content,
                        abort_flag=abort_event,
                    ):
                        # chunk 格式: "data: {...}\n\n"
                        # 提取 JSON 部分
                        if chunk.startswith("data: "):
                            json_str = chunk[6:].strip()
                            if json_str:
                                await websocket.send_text(json_str)
                except Exception as e:
                    logger.error(f"OpenClaw chat 错误: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))

            elif msg_type == "abort":
                # 中止当前生成
                abort_event.set()
                await websocket.send_text(json.dumps({
                    "type": "aborted"
                }))

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: {ws_id}")
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}")
    finally:
        _active_ws.pop(ws_id, None)
