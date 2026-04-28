# OpenClaw Token 回显与可见切换 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 管理面板中 Token 输入框支持回显已保存的完整 token，并提供小眼睛按钮切换明文/密文显示。

**Architecture:** 修改前端 `loadData` 将 `setToken('')` 改为 `setToken(data.token || '')`，新增 `showToken` 状态，Token 输入框结构改为相对定位 + 小眼睛切换按钮。后端无需修改（`get_config()` 已返回完整 token）。

**Tech Stack:** React (TypeScript), Tailwind CSS

---

### Task 1: 前端 Token 回显与小眼睛切换

**Files:**
- Modify: `frontend/src/components/Admin/OpenClawManagement.tsx`

**Step 1: 新增 showToken 状态变量**

在第 27-29 行现有状态变量（`testing`, `testResult`, `saveSuccess`）之后添加：

```typescript
const [showToken, setShowToken] = useState(false);
```

**Step 2: loadData 中回显 token**

将第 34 行：

```typescript
setToken(''); // Token 不回显
```

改为：

```typescript
setToken(data.token || '');
```

**Step 3: Token 输入框添加小眼睛按钮**

将第 232-242 行左右的 Token 输入框 `<div>`（从 `<label>...Token</label>` 到 `</p>`）：

```tsx
          <div>
            <label className="block text-slate-300 text-sm mb-1">Token</label>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="留空表示不修改"
              className="w-full bg-slate-900 text-white border border-slate-600 rounded-lg px-4 py-2.5 focus:outline-none focus:border-cyan-500 font-mono"
            />
            <p className="text-amber-400/70 text-xs mt-1">...</p>
          </div>
```

改为：

```tsx
          <div>
            <label className="block text-slate-300 text-sm mb-1">Token</label>
            <div className="relative">
              <input
                type={showToken ? 'text' : 'password'}
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="留空表示不修改"
                className="w-full bg-slate-900 text-white border border-slate-600 rounded-lg px-4 py-2.5 pr-12 focus:outline-none focus:border-cyan-500 font-mono"
              />
              <button
                type="button"
                onClick={() => setShowToken(!showToken)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
              >
                <i className={`fas ${showToken ? 'fa-eye-slash' : 'fa-eye'}`}></i>
              </button>
            </div>
            <p className="text-amber-400/70 text-xs mt-1">💡 保存配置后将自动尝试连接，如果连接失败会在页面顶部显示错误信息。建议先点击"测试连接"验证配置</p>
          </div>
```

**Step 4: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -i "OpenClawManagement" | head -5`
Expected: 无错误

**Step 5: 提交**

```bash
git add frontend/src/components/Admin/OpenClawManagement.tsx
git commit -m "feat: OpenClaw 管理面板 Token 支持回显和小眼睛切换"
```
