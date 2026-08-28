# HTTP API 客户端 请求列表项改名与删除 设计文档

- 日期：2026-08-22
- 状态：已确认

## 背景与问题

请求集合展开后的请求列表项（方法列表）缺少树内管理入口：

- 删除仅能通过右键菜单（隐藏较深）
- 重命名只能打开请求后在标签页内联改名（多步操作）
- 从树内删除请求后，已打开的同请求标签页不会关闭，残留失效页（保存时报 404）

集合行此前已具备行内悬停按钮 + 右键菜单的完整交互（重命名/删除），请求行需要对齐。

## 目标

1. 请求列表项获得与集合行一致的树内交互：行内悬停"重命名/删除"按钮 + 右键菜单补"重命名"
2. 重命名采用行内编辑（铅笔→输入框，回车/失焦确认、Esc 取消），与标签页改名交互一致
3. 树内删除请求时同步关闭已打开的同请求标签页
4. 树内改名成功后同步更新标签页标题，且**不标记 isModified**（改名已持久化）

## 范围界定

- 仅前端 UI 层（后端与前端 API 层 CRUD 已完备）
- 不涉及新建/复制请求（已有功能）；仅一级集合
- 标签页改名流程（编辑+保存）保持不变，树内改名是独立的"直接持久化"通道

## 现状分析

- `frontend/src/components/Tools/HttpApiClient/components/CollectionTree.tsx`：
  请求行（第 194-218 行）仅有点击打开与右键回调；集合行已具备悬停按钮模式（第 154-177 行）可复用
- `frontend/src/components/Tools/HttpApiClient/components/RequestContextMenu.tsx`：
  菜单仅"复制请求/删除请求"两项，无重命名
- `frontend/src/components/Tools/HttpApiClient/HttpApiClient.tsx`：
  `handleDeleteRequest`（约第 244-252 行）删除后不关闭标签页
- `frontend/src/stores/httpClientStore.tsx`：
  `updateTabRequest` 会置 `isModified=true`，不适合"已持久化的改名"场景；需新增不标脏的 action
- API：`updateRequest(id, data: Partial<...>)`（`httpClientApi.ts:177-183`）、`deleteRequest(id)` 均已有

## 设计

### 1. CollectionTree.tsx（请求行交互）

新增 props：
- `onRequestRename?: (request: HttpRequest, name: string) => void`
- `onRequestDelete?: (request: HttpRequest) => void`

请求行改造：
- 行 div 加 `group` 类；名称 span 后追加悬停铅笔/垃圾桶按钮
  （`opacity-0 group-hover:opacity-100 focus-visible:opacity-100`，沿用集合行样式），
  点击均 `e.stopPropagation()`（不触发打开请求）
- 行内编辑：新增 `editingRequestId` / `editingRequestName` 状态
  - 点铅笔：进入编辑态（输入框 `autoFocus`，预填当前名）
  - 回车/失焦：`handleConfirmRequestRename` —— 非空才回调 `onRequestRename`，然后退出编辑态
  - Esc：退出编辑态并清空 `editingRequestName`
  - 输入框 `onClick`/`onKeyDown` 均 `stopPropagation`，防止触发"打开请求"
- 右键菜单回调 `onRequestContextMenu` 保持不变

### 2. RequestContextMenu.tsx

- 新增 prop `onRename: (request: HttpRequest) => void`
- "复制请求"菜单项上方新增"重命名"菜单项（铅笔图标），点击回调并关闭菜单

### 3. httpClientStore.tsx

新增 action `renameRequest(requestId: string, name: string): Promise<HttpRequest>`：
- 调 `updateRequest(requestId, { name })`
- 成功后更新对应 tab 的 `request.name`，**不改变 isModified**
- 失败抛错；采用 `saveRequest` 同款模式：await 后重读 `get().openTabs` 再合并，避免快照竞态
- tab 不存在时静默跳过同步（请求未打开无需更新）

### 4. HttpApiClient.tsx

- `handleRequestRename(request, name)`：调 `store.renameRequest` → toast 成功 →
  `setRefreshTrigger(prev => prev + 1)` 刷新树；失败 toast 错误
- `handleDeleteRequest` 改造：删除 API 成功后追加 `closeTab(requestId)`（若该请求已打开）；
  confirm 文案保持"确定删除请求 X 吗？"
- 接线：`CollectionTree` 传 `onRequestRename`/`onRequestDelete`；
  `RequestContextMenu` 传 `onRename`

### 数据流

- 树内改名：行内编辑确认 → `onRequestRename(request, name)` → `store.renameRequest`
  （API 持久化 + tab 标题同步，不标脏）→ refreshTrigger 刷新树
- 树内删除：悬停按钮或右键菜单 → confirm → `deleteRequest` API → `closeTab`（若打开）→ refreshTrigger
- 与标签页改名关系：树内改名走"直接持久化"通道（不标 isModified）；
  标签页改名走"编辑+保存"通道（标 isModified）；两者最终都通过 `updateRequest` 落库

### 错误处理（沿用现有模式）

- 所有 API 调用 try/catch + `toast.error`（`error?.response?.data?.detail || error?.message`）
- `updateRequest` 404（请求已被删）：toast 明确提示
- 空名称忽略不回调（trim 后为空直接退出编辑态）
- 删除 confirm 二次确认；行内按钮 `stopPropagation` 不触发行点击

### 测试（vitest + @testing-library/react）

- `CollectionTree.test.tsx` 扩展：
  - 点击铅笔进入编辑态并显示当前名
  - 修改后回车回调 `onRequestRename(request, 新名)` 并退出编辑态
  - Esc 取消不回调
  - 铅笔/垃圾桶按钮点击不触发 `onRequestOpen`（stopPropagation）
  - 删除按钮回调 `onRequestDelete(request)`
- `RequestContextMenu.test.tsx`（新建）：重命名菜单项渲染；点击回调 `onRename(request)` 并关闭
- `httpClientStore.test.ts` 扩展：
  - `renameRequest` 成功后对应 tab `request.name` 更新且 `isModified` 保持 false
  - `renameRequest` 失败抛错且 tab 状态不变
- 验证命令（frontend 目录）：`npm test`（基线 6 个既有失败不变，无新增失败）、`npm run build`
