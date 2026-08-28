# HTTP API 客户端 集合与请求完整增删改 设计文档

- 日期：2026-08-22
- 状态：已确认

## 背景与问题

HTTP API 客户端页面的请求集合列表与请求编辑页缺少完整的管理能力：

- 集合：新建使用浏览器 `prompt()` 简陋弹窗；无重命名、无删除、无右键菜单
- 请求编辑页：编辑只保存在标签页本地状态（`isModified`），无保存按钮，刷新即丢失；
  请求名称无法编辑；删除/复制只能通过集合树中请求的右键菜单
- 后端与前端 API 层 CRUD 已完备（`http_client.py` 端点与 `httpClientApi.ts` 函数齐全），
  本次只补 UI 层

## 目标

1. 集合列表：新建（自定义弹窗）、重命名、删除（级联警告），入口为行内悬停按钮 + 右键菜单
2. 请求编辑页：显式保存（按钮 + Ctrl+S）、删除（关闭标签页）、标签页内联改名、关闭未保存标签页提示

## 范围界定

- 仅一级集合（`parent_id` 保持 null），不支持嵌套子集合
- 请求"复制"功能保持现状（仅集合树右键菜单）
- 不引入新依赖，不重构现有弹窗体系

## 现状分析

- `frontend/src/components/Tools/HttpApiClient/components/CollectionTree.tsx`：
  集合行只有高亮 + 展开/折叠；请求行有右键菜单回调 `onRequestContextMenu`
- `frontend/src/components/Tools/HttpApiClient/HttpApiClient.tsx`：
  集合新建用 `prompt()`（第 364-370 行）；请求右键菜单状态与删除/复制处理在父组件
- `frontend/src/components/Tools/HttpApiClient/components/RequestEditor/RequestEditor.tsx`：
  无保存/删除按钮；`isModified` 已由 props 传入但未用于任何按钮
- `frontend/src/components/Tools/HttpApiClient/components/RequestTabs.tsx`：
  标签页仅显示名称，无改名入口
- `frontend/src/stores/httpClientStore.tsx`：
  `updateTabRequest` 将 `isModified` 置 true；无"标记已保存"action；
  `deleteRequest(requestId, collectionId)` 已封装 API 调用；`closeTab` 已有
- `backend/app/services/http_client_service.py:277`：删除集合 ON DELETE CASCADE 级联删除请求

## 设计

### 1. 集合列表 CRUD

**新增 `frontend/src/components/Tools/HttpApiClient/components/CollectionContextMenu.tsx`**
- 仿 `RequestContextMenu` 模式：固定定位（`left/top`）、点击外部关闭、`z-[9999]`
- Props：`collection`、`x`、`y`、`onRename(collection)`、`onDelete(collection)`、`onClose`
- 菜单项：重命名（铅笔图标）、删除（红色垃圾桶）

**修改 `CollectionTree.tsx`**
- 新增 props：`onCollectionRename(collection)`、`onCollectionDelete(collection)`、
  `onCollectionContextMenu(e, collection)`
- 集合行加 `group` 类；悬停时行尾显示重命名/删除小图标按钮
  （`opacity-0 group-hover:opacity-100`），点击时 `e.stopPropagation()`
  （不触发行点击展开/折叠，也不触发选中）
- 集合行 `onContextMenu`：`e.preventDefault()` 后回调 `onCollectionContextMenu`
- 请求行右键行为不变

**修改 `HttpApiClient.tsx`**
- 集合弹窗状态 `collectionModal: { mode: 'create' } | { mode: 'rename'; collection: Collection } | null`；
  自定义弹窗（样式仿现有"新建请求"弹窗），名称必填，空值禁用提交
- 新建入口：侧栏"+"按钮打开弹窗（替换现有 `prompt()`）
- 删除集合：`confirm('确定删除集合 "X"？其中的所有请求将一并删除。')` →
  `deleteCollection` → `loadCollections()` → 关闭该集合下所有已打开请求的标签页
  （`tab.request.collection_id === 被删集合 id`）→ 清空 `selectedCollectionId`（若指向被删集合）
