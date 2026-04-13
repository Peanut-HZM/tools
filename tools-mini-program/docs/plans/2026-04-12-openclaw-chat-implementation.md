# OpenClaw 对话工具 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在工具箱小程序中新增 OpenClaw AI 对话工具，通过后端 WebSocket 代理将 OpenClaw Gateway 的 JSON-RPC 协议转换为 HTTP SSE 流式响应，支持 Markdown 渲染。

**Architecture:** Python FastAPI 后端通过 `websockets` 库建立长连接至 OpenClaw Gateway（ws://127.0.0.1:18081），处理 JSON-RPC 握手和消息转发。小程序通过 HTTP POST + SSE 接收流式 AI 回复，使用 `marked` + `rich-text` 渲染 Markdown。

**Tech Stack:** Python FastAPI, websockets>=12.0, SSE, Taro 4.1.11, React 18, TypeScript, marked, 微信小程序 rich-text

---

### Task 1: 后端配置 — 添加 OpenClaw 环境变量

**Files:**
- Modify: `backend/app/config/config.py`（在 CORS_ORIGINS 之后、ALIYUN_OSS 之前添加）

**Step 1: 添加配置项**

在 `Settings` 类第 51 行（CORS_ORIGINS）之后、第 53 行（ALIYUN_OSS）之前插入：

```python
    # OpenClaw Gateway
    OPENCLAW_GATEWAY_URL: str = "ws://127.0.0.1:18081"
    OPENCLAW_TOKEN: str = ""
```

**Step 2: 验证配置**

Run: `cd backend && python -c "from app.config.config import settings; print(settings.OPENCLAW_GATEWAY_URL)"`
Expected: 输出 `ws://127.0.0.1:18081`

**Step 3: 提交**

```bash
git add backend/app/config/config.py
git commit -m "feat(openclaw): 添加 Gateway 配置项"
```

---

### Task 2: 后端服务 — OpenClaw WebSocket 客户端

**Files:**
- Create: `backend/app/services/openclaw_service.py`

**Step 1: 创建完整服务文件**

```python
"""
OpenClaw Gateway WebSocket 客户端
负责与 OpenClaw Gateway 建立 WebSocket 连接，处理 JSON-RPC 协议
"""

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from app.config.config import settings

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
        url = settings.OPENCLAW_GATEWAY_URL
        token = settings.OPENCLAW_TOKEN

        logger.info(f"正在连接 OpenClaw Gateway: {url}")
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
```

**Step 2: 验证语法**

Run: `cd backend && python -m py_compile app/services/openclaw_service.py`
Expected: 无输出

**Step 3: 提交**

```bash
git add backend/app/services/openclaw_service.py
git commit -m "feat(openclaw): 创建 WebSocket 客户端服务"
```

---

### Task 3: 后端路由 — OpenClaw API 接口

**Files:**
- Create: `backend/app/routes/openclaw.py`
- Modify: `backend/app/main.py`（末尾 HTTP Client router 之后）

**Step 1: 创建路由文件**

```python
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
    if not openclaw_service.is_connected():
        return {"connected": False}
    try:
        status = await openclaw_service.get_status()
        return {"connected": True, **status}
    except Exception as e:
        return {"connected": False, "error": str(e)}
```

**Step 2: 注册路由到 main.py**

在 `backend/app/main.py` 第 206 行（`# HTTP Client router` 之后）添加：

```python
# OpenClaw router
from app.routes import openclaw as openclaw_router
app.include_router(openclaw_router.router, prefix="/api")
```

**Step 3: 验证语法**

Run: `cd backend && python -m py_compile app/routes/openclaw.py && python -m py_compile app/main.py`
Expected: 无输出

**Step 4: 提交**

```bash
git add backend/app/routes/openclaw.py backend/app/main.py
git commit -m "feat(openclaw): 添加 API 路由（SSE 对话 + 中止 + 状态）"
```

---

### Task 4: 后端依赖 — 安装 websockets

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: 添加依赖**

在 `requirements.txt` 末尾添加：

```
# WebSocket client
websockets>=12.0
```

**Step 2: 安装**

Run: `cd backend && pip install websockets`
Expected: 安装成功

**Step 3: 提交**

```bash
git add backend/requirements.txt
git commit -m "chore: 添加 websockets 依赖"
```

---

### Task 5: 后端生命周期 — 启动/关闭 OpenClaw 连接

**Files:**
- Modify: `backend/app/main.py`（lifespan 函数）

**Step 1: 修改 lifespan 函数**

