# Database Tool SQL 执行器 可拖动高度 + 全屏 + 文案修复 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 SQLExecutor 增加拖动分隔条 + 全屏覆盖功能，并修复"执行中"按钮文案错误的 Bug。

**Architecture:** 纯 React 状态（`useState`）管理编辑器高度与全屏标志；自定义鼠标事件实现拖动（零新依赖）；`localStorage` 持久化用户高度；`ResizeObserver` 获取父列实际高度做 max 约束；Esc 键监听退出全屏。

**Tech Stack:** React 18, TypeScript, Tailwind CSS, Vitest, @testing-library/react, agent-browser (E2E)

**前置文档**:
- Spec: `docs/superpowers/specs/2026-06-05-sql-executor-resizable-fullscreen-design.md`

**前置依赖**:
- 数据库工具页面已开发完毕，前后端服务在 5178/19092 运行
- 测试框架 Vitest 已配置（参考 `ResultViewer.columnVisibility.test.tsx`）
- 用户已登录 `peanut` 账户，可访问 `http://localhost:5178/tools/database-tool`

---

## Task 1: i18n 新增 key + 修复按钮文案

**Files:**
- Modify: `frontend/src/i18n/locales/zh-CN.ts:347-360`
- Modify: `frontend/src/i18n/locales/en-US.ts:346-359`
- Modify: `frontend/src/components/Tools/DatabaseTool/components/SQLEditor.tsx:119`

**Step 1: 写失败测试**

在 `frontend/src/components/Tools/DatabaseTool/components/SQLEditor.test.tsx` 新建测试文件（如果不存在则创建）：

```tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import SQLEditor from './SQLEditor';

// Mock Monaco 编辑器（避免 jsdom 加载）
vi.mock('@monaco-editor/react', () => ({
  default: () => <div data-testid="monaco-mock" />,
  useMonaco: () => null,
}));

vi.mock('../../../../i18n', () => ({
  useI18n: () => ({
    t: {
      database: {
        executor: {
          title: 'SQL 执行器',
          run: '执行',
          executing: '执行中...',
          stop: '停止',
          clear: '清空',
          history: '执行历史',
          results: '执行结果',
          enterFullscreen: '全屏',
          exitFullscreen: '退出全屏',
        },
        status: { testing: '测试中...' },
      },
    },
  }),
}));

const baseProps = {
  value: 'SELECT 1',
  onChange: vi.fn(),
  onExecute: vi.fn(),
  tables: [],
};

describe('SQLEditor 按钮文案', () => {
  it('静态按钮显示"执行"', () => {
    render(<SQLEditor {...baseProps} loading={false} />);
    expect(screen.getByRole('button', { name: '执行' })).toBeTruthy();
  });

  it('loading 状态显示"执行中..."', () => {
    render(<SQLEditor {...baseProps} loading={true} />);
    expect(screen.getByText('执行中...')).toBeTruthy();
    expect(screen.queryByText('测试中...')).toBeNull();
  });
});
```

**Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/components/Tools/DatabaseTool/components/SQLEditor.test.tsx`

Expected: 2 个测试**失败**（按钮当前显示"测试中..."，且 SQLEditor 还不接受 isFullscreen prop — 测试先不传该 prop，因为这是 Task 2 的范围）

注：当前 SQLEditor.tsx:119 用的是 `t.database.status.testing`，测试断言"执行中"会失败 ✓

**Step 3: 修改 SQLEditor.tsx 修复按钮文案**

打开 `frontend/src/components/Tools/DatabaseTool/components/SQLEditor.tsx`，定位到行 119，修改：

```diff
- {loading ? t.database.status.testing : t.database.executor.run}
+ {loading ? t.database.executor.executing : t.database.executor.run}
```

**Step 4: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/components/Tools/DatabaseTool/components/SQLEditor.test.tsx`

Expected: 2 个测试**通过**

**Step 5: 在 zh-CN.ts 新增 i18n key**

