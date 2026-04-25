# OpenClaw 认证模式切换实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 新增 `auth_mode` 配置项，支持在后台管理面板中选择 OpenClaw 的认证方式，兼容仅 Token 鉴权和 Token + 用户名密码双重认证两种模式。

**Architecture:** 通过数据库配置项 `auth_mode` 控制后端连接行为，前端表单根据选择动态显示/隐藏用户名密码字段。后端 `_connect()` 方法读取 `auth_mode` 决定是否将用户名密码嵌入 WebSocket URL。

**Tech Stack:** Python (FastAPI, psycopg2), React (TypeScript), Fernet 加密

---

### Task 1: 后端配置服务新增 auth_mode

**Files:**
- Modify: `backend/app/services/openclaw_config_service.py:55-61`

**Step 1: 在 DEFAULT_CONFIGS 中新增 auth_mode**

找到第 55-61 行的 `DEFAULT_CONFIGS`：

```python
DEFAULT_CONFIGS = {
    "gateway_url": "ws://127.0.0.1:18081",
    "username": "",
    "password": "",
    "token": "",
    "enabled": "true",
}
```

改为：

```python
DEFAULT_CONFIGS = {
    "gateway_url": "ws://127.0.0.1:18081",
    "auth_mode": "token",
    "username": "",
    "password": "",
    "token": "",
    "enabled": "true",
}
```

**Step 2: 验证语法**

```bash
cd backend && python -m py_compile app/services/openclaw_config_service.py
```
Expected: 无输出

**Step 3: 提交**

```bash
git add backend/app/services/openclaw_config_service.py
git commit -m "feat: OpenClaw 配置新增 auth_mode 认证模式选项"
```

---

### Task 2: 后端连接服务根据 auth_mode 控制认证行为

**Files:**
- Modify: `backend/app/services/openclaw_service.py:93-106`

**Step 1: 修改 _connect() 方法**

找到第 93-106 行的 `_connect()` 方法中的配置读取和 URL 嵌入逻辑：

```python
    async def _connect(self):
        """建立 WebSocket 连接并完成握手"""
        config = openclaw_config_service.get_config()
        url = config.get("gateway_url", settings.OPENCLAW_GATEWAY_URL)
        username = config.get("username", "")
        password = config.get("password", "")
        token = config.get("token", settings.OPENCLAW_TOKEN)

        # 如果有用户名密码，嵌入到 URL 中 (ws://user:pass@domain.com)
        if username and password:
            if url.startswith("ws://"):
                url = url.replace("ws://", f"ws://{username}:{password}@", 1)
            elif url.startswith("wss://"):
                url = url.replace("wss://", f"wss://{username}:{password}@", 1)
```

改为：

```python
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
```

注意：删除原来的 `logger.info(f"正在连接 OpenClaw Gateway: {url}")` 和 `self.ws = await ...` 两行，替换为上面带条件日志的版本。

**Step 2: 验证语法**

```bash
cd backend && python -m py_compile app/services/openclaw_service.py
```
Expected: 无输出

**Step 3: 提交**

```bash
git add backend/app/services/openclaw_service.py
git commit -m "feat: OpenClaw 连接根据 auth_mode 动态切换认证方式"
```

---

### Task 3: 后端管理 API 支持 auth_mode

**Files:**
- Modify: `backend/app/routes/openclaw_admin.py:29-34`
- Modify: `backend/app/routes/openclaw_admin.py:48-77`

**Step 1: 扩展 ConfigUpdateRequest**

找到第 29-34 行：

```python
class ConfigUpdateRequest(BaseModel):
    gateway_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    enabled: Optional[str] = None
```

改为：

```python
class ConfigUpdateRequest(BaseModel):
    gateway_url: Optional[str] = None
    auth_mode: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    enabled: Optional[str] = None
```

**Step 2: 在 update_config 端点中新增 auth_mode 验证**

在 `update_config` 函数中，`enabled` 验证之后（第 65 行之后），添加 auth_mode 验证：

```python
    # 验证 auth_mode 值
    if "auth_mode" in data:
        if data["auth_mode"] not in ("token", "token_with_password"):
            raise HTTPException(status_code=400, detail="auth_mode 必须为 token 或 token_with_password")
```

**Step 3: 验证语法**

```bash
cd backend && python -m py_compile app/routes/openclaw_admin.py
```
Expected: 无输出