将 `backend/app/main.py` 第 81-99 行的 `lifespan` 函数替换为：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting application...")

    manager = get_manager()
    cleanup_task = asyncio.create_task(manager.start_cleanup_task())

    # 启动 OpenClaw 连接
    try:
        from app.services.openclaw_service import openclaw_service
        await openclaw_service.start()
    except Exception as e:
        logger.warning(f"OpenClaw 连接启动失败（功能将不可用）: {e}")

    yield

    logger.info("Shutting down application...")

    try:
        from app.services.openclaw_service import openclaw_service
        await openclaw_service.stop()
    except Exception as e:
        logger.error(f"OpenClaw 关闭异常: {e}")

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
```

**Step 2: 验证语法**

Run: `cd backend && python -m py_compile app/main.py`
Expected: 无输出

**Step 3: 提交**

```bash
git add backend/app/main.py
git commit -m "feat(openclaw): 在生命周期中管理连接"
```

---

### Task 6: 小程序 Markdown 组件

**Files:**
- Create: `tools-mini-program/src/components/Markdown/index.tsx`
- Create: `tools-mini-program/src/components/Markdown/index.scss`
- Modify: `tools-mini-program/package.json`（添加 marked 依赖）

**Step 1: 安装 marked**

Run: `cd tools-mini-program && npm install marked`

**Step 2: 创建组件**

```typescript
import { View } from '@tarojs/components'
import { marked } from 'marked'
import './index.scss'

interface MarkdownProps {
  content: string
}

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

export default function Markdown({ content }: MarkdownProps) {
  if (!content) return null

  const html = marked(content)

  return (
    <View className='markdown-renderer'>
      <rich-text nodes={html} />
    </View>
  )
}
```

**Step 3: 创建样式**

```scss
.markdown-renderer {
  line-height: 1.6;
  font-size: 28rpx;
  color: var(--text-primary);
  word-break: break-word;

  p { margin-bottom: 12rpx; }

  h1 { font-size: 36rpx; font-weight: 600; margin: 16rpx 0 8rpx; }
  h2 { font-size: 32rpx; font-weight: 600; margin: 14rpx 0 6rpx; }
  h3 { font-size: 30rpx; font-weight: 600; margin: 12rpx 0 4rpx; }

  pre {
    background: rgba(0, 0, 0, 0.3);
    border-radius: 8rpx;
    padding: 16rpx;
    overflow-x: auto;
    margin: 12rpx 0;

    code {
      font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
      font-size: 24rpx;
      color: #e2e8f0;
    }
  }

  code {
    background: rgba(59, 130, 246, 0.15);
    color: var(--color-primary);
    padding: 2rpx 8rpx;
    border-radius: 4rpx;
    font-size: 26rpx;
  }

  ul, ol { padding-left: 24rpx; margin-bottom: 12rpx; }
  li { margin-bottom: 6rpx; }

  blockquote {
    border-left: 4rpx solid var(--color-primary);
    padding-left: 16rpx;
    color: var(--text-secondary);
    margin: 12rpx 0;
  }

  a { color: var(--color-primary); }

  table {
    border-collapse: collapse;
    width: 100%;
    margin: 12rpx 0;
  }

  th, td {
    border: 1px solid var(--border-color);
    padding: 8rpx 12rpx;
  }

  th {
    background: rgba(59, 130, 246, 0.1);
    font-weight: 600;
  }

  hr {
    border: none;
    border-top: 1px solid var(--border-color);
    margin: 16rpx 0;
  }
}
```

**Step 4: 提交**

```bash
git add tools-mini-program/package.json tools-mini-program/package-lock.json tools-mini-program/src/components/Markdown/
git commit -m "feat(openclaw): 添加 Markdown 渲染组件"
```

---

### Task 7: 小程序 API 服务 — OpenClaw 封装

**Files:**
- Create: `tools-mini-program/src/services/openclaw.ts`

**Step 1: 创建 API 封装**

```typescript
import Taro from '@tarojs/taro'
import { getHeaders } from './request'

const API_BASE_URL = process.env.TARO_APP_API_URL || 'http://localhost:19092/api'

/**
 * OpenClaw 流式对话
 * 使用 enableChunked + onChunkReceived 接收 SSE 流
 */