打开 `frontend/src/i18n/locales/zh-CN.ts`，定位到 `executor:` 段（行 347-360），在 `copyInsert` 之后新增：

```typescript
  copyInsert: '复制 INSERT',
  enterFullscreen: '全屏',
  exitFullscreen: '退出全屏',
  dragHandleHint: '拖动调整编辑器高度',
```

**Step 6: 在 en-US.ts 新增 i18n key**

打开 `frontend/src/i18n/locales/en-US.ts`，定位到 `executor:` 段（行 346-359），在 `copyInsert` 之后新增：

```typescript
  copyInsert: 'Copy INSERT',
  enterFullscreen: 'Fullscreen',
  exitFullscreen: 'Exit Fullscreen',
  dragHandleHint: 'Drag to resize editor',
```

**Step 7: TypeScript 类型检查**

Run: `cd frontend && npx tsc --noEmit`

Expected: 0 错误

**Step 8: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/DatabaseTool/components/SQLEditor.tsx \
        frontend/src/components/Tools/DatabaseTool/components/SQLEditor.test.tsx \
        frontend/src/i18n/locales/zh-CN.ts \
        frontend/src/i18n/locales/en-US.ts
git commit -m "fix(frontend): 修复执行按钮文案 + 新增全屏 i18n key"
```

---

## Task 2: SQLExecutor 状态管理 + 拖动手柄 + 持久化

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx` (全文重构顶部 state + JSX)
- Create: `frontend/src/components/Tools/DatabaseTool/SQLExecutor.test.tsx`

**Step 1: 写失败测试**

新建 `frontend/src/components/Tools/DatabaseTool/SQLExecutor.test.tsx`：

```tsx
import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import SQLExecutor from './SQLExecutor';
import { DatabaseToolProvider } from '../../../contexts/DatabaseToolContext';

// Mock 依赖
vi.mock('@monaco-editor/react', () => ({
  default: () => <div data-testid="monaco-mock" />,
  useMonaco: () => null,
}));

vi.mock('../../../hooks/useToast', () => ({
  useToast: () => ({ error: vi.fn(), success: vi.fn() }),
}));

vi.mock('../../../api/databaseToolApi', () => ({
  executeSQL: vi.fn(),
  getDatabasesList: vi.fn(() => Promise.resolve([])),
  getSchemasList: vi.fn(() => Promise.resolve([])),
  getDatabaseStructure: vi.fn(() => Promise.resolve({ tables: [], views: [] })),
}));

const STORAGE_KEY = 'db-tool:sqlEditorHeight';

describe('SQLExecutor 拖动 + 持久化', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('首次加载无 localStorage 时使用 CSS 1/3 默认布局', () => {
    const { container } = render(
      <SQLExecutor configId="cfg-1" database="" schema="" sql="SELECT 1" onStateChange={() => {}} />
    );
    const editorWrapper = container.querySelector('[data-testid="editor-wrapper"]');
    expect(editorWrapper?.className).toContain('h-1/3');
  });

  it('首次加载有 localStorage 时使用保存的高度', () => {
    localStorage.setItem(STORAGE_KEY, '450');
    const { container } = render(
      <SQLExecutor configId="cfg-1" database="" schema="" sql="SELECT 1" onStateChange={() => {}} />
    );
    const editorWrapper = container.querySelector('[data-testid="editor-wrapper"]');
    expect(editorWrapper?.getAttribute('style')).toContain('height: 450px');
  });

  it('拖动 mouseup 后高度写入 localStorage', () => {
    const { container } = render(
      <SQLExecutor configId="cfg-1" database="" schema="" sql="SELECT 1" onStateChange={() => {}} />
    );
    const handle = container.querySelector('[data-testid="drag-handle"]') as HTMLElement;
    expect(handle).toBeTruthy();

    // 模拟拖动：mousedown 记录起点，移动 200px 后 mouseup
    fireEvent.mouseDown(handle, { clientY: 100 });
    fireEvent.mouseMove(document, { clientY: 300 });
    fireEvent.mouseUp(document);

    const stored = localStorage.getItem(STORAGE_KEY);
    expect(stored).toBeTruthy();
    expect(Number(stored)).toBeGreaterThanOrEqual(200);
  });

  it('拖动低于 200px 时 clamp 到 200', () => {
    const { container } = render(
      <SQLExecutor configId="cfg-1" database="" schema="" sql="SELECT 1" onStateChange={() => {}} />
    );
    const handle = container.querySelector('[data-testid="drag-handle"]') as HTMLElement;

    fireEvent.mouseDown(handle, { clientY: 500 });
    fireEvent.mouseMove(document, { clientY: 10000 }); // 尝试拖到很大
    fireEvent.mouseUp(document);

    const stored = Number(localStorage.getItem(STORAGE_KEY));
    expect(stored).toBeLessThanOrEqual(2000); // 任何合理上限
  });

  it('localStorage 解析失败时回退到默认', () => {
    localStorage.setItem(STORAGE_KEY, 'not-a-number');
    const { container } = render(
      <SQLExecutor configId="cfg-1" database="" schema="" sql="SELECT 1" onStateChange={() => {}} />
    );
    const editorWrapper = container.querySelector('[data-testid="editor-wrapper"]');
    // 应回退到 h-1/3 而非错误使用 NaN
    expect(editorWrapper?.className).toContain('h-1/3');
  });
});
```

**Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run src/components/Tools/DatabaseTool/SQLExecutor.test.tsx`

Expected: 5 个测试**全部失败**（data-testid 找不到，状态未实现）

**Step 3: 修改 SQLExecutor.tsx 添加 state、ref、useEffect**

打开 `frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx`，**修改文件顶部**：

在 import 段（行 1-9）之后，组件定义之前（行 11 之前）新增常量：

```typescript
const MIN_EDITOR_H = 200;
const MAX_EDITOR_RATIO = 0.9;
const STORAGE_KEY = 'db-tool:sqlEditorHeight';
```

修改 `interface SQLExecutorProps` 保持不变。

在组件函数体内（行 26 之后，`currentConfig` 之前）新增 state 和 ref：

```typescript
const { configs, refreshHistory } = useDatabaseTool();
const toast = useToast();
const { t } = useI18n();

const leftColumnRef = React.useRef<HTMLDivElement>(null);
const [editorHeight, setEditorHeight] = React.useState<number | null>(null);
const [isDragging, setIsDragging] = React.useState(false);
const [columnHeight, setColumnHeight] = React.useState(0);
```

注意：需要先确认 `React.useRef` / `React.useState` / `React.useEffect` 已经在顶部 import。检查方法：

Run: `grep -n "^import React" frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx`

如果第一行是 `import React, { useState, useEffect, useMemo, useCallback } from 'react';`，那么 `useRef` 没被导入，需要改成：

```typescript
import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
```

**Step 4: 添加 useEffect（加载 localStorage + ResizeObserver）**

在 `currentConfig` 计算之后（行 34 之后，`currentDatabase` 计算之前）新增两个 useEffect：

```typescript
// 加载 localStorage 高度
useEffect(() => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = Number(stored);
      if (Number.isFinite(parsed) && parsed >= MIN_EDITOR_H) {
        setEditorHeight(parsed);
      }
    }
  } catch (e) {
    console.error('Failed to load editor height:', e);
  }
}, []);

// 持久化高度
useEffect(() => {
  if (editorHeight === null) return;
  try {
    localStorage.setItem(STORAGE_KEY, String(editorHeight));
  } catch (e) {
    console.error('Failed to save editor height:', e);
  }
}, [editorHeight]);

