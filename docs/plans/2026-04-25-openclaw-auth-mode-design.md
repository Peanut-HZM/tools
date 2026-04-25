# OpenClaw 认证模式灵活切换设计

## 概述

新增 `auth_mode` 配置项，支持在后台管理面板中选择 OpenClaw 的认证方式，兼容仅 Token 鉴权和 Token + 用户名密码双重认证两种模式。

## 设计

### 新增配置项：`auth_mode`

| 值 | 说明 | 行为 |
|---|---|---|
| `token` | 仅 Token 鉴权 | 不修改 URL，仅传递 Token |
| `token_with_password` | Token + 用户名密码 | URL 嵌入 `ws://user:pass@domain`，同时传递 Token |

### 修改文件（4 个）

| 文件 | 修改内容 |
|------|------|
| `openclaw_config_service.py` | DEFAULT_CONFIGS 新增 `auth_mode: "token"` |
| `openclaw_service.py` | `_connect()` 根据 `auth_mode` 决定是否嵌入用户名密码 |
| `openclaw_admin.py` | `ConfigUpdateRequest` 新增 `auth_mode` 字段 |
| `OpenClawManagement.tsx` | 配置表单新增认证模式下拉选择框，根据选择显示/隐藏用户名密码字段 |

### 连接逻辑

```python
auth_mode = config.get("auth_mode", "token")
if auth_mode == "token_with_password" and username and password:
    url = url.replace("ws://", f"ws://{username}:{password}@", 1)
```

### 前端交互

- 默认显示：认证方式（下拉）+ Gateway URL + Token
- 选择 "Token + 用户名密码" 时：额外显示用户名和密码输入框
- 密码留空表示不修改
