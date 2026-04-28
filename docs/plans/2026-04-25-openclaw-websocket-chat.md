# OpenClaw 小程序 WebSocket 流式对话 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为小程序端的 OpenClaw 聊天功能实现 WebSocket 流式对话，替代当前不可靠的 `enableChunked` + `onChunkReceived` 方案。

**架构：** 新增 FastAPI WebSocket 端点 `/api/openclaw/chat/ws`，小程序通过 `Taro.connectSocket` 建立 WebSocket 连接，逐条接收 AI 响应 chunk。WebSocket 端点复用现有的 `openclaw_service.send_chat()` async generator，将 SSE 格式的 chunk 转换为 JSON 消息通过 WebSocket 发送。不影响现有 Web 端的 SSE 流式对话和历史消息加载功能。

**技术栈：** FastAPI WebSocket, Taro `connectSocket`, Python async generator, JSON 消息协议

---

### Task 1: 后端新增 OpenClaw WebSocket 路由文件

**Files:**
- Create: `backend/app/routes/openclaw_ws.py`

**Step 1: 创建 WebSocket 路由文件**

创建文件 `backend/app/routes/openclaw_ws.py`，内容如下：

```python
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
```

**Step 2: 验证文件能正常导入**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/backend && python -c "from app.routes.openclaw_ws import router; print('OK')"`
Expected: 输出 `OK`，无报错

**Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
git add app/routes/openclaw_ws.py
git commit -m "feat: OpenClaw WebSocket 流式对话路由（小程序专用）"
```

---

### Task 2: 后端注册 WebSocket 路由到 main.py

**Files:**
- Modify: `backend/app/main.py:252` 附近

**Step 1: 在 openclaw_router 注册后添加 WebSocket 路由**

读取 `backend/app/main.py` 找到第 252 行 `app.include_router(openclaw_router.router, prefix="/api")`，在其后添加：

```python
# OpenClaw WebSocket router (mini-program)
from app.routes import openclaw_ws as openclaw_ws_router
app.include_router(openclaw_ws_router.router, prefix="/api")
```

具体操作：在第 252 行 `app.include_router(openclaw_router.router, prefix="/api")` 后插入 3 行新代码。

**Step 2: 验证后端能正常启动**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/backend && python -m py_compile app/main.py && echo "OK"`
Expected: 输出 `OK`，无报错

**Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
git add app/main.py
git commit -m "feat: 注册 OpenClaw WebSocket 路由"
```

---

### Task 3: 前端新增 chatWebSocket 服务函数

**Files:**
- Modify: `tools-mini-program/src/services/openclaw.ts`

**Step 1: 在 openclaw.ts 末尾添加 chatWebSocket 函数**

在文件最后（`getStatus` 函数之后，第 176 行之后）追加以下代码：

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
  // 将 HTTP URL 转为 WebSocket URL: http://x/api -> ws://x
  const baseUrl = API_BASE_URL.replace('/api', '')
  const wsUrl = baseUrl.startsWith('https')
    ? baseUrl.replace('https', 'wss') + '/api/openclaw/chat/ws'
    : baseUrl.replace('http', 'ws') + '/api/openclaw/chat/ws'

  console.log('[chatWebSocket] 开始连接:', wsUrl)

  socketTask = Taro.connectSocket({
    url: `${wsUrl}?session_key=${encodeURIComponent(sessionKey)}`,
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
        socketTask.send({
          data: JSON.stringify({ type: 'abort' }),
        }).catch(() => {})
      }
    }
  }
}
```

**Step 2: 验证 TypeScript 编译**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/tools-mini-program && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`
Expected: 无错误输出

**Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/tools-mini-program
git add src/services/openclaw.ts
git commit -m "feat: OpenClaw WebSocket 流式对话服务（小程序专用）"
```

---

### Task 4: 修改聊天页面 import 和添加 wsAbortRef

**Files:**
- Modify: `tools-mini-program/src/pages/openclaw/index.tsx:4` 和 `index.tsx:79`

**Step 1: 修改 import 语句**

将第 4 行：
```typescript
import { chatStream, resetSession, getStatus, abortChat, loadHistory } from '../../services/openclaw'
```
改为：
```typescript
import { chatWebSocket, resetSession, getStatus, abortChat, loadHistory } from '../../services/openclaw'
```

**Step 2: 添加 wsAbortRef**

在第 79 行 `const abortRef = useRef(false)` 之后添加：
```typescript
const wsAbortRef = useRef<{ abort: () => void } | null>(null)
```

**Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/tools-mini-program
git add src/pages/openclaw/index.tsx
git commit -m "refactor: OpenClaw 聊天页面引入 WebSocket 引用"
```

---

### Task 5: 重写 handleSend 使用 chatWebSocket

**Files:**
- Modify: `tools-mini-program/src/pages/openclaw/index.tsx` (handleSend 函数)

**Step 1: 替换 handleSend 中的 chatStream 调用**

找到 `handleSend` 函数中的 `try { await chatStream(...) }` 部分（约第 162-199 行），将其替换为：

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

**Step 2: 验证 TypeScript 编译**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/tools-mini-program && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`
Expected: 无错误输出

**Step 3: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/tools-mini-program
git add src/pages/openclaw/index.tsx
git commit -m "fix: handleSend 改用 WebSocket 流式对话"
```

---

### Task 6: 修改 handleStop 和 useDidHide

**Files:**
- Modify: `tools-mini-program/src/pages/openclaw/index.tsx` (handleStop 函数和 useDidHide)

**Step 1: 替换 handleStop 函数**

将 `handleStop` 函数（约第 206-221 行）替换为：

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

**Step 2: 修改 useDidHide**

将 `useDidHide` 回调（约第 87-92 行）中的 `abortChat` 调用改为使用 `wsAbortRef`：

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

**Step 3: 验证 TypeScript 编译**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/tools-mini-program && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`
Expected: 无错误输出

**Step 4: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/tools-mini-program
git add src/pages/openclaw/index.tsx
git commit -m "fix: handleStop 和 useDidHide 改用 WebSocket 中止"
```

---

### Task 7: 启动后端并验证 WebSocket 端点可用

**Files:**
- None (verification only)

**Step 1: 启动后端服务**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/backend && uvicorn app.main:app --reload --port 19092`
Expected: 启动成功，日志中包含 "OpenClaw 连接成功" 或类似连接信息

**Step 2: 验证 WebSocket 端点存在**

在浏览器或终端中访问 `http://localhost:19092/docs`，确认 `/openclaw/chat/ws` WebSocket 端点出现在 Swagger UI 中。

Expected: 能看到 `GET /openclaw/chat/ws` WebSocket 端点

**注意：** 此步骤不需要测试 WebSocket 连接本身（需要在小程序环境中测试），只需确认端点已注册。

---

### Task 8: 启动小程序并在微信开发者工具中测试

**Files:**
- None (manual testing)

**Step 1: 启动小程序开发服务**

Run: `cd /Users/huazhongmin/IdeaProjects/tools/tools-mini-program && pnpm dev:weapp -- --watch`
Expected: 编译成功，输出类似 `webpack compiled successfully`，无错误

**Step 2: 在微信开发者工具中测试**

1. 打开微信开发者工具
2. 导入/打开项目 `tools-mini-program`
3. 等待编译完成
4. 进入 OpenClaw 聊天页面
5. 发送一条测试消息（如 "你好"）
6. 观察以下行为：
   - ✅ 用户消息立即显示在聊天区域（蓝色气泡，右侧）
   - ✅ AI 回复内容逐字显示（流式效果，灰色气泡，左侧）
   - ✅ AI 回复过程中显示 "..." 流式指示器
   - ✅ 回复完成后 "..." 消失
   - ✅ 点击"停止"按钮能立即中止生成
   - ✅ 页面切走再回来，历史消息正常加载
   - ✅ 小程序 Console 没有红色报错

**Step 3: 验证 Web 端不受影响**

访问 Web 前端（`http://localhost:5178` 或项目对应地址），进入 OpenClaw 聊天页面，发送消息，验证 SSE 流式仍然正常工作。

Expected: Web 端 SSE 流式对话正常，不受 WebSocket 端点影响