// 监听父列高度（用于 max 约束）
useEffect(() => {
  const el = leftColumnRef.current;
  if (!el) return;
  const ro = new ResizeObserver(entries => {
    const h = entries[0].contentRect.height;
    setColumnHeight(h);
  });
  ro.observe(el);
  return () => ro.disconnect();
}, []);
```

**Step 5: 添加 handleDragStart 函数**

在 `handleReuseHistory` 之后（行 199 之后，`return` 之前）新增：

```typescript
const handleDragStart = useCallback((e: React.MouseEvent) => {
  e.preventDefault();
  setIsDragging(true);

  const startY = e.clientY;
  const startH = editorHeight ?? MIN_EDITOR_H;
  const observedMax = Math.floor(columnHeight * MAX_EDITOR_RATIO);
  const refMax = leftColumnRef.current
    ? Math.floor(leftColumnRef.current.getBoundingClientRect().height * MAX_EDITOR_RATIO)
    : 0;
  const maxH = Math.max(observedMax, refMax, MIN_EDITOR_H * 2);

  let rafId: number | null = null;
  let nextHeight = startH;

  const onMove = (ev: MouseEvent) => {
    const delta = ev.clientY - startY;
    nextHeight = Math.max(MIN_EDITOR_H, Math.min(startH + delta, maxH));
    if (rafId === null) {
      rafId = requestAnimationFrame(() => {
        setEditorHeight(nextHeight);
        rafId = null;
      });
    }
  };
  const onUp = () => {
    if (rafId !== null) cancelAnimationFrame(rafId);
    setIsDragging(false);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
  };

  document.body.style.cursor = 'ns-resize';
  document.body.style.userSelect = 'none';
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
}, [editorHeight, columnHeight]);
```

**Step 6: 修改 JSX（外层 + 编辑器包装 + 拖动手柄）**

找到行 287-325 的 `<div className="flex flex-1 gap-4 overflow-hidden">` 段。修改为：

```tsx
<div className="flex flex-1 gap-4 overflow-hidden">
  {/* 左列 */}
  <div
    ref={leftColumnRef}
    className={`flex flex-col gap-4 min-w-0 ${isDragging ? 'select-none' : ''}`}
  >
    {/* 编辑器包装：根据状态选择 className 或 inline height */}
    <div
      data-testid="editor-wrapper"
      className={
        editorHeight === null
          ? 'h-1/3 min-h-[200px]'
          : 'shrink-0'
      }
      style={editorHeight !== null ? { height: `${editorHeight}px` } : undefined}
    >
      <SQLEditor
        value={sql}
        onChange={handleSqlChange}
        onExecute={handleExecute}
        loading={loading}
        tables={tables}
      />
    </div>

    {/* 拖动手柄 */}
    <div
      data-testid="drag-handle"
      role="separator"
      aria-orientation="horizontal"
      aria-label={t.database.executor.dragHandleHint}
      onMouseDown={handleDragStart}
      className="h-1.5 bg-slate-700 hover:bg-blue-500 active:bg-blue-400
                 cursor-ns-resize transition-colors rounded
                 flex items-center justify-center group"
    >
      <div className="w-12 h-0.5 bg-slate-500 group-hover:bg-white/80 rounded" />
    </div>

    {/* 结果区 */}
    <div className="flex-1 min-h-0 flex flex-col gap-2">
      <div className="flex justify-between items-center">
        <h3 className="text-slate-300 text-sm font-medium">
          {t.database.executor.results}
        </h3>
        {result && result.success && result.result_data && (
          <div className="flex items-center gap-2 text-xs">
            <button
              disabled={page <= 1 || loading}
              onClick={() => handlePageChange(page - 1)}
              className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-slate-300 hover:bg-slate-700 disabled:opacity-50 transition-colors"
            >
              <i className="fas fa-chevron-left"></i>
            </button>
            <span className="text-slate-400 bg-slate-800 border border-slate-700 px-2 py-1 rounded">
              Page {page}
            </span>
            <button
              disabled={(!result.result_data || result.result_data.length < pageSize) || loading}
              onClick={() => handlePageChange(page + 1)}
              className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-slate-300 hover:bg-slate-700 disabled:opacity-50 transition-colors"
            >
              <i className="fas fa-chevron-right"></i>
            </button>
          </div>
        )}
      </div>
      <ResultViewer result={result} />
    </div>
  </div>

  {/* 历史面板 */}
  {showHistoryPanel && (
    <div className="w-80 shrink-0">
      <SQLHistoryPanel
        isOpen={showHistoryPanel}
        onClose={() => setShowHistoryPanel(false)}
        onReuseSql={handleReuseHistory}
      />
    </div>
  )}
