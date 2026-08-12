# 工作区侧边栏优化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 隐藏工作区 Header、修复侧边栏图标显示、添加搜索框，提升工作区沉浸式体验

**Architecture:** 3 个独立改动：Layout 条件渲染 Header、WorkspaceSidebar 添加 `fas` 前缀修复图标并新增搜索过滤功能、i18n 新增翻译 key

**Tech Stack:** React 18 + TypeScript + Tailwind CSS + Zustand + i18n

## Global Constraints

- 所有对话、文档、注释、提交信息使用中文
- 修改前端代码后必须使用浏览器验证
- 优先利用热加载，非必要不重启服务
- TypeScript 编译无新增错误
- 浏览器 Console 无错误
- Tailwind 暗色主题：bg-slate-800/900, border-slate-700, text-slate-300/400

---

### Task 1: 隐藏工作区 Header

**Files:**
- Modify: `frontend/src/components/Layout/Layout.tsx`

**Interfaces:**
- Consumes: `isImmersion` 变量（已存在）
- Produces: Header 在工作区路由下不渲染

**Context:** Layout.tsx 已有 `isImmersion` 判断（匹配 `/workspace` 和 `/tools/*`），但 Header 组件始终渲染。需改为条件渲染。

- [ ] **Step 1: 修改 Header 渲染逻辑**

修改 `frontend/src/components/Layout/Layout.tsx`，将 Header 包裹在条件判断中：

```tsx
// 修改前（第 32-36 行）：
<Header
  searchValue={searchValue}
  onSearchChange={handleSearchChange}
  onSearch={onSearch}
/>

// 修改后：
{!isImmersion && (
  <Header
    searchValue={searchValue}
    onSearchChange={handleSearchChange}
    onSearch={onSearch}
  />
)}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `npx tsc --noEmit 2>&1 | grep "Layout" | head -5`
Expected: 无错误

- [ ] **Step 3: 浏览器验证**

验证以下场景：
1. `/workspace` 路由 → Header 隐藏 ✅
2. `/` 首页 → Header 正常显示 ✅
3. `/tools/database-tool` 路由 → Header 隐藏 ✅

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Layout/Layout.tsx
git commit -m "fix(layout): 工作区模式下隐藏 Header 导航栏"
```

---

### Task 2: 修复图标 + 添加搜索框

**Files:**
- Modify: `frontend/src/components/Workspace/WorkspaceSidebar.tsx`
- Test: `frontend/src/components/Workspace/WorkspaceSidebar.test.tsx`

**Interfaces:**
- Consumes: `tools: Tool[]`（props，已有），`useI18n`（已有）
- Produces: 图标正确显示、搜索框实时过滤工具列表

**Context:** 
- API 返回的图标值为 `fa-database`、`fa-server` 等，缺少 `fas` 样式前缀
- 搜索框需在"返回首页"按钮下方、工具列表上方，按 `tool.title` 实时过滤

- [ ] **Step 1: 编写搜索框相关测试**

修改 `frontend/src/components/Workspace/WorkspaceSidebar.test.tsx`，添加搜索相关测试：

```tsx
// 在现有 describe 块中添加以下测试

it('should render search input', () => {
  render(<WorkspaceSidebar tools={mockTools} />);
  const searchInput = screen.getByPlaceholderText('搜索工具...');
  expect(searchInput).toBeTruthy();
});

it('should filter tools by search query', () => {
  render(<WorkspaceSidebar tools={mockTools} />);
  const searchInput = screen.getByPlaceholderText('搜索工具...');
  fireEvent.change(searchInput, { target: { value: 'K8s' } });
  
  // Only K8s should be visible
  expect(screen.queryByText('SSH')).toBeNull();
});

it('should show all tools when search is cleared', () => {
  render(<WorkspaceSidebar tools={mockTools} />);
  const searchInput = screen.getByPlaceholderText('搜索工具...');
  fireEvent.change(searchInput, { target: { value: 'K8s' } });
  fireEvent.change(searchInput, { target: { value: '' } });
  
  expect(screen.getByText('K8s')).toBeTruthy();
  expect(screen.getByText('SSH')).toBeTruthy();
});
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd frontend && npx vitest run src/components/Workspace/WorkspaceSidebar.test.tsx`
Expected: 搜索相关测试 FAIL（搜索框尚未实现）

- [ ] **Step 3: 实现图标修复 + 搜索框**

修改 `frontend/src/components/Workspace/WorkspaceSidebar.tsx`：

```tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useI18n } from '../../i18n';
import type { Tool } from '../../types';

interface Props {
  tools: Tool[];
}

const SIDEBAR_COLLAPSED_KEY = 'workspace-sidebar-collapsed';

export const WorkspaceSidebar: React.FC<Props> = ({ tools }) => {
  const navigate = useNavigate();
  const { t } = useI18n();
  const { tabs, addTab } = useWorkspaceStore();
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true';
  });
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(collapsed));
  }, [collapsed]);

  const openedToolIds = new Set(tabs.map((t) => t.toolId));

  // 按名称过滤工具
  const filteredTools = tools.filter((tool) =>
    tool.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleToolClick = (tool: Tool) => {
    addTab({ id: tool.id, title: tool.title, icon: tool.icon });
  };

  const handleGoHome = () => {
    navigate('/');
  };

  if (collapsed) {
    return (
      <div className="w-12 bg-slate-800 border-r border-slate-700 flex flex-col items-center py-2">
        <button
          onClick={() => setCollapsed(false)}
          className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded transition-colors"
          title={t.workspace.expandSidebar}
        >
          <i className="fas fa-chevron-right text-xs"></i>
        </button>
      </div>
    );
  }

  return (
    <div className="w-52 bg-slate-800 border-r border-slate-700 flex flex-col h-full">
      {/* 首页按钮 */}
      <div className="p-3 border-b border-slate-700">
        <button
          onClick={handleGoHome}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-sm font-medium transition-colors"
        >
          <i className="fas fa-home"></i>
          <span>{t.workspace.home}</span>
        </button>
      </div>

      {/* 搜索框 */}
      <div className="px-3 py-2 border-b border-slate-700">
        <div className="relative">
          <i className="fas fa-search absolute left-2 top-1/2 -translate-y-1/2 text-slate-500 text-xs"></i>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t.workspace.searchPlaceholder}
            className="w-full bg-slate-900 border border-slate-700 rounded-md pl-7 pr-2 py-1.5 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-slate-600"
          />
        </div>
      </div>

      {/* 折叠按钮 */}
      <div className="flex justify-end px-2 pt-2">
        <button
          onClick={() => setCollapsed(true)}
          className="p-1 text-slate-500 hover:text-slate-300 hover:bg-slate-700 rounded transition-colors"
          title={t.workspace.collapseSidebar}
        >
          <i className="fas fa-chevron-left text-xs"></i>
        </button>
      </div>

      {/* 工具列表 */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        <div className="text-[10px] text-slate-500 uppercase font-semibold tracking-wider px-2 mb-2">
          {t.workspace.toolList}
        </div>
        <div className="space-y-0.5">
          {filteredTools.map((tool) => {
            const isOpened = openedToolIds.has(tool.id);
            return (
              <div
                key={tool.id}
                data-tool-id={tool.id}
                data-active={isOpened}
                className={[
                  'flex items-center gap-2 px-3 py-2 rounded-md text-sm cursor-pointer transition-colors',
                  isOpened
                    ? 'bg-blue-600/20 text-blue-300'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white',
                ].join(' ')}
                onClick={() => handleToolClick(tool)}
              >
                <i className={['fas', tool.icon, 'text-xs w-4 text-center flex-shrink-0'].join(' ')}></i>
                <span className="truncate">{tool.title}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
```

**关键改动说明：**
1. 添加 `searchQuery` 状态和 `filteredTools` 过滤逻辑
2. 图标渲染从 `tool.icon` 改为 `['fas', tool.icon, ...].join(' ')`
3. 在首页按钮和折叠按钮之间添加搜索框 UI

- [ ] **Step 4: 运行测试验证通过**

Run: `cd frontend && npx vitest run src/components/Workspace/WorkspaceSidebar.test.tsx`
Expected: 全部测试通过（含新增的 3 个搜索测试）

- [ ] **Step 5: 验证 TypeScript 编译**

Run: `npx tsc --noEmit 2>&1 | grep "WorkspaceSidebar" | head -5`
Expected: 无错误

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Workspace/WorkspaceSidebar.tsx frontend/src/components/Workspace/WorkspaceSidebar.test.tsx
git commit -m "feat(workspace): 修复工具图标显示，添加侧边栏搜索过滤功能"
```

---

### Task 3: 添加 i18n 翻译

**Files:**
- Modify: `frontend/src/i18n/locales/zh-CN.ts:35-44`
- Modify: `frontend/src/i18n/locales/en-US.ts:35-44`

**Interfaces:**
- Consumes: 现有 `workspace` 翻译对象
- Produces: `workspace.searchPlaceholder` 翻译 key

- [ ] **Step 1: 添加中文翻译**

修改 `frontend/src/i18n/locales/zh-CN.ts`，在 `workspace` 对象中添加：

```typescript
// 在 workspace 对象中添加（第 43 行 unknownTool 之后）
workspace: {
  // ... 现有 key ...
  unknownTool: '未知工具',
  searchPlaceholder: '搜索工具...',
},
```

- [ ] **Step 2: 添加英文翻译**

修改 `frontend/src/i18n/locales/en-US.ts`，在 `workspace` 对象中添加：

```typescript
// 在 workspace 对象中添加（第 43 行 unknownTool 之后）
workspace: {
  // ... 现有 key ...
  unknownTool: 'Unknown Tool',
  searchPlaceholder: 'Search tools...',
},
```

- [ ] **Step 3: 验证 TypeScript 编译**

Run: `npx tsc --noEmit 2>&1 | grep -E "(zh-CN|en-US|i18n)" | head -5`
Expected: 无错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/i18n/locales/zh-CN.ts frontend/src/i18n/locales/en-US.ts
git commit -m "feat(i18n): 添加工作区搜索框翻译（中英文）"
```

---

## 实施顺序

1. **Task 1** — 修复 Header 隐藏（独立改动，无依赖）
2. **Task 2** — 修复图标 + 搜索框（依赖 Task 1 完成后的布局状态）
3. **Task 3** — i18n 翻译（可与 Task 2 并行，但建议顺序执行以保持一致性）

## 验收标准

- [ ] `/workspace` 路由下 Header 完全隐藏
- [ ] 侧边栏工具列表显示正确的 Font Awesome 图标（`fas fa-database` 等）
- [ ] 侧边栏顶部有搜索框，占位符为"搜索工具..."
- [ ] 输入关键词实时过滤工具列表（按名称）
- [ ] 清空搜索框后显示所有工具
- [ ] TypeScript 编译无新增错误
- [ ] 浏览器 Console 无错误
- [ ] 首页 Header 正常显示（不受影响）
