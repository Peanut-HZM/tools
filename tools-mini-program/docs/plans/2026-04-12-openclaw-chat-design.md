# OpenClaw 对话工具设计文档

## 概述

在工具箱小程序中新增 OpenClaw AI 对话工具，通过后端 WebSocket 代理将 OpenClaw Gateway 的自定义 JSON-RPC 协议转换为小程序友好的 HTTP SSE 流式响应。

## 架构

```
小程序 OpenClaw 页面
    │
    │  HTTP POST /api/openclaw/chat (SSE)
    ▼
FastAPI 后端 (openclaw.py routes)
    │
    │  WebSocket ws://127.0.0.1:18081
    ▼
OpenClaw Gateway (端口 18081, Token 认证)
    │
    │  内部调用
    ▼
百炼 Qwen/Kimi 等模型
```

## OpenClaw 协议分析

OpenClaw 运行在 `127.0.0.1:18081`，使用 WebSocket 自定义 JSON-RPC 协议：

### 连接握手
1. 客户端连接 WebSocket
2. 服务器发送 `connect.challenge` 事件（含 nonce）
3. 客户端发送 `connect` 请求，携带 token 和协议版本（minProtocol/maxProtocol = 3）
4. 服务器返回 `hello_ok`

### 核心 RPC 方法

| 方法 | 用途 | 参数 | 返回 |
|------|------|------|------|
| `chat.send` | 发送消息 | `{ sessionKey, message, thinking?, deliver? }` | `{ runId, status }` + event 推送 |
| `chat.history` | 获取历史 | `{ sessionKey, limit? }` | `{ messages: [...] }` |
| `chat.abort` | 中止生成 | `{ sessionKey, runId }` | `{ ok, aborted }` |
| `sessions.list` | 会话列表 | 可选过滤参数 | `{ sessions: [...] }` |
| `sessions.reset` | 重置会话 | `{ key, reason? }` | 确认 |
| `status` | 状态检查 | 无 | 网关状态 |
| `models.list` | 模型列表 | 无 | 可用模型列表 |

### 流式响应机制
`chat.send` 先返回 ack `{ runId, status: "started" }`，AI 生成的每个 chunk 通过 `event: "chat"` 事件推送到 WebSocket 连接。

## 后端代理实现

### 连接管理
- Python 后端使用 `websockets` 库连接 OpenClaw Gateway
- 维护一个长连接池（单例），启动时建立连接
- 自动重连机制：连接断开后自动重试（指数退避）

### 协议转换
```
小程序 POST → FastAPI → WebSocket.send({ type: "req", method: "chat.send" })
OpenClaw ack → FastAPI → SSE data: { "type": "started", "runId": "..." }
OpenClaw event "chat" (state:delta) → FastAPI → SSE data: { "type": "chunk", "content": "..." }
  # payload 格式: { state: "delta"/"final", message: { content: [{ text: "..." }] } }
  # lifecycle 事件: { stream: "lifecycle", data: { phase: "end" } } 表示完成
OpenClaw 完成 (state:final) → FastAPI → SSE data: { "type": "done" }
```

### 配置项
- `OPENCLAW_GATEWAY_URL`: WebSocket 地址，默认 `ws://127.0.0.1:18081`
- `OPENCLAW_TOKEN`: 认证 token

## 小程序端设计

### 页面结构
- 顶部导航栏显示 "OpenClaw"
- 中间滚动消息列表（用户消息靠右，AI 消息靠左）
- 底部输入框 + 发送按钮
- 支持流式渲染 AI 回复（Markdown 格式）
- 支持停止生成和新建对话

### Markdown 渲染
- 使用 `marked` 库将 Markdown 解析为 HTML
- 通过小程序原生 `rich-text` 组件渲染 HTML
- 支持代码块语法高亮、表格、列表、链接等
- 流式更新：每次收到新 chunk 时重新解析完整 Markdown 内容
- 该方案与 Taro + React 架构完全兼容

### 技术实现
- 使用 `Taro.request` 的 `enableChunked: true` + `onChunkReceived` 接收 SSE 流
- 解析 SSE `data:` 行，提取 JSON 中的 `type: "chunk"` 内容
- 默认 sessionKey 为 `main`（OpenClaw 主会话）
- 流式接收 chunk 并逐段追加到当前消息
- 使用 `towxml` 或 `wemark` 等小程序 Markdown 渲染库显示 AI 回复

### 错误处理
- 连接失败：显示"OpenClaw 服务不可用"
- Token 错误：显示"服务配置错误"
- 超时：120s 超时提示
- 断网：检测并显示重连提示

## 文件清单

**后端：**
- `backend/app/routes/openclaw.py` — FastAPI 路由（SSE endpoint + 会话管理）
- `backend/app/services/openclaw_service.py` — WebSocket 连接管理、协议转换
- `backend/app/config/config.py` — 新增 OpenClaw 配置项
- `backend/app/main.py` — 注册 openclaw router
- `backend/requirements.txt` — 添加 `websockets` 依赖

**前端：**
- `src/pages/openclaw/index.tsx` — 对话页面
- `src/pages/openclaw/index.scss` — 样式
- `src/services/openclaw.ts` — API 封装
- `src/app.config.ts` — 添加页面路由
- `src/services/tool.ts` — 工具路径映射
- `package.json` — 添加 `marked` Markdown 解析库依赖

## 实施优先级

1. **Phase 1**（核心对话）：后端 WebSocket 代理 + 小程序对话页面 + 流式渲染
2. **Phase 2**（增强功能）：停止生成、新建对话、会话列表（后续迭代）
