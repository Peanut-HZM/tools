# OpenClaw 连接测试与错误反馈设计

## 概述

增强 OpenClaw 配置管理的错误反馈机制，新增测试连接功能，改善用户体验。解决"保存了 token 仍提示未连接"的问题。

## 修改文件

| 文件 | 修改内容 |
|------|------|
| `openclaw_admin.py` | 新增 `/test-connection` 端点 |
| `openclawApi.ts` | 新增 `testOpenClawConnection` API 函数 |
| `OpenClawManagement.tsx` | 添加测试连接按钮、Token 提示、保存结果反馈 |
| `OpenClawChat.tsx` | 未连接时显示引导信息 |

## 设计方案

### 1. 后端：测试连接端点

**路径**: `POST /api/admin/openclaw/test-connection`

接收临时配置参数，尝试建立 WebSocket 连接并完成握手，不写入数据库。

```python
class TestConnectionRequest(BaseModel):
    gateway_url: str
    auth_mode: str = "token"
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
```

响应：
- 成功：`{"ok": true, "message": "连接成功", "latency_ms": 123}`
- 失败：`{"ok": false, "message": "具体错误原因"}`

### 2. 后端：增强保存端点返回

`update_config` 已经返回 `ok` 和 `message`，无需改动。前端只需更好地利用返回信息。

### 3. 前端：管理面板

- Token 输入框下方添加提示文字
- "保存配置"按钮旁添加"测试连接"按钮
- 测试时显示 loading，结果用颜色区分（绿/红）
- 保存后根据返回结果显示成功/错误提示

### 4. 前端：聊天页面

未连接时显示引导文字："服务未连接，请前往管理面板配置 OpenClaw 连接信息"
