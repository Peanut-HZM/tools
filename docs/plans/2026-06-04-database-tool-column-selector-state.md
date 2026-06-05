# Database Tool ColumnSelector 复选框失效 Bug 修复实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 `ResultViewer.tsx` 中列可见性状态管理错误，让 ColumnSelector 的复选框和表格列实时同步。

**Architecture:** 把 `visibleColumns` 从 const 派生值改为 `useState` 状态，初始值从 localStorage 懒加载；`handleColumnChange` 同时调用 setState 和 localStorage 持久化；用 useEffect 在 `storageKey/columns` 变化时从 localStorage 重新加载。

**Tech Stack:** React 18, TypeScript, Vitest, @testing-library/react, agent-browser (E2E 验证)

**前置文档**:
- Spec: `docs/superpowers/specs/2026-06-04-database-tool-column-selector-state-design.md`

---

## Task 1: 写失败的测试用例

**Files:**
- Create: `frontend/src/components/Tools/DatabaseTool/components/ResultViewer.columnVisibility.test.tsx`

**Step 1: 创建测试文件**

新建文件，验证以下三种行为（每种一个 test case）：

```tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import ResultViewer from './ResultViewer';
import { SQLExecutionResult } from '../../../../types/databaseTool';

// Mock 依赖
vi.mock('../../../../hooks/useToast', () => ({
  useToast: () => ({ addToast: vi.fn() })
}));

vi.mock('../../../../utils/sqlGenerator', () => ({
  generateInsertStatements: vi.fn(() => '-- insert'),
  generateUpdateStatements: vi.fn(() => '-- update')
}));

vi.mock('../../../../api/databaseToolApi', () => ({
  executeSQL: vi.fn(),
  updateRows: vi.fn()
}));

const baseResult: SQLExecutionResult = {
  success: true,
  affected_rows: 2,
  execution_time_ms: 10,
  result_data: [
    { id: 1, name: 'A', description: 'desc-A' },
    { id: 2, name: 'B', description: 'desc-B' }
  ],
  columns: ['id', 'name', 'description'],
  column_types: {}
};

const renderViewer = (props: any = {}) => {
  return render(
    <ResultViewer
      result={baseResult}
      configId="test-cfg"
      databaseName="test-db"
      tableName="test_table"
      {...props}
    />
  );
};

describe('ResultViewer 列可见性管理', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('取消勾选某列后，表格立即移除该列', async () => {
    const { container } = renderViewer();
    
    // 打开列选择 dropdown
    const colButton = container.querySelector('button[title="列"]')!;
    fireEvent.click(colButton);
    
    // 取消勾选第二列 'name'
    const rows = container.querySelectorAll('.absolute.top-full .cursor-pointer');
    fireEvent.click(rows[1]);
    
    // 等待 React 重渲染
    await waitFor(() => {
      // 列头 'name' 应该不在表格中了
      const headers = container.querySelectorAll('thead th');
      const headerTexts = Array.from(headers).map(h => h.textContent);
      expect(headerTexts.some(t => t?.toUpperCase().includes('NAME'))).toBe(false);
    });
  });

  it('取消勾选后，列可见性持久化到 localStorage', async () => {
    const { container } = renderViewer();
    const storageKey = 'db-column-visibility-test-cfg-test-db--test_table';
    
    const colButton = container.querySelector('button[title="列"]')!;
    fireEvent.click(colButton);
    
    const rows = container.querySelectorAll('.absolute.top-full .cursor-pointer');
    fireEvent.click(rows[1]); // 取消 name
    
    await waitFor(() => {
      const stored = JSON.parse(localStorage.getItem(storageKey) || '[]');
      expect(stored).toEqual(['id', 'description']); // 不包含 'name'
    });
  });

  it('至少保留一列的约束有效', async () => {
    const { container } = renderViewer();
    
    const colButton = container.querySelector('button[title="列"]')!;
    fireEvent.click(colButton);
    
    // 取消所有列（除最后一个外）
    const rows = container.querySelectorAll('.absolute.top-full .cursor-pointer');
    fireEvent.click(rows[0]);
    fireEvent.click(rows[1]); // 此时应该只剩 'description'，再点 rows[2] 应该被阻止
    
    await waitFor(() => {
      const checkboxes = container.querySelectorAll('.absolute.top-full input[type=checkbox]');
      const checkedCount = Array.from(checkboxes).filter((c: any) => c.checked).length;
      // 全选 + 列表中的列：全选 checkbox 的状态是 isAllSelected (length === visibleColumns.length)
      // 至少应该有一个列保留
      expect(checkedCount).toBeGreaterThan(0);
    });
  });
});
```

