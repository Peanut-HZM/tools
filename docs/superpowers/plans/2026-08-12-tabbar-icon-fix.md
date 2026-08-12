# TabBar 图标修复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 TabBar 页签图标显示，添加 `fas` 前缀以正确渲染 Font Awesome 图标

**Architecture:** 单文件改动 — TabBar.tsx 第 28 行添加 `fas` 前缀，与 Phase 10 侧边栏图标修复方案一致

**Tech Stack:** React 18 + TypeScript + Tailwind CSS

## Global Constraints

- 所有对话、文档、注释、提交信息使用中文
- 修改前端代码后必须使用浏览器验证
- 优先利用热加载，非必要不重启服务
- TypeScript 编译无新增错误
- 浏览器 Console 无错误
- Tailwind 暗色主题：bg-slate-800/900, border-slate-700, text-slate-300/400

---

### Task 1: 修复 TabBar 图标显示

**Files:**
- Modify: `frontend/src/components/Workspace/TabBar.tsx:28`
- Test: `frontend/src/components/Workspace/TabBar.test.tsx`

**Interfaces:**
- Consumes: `tab.toolIcon`（来自 workspaceStore，值为 `fa-database` 等）
- Produces: 图标正确显示为 `fas fa-database`

**Context:** 
- API 返回的图标值为 `fa-database`、`fa-server` 等，缺少 `fas` 样式前缀
- TabBar 第 28 行直接渲染 `tab.toolIcon`，导致图标无法显示
- 修复方案与 WorkspaceSidebar.tsx 一致（Phase 10 已修复）

- [ ] **Step 1: 编写测试验证图标渲染**

修改 `frontend/src/components/Workspace/TabBar.test.tsx`，添加图标测试：

```tsx
it('should render tool icons with fas prefix', () => {
  useWorkspaceStore.setState({
    tabs: [
      { id: '1', toolId: 'database-tool', toolName: '数据库', toolIcon: 'fa-database', openedAt: Date.now() },
    ],
    activeTabId: '1',
  });
  
  render(<TabBar />);
  const icon = document.querySelector('[data-tab-id="1"] i');
  expect(icon?.className).toContain('fas');
  expect(icon?.className).toContain('fa-database');
});
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd frontend && npx vitest run src/components/Workspace/TabBar.test.tsx`
Expected: 图标测试 FAIL（`fas` 前缀尚未添加）

- [ ] **Step 3: 实现图标修复**

修改 `frontend/src/components/Workspace/TabBar.tsx` 第 28 行：

```tsx
// 修改前
<i className={[tab.toolIcon, 'text-xs flex-shrink-0'].join(' ')}></i>

// 修改后
<i className={['fas', tab.toolIcon, 'text-xs flex-shrink-0'].join(' ')}></i>
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd frontend && npx vitest run src/components/Workspace/TabBar.test.tsx`
Expected: 全部测试通过（含新增的图标测试）

- [ ] **Step 5: 验证 TypeScript 编译**

Run: `npx tsc --noEmit 2>&1 | grep "TabBar" | head -5`
Expected: 无错误

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Workspace/TabBar.tsx frontend/src/components/Workspace/TabBar.test.tsx
git commit -m "fix(workspace): TabBar 页签添加 fas 图标前缀，正确显示工具图标"
```

---

## 验收标准

- [ ] Tab 页签显示正确的 Font Awesome 图标（`fas fa-database` 等）
- [ ] TypeScript 编译无新增错误
- [ ] 浏览器 Console 无错误
- [ ] 测试通过
