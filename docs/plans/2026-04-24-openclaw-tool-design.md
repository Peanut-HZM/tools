# OpenClaw 工具完整实现设计

## 概述

将 OpenClaw AI 对话功能作为标准工具集成到平台中，实现前端用户端聊天页面 + 后台管理配置控制面板。后端 API 已完整实现，本次主要是补充前端和后台管理能力。

## 系统架构

```
前端 (React)                    后端 (FastAPI)                    外部服务
┌─────────────┐              ┌─────────────────────┐            ┌──────────────┐
│ OpenClawChat │ ──SSE──→    │ /api/openclaw/chat  │ ──WS──→    │ OpenClaw GW  │
│ (用户聊天)   │ ←──SSE──    │ (SSE 流式响应)       │ ←──WS──    │ (ws://...)   │
└─────────────┘              └─────────────────────┘            └──────────────┘
                                  ↑
┌──────────────────┐       ┌─────────────────────┐
│ OpenClawMgmt     │ ──→   │ /api/admin/openclaw │
│ (后台管理面板)    │       │ /config             │
└──────────────────┘       └─────────────────────┘
                                  ↑
                           ┌──────────────────┐
                           │ openclaw_configs │
                           │ (数据库配置表)    │
                           └──────────────────┘
```

## 数据库设计

### 新增表：`openclaw_configs`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | VARCHAR(36) PK | 主键 |
| `config_key` | VARCHAR(50) UNIQUE | 配置键（gateway_url, token, enabled） |
| `config_value` | TEXT | 配置值 |
| `updated_at` | DATETIME | 最后更新时间 |

初始化数据：
```sql
INSERT INTO openclaw_configs (id, config_key, config_value, updated_at) VALUES
  (UUID(), 'gateway_url', 'ws://127.0.0.1:18081', NOW()),
  (UUID(), 'token', '', NOW()),
  (UUID(), 'enabled', 'true', NOW());
```

### 修改：`tools_data.py`

新增 Tool 记录：
```python
Tool(
    id="openclaw",
    icon="fa-comments",
    iconColor="bg-violet-500",
    title="OpenClaw AI 对话",
    description="连接 OpenClaw Gateway 的 AI 智能对话助手",
    rating=4.9,
    usageCount="New",
    category="AI 工具",
    require_login=True,
)
```

## 后端 API 设计

### 新增管理端点（`/api/admin/openclaw/*`）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/admin/openclaw/config` | 获取当前配置（Token 脱敏） | admin |
| PUT | `/api/admin/openclaw/config` | 更新配置并热加载 | admin |
| GET | `/api/admin/openclaw/status` | 获取连接状态 + 历史统计 | admin |
| POST | `/api/admin/openclaw/reconnect` | 手动重连 | admin |
| POST | `/api/admin/openclaw/disconnect` | 断开连接 | admin |

### 修改现有端点

| 端点 | 变更 |
|------|------|
| `GET /api/openclaw/status` | 改为从数据库读取 enabled 配置，未启用时返回 `{connected: false, disabled: true}` |
| `POST /api/openclaw/chat` 等 | 增加 enabled 检查，未启用时返回 502 |

### 配置热加载逻辑

```
PUT /api/admin/openclaw/config
  → 验证新配置（URL 格式、Token 非空）
  → 更新数据库 openclaw_configs 表
  → openclaw_service.reload_config(new_config)
    → 关闭旧连接
  → 用新配置重新连接
  → 返回新状态
```

## 前端组件设计

### 用户端：`/tools/openclaw` — OpenClawChat 页面

```
OpenClawChat (页面容器)
├── ChatHeader
│   ├── 标题 "OpenClaw AI 对话"
│   ├── 连接状态指示灯（绿/红）
│   └── 重置会话按钮
├── ChatMessages (消息列表)
│   ├── UserMessage (气泡，右侧)
│   ├── BotMessage (气泡，左侧，支持流式打字效果)
│   └── ErrorMessage
├── ChatInput (底部输入区)
│   ├── 文本输入框
│   ├── 发送按钮
│   └── 中止生成按钮（生成中时显示）
└── EmptyState (无消息时的占位提示)
```

### 后台管理：`/admin/openclaw` — OpenClaw 管理面板

```
OpenClawManagement (页面容器)
├── 状态卡片
│   ├── 连接状态（颜色指示 + 文字）
│   ├── Gateway 地址（只读展示）
│   ├── Token（脱敏展示）
│   └── 操作按钮：[ 重连 ] [ 断开 ]
├── 配置表单
│   ├── Gateway URL (输入框)
│   ├── Token (密码输入框)
│   ├── 启用/禁用 (开关)
│   └── [ 保存配置 ] 按钮
└── 连接日志（简易列表）
    ├── 时间 | 事件 | 详情
    └── 最近 50 条
```

## 错误处理

### 后端

- Gateway 未连接 → 502 + "OpenClaw 服务未连接"
- 功能未启用 → 502 + `{disabled: true}`
- WebSocket 断开 → 自动重连（指数退避）
- Token 认证失败 → 502 + "认证失败，请检查 Token"
- 消息超时（>120s）→ SSE 返回 `{type: 'error', message: '响应超时'}`

### 前端

- 服务未连接 → 顶部横幅提示，输入框禁用
- SSE 中断 → 消息标记失败，显示重试按钮
- 发送空消息 → 禁用发送按钮
- 管理端保存失败 → 表单内联错误提示

## 安全

- Token API 响应中始终脱敏（`sk-****abc123`）
- 用户输入限制 4000 字符
- 管理端 API 需 admin 权限
- CORS 已配置