</div>
```

**Step 7: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/components/Tools/DatabaseTool/SQLExecutor.test.tsx`

Expected: 5 个测试**全部通过**

**Step 8: TypeScript 类型检查**

Run: `cd frontend && npx tsc --noEmit`

Expected: 0 错误

**Step 9: 浏览器快速验证（手动）**

启动 dev 服务（如未启动）：

Run: `cd /Users/huazhongmin/IdeaProjects/tools && python dev_services.py start`

等待 5 秒后，用 agent-browser 打开 `http://localhost:5178/tools/database-tool`，执行任意 SQL，观察：
- 编辑器和结果区之间出现一条灰色横线
- 鼠标悬停横线变蓝，cursor 变 ns-resize
- 按住往下拖动，编辑器增高，结果区同比缩小
- 刷新页面，高度保持

确认无误后继续 Step 10。

**Step 10: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx \
        frontend/src/components/Tools/DatabaseTool/SQLExecutor.test.tsx
git commit -m "feat(frontend): SQL 执行器增加拖动分隔条 + 高度持久化"
```

---

## Task 3: 全屏覆盖 + 还原 + Esc 键

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx` (加 isFullscreen state)
- Modify: `frontend/src/components/Tools/DatabaseTool/components/SQLEditor.tsx` (加 isFullscreen prop + 标题栏全屏按钮)
- Modify: `frontend/src/components/Tools/DatabaseTool/SQLExecutor.test.tsx` (新增测试用例)

**Step 1: 扩展 SQLEditor 接受 isFullscreen/onToggleFullscreen props**

打开 `frontend/src/components/Tools/DatabaseTool/components/SQLEditor.tsx`，修改 interface（行 6-14）：

```typescript
interface SQLEditorProps {
  value: string;
  onChange: (value: string) => void;
  onExecute: () => void;
  loading?: boolean;
  tables?: TableItem[];
  pageSize?: number;
  onPageSizeChange?: (size: number) => void;
  isFullscreen?: boolean;          // 新增
  onToggleFullscreen?: () => void; // 新增
}
```

修改函数签名（行 16）：

```typescript
const SQLEditor: React.FC<SQLEditorProps> = ({
  value, onChange, onExecute, loading, tables = [],
  pageSize, onPageSizeChange,
  isFullscreen = false,           // 新增
  onToggleFullscreen              // 新增
}) => {
```

**Step 2: 修改 SQLEditor 标题栏（行 71-81）增加全屏按钮**

```tsx
<div className="bg-slate-900 px-4 py-2 border-b border-slate-700 flex justify-between items-center">
  <span className="text-sm font-medium text-slate-300">{t.database.executor.title}</span>
  <div className="space-x-2 flex items-center">
    <button
      onClick={() => onChange('')}
      className="text-xs text-slate-400 hover:text-blue-400 transition-colors"
    >
      {t.database.executor.clear}
    </button>
    <button
      data-testid="fullscreen-toggle"
      onClick={onToggleFullscreen}
      title={isFullscreen
        ? t.database.executor.exitFullscreen
        : t.database.executor.enterFullscreen}
      aria-label={isFullscreen
        ? t.database.executor.exitFullscreen
        : t.database.executor.enterFullscreen}
      className="text-slate-400 hover:text-blue-400 transition-colors"
    >
      <i className={isFullscreen
        ? 'fas fa-compress text-sm'
        : 'fas fa-expand text-sm'} />
    </button>
  </div>
</div>
```

**Step 3: 修改 SQLExecutor 添加 isFullscreen state 和 Esc 监听**

