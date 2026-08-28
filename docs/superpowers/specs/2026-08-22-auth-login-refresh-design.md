# 登录弹框 + 登录后自动刷新页面数据 — 设计文档

日期：2026-08-22
状态：已确认（用户逐节批准）

## 1. 背景与问题

工具箱前端存在以下问题：

1. **登录后无自动刷新机制**：登录成功后没有任何机制通知各页面重新加载数据。
   多数受保护页面的数据加载 `useEffect` 依赖数组为 `[]`（仅挂载时执行），
   登录后需要用户手动刷新页面才能看到数据。
2. **未登录拦截体验差**：访问需要登录的工具时使用 `window.confirm` 弹原生确认框，
   再跳转 `/login` 独立页面，登录后需手动返回。
3. **401 处理缺陷**：全局 401 回调只删除 localStorage 中的 token 并打开弹框，
   不更新 `authStore` 的 `isAuthenticated`，导致状态与实际不符；且轮询页面
   （如 TokenUsage 每 30 秒轮询）token 失效时会反复触发 401。
4. **未登录时产生无意义请求**：受保护页面在未登录时仍发起请求，
   产生 401 错误条和无意义日志。

## 2. 需求

- 未登录访问需要登录的页面时，弹出登录弹框（替换 `window.confirm` + 跳转 `/login`）；
  `/login` 独立页面保留（兼容直接访问链接）。
- API 返回 401（token 过期）时弹出登录弹框。
- 登录成功后自动刷新页面数据，无需用户手动刷新，覆盖**全部受保护页面**。
- 弹框被用户关闭（不登录）时：停留当前页，页面显示"未登录"提示状态，
  用户可再次触发登录。
- 401 弹框去重：弹框已打开时，后续 401 不重复触发。
- 未登录状态下，受保护页面不发数据请求。

## 3. 方案选择

选择**方案 A：authStore 增加 authVersion 计数 + 通用加载 Hook**。

备选方案对比：

| 方案 | 描述 | 结论 |
|---|---|---|
| A（选定） | authStore 增加 `authVersion`，登录/登出/401 时递增；新建 `useAuthPageData` Hook 统一数据加载生命周期 | 纯 React 状态流、类型安全，是 `DatabaseToolContext` 现有成功模式的提炼推广，无新依赖 |
| B | 全局 `CustomEvent('auth-changed')` 广播，各页面监听后自行重载 | DOM 事件无类型安全、事件名散落、耦合隐晦；改动量与 A 相同，无优势 |
| C | 登录成功后 `location.reload()` 整页刷新 | 整页闪烁、丢失 SPA 状态，违背平滑刷新预期 |

## 4. 设计

### 4.1 核心机制（认证状态 + 弹框）

#### 4.1.1 authStore 改造（`src/stores/authStore.tsx`，React Context）

- 新增状态 `authVersion: number`，语义为"认证状态代际"，以下时机递增：
  - 登录成功
  - 登出
  - 401 失效
- 新增 action `markUnauthorized()`：
  - 清除 token（复用现有 `removeAuthToken()`）
  - `user=null`、`isAuthenticated=false`
  - **仅当此前是已登录状态时**才 `authVersion+1`（防轮询页面反复 401 导致无效递增）
- 修复现有缺陷：401 后 `authStore` 状态与实际保持一致。

#### 4.1.2 全局 401 处理（`src/App.tsx` GlobalAuthHandler）

- 401 回调改为：`markUnauthorized()` → 打开登录弹框。
- 弹框打开动作幂等：已打开时后续 401 不再重复触发（天然去重）。

#### 4.1.3 弹框状态独立管理（新建 `src/stores/loginModalStore.ts`，Zustand）

- 提供 `isOpen` 状态与 `openLoginModal() / closeLoginModal()`，任何组件可调用。
- `LoginModal`（`src/components/Common/LoginModal.tsx`）改为订阅该 store，
  去掉 `isOpen/onClose` props 传参。
- Header 的登录按钮（`src/components/Header/LoginButton.tsx`）复用该 store。
- `GlobalAuthHandler` 职责收敛为：注册 401 回调 → `markUnauthorized()` + `openLoginModal()`。

#### 4.1.4 未登录拦截改为弹框（`src/App.tsx`）

- 删除 `window.confirm('该工具需要登录后才能使用，是否前往登录？')` +
  `navigate('/login')`，改为直接 `openLoginModal()`。
- `/login` 独立页面（LoginPage）保留，登录成功后 `navigate('/')` 行为不变。

### 4.2 通用 Hook 与页面接入

#### 4.2.1 新增 `useAuthPageData` Hook（`src/hooks/useAuthPageData.ts`）

```ts
useAuthPageData<T>(loader: () => Promise<T>): {
  data: T | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;   // 页面据此渲染"未登录提示"
}
```

