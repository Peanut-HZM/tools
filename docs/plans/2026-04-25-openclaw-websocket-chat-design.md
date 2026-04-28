# OpenClaw 小程序 WebSocket 流式对话

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为小程序端的 OpenClaw 聊天功能实现 WebSocket 流式对话，替代当前不可靠的 `enableChunked` + `onChunkReceived` 方案。

**架构：** 新增 FastAPI WebSocket 端点 `/api/openclaw/chat/ws`，小程序通过 `Taro.connectSocket` 建立 WebSocket 连接，逐条接收 AI 响应 chunk。不影响现有 Web 端的 SSE 流式对话和历史消息加载功能。

**技术栈：** FastAPI WebSocket, Taro `connectSocket`, Python async generator, JSON 消息协议

---

### Task 1: 后端新增 OpenClaw WebSocket 路由

**Files:**
- Create: `backend/app/routes/openclaw_ws.py`
- Modify: `backend/app/main.py:249-257` (注册新路由)

**Step 1: 创建 WebSocket 路由文件**

```python
"""
OpenClaw WebSocket 路由
专为小程序端提供流式对话支持
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

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


async def abort_websocket_chat(session_key: str):
    """中止指定会话的 WebSocket 生成"""
    for ws_id, abort_event in list(_active_ws.items()):
        if ws_id.startswith(f"{session_key}:"):
            abort_event.set()
            break
```

**Step 2: 注册路由到 main.py**

修改 `backend/app/main.py`，在 openclaw 路由注册区域添加：

```python
# 在 import openclaw as openclaw_router 附近添加
from app.routes import openclaw_ws as openclaw_ws_router

# 在 openclaw_router 注册后添加
app.include_router(openclaw_ws_router.router, prefix="/api")
```

找到第 252 行 `app.include_router(openclaw_router.router, prefix="/api")`，在其后追加：

```python
from app.routes import openclaw_ws as openclaw_ws_router
app.include_router(openclaw_ws_router.router, prefix="/api")
```

**Step 3: 验证后端能正常启动**

Run: `cd backend && python -m py_compile app/routes/openclaw_ws.py`
Expected: 无输出（编译成功）

Run: `cd backend && python -c "from app.routes.openclaw_ws import router; print('OK')"`
Expected: 输出 `OK`

**Step 4: 提交**

```bash
cd backend && git add app/routes/openclaw_ws.py app/main.py
git commit -m "feat: OpenClaw WebSocket 流式对话端点（小程序专用）"
```

---

### Task 2: 前端新增 chatWebSocket 服务函数

**Files:**
- Modify: `tools-mini-program/src/services/openclaw.ts:1-177` (新增 chatWebSocket 函数)

**Step 1: 在 openclaw.ts 中新增 chatWebSocket 函数**

在文件末尾（`getStatus` 函数之后）添加：

```typescript
/**
 * WebSocket 流式对话（小程序专用）
 * 使用 Taro.connectSocket 建立 WebSocket 连接，逐条接收 AI 响应
 */
export function chatWebSocket(
  message: string,
  sessionKey: string = 'main',
  onChunk: (chunk: string) => void,
  onDone?: () => void,
  onError?: (error: string) => void
): { abort: () => void } {
  let socketTask: Taro.SocketTask | null = null
  let isDone = false
  const API_WS_URL = API_BASE_URL.replace('http', 'ws').replace('/api', '') + '/api/openclaw/chat/ws'

  console.log('[chatWebSocket] 开始连接:', API_WS_URL)

  socketTask = Taro.connectSocket({
    url: `${API_WS_URL}?session_key=${encodeURIComponent(sessionKey)}`,
    success: () => {
      console.log('[chatWebSocket] WebSocket 连接成功')
      // 连接成功后发送消息
      if (socketTask) {
        socketTask.send({
          data: JSON.stringify({
            type: 'message',
            content: message,
          }),
          success: () => {
            console.log('[chatWebSocket] 消息发送成功')
          },
          fail: (err) => {
            console.error('[chatWebSocket] 消息发送失败:', err)
            if (!isDone) {
              isDone = true
              onError?.(`消息发送失败: ${JSON.stringify(err)}`)
            }
          }
        })
      }
    },
    fail: (err) => {
      console.error('[chatWebSocket] 连接失败:', err)
      if (!isDone) {
        isDone = true
        onError?.(`WebSocket 连接失败: ${JSON.stringify(err)}`)
      }
    }
  })

  // 监听消息
  if (socketTask) {
    socketTask.onMessage((res) => {
      try {
        const data = JSON.parse(res.data)
        console.log('[chatWebSocket] 收到消息:', data.type, data.content ? data.content.substring(0, 50) : '')

        if (data.type === 'chunk' && data.content) {
          onChunk(data.content)
        } else if (data.type === 'error') {
          if (!isDone) {
            isDone = true
            onError?.(data.message || '服务端错误')
          }
        } else if (data.type === 'done' || data.type === 'aborted') {
          if (!isDone) {
            isDone = true
            onDone?.()
            socketTask?.close()
          }
        } else if (data.type === 'started') {
          console.log('[chatWebSocket] 生成已开始, runId:', data.runId)
        }
      } catch (e) {
        console.error('[chatWebSocket] JSON 解析失败:', e, res.data)
      }
    })

    socketTask.onClose(() => {
      console.log('[chatWebSocket] 连接已关闭')
      if (!isDone) {
        isDone = true
        // 如果还没收到 done 就关闭了，视为异常
        onError?.('连接意外关闭')
      }
    })

    socketTask.onError((err) => {
      console.error('[chatWebSocket] 连接错误:', err)
      if (!isDone) {
        isDone = true
        onError?.(`连接错误: ${JSON.stringify(err)}`)
      }
    })
  }

  // 返回中止函数
  return {
    abort: () => {
      if (socketTask && !isDone) {
        // 发送中止消息
        socketTask.send({
          data: JSON.stringify({ type: 'abort' }),
        }).catch(() => {})
      }
    }
  }
}
```