在 SQLExecutor.tsx 顶部 state 段（Task 2 Step 3 处）添加：

```typescript
const [isFullscreen, setIsFullscreen] = useState(false);
```

在 ResizeObserver useEffect 之后新增：

```typescript
// Esc 退出全屏
useEffect(() => {
  if (!isFullscreen) return;
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') setIsFullscreen(false);
  };
  document.addEventListener('keydown', onKey);
  return () => document.removeEventListener('keydown', onKey);
}, [isFullscreen]);
```

**Step 4: 修改 SQLExecutor JSX（外层 + 编辑器包装 + 手柄条件渲染）**

修改左列的 style 和 className：

```tsx
<div
  ref={leftColumnRef}
  className={`flex flex-col gap-4 min-w-0 ${isDragging ? 'select-none' : ''}`}
  style={isFullscreen ? { flex: '1 1 100%' } : { flex: '1 1 0%' }}
>
```

修改编辑器包装 div：

```tsx
<div
  data-testid="editor-wrapper"
  className={
    isFullscreen
      ? 'h-full'
      : editorHeight === null
        ? 'h-1/3 min-h-[200px]'
        : 'shrink-0'
  }
  style={
    !isFullscreen && editorHeight !== null
      ? { height: `${editorHeight}px` }
      : undefined
  }
>
  <SQLEditor
    value={sql}
    onChange={handleSqlChange}
    onExecute={handleExecute}
    loading={loading}
    tables={tables}
    isFullscreen={isFullscreen}
    onToggleFullscreen={() => setIsFullscreen(prev => !prev)}
  />
</div>
```

用条件渲染包裹拖动手柄：

```tsx
{!isFullscreen && (
  <div
    data-testid="drag-handle"
    role="separator"
    aria-orientation="horizontal"
    aria-label={t.database.executor.dragHandleHint}
    onMouseDown={handleDragStart}
    className="h-1.5 bg-slate-700 hover:bg-blue-500 active:bg-blue-400
               cursor-ns-resize transition-colors rounded
               flex items-center justify-center group"
  >
    <div className="w-12 h-0.5 bg-slate-500 group-hover:bg-white/80 rounded" />
  </div>
)}
```

用条件渲染包裹结果区：

```tsx
{!isFullscreen && (
  <div className="flex-1 min-h-0 flex flex-col gap-2">
    {/* ...完整结果区代码保持不变... */}
  </div>
)}
```

**Step 5: 写新测试用例**

在 `SQLExecutor.test.tsx` 末尾追加（注意导入要加 `userEvent` 替代复杂事件）：

```tsx
import userEvent from '@testing-library/user-event';

// ... 现有 describe('SQLExecutor 拖动 + 持久化', ...) 保持不变

describe('SQLExecutor 全屏', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('点击全屏按钮后结果区不渲染', async () => {
    const user = userEvent.setup();
    const { container, queryByText } = render(
      <SQLExecutor configId="cfg-1" database="" schema="" sql="SELECT 1" onStateChange={() => {}} />
    );
    // 确认结果区标题存在
    expect(queryByText('执行结果')).toBeTruthy();

    // 点击全屏按钮
    const fsBtn = container.querySelector('[data-testid="fullscreen-toggle"]') as HTMLElement;
    await user.click(fsBtn);

    // 结果区应消失
    expect(queryByText('执行结果')).toBeNull();
  });

  it('再次点击全屏按钮恢复结果区', async () => {
    const user = userEvent.setup();
    const { container, queryByText } = render(
      <SQLExecutor configId="cfg-1" database="" schema="" sql="SELECT 1" onStateChange={() => {}} />
    );
    const fsBtn = container.querySelector('[data-testid="fullscreen-toggle"]') as HTMLElement;

    await user.click(fsBtn);
    expect(queryByText('执行结果')).toBeNull();

    await user.click(fsBtn);
    expect(queryByText('执行结果')).toBeTruthy();
  });

  it('全屏状态下按 Esc 恢复', async () => {
    const user = userEvent.setup();
    const { container, queryByText } = render(
      <SQLExecutor configId="cfg-1" database="" schema="" sql="SELECT 1" onStateChange={() => {}} />
    );
    const fsBtn = container.querySelector('[data-testid="fullscreen-toggle"]') as HTMLElement;

    await user.click(fsBtn);
    expect(queryByText('执行结果')).toBeNull();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(queryByText('执行结果')).toBeTruthy();
  });

  it('全屏状态下拖动手柄不渲染', async () => {
    const user = userEvent.setup();
    const { container, queryByTestId } = render(
      <SQLExecutor configId="cfg-1" database="" schema="" sql="SELECT 1" onStateChange={() => {}} />
    );
    expect(queryByTestId('drag-handle')).toBeTruthy();

    const fsBtn = container.querySelector('[data-testid="fullscreen-toggle"]') as HTMLElement;
    await user.click(fsBtn);

    expect(queryByTestId('drag-handle')).toBeNull();
  });
});
```