- 集合右键菜单状态 `collectionContextMenu: { x; y; collection } | null`，统一由父组件管理
  （与请求右键菜单一致），渲染 `CollectionContextMenu`

### 2. 请求编辑页：保存 / 删除 / 改名 / 未保存提示

**修改 `httpClientStore.tsx`**
- 新增 action `saveRequest(requestId: string): Promise<HttpRequest>`：
  读取该 tab 当前 request → 调 `updateRequest` API → 成功后将该 tab `isModified` 置 false
  并更新 request 为后端返回 → 失败抛出异常、`isModified` 保持 true

**修改 `RequestEditor.tsx`**
- 新增 props：`onSave()`、`onDelete()`
- URL 栏发送按钮旁：
  - "保存"按钮：`isModified` 为 true 时紫色高亮可点，false 时灰色禁用
  - "删除"按钮：红色，点击触发 `onDelete()`
- 历史回放标签页（`requestId` 以 `history_` 开头）：`onSave`/`onDelete` 设计为可选 props，
  父组件对历史回放 tab 不传这两个回调，保存与删除按钮隐藏

**修改 `RequestTabs.tsx`**
- 标签页标题旁加铅笔图标 → 点击变输入框内联编辑 → 回车/失焦确认、Esc 取消 →
  新 prop `onRename(requestId, name)` 回调（由父组件 `updateTabRequest({ name })`，
  标记 `isModified`，随保存提交）

**修改 `HttpApiClient.tsx`**
- `handleSaveRequest`：调 `store.saveRequest(activeTabId)` → toast 成功 →
  `setRefreshTrigger(prev => prev + 1)` 刷新集合树；失败 toast 错误
- `handleDeleteActiveRequest`：`confirm` → `deleteRequest` → `closeTab` → 刷新树
- 关闭标签页拦截：`onTabClose` 包装——若 `tab.isModified` 弹
  `confirm('有未保存的修改，确定关闭？')`，确认后才 `closeTab`
- Ctrl+S：`useEffect` 挂 `keydown` 监听（依赖 activeTab）：`(e.ctrlKey || e.metaKey) && e.key === 's'`
  时 `e.preventDefault()`，当前 tab 存在且 `isModified` 时触发保存

### 数据流

- 编辑请求 → `updateTabRequest`（`isModified=true`）→ 保存按钮/Ctrl+S →
  `store.saveRequest` → `updateRequest` API → 成功置 `isModified=false` + 刷新树；
  失败 toast 且保持未保存
- 集合增删改 → 对应 API → `loadCollections()` 刷新；删除集合级联关闭相关 tab

### 错误处理（沿用现有模式）

- 所有 API 调用 try/catch + `toast.error`（失败消息取 `error?.response?.data?.detail || error?.message`）
- `updateRequest` 404（请求已被删除）：toast 明确提示，`isModified` 保持
- 破坏性操作（删集合/删请求/关未保存 tab）一律 `confirm` 二次确认
- 集合弹窗名称空值禁止提交

### 测试（vitest + @testing-library/react）

- `CollectionTree.test.tsx` 扩展：
  - 悬停行内重命名/删除按钮触发对应回调，且不触发行展开（不调用 `fetchRequests`）
  - 行右键触发 `onCollectionContextMenu` 并 preventDefault
- `RequestTabs.test.tsx` 新增：
  - 铅笔点击进入编辑态、回车确认回调新名称、Esc 取消不改名
- `RequestEditor.test.tsx` 新增：
  - `isModified=false` 时保存按钮禁用，true 时启用且点击回调 `onSave`
  - 删除按钮点击回调 `onDelete`
- `httpClientStore` 测试新增：
  - `saveRequest` 成功后对应 tab `isModified=false` 且 request 更新
  - `saveRequest` 失败（mock API 抛错）后 `isModified` 保持 true

验证命令（frontend 目录）：`npm test`、`npm run build`