export async function chatStream(
  message: string,
  sessionKey: string = 'main',
  onChunk: (chunk: string) => void,
  onDone?: () => void,
  onError?: (error: string) => void
): Promise<void> {
  const token = Taro.getStorageSync('auth_token')
  const header: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) {
    header['Authorization'] = `Bearer ${token}`
  }

  let buffer = ''

  try {
    const requestTask = Taro.request({
      url: `${API_BASE_URL}/openclaw/chat`,
      method: 'POST',
      data: { message, session_key: sessionKey },
      header,
      timeout: 120000,
      enableChunked: true,
      success: () => {
        parseSSEBuffer(buffer, onChunk)
        onDone?.()
      },
      fail: (err) => {
        onError?.(err.errMsg || '请求失败')
      }
    })

    requestTask.onChunkReceived?.((res: any) => {
      try {
        const chunk = typeof res.data === 'string'
          ? res.data
          : arrayBufferToString(res.data)

        buffer += chunk
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || trimmed.startsWith(':')) continue
          if (trimmed.startsWith('data: ')) {
            const jsonStr = trimmed.slice(6)
            try {
              const data = JSON.parse(jsonStr)
              if (data.type === 'chunk' && data.content) {
                onChunk(data.content)
              } else if (data.type === 'error') {
                onError?.(data.message || '服务端错误')
              }
            } catch {
              buffer = trimmed + '\n' + buffer
            }
          }
        }
      } catch (e) {
        console.error('[SSE Parse Error]', e)
      }
    })
  } catch (err: any) {
    onError?.(err.message || '网络异常')
  }
}

function arrayBufferToString(buf: ArrayBuffer): string {
  const decoder = new TextDecoder('utf-8')
  return decoder.decode(buf)
}

function parseSSEBuffer(buffer: string, onChunk: (chunk: string) => void) {
  const lines = buffer.split('\n')
  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('data: ')) {
      try {
        const data = JSON.parse(trimmed.slice(6))
        if (data.type === 'chunk' && data.content) {
          onChunk(data.content)
        }
      } catch { /* 忽略不完整的 JSON */ }
    }
  }
}

/** 获取会话历史 */
export async function loadHistory(sessionKey: string = 'main', limit: number = 50) {
  const res = await Taro.request({
    url: `${API_BASE_URL}/openclaw/history`,
    method: 'POST',
    data: { session_key: sessionKey, limit },
    header: getHeaders(),
    timeout: 15000
  })
  return res.data?.messages || []
}

/** 中止生成 */
export async function abortChat(sessionKey: string = 'main') {
  const res = await Taro.request({
    url: `${API_BASE_URL}/openclaw/abort`,
    method: 'POST',
    data: { session_key: sessionKey },
    header: getHeaders(),
    timeout: 10000
  })
  return res.data
}

/** 重置会话 */
export async function resetSession(sessionKey: string = 'main') {
  const res = await Taro.request({
    url: `${API_BASE_URL}/openclaw/reset?session_key=${sessionKey}`,
    method: 'POST',
    header: getHeaders(),
    timeout: 10000
  })
  return res.data
}

/** 获取状态 */
export async function getStatus() {
  const res = await Taro.request({
    url: `${API_BASE_URL}/openclaw/status`,
    method: 'GET',
    timeout: 10000
  })
  return res.data
}
```

**Step 2: 提交**

```bash
git add tools-mini-program/src/services/openclaw.ts
git commit -m "feat(openclaw): 创建 API 服务封装"
```

---

### Task 8: 小程序对话页面

**Files:**
- Create: `tools-mini-program/src/pages/openclaw/index.tsx`
- Create: `tools-mini-program/src/pages/openclaw/index.scss`

**Step 1: 创建页面组件**

```typescript
import { useState, useRef } from 'react'
import Taro, { useDidShow, useDidHide } from '@tarojs/taro'
import { View, Text, ScrollView, Textarea } from '@tarojs/components'
import { chatStream, resetSession, getStatus, abortChat } from '../../services/openclaw'
import Markdown from '../../components/Markdown'
import { useAuthGuard } from '../../hooks'
import './index.scss'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  isStreaming?: boolean
}