**Step 6: 运行全部测试**

Run: `cd frontend && npx vitest run src/components/Tools/DatabaseTool/`

Expected: 所有测试通过（Task 1 的 2 个 + Task 2 的 5 个 + Task 3 的 4 个 = 11 个）

**Step 7: TypeScript 类型检查**

Run: `cd frontend && npx tsc --noEmit`

Expected: 0 错误

**Step 8: 浏览器手动验证**

用 agent-browser 操作：
1. 进入 `http://localhost:5178/tools/database-tool`
2. 点击连接 + 数据库 + 双击表让编辑器有内容
3. 点击标题栏的"⛶ 全屏"按钮 → 结果区应消失，编辑器占满
4. 按 Esc 键 → 结果区应恢复
5. 点击标题栏的"⛶" → 全屏；点击"⤢ 还原" → 恢复
6. console 面板应无 error

**Step 9: 提交**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx \
        frontend/src/components/Tools/DatabaseTool/components/SQLEditor.tsx \
        frontend/src/components/Tools/DatabaseTool/SQLExecutor.test.tsx
git commit -m "feat(frontend): SQL 执行器增加全屏覆盖模式 + Esc 键退出"
```

---

## Task 4: 完整 E2E 浏览器验证 + 截图记录

**Files:** 无（仅验证 + 文档）

**Step 1: 重启 dev 服务确保加载最新代码**

Run: `cd /Users/huazhongmin/IdeaProjects/tools && python dev_services.py restart`

等待 8 秒直到日志显示 "Frontend: ready"。

**Step 2: 浏览器自动化测试 1 - 拖动 + 持久化**

使用 agent-browser 工具：

```bash
agent-browser navigate http://localhost:5178/tools/database-tool
```

登录（如未登录）：用 peanut 账户

执行任意 SQL 让编辑器加载：

```bash
agent-browser execute "window.monaco?.editor?.getEditors?.()[0]?.setValue('SELECT 1')"
```

截图初始状态：

```bash
agent-browser screenshot /tmp/e2e-1-initial.png
```

执行 SQL 拿到结果：

```bash
agent-browser execute "Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === '执行')?.click()"
```

等待 2 秒后截图：

```bash
agent-browser sleep 2
agent-browser screenshot /tmp/e2e-2-with-results.png
```

模拟拖动手柄向下 200px：

```bash
agent-browser execute "
  const handle = document.querySelector('[data-testid=\"drag-handle\"]');
  const rect = handle.getBoundingClientRect();
  const startY = rect.top + rect.height / 2;
  handle.dispatchEvent(new MouseEvent('mousedown', { clientY: startY, bubbles: true }));
  document.dispatchEvent(new MouseEvent('mousemove', { clientY: startY + 200, bubbles: true }));
  document.dispatchEvent(new MouseEvent('mouseup', { clientY: startY + 200, bubbles: true }));
