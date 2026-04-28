# OpenClaw 连接测试与错误反馈 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 新增测试连接功能，增强保存后的错误反馈，聊天页面未连接时显示引导信息，解决"保存了 token 仍提示未连接"的用户困惑。

**Architecture:** 后端新增独立 `/test-connection` 端点，接收临时配置尝试 WebSocket 握手后关闭；管理面板添加测试按钮和 Token 提示，保存后显示成功/失败反馈；聊天页面未连接时显示操作引导。

**Tech Stack:** Python (FastAPI, websockets, asyncio), React (TypeScript), Tailwind CSS

---

### Task 1: 后端新增测试连接端点

**Files:**
- Modify: `backend/app/routes/openclaw_admin.py` (entire file)

**Step 1: 新增 TestConnectionRequest 模型和 test-connection 端点**

在文件末尾（第 121 行之后）添加：

```python
class TestConnectionRequest(BaseModel):
    gateway_url: str
    auth_mode: str = "token"
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None


@router.post("/test-connection")
async def test_connection(
    request: TestConnectionRequest,
    admin_user: UserResponse = Depends(get_admin_user),
):
    """测试连接（不保存配置，仅验证当前输入能否连通）"""
    import asyncio
    import json
    import uuid
    import time
    from websockets import connect as ws_connect

    url = request.gateway_url
    # 根据认证模式决定是否嵌入用户名密码
    if request.auth_mode == "token_with_password" and request.username and request.password:
        if url.startswith("ws://"):
            url = url.replace("ws://", f"ws://{request.username}:{request.password}@", 1)
        elif url.startswith("wss://"):
            url = url.replace("wss://", f"wss://{request.username}:{request.password}@", 1)

    start_time = time.monotonic()
    try:
        async with ws_connect(url, ping_interval=30, ping_timeout=10) as ws:
            # 等待 connect.challenge
            challenge_raw = await asyncio.wait_for(ws.recv(), timeout=10)
            challenge = json.loads(challenge_raw)
            if challenge.get("event") != "connect.challenge":
                return {"ok": False, "message": f"预期 connect.challenge，收到: {challenge.get('event', 'unknown')}"}
            nonce = challenge.get("payload", {}).get("nonce", "")
            if not nonce:
                return {"ok": False, "message": "connect.challenge 缺少 nonce"}

            # 发送 connect 请求
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
                    "auth": {"token": request.token} if request.token else None,
                    "role": "operator",
                    "scopes": ["operator.admin"],
                },
            }
            connect_msg["params"] = {k: v for k, v in connect_msg["params"].items() if v is not None}

            await ws.send(json.dumps(connect_msg))

            # 等待 hello_ok
            response_raw = await asyncio.wait_for(ws.recv(), timeout=10)
            response = json.loads(response_raw)

            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            if response.get("ok"):
                return {"ok": True, "message": f"连接成功（耗时 {elapsed_ms}ms）"}
            else:
                error = response.get("error", {})
                return {"ok": False, "message": f"鉴权失败: {error.get('message', 'unknown')}"}
    except asyncio.TimeoutError:
        return {"ok": False, "message": "连接超时，请检查 Gateway 地址和网络"}
    except ConnectionRefusedError:
        return {"ok": False, "message": "连接被拒绝，Gateway 可能未启动"}
    except Exception as e:
        error_msg = str(e)
        if "connect" in error_msg.lower() or "refused" in error_msg.lower():
            return {"ok": False, "message": f"连接失败: {error_msg}"}
        return {"ok": False, "message": f"连接失败: {error_msg}"}
```

**Step 2: 验证语法**

Run: `cd backend && python -m py_compile app/routes/openclaw_admin.py`
Expected: 无输出

**Step 3: 提交**

```bash
git add backend/app/routes/openclaw_admin.py
git commit -m "feat: OpenClaw 管理 API 新增测试连接端点"
```

---

### Task 2: 前端 API 新增测试连接函数

**Files:**
- Modify: `frontend/src/api/openclawApi.ts:181-192`（在 reconnectOpenClaw 之后）

**Step 1: 新增 testOpenClawConnection 函数**

在 `reconnectOpenClaw` 函数之后（第 192 行之后）添加：

```typescript
/** 测试连接 */
export async function testOpenClawConnection(data: {
  gateway_url: string;
  auth_mode: string;
  username?: string;
  password?: string;
  token?: string;
}) {
  const response = await fetch(`${ADMIN_API_BASE_URL}/openclaw/test-connection`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '测试失败' }));
    throw new Error(error.detail || '测试失败');
  }
  return response.json();
}
```

**Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -i "openclaw" | head -5`
Expected: 无与 openclaw 相关的错误

**Step 3: 提交**

```bash
git add frontend/src/api/openclawApi.ts
git commit -m "feat: OpenClaw API 新增测试连接函数"
```

---

### Task 3: 管理面板添加测试连接按钮、Token 提示和保存反馈

**Files:**
- Modify: `frontend/src/components/Admin/OpenClawManagement.tsx`（多个位置）

**Step 1: 导入测试连接函数和新增状态变量**

修改第 2-8 行的 import：

```typescript
import {
  getOpenClawConfig,
  updateOpenClawConfig,
  getOpenClawStatus,
  reconnectOpenClaw,
  disconnectOpenClaw,
  testOpenClawConnection,
  type OpenClawConfig,
} from '../../api/openclawApi';
```

在 `const [showPassword, setShowPassword] = useState(false);` 之后添加：

```typescript
const [testing, setTesting] = useState(false);
const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
```

**Step 2: 新增 handleTestConnection 函数**

在 `handleDisconnect` 函数之后（第 96 行之后）添加：

```typescript
const handleTestConnection = async () => {
  setTesting(true);
  setTestResult(null);
  setError(null);
  try {
    const result = await testOpenClawConnection({
      gateway_url: gatewayUrl || 'ws://127.0.0.1:18081',
      auth_mode: authMode,
      username: authMode === 'token_with_password' ? username : undefined,
      password: authMode === 'token_with_password' ? password : undefined,
      token: token || undefined,
    });
    setTestResult({ ok: result.ok, message: result.message });
  } catch (err: any) {
    setTestResult({ ok: false, message: err.message || '测试失败' });
  } finally {
    setTesting(false);
  }
};
```

**Step 3: 修改 handleSave 增加成功反馈**

修改第 50-70 行的 `handleSave` 函数：

```typescript
const handleSave = async () => {
  setSaving(true);
  setError(null);
  setSaveSuccess(null);
  try {
    const data: any = { enabled, auth_mode: authMode };
    if (gatewayUrl) data.gateway_url = gatewayUrl;
    if (username) data.username = username;
    if (password) data.password = password;
    if (token) data.token = token;

    const result = await updateOpenClawConfig(data);
    if (result.ok === false) {
      setError(result.message || '配置已保存，但重连失败');
    } else {
      setSaveSuccess('配置已保存，连接成功');
    }
    await loadData();
  } catch (err: any) {
    setError(err.message || '保存失败');
  } finally {
    setSaving(false);
  }
};
```

**Step 4: 添加成功提示条**

在错误提示条之后（第 117 行之后）添加成功提示：

```tsx
{saveSuccess && (
  <div className="bg-green-500/10 border border-green-500/30 text-green-400 px-4 py-3 rounded-lg">
    {saveSuccess}
  </div>
)}
```

**Step 5: Token 输入框下方添加提示文字**

修改第 241 行的提示文字，将 `text-slate-500` 改为 `text-amber-400/70` 并更新文案：

```tsx
<p className="text-amber-400/70 text-xs mt-1">💡 保存配置后将自动尝试连接，如果连接失败会在页面顶部显示错误信息。建议先点击"测试连接"验证配置</p>
```

注意：去掉原有的 `text-slate-500` class，替换为 `text-amber-400/70`。

**Step 6: 添加测试连接按钮和结果展示**

修改第 262-269 行的按钮区域，将单个按钮改为按钮组：

```tsx
        <div className="flex gap-3 items-start mt-6">
          <button
            onClick={handleSave}
            disabled={saving || testing}
            className="px-6 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-lg hover:from-cyan-600 hover:to-blue-700 transition-all disabled:opacity-50"
          >
            <i className="fas fa-save mr-1"></i>
            {saving ? '保存中...' : '保存配置'}
          </button>
          <button
            onClick={handleTestConnection}
            disabled={testing || saving}
            className="px-6 py-2.5 bg-slate-700 text-white rounded-lg hover:bg-slate-600 transition-all disabled:opacity-50"
          >
            {testing ? (
              <>
                <span className="inline-block animate-spin mr-1">⟳</span>
                测试中...
              </>
            ) : (
              <>
                <i className="fas fa-plug mr-1"></i>
                测试连接
              </>
            )}
          </button>
        </div>
        {testResult && (
          <div className={`mt-3 text-sm ${testResult.ok ? 'text-green-400' : 'text-red-400'}`}>
            <i className={`fas ${testResult.ok ? 'fa-check-circle' : 'fa-times-circle'} mr-1`}></i>
            {testResult.message}
          </div>
        )}
```

**Step 7: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -i "OpenClawManagement" | head -5`
Expected: 无错误

**Step 8: 提交**

```bash
git add frontend/src/components/Admin/OpenClawManagement.tsx
git commit -m "feat: OpenClaw 管理面板新增测试连接按钮、保存反馈和 Token 提示"
```

---

### Task 4: 聊天页面未连接时显示引导信息

**Files:**
- Modify: `frontend/src/components/Tools/OpenClawChat/OpenClawChat.tsx:212-216`（Header 中的状态显示区域）

**Step 1: 在未连接时显示引导**

修改第 212-216 行的状态显示部分，在未连接时添加引导文字。

将：

```tsx
            <div className="flex items-center gap-2 text-sm">
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
              <span className="text-slate-400">{isConnected ? '已连接' : '未连接'}</span>
            </div>
```

改为：

```tsx
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2 text-sm">
                <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
                <span className="text-slate-400">{isConnected ? '已连接' : '未连接'}</span>
              </div>
              {!isConnected && (
                <span className="text-xs text-amber-400/80">服务未连接，请前往管理面板配置 OpenClaw 连接信息</span>
              )}
            </div>
```

**Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -i "OpenClawChat" | head -5`
Expected: 无错误

**Step 3: 提交**

```bash
git add frontend/src/components/Tools/OpenClawChat/OpenClawChat.tsx
git commit -m "feat: OpenClaw 聊天页面未连接时显示配置引导"
```

---

## 总结

共 4 个 Task：

1. **Task 1**: 后端新增 `/test-connection` 端点，接收临时配置尝试 WebSocket 握手
2. **Task 2**: 前端 API 新增 `testOpenClawConnection` 函数
3. **Task 3**: 管理面板添加测试连接按钮、保存成功反馈、Token 提示文字
4. **Task 4**: 聊天页面未连接时显示引导信息

每个 Task 完成后提交一次，确保可回滚。