**Step 2: 运行测试，验证失败**

Run:
```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend && npx vitest run src/components/Tools/DatabaseTool/components/ResultViewer.columnVisibility.test.tsx 2>&1 | tail -30
```

Expected: 测试**失败**，因为当前实现下点击 checkbox 不会更新表格列（bug 仍然存在）。

如果测试意外通过：检查渲染的组件是否真的是 `ResultViewer`，或者是否有 mock 覆盖了 `handleColumnChange`。

**Step 3: 不做 commit（测试尚未通过）**

---

## Task 2: 实施修复

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx:400-425`

**Step 1: 删除 const 派生值**

在 `ResultViewer.tsx` 第 400-415 行，删除 `getStoredColumns` 函数和 `storedCols` / `displayColumns` / `visibleColumns` 的 const 派生。

**Step 2: 改为 useState**

在 `ResultViewer.tsx` 第 42 行附近（紧跟 `storageKey` 声明后），添加：

```tsx
// 列可见性状态（按表名持久化到 localStorage）
const storageKey = tableName ? `db-column-visibility-${configId}-${databaseName || ''}-${schemaName || ''}-${tableName}` : null;

const [visibleColumns, setVisibleColumns] = useState<string[]>(() => {
  if (!storageKey) return [];
  try {
    const saved = localStorage.getItem(storageKey);
    if (!saved) return [];
    const parsed: string[] = JSON.parse(saved);
    return parsed;
  } catch {
    return [];
  }
});
```

**Step 3: 在 columns 计算后添加派生逻辑**

在 `ResultViewer.tsx` 第 398 行（`const columns = ...`）之后，添加 useEffect 来同步：

```tsx
// 同步：columns 或 storageKey 变化时，从 localStorage 重新加载并过滤
useEffect(() => {
  if (!storageKey) {
    setVisibleColumns(columns);
    return;
  }
  try {
    const saved = localStorage.getItem(storageKey);
    if (!saved) {
      setVisibleColumns(columns);
      return;
    }
    const parsed: string[] = JSON.parse(saved);
    // 过滤掉已不存在的列
    const filtered = parsed.filter((col) => columns.includes(col));
    setVisibleColumns(filtered.length > 0 ? filtered : columns);
  } catch {
    setVisibleColumns(columns);
  }
}, [storageKey, columns]);
```

**Step 4: 修改 handleColumnChange**

替换第 417-425 行的 `handleColumnChange`：

```tsx
const handleColumnChange = (cols: string[]) => {
  // 1. 立即更新 React state，触发重渲染（让 ColumnSelector 和表格都更新）
  setVisibleColumns(cols);
  // 2. 持久化到 localStorage
  if (storageKey) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(cols));
    } catch (e) {
      console.error('Failed to save column visibility:', e);
    }
  }
};
```

**Step 5: 移除现在已经成为孤儿代码的局部 `visibleColumns` 派生**

确保文件里**没有**重复的 const `visibleColumns` 声明（从派生值改成 useState 之后）。

**Step 6: 运行测试，验证通过**

Run:
```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend && npx vitest run src/components/Tools/DatabaseTool/components/ResultViewer.columnVisibility.test.tsx 2>&1 | tail -30
```

Expected: **3 个 test 全部通过**。

如果失败：
- 检查 `useEffect` 依赖是否正确
- 检查 `storageKey` 是否正确生成
- 检查 `setVisibleColumns` 是否被调用

**Step 7: TypeScript 类型检查**

Run:
```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend && npx tsc --noEmit 2>&1 | grep "ResultViewer\|ColumnSelector" | head -10
```

Expected: 无输出（零错误）。

**Step 8: Commit**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx frontend/src/components/Tools/DatabaseTool/components/ResultViewer.columnVisibility.test.tsx
git commit -m "fix(database-tool): 列可见性改为 useState 管理

修复 ResultViewer 中 visibleColumns 派生值不触发重渲染的 bug。
原来：const 派生 + 只写 localStorage，React 不知道有变化。
现在：useState + setVisibleColumns + useEffect 同步，状态正确驱动 UI。

ColumnSelector 复选框现在能实时切换，表格列数同步变化。
保留'至少保留 1 列'约束。
"
```