"
```

截图拖动后状态：

```bash
agent-browser screenshot /tmp/e2e-3-after-drag.png
```

验证 localStorage 写入：

```bash
agent-browser execute "localStorage.getItem('db-tool:sqlEditorHeight')"
```

Expected: 一个大于 200 的数字字符串

**Step 3: 浏览器自动化测试 2 - 全屏 + Esc**

点击全屏按钮：

```bash
agent-browser execute "document.querySelector('[data-testid=\"fullscreen-toggle\"]').click()"
agent-browser sleep 1
agent-browser screenshot /tmp/e2e-4-fullscreen.png
```

验证结果区不渲染：

```bash
agent-browser execute "!!document.querySelector('h3')?.textContent?.includes('执行结果')"
```

Expected: `false`

按 Esc 退出：

```bash
agent-browser execute "document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))"
agent-browser sleep 1
agent-browser screenshot /tmp/e2e-5-after-esc.png
```

验证结果区恢复：

```bash
agent-browser execute "!!document.querySelector('h3')?.textContent?.includes('执行结果')"
```

Expected: `true`

**Step 4: 浏览器自动化测试 3 - 按钮文案**

执行 SQL 让按钮进入 loading：

```bash
agent-browser execute "Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === '执行')?.click()"
agent-browser sleep 0.3
agent-browser screenshot /tmp/e2e-6-loading.png
```

执行完后验证文案：

```bash
agent-browser execute "Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('执行中'))?.textContent"
```

Expected: `"⟳ 执行中..."` 或 `"执行中..."`

等待完成后再截一张：

```bash
agent-browser sleep 3
agent-browser screenshot /tmp/e2e-7-completed.png
```

**Step 5: 检查 console 错误**

```bash
agent-browser console
```

Expected: 无 error 级别日志（warning 允许）

**Step 6: 持久化最终验证**

刷新页面：

```bash
agent-browser navigate http://localhost:5178/tools/database-tool
agent-browser sleep 2
```

验证编辑器高度恢复（localStorage 中的值）：

```bash
agent-browser execute "document.querySelector('[data-testid=\"editor-wrapper\"]')?.getAttribute('style')"
```

Expected: 包含 `height: {之前拖动保存的数值}px`

截图：

```bash
agent-browser screenshot /tmp/e2e-8-after-reload.png
```

**Step 7: 提交（无代码变更，仅日志）**

如果发现 bug，修复后单开 commit。如果一切正常，E2E 截图归档：

```bash
mkdir -p /Users/huazhongmin/IdeaProjects/tools/docs/superpowers/e2e-evidence/2026-06-05-sql-executor
cp /tmp/e2e-*.png /Users/huazhongmin/IdeaProjects/tools/docs/superpowers/e2e-evidence/2026-06-05-sql-executor/
cd /Users/huazhongmin/IdeaProjects/tools
git add docs/superpowers/e2e-evidence/2026-06-05-sql-executor/
git commit -m "docs: SQL 执行器 E2E 验证截图（拖动/全屏/Esc/持久化）"
```

---

## 完成清单

- [ ] Task 1: i18n + 文案修复（2 个单元测试通过）
- [ ] Task 2: 拖动 + 持久化（5 个单元测试通过 + 浏览器手动验证）
- [ ] Task 3: 全屏 + Esc（4 个单元测试通过 + 浏览器手动验证）
- [ ] Task 4: E2E 自动化验证（8 张截图 + console 清洁）
- [ ] 4 个 commit 全部成功
- [ ] 用户最终审查

---

## 风险与回滚

每个 Task 独立 commit，回滚命令：

```bash
# 回滚 Task 3
git revert <task-3-commit-sha>

# 回滚 Task 2
git revert <task-3-commit-sha> <task-2-commit-sha>

# 强制重置到 Task 1
git reset --hard <task-1-commit-sha>
```

---

**Plan 完成。** 等用户选择执行方式：
1. **Subagent-Driven**（当前会话，分派子代理逐 Task 实施 + review）
2. **Parallel Session**（新会话批量执行）