export default function OpenClawPage() {
  useAuthGuard()

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [connected, setConnected] = useState(true)
  const [scrollTop, setScrollTop] = useState(0)
  const abortRef = useRef(false)

  useDidShow(() => {
    checkStatus()
  })

  // 页面隐藏时中止生成
  useDidHide(() => {
    if (isStreaming) {
      abortChat('main').catch(() => {})
      setIsStreaming(false)
    }
  })

  const checkStatus = async () => {
    try {
      const status = await getStatus()
      setConnected(status.connected !== false)
    } catch {
      setConnected(false)
    }
  }

  const scrollToBottom = () => {
    setScrollTop(Date.now())
  }

  const handleSend = async () => {
    if (!inputValue.trim() || isStreaming) return

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      timestamp: Date.now()
    }

    const assistantMessage: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      isStreaming: true
    }

    setMessages(prev => [...prev, userMessage, assistantMessage])
    setInputValue('')
    setIsStreaming(true)
    abortRef.current = false
    scrollToBottom()

    try {
      await chatStream(
        userMessage.content,
        'main',
        (chunk: string) => {
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              return [...prev.slice(0, -1), { ...last, content: last.content + chunk }]
            }
            return prev
          })
          scrollToBottom()
        },
        () => {
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              return [...prev.slice(0, -1), { ...last, isStreaming: false }]
            }
            return prev
          })
          setIsStreaming(false)
        },
        (error: string) => {
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              return [...prev.slice(0, -1), {
                ...last,
                content: last.content ? `${last.content}\n\n[生成失败] ${error}` : `[生成失败] ${error}`,
                isStreaming: false
              }]
            }
            return prev
          })
          setIsStreaming(false)
        }
      )
    } catch (err: any) {
      setIsStreaming(false)
      Taro.showToast({ title: err.message || '发送失败', icon: 'none' })
    }
  }

  const handleStop = async () => {
    abortRef.current = true
    try {
      await abortChat('main')
    } catch (err) {
      console.error('中止请求失败:', err)
    }
    setIsStreaming(false)
    setMessages(prev => {
      const last = prev[prev.length - 1]
      if (last && last.role === 'assistant') {
        return [...prev.slice(0, -1), { ...last, isStreaming: false }]
      }
      return prev
    })
    Taro.showToast({ title: '已停止生成', icon: 'none' })
  }

  const handleNewChat = async () => {
    if (isStreaming) {
      Taro.showToast({ title: '请先生成完成', icon: 'none' })
      return
    }
    try {
      await resetSession('main')
      setMessages([])
      Taro.showToast({ title: '已新建对话', icon: 'success' })
    } catch (err: any) {
      Taro.showToast({ title: '新建失败', icon: 'none' })
    }
  }

  return (
    <View className='openclaw-page'>
      {/* 顶部工具栏 */}
      <View className='toolbar'>
        <Text className='toolbar-btn' onClick={handleNewChat}>
          + 新对话
        </Text>
        {!connected && (
          <Text className='disconnected-badge'>连接断开</Text>
        )}
      </View>

      {/* 消息列表 */}
      {messages.length === 0 ? (
        <View className='empty-state'>
          <View className='empty-icon-wrapper'>
            <View className='empty-icon-circle' />
          </View>
          <Text className='empty-title'>OpenClaw AI 助手</Text>
          <Text className='empty-desc'>输入消息开始对话</Text>
        </View>
      ) : (
        <ScrollView
          className='chat-scroll'
          scrollY
          scrollWithAnimation
          scrollTop={scrollTop}
        >
          <View className='messages-list'>
            {messages.map((msg) => (
              <View key={msg.id} className={`message-row ${msg.role === 'user' ? 'message-row-user' : 'message-row-assistant'}`}>
                <View className={`message-bubble ${msg.role === 'user' ? 'bubble-user' : 'bubble-assistant'}`}>
                  {msg.role === 'user' ? (
                    <Text className='message-text' selectable>{msg.content}</Text>
                  ) : (
                    <Markdown content={msg.content} />
                  )}
                  {msg.isStreaming && <Text className='streaming-indicator'>...</Text>}
                </View>
              </View>
            ))}
          </View>
        </ScrollView>
      )}

      {/* 输入区域 */}
      <View className='input-area'>
        <View className='input-wrapper'>
          <Textarea
            className='chat-input'
            value={inputValue}
            onInput={(e) => setInputValue(e.detail.value)}
            placeholder='输入消息...'
            maxlength={4000}
            autoHeight
            disabled={isStreaming}
            confirmType='send'
            onConfirm={handleSend}
          />
        </View>
        {isStreaming ? (
          <button className='stop-btn' onClick={handleStop}>
            停止
          </button>
        ) : (
          <button
            className={`send-btn ${!inputValue.trim() ? 'disabled' : ''}`}
            disabled={!inputValue.trim()}
            onClick={handleSend}
          >
            发送
          </button>
        )}
      </View>
    </View>
  )
}
```

**Step 2: 创建样式文件**

```scss
.openclaw-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16rpx 32rpx;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.toolbar-btn {
  font-size: 28rpx;
  color: var(--color-primary);
  padding: 8rpx 16rpx;
  border-radius: var(--radius-sm);
  cursor-pointer;

  &:active {
    background: rgba(59, 130, 246, 0.1);
  }
}

