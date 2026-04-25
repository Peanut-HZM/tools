"""
OpenClaw Gateway WebSocket 客户端
负责与 OpenClaw Gateway 建立 WebSocket 连接，处理 JSON-RPC 协议
"""

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator, Dict, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from app.config.config import settings
from app.services.openclaw_config_service import openclaw_config_service

logger = logging.getLogger(__name__)


class OpenClawService:
    """OpenClaw Gateway WebSocket 客户端（单例）"""

    def __init__(self):
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connect_task: Optional[asyncio.Task] = None
        self._running = False
        self._pending_requests: dict[str, asyncio.Queue] = {}
        self._event_listeners: dict[str, list[asyncio.Queue]] = {}
        self._reconnect_delay = 1
        self._disconnect_event = asyncio.Event()
        self._send_lock = asyncio.Lock()

    async def start(self):
        """启动连接（后台任务）"""
        if self._running:
            return
        if not openclaw_config_service.is_enabled():
            logger.info("OpenClaw 功能未启用，跳过连接")
            return
        self._running = True
        self._connect_task = asyncio.create_task(self._connect_loop())
        logger.info("OpenClaw Gateway 连接任务已启动")

    async def stop(self):
        """停止连接"""
        self._running = False
        if self._connect_task:
            self._connect_task.cancel()
            try:
                await self._connect_task
            except asyncio.CancelledError:
                pass
        if self.ws:
            await self.ws.close()
        logger.info("OpenClaw Gateway 连接已关闭")

    async def reload_config(self, new_config: Dict[str, str]):
        """热加载配置并重新连接"""
        logger.info("OpenClaw 配置热加载中...")
        await self.stop()
        self._running = True
        self._connect_task = asyncio.create_task(self._connect_loop())
        logger.info("OpenClaw 配置热加载完成")

    def get_connection_info(self) -> dict:
        """获取当前连接信息（Token 脱敏）"""
        config = openclaw_config_service.get_config()
        token = config.get("token", "")
        masked_token = token[:6] + "****" + token[-4:] if len(token) > 10 else "****" if token else ""
        return {
            "gateway_url": config.get("gateway_url", ""),
            "token": masked_token,
            "enabled": config.get("enabled", "true"),
            "connected": self.is_connected(),
        }

    async def _connect_loop(self):
        """重连循环"""
        while self._running:
            try:
                await self._connect()
                self._reconnect_delay = 1
                await self._disconnect_event.wait()
                self._disconnect_event.clear()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"OpenClaw 连接断开，{self._reconnect_delay}s 后重连: {e}")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, 30)

    async def _connect(self):
        """建立 WebSocket 连接并完成握手"""
        config = openclaw_config_service.get_config()
        url = config.get("gateway_url", settings.OPENCLAW_GATEWAY_URL)
        auth_mode = config.get("auth_mode", "token")
        username = config.get("username", "")
        password = config.get("password", "")
        token = config.get("token", settings.OPENCLAW_TOKEN)

        # 根据认证模式决定是否嵌入用户名密码到 URL
        if auth_mode == "token_with_password" and username and password:
            if url.startswith("ws://"):
                url = url.replace("ws://", f"ws://{username}:{password}@", 1)
            elif url.startswith("wss://"):
                url = url.replace("wss://", f"wss://{username}:{password}@", 1)
            logger.info(f"正在连接 OpenClaw Gateway (双重认证): {url}")
        else:
            logger.info(f"正在连接 OpenClaw Gateway (Token 认证): {url}")
        self.ws = await websockets.connect(url, ping_interval=30, ping_timeout=10)

        # 等待 connect.challenge
        challenge_raw = await asyncio.wait_for(self.ws.recv(), timeout=10)
        challenge = json.loads(challenge_raw)
        if challenge.get("event") != "connect.challenge":
            raise ValueError(f"预期 connect.challenge，收到: {challenge}")
        nonce = challenge.get("payload", {}).get("nonce", "")
        if not nonce:
            raise ValueError("connect.challenge 缺少 nonce")

        # 发送 connect 请求（协议版本 3）
        connect_msg = {
            "type": "req",
            "id": str(uuid.uuid4()),
            "method": "connect",
            "params": {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": "tools-mini-program",
                    "displayName": "Tools Mini Program",
                    "version": "1.0.0",
                    "platform": "linux",
                    "mode": "backend",
                    "instanceId": str(uuid.uuid4()),
                },
                "caps": [],
                "auth": {"token": token} if token else None,
                "role": "operator",
                "scopes": ["operator.admin"],
            },
        }
        connect_msg["params"] = {k: v for k, v in connect_msg["params"].items() if v is not None}

        await self.ws.send(json.dumps(connect_msg))

        # 等待 hello_ok
        response_raw = await asyncio.wait_for(self.ws.recv(), timeout=10)
        response = json.loads(response_raw)

        if response.get("ok"):
            logger.info(f"OpenClaw 连接成功: {response.get('payload', {})}")
        else:
            error = response.get("error", {})
            raise ConnectionError(f"OpenClaw 连接失败: {error.get('message', 'unknown')}")

        asyncio.create_task(self._event_loop())

    async def _event_loop(self):
        """持续监听事件并分发"""
        try:
            async for raw in self.ws:
                data = json.loads(raw)
                msg_id = data.get("id")
                event = data.get("event")

                if msg_id and msg_id in self._pending_requests:
                    queue = self._pending_requests[msg_id]
                    await queue.put(data)

                if event == "chat":
                    for queue in self._event_listeners.get("chat", []):
                        await queue.put(data)
        except ConnectionClosed:
            logger.warning("OpenClaw WebSocket 连接关闭")
        except Exception as e:
            logger.error(f"OpenClaw 事件循环异常: {e}")
        finally:
            for q in self._pending_requests.values():
                q.put_nowait({"ok": False, "error": {"message": "连接已断开"}})
            self._pending_requests.clear()
            self._disconnect_event.set()

    async def _send_request(self, method: str, params: dict, timeout: float = 10) -> dict:
        """发送 RPC 请求并等待响应（支持并发）"""
        if not self.ws or self.ws.closed:
            raise ConnectionError("OpenClaw 未连接")

        msg_id = str(uuid.uuid4())
        frame = {
            "type": "req",
            "id": msg_id,
            "method": method,
            "params": params,
        }
        queue = asyncio.Queue()
        self._pending_requests[msg_id] = queue

        try:
            async with self._send_lock:
                await self.ws.send(json.dumps(frame))
            response = await asyncio.wait_for(queue.get(), timeout=timeout)

            if response.get("ok"):
                return response.get("payload", {})
            else:
                error = response.get("error", {})
                raise ValueError(f"OpenClaw 请求失败 ({method}): {error.get('message', 'unknown')}")
        finally:
            self._pending_requests.pop(msg_id, None)

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.ws is not None and not self.ws.closed

    async def send_chat(self, session_key: str, message: str, abort_flag: Optional[asyncio.Event] = None) -> AsyncGenerator[str, None]:
        """发送聊天消息并流式返回 SSE 格式 chunk"""
        if not self.is_connected():
            raise ConnectionError("OpenClaw 服务未连接")

        run_id = str(uuid.uuid4())
        event_queue: asyncio.Queue = asyncio.Queue()

        if "chat" not in self._event_listeners:
            self._event_listeners["chat"] = []
        self._event_listeners["chat"].append(event_queue)

        try:
            ack = await self._send_request("chat.send", {
                "sessionKey": session_key,
                "message": message,
            }, timeout=30)

            run_id = ack.get("runId", run_id)
            yield f"data: {json.dumps({'type': 'started', 'runId': run_id}, ensure_ascii=False)}\n\n"

            max_wait = 120
            start_time = asyncio.get_event_loop().time()

            while asyncio.get_event_loop().time() - start_time < max_wait:
                if abort_flag and abort_flag.is_set():
                    try:
                        await self._send_request("chat.abort", {
                            "sessionKey": session_key,
                            "runId": run_id,
                        }, timeout=5)
                        yield f"data: {json.dumps({'type': 'aborted'}, ensure_ascii=False)}\n\n"
                    except Exception as e:
                        logger.warning(f"中止请求失败: {e}")
                    break

                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=5)
                    payload = event.get("payload", {})

                    state = payload.get("state")
                    stream = payload.get("stream")

                    if stream == "lifecycle":
                        phase = payload.get("data", {}).get("phase")
                        if phase == "end":
                            break
                        continue

                    if state in ("delta", "final"):
                        text = self._extract_text_from_payload(payload)
                        if text:
                            yield f"data: {json.dumps({'type': 'chunk', 'content': text}, ensure_ascii=False)}\n\n"

                    if state == "final":
                        break

                except asyncio.TimeoutError:
                    continue

            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        finally:
            if event_queue in self._event_listeners.get("chat", []):
                self._event_listeners["chat"].remove(event_queue)

    def _extract_text_from_payload(self, payload: dict) -> Optional[str]:
        """从 chat 事件 payload 中提取文本"""
        message = payload.get("message", {})
        content_list = message.get("content", [])
        if isinstance(content_list, list) and len(content_list) > 0:
            text = content_list[0].get("text")
            if text:
                return text
        return payload.get("text") or payload.get("content")

    async def chat_history(self, session_key: str, limit: int = 50) -> list:
        """获取会话历史"""
        result = await self._send_request("chat.history", {"sessionKey": session_key, "limit": limit})
        return result.get("messages", [])

    async def reset_session(self, session_key: str) -> dict:
        """重置会话"""
        return await self._send_request("sessions.reset", {"key": session_key})

    async def get_status(self) -> dict:
        """获取网关状态"""
        return await self._send_request("status")


# 全局单例
openclaw_service = OpenClawService()
