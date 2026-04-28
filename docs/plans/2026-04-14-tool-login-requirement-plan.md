# 工具登录控制功能 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为工具新增 `require_login` 字段，管理后台可控制是否需要登录才能使用，Web 前端和小程序端根据该字段展示标签并拦截未登录访问

**Architecture:** 后端新增数据库字段 + Pydantic 模型 + Service 层 + API → 管理后台三处控制（弹窗 Toggle + 表格行内开关 + 筛选栏） → Web 前端 ToolCard 标签 + App.tsx 点击拦截 → 小程序 ToolCard 标签 + 首页点击拦截

**Tech Stack:** Python 3.10, FastAPI, PostgreSQL, psycopg2, React 18, TypeScript, Tailwind CSS, Taro (小程序)

**设计文档:** `docs/plans/2026-04-14-tool-login-requirement-design.md`

---

### Task 1: 后端数据库迁移 + Pydantic 模型

**Files:**
- Modify: `backend/app/services/tools_service.py:45-76`
- Modify: `backend/app/models/tool_models.py`

**Step 1: 数据库迁移**

在 `ToolsService._init_db()` 中，找到 `tools` 表创建语句（约第 45-62 行），在 `show_mobile BOOLEAN DEFAULT TRUE` 后面新增：

```sql
                        require_login BOOLEAN DEFAULT FALSE,
```

在迁移区域（约第 65-76 行，`ALTER TABLE tools ADD COLUMN IF NOT EXISTS show_mobile ...` 之后）新增：

```python
                cur.execute("""
                    ALTER TABLE tools
                    ADD COLUMN IF NOT EXISTS require_login BOOLEAN DEFAULT FALSE
                """)
```

**Step 2: Pydantic 模型**

`backend/app/models/tool_models.py`，在 `Tool` 模型（约第 13-28 行）的 `created_at` 之前新增：

```python
    require_login: bool = False
```

在 `ToolUpdateRequest`（约第 55-65 行）的 `show_mobile` 之后新增：

```python
    require_login: Optional[bool] = None
```

**Step 3: 验证 Python 语法**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend && python -m py_compile app/models/tool_models.py app/services/tools_service.py
```
Expected: no output

**Step 4: Commit**

```bash
git add backend/app/models/tool_models.py backend/app/services/tools_service.py
git commit -m "feat(tool-login): 数据库新增 require_login 字段 + Pydantic 模型"
```

---

### Task 2: 后端 Service 层 + API 过滤

**Files:**
- Modify: `backend/app/services/tools_service.py`
- Modify: `backend/app/routes/admin.py`

**Step 1: `_row_to_tool()` 新增字段**

在 `ToolsService._row_to_tool()` 方法（约第 710-729 行），`show_mobile=row.get("show_mobile", True),` 之后新增：

```python
            require_login=row.get("require_login", False),
```

**Step 2: `update_tool()` 新增字段处理**

在 `update_tool()` 方法（约第 302-359 行），找到 `if "custom_icon_url" in data:` 块（约第 332-334 行）之后新增：

```python
            if "require_login" in data:
                updates.append("require_login = %s")
                params.append(data["require_login"])
```

**Step 3: `get_tools_paginated()` 新增过滤参数**

在 `get_tools_paginated()` 方法签名（约第 361-372 行）的 `show_mobile: Optional[bool] = None,` 之后新增：

```python
        require_login: Optional[bool] = None,
```

在过滤条件区域（约第 398-400 行，`show_mobile` 过滤之后）新增：

```python
                if require_login is not None:
                    conditions.append("require_login = %s")
                    params.append(require_login)
```

**Step 4: 管理 API 路由新增参数**

`backend/app/routes/admin.py`，在 `list_tools_paginated` 函数签名（约第 159-177 行）的 `show_mobile: Optional[bool] = Query(None),` 之后新增：

```python
    require_login: Optional[bool] = Query(None),
```

在调用 `tools_service.get_tools_paginated()` 的参数中（约第 173-177 行）新增：

```python
        show_pc=show_pc, show_mobile=show_mobile, require_login=require_login,
```

**Step 5: 验证 Python 语法**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend && python -m py_compile app/services/tools_service.py app/routes/admin.py
```
Expected: no output

**Step 6: Commit**

```bash
git add backend/app/services/tools_service.py backend/app/routes/admin.py
git commit -m "feat(tool-login): Service 层和 API 新增 require_login 支持"
```

---

### Task 3: Web 前端类型定义 + ToolCard 组件

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/components/ToolCard/ToolCard.tsx`

**Step 1: TypeScript 类型**

`frontend/src/types/index.ts`，在 `Tool` 接口（约第 11-23 行）的 `show_mobile?: boolean` 之后新增：

```typescript
  require_login?: boolean;