---

## Task 3: 浏览器端到端验证

**Files:** N/A（仅验证）

**Step 1: 启动前端 dev server（如果未运行）**

```bash
cd /Users/huazhongmin/IdeaProjects/tools && python dev_services.py status
```

如果未运行：
```bash
cd /Users/huazhongmin/IdeaProjects/tools && python dev_services.py start --frontend-only
```

**Step 2: 用 agent-browser 登录并导航到表数据视图**

注入 token（参考之前的会话）：
```bash
agent-browser eval "localStorage.setItem('auth_token', '<token>')"
agent-browser navigate "http://localhost:5178/tools/database-tool"
```

展开 `glodon-hr-dev` → `ehr_onbserviice_dev` → `Tables` → 双击 `gen_table`。

**Step 3: 打开 ColumnSelector dropdown 并操作**

```bash
agent-browser eval "(() => {
  const btn = document.querySelector('button[title=\"列\"]');
  if (btn) { btn.click(); return 'clicked'; }
  return 'not found';
})()"
```

**Step 4: 截图确认 dropdown 正常显示**

```bash
agent-browser screenshot
```

Expected: dropdown 显示"全选" + 列列表，初始全部勾选。

**Step 5: 取消勾选第二列（table_name）并截图**

```bash
agent-browser eval "(() => {
  const rows = document.querySelectorAll('.absolute.top-full .cursor-pointer');
  if (rows[1]) { rows[1].click(); return 'clicked row 1'; }
  return 'no row';
})()"
agent-browser screenshot
```

Expected: dropdown 中 table_name 复选框取消勾选，表格中 table_name 列立即消失（不再渲染）。

**Step 6: 全选 checkbox 切到"只保留 1 列"测试**

```bash
agent-browser eval "(() => {
  const all = document.querySelector('input[id^=\"col-select-all\"]');
  if (all) { all.click(); return 'clicked select all'; }
  return 'not found';
})()"
agent-browser screenshot
```

Expected: 表格只显示 1 列（保留第一个有效列）。

**Step 7: 关闭再打开下拉，验证状态保留**

```bash
agent-browser eval "document.body.click()"
sleep 1
agent-browser eval "document.querySelector('button[title=\"列\"]').click()"
agent-browser screenshot
```

Expected: dropdown 中复选框状态反映"只显示 1 列"。

**Step 8: 关闭 tab → 重新打开同表，验证 localStorage 持久化**

（agent-browser 中通过 reload 模拟）

```bash
agent-browser navigate "http://localhost:5178/tools/database-tool"
# 重新展开导航树 → 双击 gen_table
agent-browser eval "document.querySelector('button[title=\"列\"]').click()"
agent-browser screenshot
```

Expected: 列可见性保持（仍只显示 1 列）。

**Step 9: console 错误检查**

```bash
agent-browser eval "JSON.stringify({errors: window.__errors || [], hasErrors: (window.__errors||[]).length > 0})"
```

Expected: `{errors: [], hasErrors: false}`。

---

## 任务收尾

完成后：
- [x] 测试通过（Task 1 → Task 2 Step 6）
- [x] TypeScript 零错误（Task 2 Step 7）
- [x] 浏览器 E2E 行为符合预期（Task 3 全部）
- [x] 提交（Task 2 Step 8）
- [x] 等待用户确认后归档 spec → openspec:archive-change 或 docs 更新

**回退方案**：
```bash
cd /Users/huazhongmin/IdeaProjects/tools
git revert HEAD~0  # 或 git reset --hard HEAD~1
```