**Step 4: 提交**

```bash
git add backend/app/routes/openclaw_admin.py
git commit -m "feat: OpenClaw 管理 API 支持 auth_mode 配置"
```

---

### Task 4: 前端 API 接口和配置表单

**Files:**
- Modify: `frontend/src/api/openclawApi.ts:136-142`
- Modify: `frontend/src/components/Admin/OpenClawManagement.tsx` (multiple sections)

**Step 1: 更新 OpenClawConfig 接口**

找到第 136-142 行：

```typescript
export interface OpenClawConfig {
  gateway_url: string;
  username: string;
  password: string;
  token: string;
  enabled: string;
  connected: boolean;
}
```

改为：

```typescript
export interface OpenClawConfig {
  gateway_url: string;
  auth_mode: string;
  username: string;
  password: string;
  token: string;
  enabled: string;
  connected: boolean;
}
```

**Step 2: 更新 OpenClawManagement 组件**

在 `frontend/src/components/Admin/OpenClawManagement.tsx` 中进行以下修改：

**2A. 新增 authMode 状态变量**

在 `const [enabled, setEnabled] = useState('true');` 之后添加：

```typescript
const [authMode, setAuthMode] = useState('token');
```

**2B. 更新 loadData 函数**

在 `setUsername(data.username || '');` 之后添加：

```typescript
setAuthMode(data.auth_mode || 'token');
```

**2C. 更新 handleSave 函数**

在 `const data: any = { enabled };` 之后添加：

```typescript
data.auth_mode = authMode;
// 如果认证模式为 token，清空用户名密码
if (authMode === 'token') {
  delete data.username;
  delete data.password;
}
```

**2D. 在配置表单中添加认证模式下拉框**

在配置表单的 `space-y-4` div 中，在 Gateway URL 输入框 div **之后**、用户名输入框 div **之前**，添加认证模式下拉框：

```tsx
          <div>
            <label className="block text-slate-300 text-sm mb-1">认证方式</label>
            <select
              value={authMode}
              onChange={(e) => setAuthMode(e.target.value)}
              className="w-full bg-slate-900 text-white border border-slate-600 rounded-lg px-4 py-2.5 focus:outline-none focus:border-cyan-500"
            >
              <option value="token">仅 Token 鉴权</option>
              <option value="token_with_password">Token + 用户名密码双重认证</option>
            </select>
          </div>
```

**2E. 将用户名和密码输入框包装为条件渲染**

将用户名和密码两个 `<div>` 包裹在条件渲染中。找到用户名输入框的 `<div>`（从 `<label>用户名</label>` 开始）到密码输入框的 `</div>` 结束，在这两个 div 外面包裹：

```tsx
          {authMode === 'token_with_password' && (
            <>
              {/* 用户名输入框 */}
              <div>
                ...
              </div>
              {/* 密码输入框 */}
              <div>
                ...
              </div>
            </>
          )}
```

**2F. 更新状态卡片**

在状态卡片中，在"启用状态"之后添加"认证方式"显示：

找到：
```tsx
          <div>
            <p className="text-slate-400 text-sm">启用状态</p>
            <p className="text-white font-medium mt-1">{enabled === 'true' ? '已启用' : '已禁用'}</p>
          </div>
```

在其后添加：
```tsx
          <div>
            <p className="text-slate-400 text-sm">认证方式</p>
            <p className="text-white font-medium mt-1">{config?.auth_mode === 'token_with_password' ? '双重认证' : 'Token 认证'}</p>
          </div>
```

**Step 3: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -i "openclaw" | head -10
```
Expected: 无与 openclaw 相关的错误

**Step 4: 提交**

```bash
git add frontend/src/api/openclawApi.ts frontend/src/components/Admin/OpenClawManagement.tsx
git commit -m "feat: OpenClaw 管理面板支持认证模式切换和条件表单"
```

---

## 总结

本计划共 4 个 Task：

1. **Task 1**: 配置服务新增 `auth_mode` 默认值（数据库自动初始化）
2. **Task 2**: 连接服务根据 `auth_mode` 决定是否嵌入用户名密码
3. **Task 3**: 管理 API 新增 `auth_mode` 字段和验证
4. **Task 4**: 前端下拉选择认证模式，条件显示用户名密码表单

每个 Task 提交一次，确保可回滚。