```

**Step 2: ToolCardProps 接口**

`frontend/src/types/index.ts`，在 `ToolCardProps` 接口（约第 25-35 行）的 `onClick: () => void;` 之前新增：

```typescript
  require_login?: boolean;
```

**Step 3: ToolCard 组件显示标签**

`frontend/src/components/ToolCard/ToolCard.tsx`，完整替换组件代码：

```tsx
import { ToolCardProps } from '../../types';

export default function ToolCard({
  icon,
  iconColor,
  title,
  description,
  rating,
  usageCount,
  custom_icon_url,
  require_login,
  onClick
}: ToolCardProps) {
  return (
    <div
      onClick={onClick}
      className="tool-card bg-slate-800 rounded-xl p-6 border border-slate-700 hover:border-primary transition-all cursor-pointer relative"
    >
      {/* 需登录标签 */}
      {require_login && (
        <span className="absolute top-3 right-3 bg-orange-500/20 text-orange-400 text-[10px] px-1.5 py-0.5 rounded border border-orange-500/30">
          需登录
        </span>
      )}
      <div className={`w-12 h-12 ${iconColor} rounded-lg flex items-center justify-center mb-4`}>
        {custom_icon_url ? (
          <img src={custom_icon_url} alt={title} className="w-6 h-6 object-contain" />
        ) : (
          <i className={`fas ${icon} text-white text-xl`}></i>
        )}
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-slate-400 text-sm mb-4">{description}</p>
      <div className="flex items-center text-xs text-slate-500">
        <i className="fas fa-star mr-1"></i>
        <span>{rating}</span>
        <span className="mx-2">•</span>
        <span>{usageCount} 使用</span>
      </div>
    </div>
  );
}
```

**Step 4: ToolGrid 传递 require_login**

`frontend/src/components/Hero/ToolGrid.tsx`，在 `ToolCard` 调用处（约第 34-45 行）新增 prop：

```tsx
            require_login={tool.require_login}
```

**Step 5: 验证编译**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend && npx tsc --noEmit 2>&1 | grep -E "ToolCard|ToolGrid|types/index"
```
Expected: no output

**Step 6: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/components/ToolCard/ToolCard.tsx frontend/src/components/Hero/ToolGrid.tsx
git commit -m "feat(tool-login): Web 前端 ToolCard 新增需登录标签"
```

---

### Task 4: Web 前端点击登录拦截

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: 在 HomePage 中获取认证状态**

`frontend/src/App.tsx`，在 `HomePage` 函数内（约第 61 行后）找到 `const { t } = useI18n();` 之后，新增：

```tsx
  const { isAuthenticated } = useContext(AuthContext);
```

需要导入 `AuthContext`（文件顶部已有 `AuthProvider` 和 `useAuth` 的 import，在 `AuthContext` 的导出语句中已有）。确认 import：

```tsx
import { AuthProvider, AuthContext, useAuth } from './stores/authStore';
```

**Step 2: 修改 handleToolClick 加入拦截**

在 `handleToolClick` 函数（约第 163-199 行），在 `const route = toolRoutes[toolId];` 之后、`if (route)` 之前，加入：

```tsx
    // 登录拦截
    const tool = filteredTools.find(t => t.id === toolId);
    if (tool?.require_login && !isAuthenticated) {
      if (window.confirm('该工具需要登录后才能使用，是否前往登录？')) {
        navigate('/login');
      }
      return;
    }
```

注意：原代码第 166-172 行已经有一个 `const tool = filteredTools.find(...)` 用于记录访问，可以复用。将拦截逻辑放在 `recordToolVisit` 之后、路由查找之前。

**Step 3: 验证编译**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend && npx tsc --noEmit 2>&1 | grep "App.tsx"
```
Expected: no output

**Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(tool-login): Web 前端工具点击登录拦截"
```

---

### Task 5: 小程序类型定义 + ToolCard + 点击拦截

**Files:**
- Modify: `tools-mini-program/src/types/index.ts`
- Modify: `tools-mini-program/src/components/ToolCard/index.tsx`
- Modify: `tools-mini-program/src/pages/index/index.tsx`

**Step 1: TypeScript 类型**

`tools-mini-program/src/types/index.ts`，在 `Tool` 接口（约第 25-42 行）的 `show_mobile?: boolean` 之后新增：

```typescript
  require_login?: boolean;
```

**Step 2: ToolCard 组件显示标签**

`tools-mini-program/src/components/ToolCard/index.tsx`，在 `<View className='tool-card' onClick={onClick}>` 内部，`tool-card-icon` 之前新增：

```tsx
      {tool.require_login && (
        <View className='tool-card-login-badge'>
          <Text className='tool-card-login-badge-text'>需登录</Text>
        </View>
      )}