**Step 2: 验证编译**

Run: `cd tools-mini-program && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`
Expected: 无错误输出

**Step 3: 提交**

```bash
cd tools-mini-program && git add src/services/openclaw.ts
git commit -m "feat: OpenClaw WebSocket 流式对话服务（小程序专用）"
```

---

### Task 3: 修改聊天页面使用 WebSocket 替代 SSE

**Files:**
- Modify: `tools-mini-program/src/pages/openclaw/index.tsx` (修改 handleSend 和 handleStop)

**Step 1: 修改 import**

将第 4 行：
```typescript
import { chatStream, resetSession, getStatus, abortChat, loadHistory } from '../../services/openclaw'
```
改为：
```typescript
import { chatWebSocket, resetSession, getStatus, abortChat, loadHistory } from '../../services/openclaw'
```

**Step 2: 添加 socketTaskRef**

在 `abortRef` 之后（第 79 行后）添加：
```typescript
const wsAbortRef = useRef<{ abort: () => void } | null>(null)
```

**Step 3: 重写 handleSend 中的 chatStream 调用**

将 `handleSend` 函数中 `try { await chatStream(...) }` 部分替换为：

```typescript
try {
  const wsResult = chatWebSocket(
    userMessage.content,
    'main',
    // onChunk
    (chunk: string) => {
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMsgId
            ? { ...msg, content: chunk }
            : msg
        )
      )
      scrollToBottom()
    },
    // onDone
    () => {
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMsgId
            ? { ...msg, isStreaming: false }
            : msg
        )
      )
      setIsStreaming(false)
      wsAbortRef.current = null
    },
    // onError
    (error: string) => {
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMsgId
            ? { ...msg, content: msg.content || `[生成失败] ${error}`, isStreaming: false }
            : msg
        )
      )
      setIsStreaming(false)
      wsAbortRef.current = null
    }
  )
  wsAbortRef.current = wsResult
} catch (err: any) {
  setIsStreaming(false)
  wsAbortRef.current = null
  Taro.showToast({ title: err.message || '发送失败', icon: 'none' })
}
```

**Step 4: 修改 handleStop**

将 `handleStop` 函数替换为：

```typescript
const handleStop = () => {
  if (wsAbortRef.current) {
    wsAbortRef.current.abort()
    wsAbortRef.current = null
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
```

**Step 5: 修改 useDidHide（页面隐藏时中止）**

将 `useDidHide` 中的 `abortChat` 调用改为同时调用 WebSocket 中止：

```typescript
useDidHide(() => {
  if (isStreaming) {
    if (wsAbortRef.current) {
      wsAbortRef.current.abort()
      wsAbortRef.current = null
    }
    setIsStreaming(false)
  }
})
```

**Step 6: 验证编译**

Run: `cd tools-mini-program && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`
Expected: 无错误输出

**Step 7: 提交**

```bash
cd tools-mini-program && git add src/pages/openclaw/index.tsx
git commit -m "fix: OpenClaw 聊天页面改用 WebSocket 流式对话"
```

---

### Task 4: 启动后端并测试

**Step 1: 启动后端服务**

Run: `cd backend && uvicorn app.main:app --reload --port 19092`
Expected: 启动成功，日志显示 "OpenClaw 连接成功"

**Step 2: 启动小程序开发服务**

Run: `cd tools-mini-program && pnpm dev:weapp -- --watch`
Expected: 编译成功，无错误

**Step 3: 微信开发者工具中测试**

1. 打开微信开发者工具，导入小程序项目
2. 进入 OpenClaw 聊天页面
3. 发送一条测试消息
4. 验证：
   - ✅ 用户消息显示在聊天区域
   - ✅ AI 回复内容逐字显示（流式效果）
   - ✅ 点击"停止"按钮能中止生成
   - ✅ 切换页面再回来，历史消息正常加载
   - ✅ 小程序 Console 无报错

**Step 4: 验证 Web 端不受影响**

- 访问 Web 端 OpenClaw 聊天页面（http://localhost:5178 或对应地址）
- 发送消息，验证 SSE 流式仍然正常工作
