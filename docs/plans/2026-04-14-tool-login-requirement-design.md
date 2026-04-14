# 工具登录控制功能设计

**目标**: 为工具新增 `require_login` 字段，控制是否需要登录才能使用，并在管理后台、Web 前端、小程序端完整实现该逻辑

**架构**: 数据库新增字段 → 后端模型/Service/API 全链路支持 → 管理后台三处控制（弹窗+表格+筛选） → Web 前端卡片标签+点击拦截 → 小程序端卡片标签+点击拦截

**设计原则**: 与现有 `show_pc`/`show_mobile` 字段模式保持一致，全链路同步

---

## 第一部分：数据库 + 后端

### 1. 数据库迁移

**文件**: `backend/app/services/tools_service.py:45-76`

在 `_init_db()` 的 `tools` 表创建语句（第 45-62 行）中新增字段：
```sql
require_login BOOLEAN DEFAULT FALSE
```

在迁移语句区域（第 65-76 行）新增：
```sql
ALTER TABLE tools ADD COLUMN IF NOT EXISTS require_login BOOLEAN DEFAULT FALSE
```

### 2. Pydantic 模型

**文件**: `backend/app/models/tool_models.py`

`Tool` 模型（第 13-28 行）新增：
```python
require_login: bool = False
```

`ToolUpdateRequest`（第 55-65 行）新增：
```python
require_login: Optional[bool] = None
```

`ToolCreateRequest`（第 29-37 行）新增（可选）：
```python
require_login: bool = False
```

### 3. Service 层

**文件**: `backend/app/services/tools_service.py`

**`_row_to_tool()`（第 710-729 行）** 新增：
```python
require_login=row.get("require_login", False),
```

**`update_tool()`（第 302-359 行）** 的字段循环中加入：
```python
if "require_login" in data:
    updates.append("require_login = %s")
    params.append(data["require_login"])
```

**种子数据 INSERT（第 118-140 行）** 不变（使用默认值 FALSE）。

### 4. API 路由

**文件**: `backend/app/routes/admin.py:159-177`

管理端分页接口新增 `require_login` 过滤参数：
```python
require_login: Optional[bool] = Query(None),
```
传递给 `get_tools_paginated()`。

**文件**: `backend/app/routes/tools.py`

公开 `/tools` 接口不变（不过滤 `require_login`，由前端决定显示策略）。

---

## 第二部分：管理后台

### 1. 编辑弹窗新增 Toggle

**文件**: `frontend/src/components/Admin/ToolManagement.tsx`（弹窗 Toggle 区域，约第 606-645 行）

在现有三个 Toggle（PC展示、移动展示、上线状态）旁新增第四个：
- 标签："需要登录"
- 颜色：`peer-checked:bg-orange-500`（橙色，区分其他三个）
- 默认值：`toolForm.require_login ?? false`

### 2. 表格新增 Toggle 列

**文件**: `frontend/src/components/Admin/ToolManagement.tsx`

- 表头 6列 → 7列：工具名称、分类、上线状态、PC展示、移动展示、**登录要求**、操作
- 行内新增橙色 Toggle 开关，`w-9 h-5` 紧凑版
- 新增 `handleLoginToggle(toolId, currentValue)` handler，调用 `updateTool(toolId, { require_login: !currentValue })`

### 3. 筛选栏新增过滤

**文件**: `frontend/src/components/Admin/ToolManagement.tsx`（筛选工具栏，约第 297-389 行）

新增筛选控件：
- 图标：`fa-lock`（锁定=需登录）
- 选项：全部 / 需登录 / 免登录
- 对应 state：`showLoginFilter`（'all' | 'true' | 'false'）
- 传给后端 `require_login` 过滤参数

---

## 第三部分：Web 前端

### 1. TypeScript 类型

**文件**: `frontend/src/types/index.ts`（第 11-23 行）

`Tool` 接口新增：
```typescript
require_login?: boolean;
```

### 2. ToolCard 组件

**文件**: `frontend/src/components/ToolCard/ToolCard.tsx`

- 新增 `require_login?: boolean` prop
- 卡片右上角显示橙色"需登录"小徽章（`bg-orange-500/20 text-orange-400 text-xs px-1.5 py-0.5 rounded`）
- 仅当 `require_login` 为 true 时显示

### 3. 点击登录拦截

**文件**: `frontend/src/App.tsx`（`handleToolClick`，约第 163-199 行）

在 `navigate(route)` 之前加入检查：
```typescript
if (tool.require_login && !isAuthenticated) {
  // 弹窗提示并跳转登录页
  return;
}
```

需要从 `useAuth()` 获取 `isAuthenticated` 状态。

---

## 第四部分：小程序

### 1. TypeScript 类型

**文件**: `tools-mini-program/src/types/index.ts`（第 25-42 行）

`Tool` 接口新增：
```typescript
require_login?: boolean;
```

### 2. 工具列表卡片

小程序工具列表页面（需找到具体页面文件）：
- 卡片显示"需登录"标签
- 布局与 Web 端保持一致

### 3. 点击登录拦截

**文件**: `tools-mini-program/src/services/tool.ts` 或工具列表页面

在工具点击 handler 中检查：
```typescript
if (tool.require_login && !isLoggedIn) {
  // 跳转登录页，传递 redirect 参数
  Taro.redirectTo({ url: `/pages/login/index?redirect=${encodeURIComponent(currentPage)}` });
  return;
}
```

小程序已有 `Taro.getStorageSync('auth_token')` 检查登录状态的机制。

---

## 文件修改清单

| 文件 | 改动 |
|------|------|
| `backend/app/services/tools_service.py` | 数据库迁移 + `_row_to_tool` + `update_tool` |
| `backend/app/models/tool_models.py` | Tool + ToolUpdateRequest 新增字段 |
| `backend/app/routes/admin.py` | 分页接口新增 require_login 过滤 |
| `frontend/src/types/index.ts` | Tool 接口新增 require_login |
| `frontend/src/components/Admin/ToolManagement.tsx` | 弹窗 Toggle + 表格列 + 筛选栏 |
| `frontend/src/components/ToolCard/ToolCard.tsx` | 需登录徽章 + prop |
| `frontend/src/App.tsx` | handleToolClick 登录拦截 |
| `tools-mini-program/src/types/index.ts` | Tool 接口新增 require_login |
| `tools-mini-program/src/services/tool.ts` | 点击登录拦截（或具体页面文件） |
| 小程序工具列表页面 | 需登录标签显示 |

---

## 验证步骤

1. `cd backend && python -m py_compile app/models/tool_models.py app/services/tools_service.py` — Python 语法检查
2. `cd frontend && npx tsc --noEmit` — TypeScript 编译
3. 浏览器访问 http://localhost:5178/admin/tools — 管理后台三处都显示"需要登录"控制
4. 浏览器访问 http://localhost:5178 — Web 前端工具卡片显示"需登录"标签
5. 未登录用户点击需登录工具 → 弹窗提示 + 跳转登录页
6. 小程序端同样验证
7. 浏览器 Console 无错误
