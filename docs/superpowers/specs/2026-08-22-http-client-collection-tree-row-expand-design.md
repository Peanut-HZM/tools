# HTTP API 客户端集合树行点击展开/折叠 设计文档

- 日期：2026-08-22
- 状态：已确认

## 背景与问题

HTTP API 客户端页面的左侧"请求集合"树中，集合行（如 Glodon-SAP）点击时只会高亮选中，
不会展开/折叠请求列表；只有点击行首的展开/折叠箭头图标才会切换展开状态。
用户期望点击整行与点击箭头图标效果一致：展开/折叠请求列表。

## 目标

- 点击集合行（含嵌套子集合行）时：高亮选中 + 切换展开/折叠
- 点击箭头图标时：同样高亮选中 + 切换展开/折叠（与行点击行为一致）
- 不改变请求列表项（请求行）的点击行为

## 现状分析

文件：`frontend/src/components/Tools/HttpApiClient/components/CollectionTree.tsx`

- 组件本地状态：
  - `expandedCollections: Set<string>` — 已展开集合 id
  - `collectionRequests: Record<string, HttpRequest[]>` — 已加载的请求列表缓存
  - `loadingRequests: Set<string>` — 加载中的集合 id
- 行点击：`handleCollectionClick` → `onCollectionSelect(collection)`，
  仅更新父组件 `selectedCollectionId`（只用于行高亮样式，不影响其他面板）
- 箭头按钮点击：`e.stopPropagation()` + `toggleExpand(collection.id)`
- `toggleExpand`：首次展开时异步 `fetchRequests` 加载请求列表（内置 try/catch/finally），
  再次点击直接折叠
- 嵌套集合通过 `renderCollection` 递归渲染，行与箭头共用同一套处理函数

## 方案选型

- 方案 A（选定）：行点击 = 选中 + 切换展开；箭头按钮复用同一处理函数，保留 `stopPropagation`
  防止冒泡导致二次 toggle
- 方案 B（弃用）：只改行点击，箭头保持"只展开不高亮"，行为不一致
- 方案 C（弃用）：移除箭头按钮，改动过大且无必要

## 设计

### 变更点（仅修改 `CollectionTree.tsx` 一个文件）

1. `handleCollectionClick(collection)` 增加一行调用 `toggleExpand(collection.id)`：

   ```tsx
   const handleCollectionClick = (collection: Collection) => {
     onCollectionSelect(collection);
     toggleExpand(collection.id);
   };
   ```

2. 箭头按钮的 `onClick` 改为调用同一处理函数，保留 `stopPropagation`
   （阻止事件冒泡到行容器，避免二次执行）：

   ```tsx
   <button
     onClick={(e) => {
       e.stopPropagation();
       handleCollectionClick(collection);
     }}
     ...
   ```

### 数据流

点击行 → `onCollectionSelect` 更新父组件高亮 + `toggleExpand` 切换本地展开状态
→ 首次展开时异步加载请求列表，已加载则直接展示/隐藏。

### 错误处理

复用 `toggleExpand` 现有 try/catch/finally：加载失败仅 `console.error`，不阻断 UI，
loading 状态正常复位。无新增异常路径。

### 测试

新增 `frontend/src/components/Tools/HttpApiClient/components/CollectionTree.test.tsx`，
使用 vitest + @testing-library/react（项目已有同类组件测试可参照），覆盖：

1. 点击集合行 → 请求列表展开，且集合高亮
2. 再次点击集合行 → 请求列表折叠
3. 点击箭头图标 → 同样展开且高亮，且 `onCollectionSelect` 仅触发一次
4. （可选）嵌套子集合行点击同样生效

验证命令：`npm run type-check`、`npm test`、`npm run build`（frontend 目录）。