行为规则：

- `isAuthenticated === false` → 不发请求，`data=null`，由页面渲染未登录提示。
- `isAuthenticated === true` → 首次自动加载；`authVersion` 变化
  （登录成功/401 失效恢复）→ 自动重新加载。
- 竞态保护：请求带序号，旧响应丢弃（认证状态快速切换时避免旧数据覆盖新数据）。
- loader 用 ref 保存最新引用，避免陈旧闭包。

#### 4.2.2 未登录提示组件 `RequireAuthNotice`

- 轻量组件：文案"该功能需要登录后使用" + "登录"按钮（点击 `openLoginModal()`）。
- 各页面在 `isAuthenticated === false` 分支渲染它（停留当前页，不清场）。

#### 4.2.3 各受保护页面接入清单

| 页面 | 现状 | 接入方式 |
|---|---|---|
| TokenUsage（`src/components/Tools/TokenUsage.tsx`） | 自研 hooks + 30s 轮询 | 未登录跳过加载并暂停轮询；登录/authVersion 变化时重载；未登录渲染提示 |
| HttpApiClient | `useEffect([])` 一次性加载 | 改用 `useAuthPageData` / 受 authVersion 驱动 |
| K8sTool（react-query） | `refetchInterval: 30_000` | `enabled: isAuthenticated`；登录成功后 `refetch` |
| DatabaseTool（`src/contexts/DatabaseToolContext.tsx`） | 已有 `useEffect([isAuthenticated])` 范例 | 微调接入 `authVersion`（401 后也能重载） |
| OpenClawChat | "前往登录"按钮跳 /login | 按钮改为打开弹框；登录后自动重载 |
| Admin | isAuthenticated 变化时重定向 | 保持；401 后弹框联动即可 |
| MarkdownEditorTool | AuthGuard 内嵌 LoginForm | 保持现状（已是正确模式） |

### 4.3 错误处理与边界情况

状态流转矩阵：

| 场景 | authStore 变化 | 弹框 | 页面数据 |
|---|---|---|---|
| 未登录访问受保护工具 | 不变 | 弹出 | 未登录提示，不发请求 |
| 弹框关闭（不登录） | 不变 | 关闭 | 停留 + 未登录提示 |
| 登录成功 | `isAuthenticated=true`，`authVersion+1` | 自动关闭 | 全部受保护页面自动重载 |
| 已登录但 token 过期（401） | `markUnauthorized()`，`authVersion+1` | 弹出（幂等去重） | 数据清空 → 未登录提示，轮询暂停 |
| 401 后重新登录成功 | `authVersion+1` | 自动关闭 | 自动重载 |
| 登出 | `isAuthenticated=false`，`authVersion+1` | 不弹 | 数据清空 |

并发与竞态：

- Hook 请求序号机制：认证状态快速切换（如 401 → 登录）时，旧请求的迟到响应被丢弃。
- 401 去重：`markUnauthorized` 仅在"已登录 → 未登录"转变时递增 `authVersion`，
  轮询页面的连续 401 不会引发重复重载风暴。

降级与兼容：

- `/login` 独立页面保留，登录成功后 `navigate('/')` 行为不变。
- 未接入 Hook 的页面不受影响（仍按现状工作）。
- 不做：登录后自动重试失败请求（超出范围，重载页面数据已覆盖需求）。

数据安全：

- 401 或登出时立即清空页面数据（避免旧 token 残留期显示上一个用户的数据）。
- `RequireAuthNotice` 不显示任何用户数据。

## 5. 测试

### 5.1 前端单元测试（Vitest，项目已有 `*.test.ts(x)` 先例）

- `useAuthPageData.test.ts`：
  - 未登录时不调用 loader
  - 登录后自动加载
  - `authVersion` 变化触发重载
  - 竞态：旧请求迟到响应被丢弃
- authStore 相关测试：`markUnauthorized` 仅在"已登录 → 未登录"时递增 `authVersion`
- `loginModalStore` 测试：open/close 幂等

### 5.2 手动验证清单

- 未登录打开 TokenUsage → 弹框 → 关闭 → 未登录提示，无网络请求（DevTools 验证）
- 弹框内登录 → 数据自动加载，无需刷新
- 手动篡改 token → 30 秒轮询内弹框只出现一次 → 重新登录 → 数据恢复
- 登出 → 页面数据清空

### 5.3 验证命令

- `cd frontend && npm run type-check && npm run lint && npm run build`（若脚本存在则执行）

## 6. 不做的事（范围外）

- 登录后自动重试具体失败请求
- 登录后跳转回来源页面（/login 页登录后仍 navigate('/')）
- 改造 MarkdownEditorTool 的 AuthGuard 交互
- 服务端改动