```

**Step 3: 小程序 ToolCard 样式**

`tools-mini-program/src/components/ToolCard/ToolCard.scss`，在文件末尾新增：

```scss
.tool-card-login-badge {
  position: absolute;
  top: 8rpx;
  right: 8rpx;
  background: rgba(249, 115, 22, 0.2);
  border: 1rpx solid rgba(249, 115, 22, 0.3);
  border-radius: 4rpx;
  padding: 2rpx 8rpx;
  
  .tool-card-login-badge-text {
    font-size: 18rpx;
    color: #f97316;
  }
}
```

同时确保 `.tool-card` 有 `position: relative`（通常已有，检查确认）。

**Step 4: 首页点击拦截**

`tools-mini-program/src/pages/index/index.tsx`，在 `handleToolClick` 函数（约第 55-65 行），在 `toolApi.trackVisit(tool.id).catch(() => {})` 之后、`if (tool.path)` 之前加入：

```typescript
    // 登录拦截
    const token = Taro.getStorageSync('auth_token')
    if (tool.require_login && !token) {
      Taro.showToast({ title: '请先登录', icon: 'none' })
      setTimeout(() => {
        Taro.redirectTo({ url: '/pages/login/index?redirect=/pages/index/index' })
      }, 1500)
      return
    }
```

**Step 5: 验证 TypeScript**

检查小程序的 TypeScript 编译（如果有 tsconfig）：

```bash
cd /Users/huazhongmin/IdeaProjects/tools/tools-mini-program && npx tsc --noEmit 2>&1 | head -10
```
如果没有 tsconfig，跳过此步。

**Step 6: Commit**

```bash
git add tools-mini-program/src/types/index.ts tools-mini-program/src/components/ToolCard/index.tsx tools-mini-program/src/components/ToolCard/ToolCard.scss tools-mini-program/src/pages/index/index.tsx
git commit -m "feat(tool-login): 小程序端 ToolCard 标签 + 点击登录拦截"
```

---

### Task 6: 管理后台 - 编辑弹窗新增 Toggle

**Files:**
- Modify: `frontend/src/components/Admin/ToolManagement.tsx`

**Step 1: 弹窗 Toggle 区域扩展**

当前弹窗 Toggle 区域（约第 645-685 行）是 `grid-cols-3`，需要改为 `grid-cols-4` 容纳第四个 Toggle。

将 `<div className="col-span-2 grid grid-cols-3 gap-4">` 改为：

```tsx
                  <div className="col-span-2 grid grid-cols-4 gap-3">
```

在第三个 Toggle（上线状态，约第 673-684 行）之后、`</div>` 之前，新增第四个 Toggle：

```tsx
                    <div className="flex items-center justify-between bg-slate-700 rounded p-3">
                      <span className="text-sm text-slate-300">需要登录</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={toolForm.require_login ?? false}
                          onChange={(e) => setToolForm({...toolForm, require_login: e.target.checked})}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-slate-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange-500"></div>
                      </label>
                    </div>
```

**Step 2: 验证编译**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend && npx tsc --noEmit 2>&1 | grep "ToolManagement"
```
Expected: no output

**Step 3: Commit**

```bash
git add frontend/src/components/Admin/ToolManagement.tsx
git commit -m "feat(tool-login): 管理后台编辑弹窗新增需要登录 Toggle"
```

---

### Task 7: 管理后台 - 表格新增 Toggle 列

**Files:**
- Modify: `frontend/src/components/Admin/ToolManagement.tsx`

**Step 1: 新增 handler**

在 `handleMobileToggle` 函数（约第 98-106 行）之后，新增：

```tsx
  const handleLoginToggle = async (toolId: string, currentValue: boolean) => {
    try {
      await updateTool(toolId, { require_login: !currentValue });
      setTools(tools.map(t => t.id === toolId ? { ...t, require_login: !currentValue } : t));
      success(`登录要求已${!currentValue ? '开启' : '关闭'}`);
    } catch (e) {
      error('更新失败');
    }
  };
```

**Step 2: 表头 7列 → 7列（已有6列，加登录要求列）**

当前表头（约第 413-420 行）有 6 列。在"移动展示"列之后、"操作"列之前新增：

```tsx
                <th className="px-6 py-3 text-center w-[100px]">登录要求</th>
```

**Step 3: 表格行新增 Toggle 单元格**

在移动展示 Toggle 的 `</td>` 之后、操作列的 `</td>` 之前（约第 475 行之后），新增：