.disconnected-badge {
  font-size: 24rpx;
  color: var(--color-warning);
  padding: 4rpx 12rpx;
  background: rgba(245, 158, 11, 0.1);
  border-radius: var(--radius-sm);
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 48rpx;
}

.empty-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32rpx;
}

.empty-icon-circle {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary, #3b82f6), #8b5cf6);
  opacity: 0.15;
}

.empty-title {
  font-size: 36rpx;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16rpx;
}

.empty-desc {
  font-size: 28rpx;
  color: var(--text-secondary);
}

.chat-scroll {
  flex: 1;
}

.messages-list {
  padding: 32rpx 24rpx;
}

.message-row {
  margin-bottom: 24rpx;
  display: flex;
}

.message-row-user {
  justify-content: flex-end;
}

.message-row-assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 85%;
  padding: 24rpx 32rpx;
  border-radius: var(--radius-md);
  word-break: break-word;
  white-space: pre-wrap;
}

.bubble-user {
  background: var(--color-primary);
  color: #fff;
}

.bubble-assistant {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.message-text {
  font-size: 28rpx;
  line-height: 1.6;
}

.streaming-indicator {
  font-size: 28rpx;
  color: var(--text-tertiary);
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.input-area {
  display: flex;
  align-items: flex-end;
  gap: 16rpx;
  padding: 24rpx;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
}

.input-wrapper {
  flex: 1;
}

.chat-input {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16rpx 24rpx;
  font-size: 28rpx;
  color: var(--text-primary);
  max-height: 200rpx;
  width: 100%;

  &::placeholder {
    color: var(--text-tertiary);
  }
}

.send-btn {
  flex-shrink: 0;
  width: 120rpx;
  height: 72rpx;
  background: var(--color-primary);
  color: #fff;
  font-size: 28rpx;
  font-weight: 500;
  border-radius: var(--radius-sm);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;

  &.disabled {
    background: var(--text-disabled);
    opacity: 0.5;
  }
}

.stop-btn {
  flex-shrink: 0;
  width: 120rpx;
  height: 72rpx;
  background: var(--color-danger);
  color: #fff;
  font-size: 28rpx;
  font-weight: 500;
  border-radius: var(--radius-sm);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;

  &:active {
    background: #dc2626;
  }
}
```

**Step 3: 提交**

```bash
git add tools-mini-program/src/pages/openclaw/
git commit -m "feat(openclaw): 创建对话页面"
```

---

### Task 9: 注册页面路由和工具映射

**Files:**
- Modify: `tools-mini-program/src/app.config.ts`
- Modify: `tools-mini-program/src/services/tool.ts`

**Step 1: 添加页面路由**

在 `app.config.ts` 的 `pages` 数组第 15 行（`'pages/help/index'` 之后）添加：

```typescript
    'pages/openclaw/index',
```

**Step 2: 添加工具路径映射**

在 `services/tool.ts` 的 `TOOL_PATH_MAP` 中添加（第 29 行 `'course-platform': null,` 之后）：

```typescript
  'openclaw': '/pages/openclaw/index',
```

**Step 3: 提交**

```bash
git add tools-mini-program/src/app.config.ts tools-mini-program/src/services/tool.ts
git commit -m "feat(openclaw): 注册页面路由和工具映射"
```

---

### Task 10: 后端测试

**Step 1: 启动后端**

Run: `cd backend && uvicorn app.main:app --reload --port 19092`
Expected: 启动成功，日志显示 "OpenClaw Gateway 连接任务已启动" 和 "OpenClaw 连接成功"

**Step 2: 测试 SSE 接口**

Run: `curl -X POST http://localhost:19092/api/openclaw/chat -H 'Content-Type: application/json' -d '{"message": "你好"}'`
Expected: SSE 流式返回，依次收到 `type: "started"` → 多次 `type: "chunk"` → `type: "done"`

**Step 3: 测试状态接口**

Run: `curl http://localhost:19092/api/openclaw/status`
Expected: 返回 `{"connected": true, ...}`

---

### Task 11: 小程序测试

**Step 1: 启动小程序**

Run: `cd tools-mini-program && npm run dev:weapp`
Expected: 编译成功，无报错

**Step 2: 微信开发者工具测试**
1. 打开首页，找到 OpenClaw 工具卡片
2. 点击进入对话页面
3. 输入消息并发送，验证 AI 回复流式显示 + Markdown 渲染
4. 点击"停止"按钮，验证生成中断
5. 点击"+ 新对话"，验证消息清空
6. 验证页面离开时自动中止生成