```tsx
                  {/* 登录要求 */}
                  <td className="px-6 py-4 text-center">
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={tool.require_login ?? false}
                        onChange={() => handleLoginToggle(tool.id, tool.require_login ?? false)}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-slate-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-orange-500"></div>
                    </label>
                  </td>
```

**Step 4: 验证编译**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend && npx tsc --noEmit 2>&1 | grep "ToolManagement"
```
Expected: no output

**Step 5: Commit**

```bash
git add frontend/src/components/Admin/ToolManagement.tsx
git commit -m "feat(tool-login): 管理后台表格新增登录要求 Toggle 列"
```

---

### Task 8: 管理后台 - 筛选栏新增登录要求过滤

**Files:**
- Modify: `frontend/src/components/Admin/ToolManagement.tsx`

**Step 1: 新增 state**

在 `showMobileFilter` state（约第 31 行）之后新增：

```tsx
  const [requireLoginFilter, setRequireLoginFilter] = useState<string>('all');
```

**Step 2: fetchData 传递参数**

在 `fetchData` 的 `params` 对象（约第 45-55 行）中，`show_mobile:` 之后新增：

```tsx
        require_login: requireLoginFilter === 'all' ? undefined : requireLoginFilter === 'true',
```

**Step 3: useEffect 依赖项**

在 `fetchData` 的依赖数组（约第 71 行）中，`showMobileFilter` 之后新增：

```tsx
, requireLoginFilter
```

**Step 4: handleResetFilters 新增重置**

在 `handleResetFilters` 函数（约第 211-220 行）中，`setShowMobileFilter('all');` 之后新增：

```tsx
    setRequireLoginFilter('all');
```

**Step 5: hasActiveFilters 新增检查**

在 `hasActiveFilters` 判断（约第 223-224 行）中，末尾新增：

```tsx
    || requireLoginFilter !== 'all'
```

**Step 6: 筛选工具栏新增控件**

在筛选工具栏（约第 297-389 行），在"移动端展示筛选"控件之后、`</div>`（flex-wrap 的结束）之前，新增：

```tsx
              {/* 登录要求筛选 */}
              <div className={`flex items-center bg-slate-800 border rounded-lg px-3 py-2 gap-2 transition-colors duration-200 cursor-pointer ${requireLoginFilter !== 'all' ? 'border-blue-500' : 'border-slate-700 hover:border-slate-600'}`}>
                <i className="fas fa-lock text-slate-500 text-xs"></i>
                <span className="text-xs text-slate-400">登录</span>
                <select
                  value={requireLoginFilter}
                  onChange={(e) => { setRequireLoginFilter(e.target.value); setToolPage(1); }}
                  className="bg-transparent text-white text-sm outline-none appearance-none pr-2 cursor-pointer w-[60px]"
                >
                  <option value="all" className="bg-slate-800">全部</option>
                  <option value="true" className="bg-slate-800">需登录</option>
                  <option value="false" className="bg-slate-800">免登录</option>
                </select>
              </div>
```

**Step 7: 激活筛选提示新增标签**

在激活筛选提示区域（约第 258-294 行），在 `showMobileFilter !== 'all'` 的标签之后、重置按钮之前新增：

```tsx
              {requireLoginFilter !== 'all' && (
                <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 text-xs rounded-full border border-blue-500/20">
                  登录: {requireLoginFilter === 'true' ? '需登录' : '免登录'}
                </span>
              )}
```

**Step 8: 验证编译**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend && npx tsc --noEmit 2>&1 | grep "ToolManagement"
```
Expected: no output

**Step 9: Commit**

```bash
git add frontend/src/components/Admin/ToolManagement.tsx
git commit -m "feat(tool-login): 管理后台筛选栏新增登录要求过滤"
```

---

## 执行顺序

1. Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7 → Task 8
2. 后端改动（Task 1-2）优先，前端依赖后端数据
3. 每个 Task 完成后验证再进入下一个

## 关键补充点

1. **默认值**：`require_login` 默认 `false`（免登录），所有新增工具默认不需要登录
2. **颜色方案**：橙色（`orange-500`），与绿色（在线）、蓝色（PC）、紫色（移动）区分
3. **Web 前端拦截**：使用 `window.confirm` 弹窗，确认后跳转 `/login` 页
4. **小程序拦截**：使用 `Taro.showToast` 提示，1.5s 后跳转登录页并携带 redirect 参数
5. **小程序登录检查**：通过 `Taro.getStorageSync('auth_token')` 判断，与现有机制一致
6. **后端不过滤**：公开 `/tools` API 不根据 `require_login` 过滤，前端自行决定显示策略
7. **管理后台筛选**：`require_login` 过滤参数通过 `requireLoginFilter` state 传递到后端
