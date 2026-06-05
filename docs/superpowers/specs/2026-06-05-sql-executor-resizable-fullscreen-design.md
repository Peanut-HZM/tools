# 数据库工具 SQL 执行器 - 可拖动高度 + 全屏覆盖 设计

**日期**: 2026-06-05
**状态**: Draft → Pending Review
**类型**: 功能增强
**影响范围**: 前端 `SQLExecutor` + `SQLEditor` 组件

---

## 1. 需求背景

用户在 `http://localhost:5178/tools/database-tool` 页面使用 SQL 执行器时遇到两个体验问题：

1. **写长 SQL 时编辑器区域太小**：当前 SQLEditor 固定为父列高度的 1/3 (`h-1/3`)，写复杂查询时无法看到更多代码
2. **执行结果抢占屏幕**：当前结果区默认与编辑器平分空间，查询返回大量数据时挤占编辑区
3. **按钮文案错误**：执行中按钮显示"测试中..."而非"执行中..."，与功能语义不符

### 期望行为
- SQL 编辑器和结果区之间出现**可拖动分隔条**，用户可上下拖动调整两者比例
- SQL 编辑器标题栏增加"全屏"按钮，点击后**编辑器撑满左列，结果区完全隐藏**
- 全屏状态下再次点击"还原"按钮或按 `Esc` 键，恢复原布局
- 执行按钮在 `loading=true` 时文案从"测试中..."改为"执行中..."

---

## 2. 现状分析

### 2.1 当前布局（SQLExecutor.tsx:287-325）
```tsx
<div className="flex flex-1 gap-4 overflow-hidden">         // 父容器
  <div className="flex flex-col gap-4 ...">                // 左列
    <div className="h-1/3 min-h-[200px]">                  // ← 编辑器（固定 1/3）
      <SQLEditor ... />
    </div>
    <div className="flex-1 min-h-0 flex flex-col gap-2">   // ← 结果区（占剩余 2/3）
      <div>...results header + pagination...</div>
      <ResultViewer result={result} />
    </div>
  </div>
  {showHistoryPanel && <SQLHistoryPanel .../>}             // 右：历史
</div>
```

### 2.2 按钮文案 bug（SQLEditor.tsx:119）
```tsx
{loading ? t.database.status.testing : t.database.executor.run}
//                  ↑ 错误引用                      ↑ 正确应该是 executor.executing
```
`zh-CN.ts:342` 定义 `status.testing: '测试中...'`（实际用于"连接测试"），而 `zh-CN.ts:350` 已存在 `executor.executing: '执行中...'`，代码未正确引用。

### 2.3 i18n 现状
| key | zh-CN | en-US | 实际使用 |
|---|---|---|---|
| `database.executor.run` | 执行 | Run | ✓ 静态按钮文案 |
| `database.executor.executing` | 执行中... | Executing... | ✗ 已定义未用 |
| `database.status.testing` | 测试中... | Testing... | ⚠ 误用为执行按钮 loading 态 |
| `database.status.connected` | 已连接 | Connected | ✓ 连接状态 |

---

## 3. 目标

| # | 目标 | 验收标准 |
|---|---|---|
| G1 | 编辑器与结果区可拖动 | 鼠标按住分隔条向下拖动时，编辑器增高、结果区同比缩小 |
| G2 | 拖动边界 | 最小 200px，最大父列高度 90% |
| G3 | 高度持久化 | 拖动后高度写入 `localStorage`；下次进入页面自动恢复 |
| G4 | 全屏覆盖 | 点击"全屏"按钮 → 编辑器占满左列 100%，结果区消失；右侧历史面板不受影响 |
| G5 | 还原机制 | 全屏状态下点击"还原"按钮 / 按 `Esc` 键 → 恢复拖动后的高度 |
| G6 | 按钮文案修复 | loading 时按钮显示"执行中..."，不是"测试中..." |
| G7 | 不破坏现有功能 | 执行、分页、结果渲染、SQL 补全、Ctrl+Enter 执行、Loading 态、历史面板全部保留 |
| G8 | 国际化完整 | zh-CN 和 en-US 都有 `executor.executing` 和全屏相关 key |

---

## 4. 设计方案

### 4.1 架构概览

**实现方式**：纯 React 状态 + 自定义鼠标事件（**方案 1**，零新依赖）

新增文件：无  
修改文件：
- `frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx`（主改动）
- `frontend/src/components/Tools/DatabaseTool/components/SQLEditor.tsx`（标题栏加全屏按钮 + 修复按钮文案）
- `frontend/src/i18n/locales/zh-CN.ts`（新增全屏相关 key）
- `frontend/src/i18n/locales/en-US.ts`（新增全屏相关 key）

### 4.2 状态管理（SQLExecutor.tsx 顶层）

```typescript
const MIN_EDITOR_H = 200;
const MAX_EDITOR_RATIO = 0.9;
const STORAGE_KEY = 'db-tool:sqlEditorHeight';

// editorHeight: null = 首次加载（用 1/3 默认）；number = 用户拖动后保存值
const [editorHeight, setEditorHeight] = useState<number | null>(null);
const [isDragging, setIsDragging] = useState(false);
const [isFullscreen, setIsFullscreen] = useState(false);
// columnHeight: 用 ResizeObserver 监听左列实时高度，用于 max 约束
const [columnHeight, setColumnHeight] = useState(0);
```

### 4.3 UI 结构（修改后）

```tsx
<div className="flex flex-1 gap-4 overflow-hidden">
  {/* 左列：拖动状态时禁用 transition 避免抖动 */}
  <div
    ref={leftColumnRef}
    className={`flex flex-col gap-4 min-w-0 ${isDragging ? 'select-none' : ''}`}
    style={isFullscreen ? { flex: '1 1 100%' } : { flex: '1 1 0%' }}
  >
    {/* 编辑器：editorHeight 为 null 时使用 CSS 1/3 默认（与原始 SQLExecutor 行为一致） */}
    <div
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

    {/* 拖动手柄：仅非全屏时显示 */}
    {!isFullscreen && (
      <div
        role="separator"
        aria-orientation="horizontal"
        aria-label="拖动调整编辑器高度"
        aria-valuenow={editorHeight ?? 0}
        aria-valuemin={MIN_EDITOR_H}
        aria-valuemax={Math.floor(columnHeight * MAX_EDITOR_RATIO)}
        onMouseDown={handleDragStart}
        className="h-1.5 bg-slate-700 hover:bg-blue-500 active:bg-blue-400
                   cursor-ns-resize transition-colors rounded
                   flex items-center justify-center group"
      >
        <div className="w-12 h-0.5 bg-slate-500 group-hover:bg-white/80 rounded" />
      </div>
    )}

    {/* 结果区：仅非全屏时显示 */}
    {!isFullscreen && (
      <div className="flex-1 min-h-0 flex flex-col gap-2">
        <div className="flex justify-between items-center">
          <h3 className="text-slate-300 text-sm font-medium">
            {t.database.executor.results}
          </h3>
          {/* 分页按钮保持不变 */}
        </div>
        <ResultViewer result={result} />
      </div>
    )}
  </div>

  {/* 历史面板：不受全屏影响 */}
  {showHistoryPanel && <SQLHistoryPanel .../>}
</div>
```

### 4.4 SQLEditor.tsx 改动

**4.4.1 新增 Props**
```typescript
interface SQLEditorProps {
  value: string;
  onChange: (value: string) => void;
  onExecute: () => void;
  loading?: boolean;
  tables?: TableItem[];
  isFullscreen?: boolean;          // 新增
  onToggleFullscreen?: () => void; // 新增
}
```

**4.4.2 标题栏增加全屏按钮（行 71-81 区域）**
```tsx
<div className="bg-slate-900 px-4 py-2 border-b border-slate-700 flex justify-between items-center">
  <span className="text-sm font-medium text-slate-300">
    {t.database.executor.title}
  </span>
  <div className="space-x-2 flex items-center">
    <button
      onClick={() => onChange('')}
      className="text-xs text-slate-400 hover:text-blue-400 transition-colors"
    >
      {t.database.executor.clear}
    </button>
    <button
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

**4.4.3 修复按钮文案（行 119）**
```diff
- {loading ? t.database.status.testing : t.database.executor.run}
+ {loading ? t.database.executor.executing : t.database.executor.run}
```

### 4.5 关键逻辑实现

**4.5.1 拖动开始（mousedown）**
```typescript
const handleDragStart = useCallback((e: React.MouseEvent) => {
  e.preventDefault();
  setIsDragging(true);

  const startY = e.clientY;
  const startH = editorHeight ?? MIN_EDITOR_H;
  // max 优先用 columnHeight（ResizeObserver 实时值），fallback 到 ref 实时测量
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
    // 用 rAF 合并频繁 setState
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

**4.5.2 高度持久化**
```typescript
useEffect(() => {
  if (editorHeight !== null) {
    try {
      localStorage.setItem(STORAGE_KEY, String(editorHeight));
    } catch (e) {
      console.error('Failed to save editor height:', e);
    }
  }
}, [editorHeight]);

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
```

**4.5.3 Esc 退出全屏**
```typescript
useEffect(() => {
  if (!isFullscreen) return;
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') setIsFullscreen(false);
  };
  document.addEventListener('keydown', onKey);
  return () => document.removeEventListener('keydown', onKey);
}, [isFullscreen]);
```

**4.5.4 父列高度监听（ResizeObserver）**
```typescript
const leftColumnRef = useRef<HTMLDivElement>(null);

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

// 注意：columnHeight 首次回调可能在用户开始拖动之后才到达。
// 因此 4.5.1 中同时 fallback 到 ref.getBoundingClientRect() 实时测量。
```

**4.5.5 首次加载时回退到 1/3 默认**
```typescript
// 模板（见 4.3 节）：
//   editorHeight === null → className='h-1/3 min-h-[200px]' 触发 CSS 1/3 布局
//   editorHeight !== null → inline style='height: {n}px' 覆盖
// 切换数据库/连接不重置高度（除非 localStorage 主动清除）
```

### 4.6 i18n 新增 key

**zh-CN.ts（database.executor 段）**
```typescript
executor: {
  title: 'SQL 执行器',
  run: '执行',
  executing: '执行中...',
  stop: '停止',
  clear: '清空',
  history: '执行历史',
  results: '执行结果',
  noResults: '无结果',
  affectedRows: '受影响行数：{count}',
  duration: '耗时：{time}ms',
  placeholder: '请输入 SQL 语句...',
  copyInsert: '复制 INSERT',
  // 新增 ↓
  enterFullscreen: '全屏',
  exitFullscreen: '退出全屏',
  dragHandleHint: '拖动调整编辑器高度',
}
```

**en-US.ts（同位置）**
```typescript
executor: {
  title: 'SQL Executor',
  run: 'Run',
  executing: 'Executing...',
  stop: 'Stop',
  clear: 'Clear',
  history: 'Execution History',
  results: 'Results',
  noResults: 'No results',
  affectedRows: 'Affected rows: {count}',
  duration: 'Duration: {time}ms',
  placeholder: 'Enter SQL statement...',
  copyInsert: 'Copy INSERT',
  // 新增 ↓
  enterFullscreen: 'Fullscreen',
  exitFullscreen: 'Exit Fullscreen',
  dragHandleHint: 'Drag to resize editor',
}
```

---

## 5. 数据流与状态机

### 5.1 状态机
```
       ┌────────────────────────────────────┐
       │            Normal                  │
       │  editorHeight: null | number       │
       │  isFullscreen: false               │
       │  isDragging: false                 │
       └──┬───────────────┬──────────────┬──┘
          │               │              │
   mousedown       click expand     (no-op)
   on handle        button              │
          │               │              │
          ▼               ▼              │
   ┌─────────────┐  ┌──────────────┐    │
   │  Dragging   │  │ Fullscreen   │    │
   │ nextHeight  │  │ editorHeight │    │
   │ updates via │  │ frozen       │    │
   │ rAF         │  │              │    │
   └──────┬──────┘  └──┬──────┬────┘    │
          │ mouseup    │      │ Esc      │
          │            │      │ click    │
          ▼            │      ▼ compress│
       Normal ◄────────┴─ Normal          │
                              ▲            │
                              └────────────┘
```

### 5.2 localStorage 交互
| 触发 | 读取 | 写入 |
|---|---|---|
| 组件 mount | `STORAGE_KEY` → 解析数字 → `setEditorHeight(n)` | — |
| `editorHeight` 变化 | — | `STORAGE_KEY` ← String(editorHeight) |
| 全屏切换 | — | — |
| 拖动 mouseup | — | 写入最终高度 |

### 5.3 边界保护
- **min-h = 200px**：与现有 `min-h-[200px]` 保持一致
- **max-h = 90% 父列**：保证结果区最少 10%（防止挤没）
- **localStorage 异常**：try/catch；解析失败时使用 `null`（回退到 1/3 默认）
- **拖动中切换全屏**：不允许；`isDragging` 时全屏按钮仍可点但不响应（实际未禁用，因为 setIsFullscreen 不依赖 editorHeight，但视觉上拖动中点全屏是 OK 的，仅停止拖动；为简化不做限制）

---

## 6. UI 示意

### 6.1 Normal 状态
```
┌──────────────────────────────────────────────┐
│ [连接▾] [数据库▾] [Schema▾]            [历史]│
├──────────────────────────────────────────────┤
│ SQL 执行器  [清空] [⛶全屏]                    │ ← 标题栏新增全屏按钮
│ ┌──────────────────────────────────────────┐ │
│ │  SELECT * FROM ...                       │ │ ← 可拖动区域
│ │  ...                                     │ │
│ └──────────────────────────────────────────┘ │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │ ← 拖动手柄（4-6px）
│ 执行结果              [← Page 1 →]            │
│ ┌──────────────────────────────────────────┐ │
│ │  id │ name │ created_at                 │ │
│ │   1 │ ...  │ ...                        │ │
│ └──────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

### 6.2 Fullscreen 状态
```
┌──────────────────────────────────────────────┐
│ [连接▾] [数据库▾] [Schema▾]            [历史]│
├──────────────────────────────────────────────┤
│ SQL 执行器  [清空] [⤢退出全屏]                 │
│ ┌──────────────────────────────────────────┐ │
│ │                                          │ │
│ │  SELECT * FROM ...                       │ │
│ │  ...                                     │ │
│ │  （编辑器占满左列 100%）                 │ │
│ │                                          │ │
│ │                                          │ │
│ │  [执行] 或 [⟳ 执行中...]                  │ │
│ └──────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
（结果区完全不渲染；历史面板不受影响）
```

---

## 7. 测试策略

### 7.1 单元测试（SQLExecutor.test.tsx）

| # | 用例 | 断言 |
|---|---|---|
| 1 | 首次加载无 localStorage | `editorHeight` 为 null，外层 div 包含 `h-1/3` class |
| 2 | 首次加载有 localStorage | `editorHeight` 等于存储值，外层 div 使用 inline `style="height: {n}px"` |
| 3 | localStorage 异常 | 捕获后 fallback 到 null |
| 4 | 拖动 mouseup | `localStorage.getItem('db-tool:sqlEditorHeight')` 等于最终高度 |
| 5 | 拖动低于 min | 高度 clamp 到 200px |
| 6 | 拖动超过 max | 高度 clamp 到 columnHeight * 0.9 |
| 7 | 点击全屏 | `isFullscreen=true`，结果区不再渲染（queryByText('执行结果') 返回 null） |
| 8 | 再次点击全屏 | `isFullscreen=false`，结果区恢复 |
| 9 | 全屏中按 Esc | `isFullscreen=false` |
| 10 | 按钮文案 loading | `screen.getByText(/执行中/)` 存在；`queryByText(/测试中/)` 不存在 |

### 7.2 集成测试
- 真实浏览器：拖动 → 高度变化 → 刷新 → 高度保持
- 真实浏览器：全屏 → 执行查询 → 验证结果在退出全屏后正常显示
- 真实浏览器：按钮文案：执行中 vs 静态 "执行"

### 7.3 回归测试
- 现有执行功能（SQL 补全、Ctrl+Enter、Shift+Enter、分页）全部保留
- 历史面板开关/复用 SQL 流程不受影响
- `useEffect(() => setResult(null), [configId])` 切换连接时行为不变
- localStorage 写异常时不崩溃

---

## 8. 风险与限制

| 风险 | 缓解 |
|---|---|
| 拖动频繁 setState 导致性能问题 | 用 `requestAnimationFrame` 合并 mousemove 事件 |
| `localStorage` 在隐私模式/异常时抛错 | try/catch 包裹所有读写 |
| 父列高度在 ResizeObserver 首次回调前为 0 | max 约束只在 columnHeight > 0 时生效；初始拖动用编辑器当前 height 作上限 |
| 拖动中切换全屏 | 拖动停止后 setEditorHeight 才最终确定；切换时直接冻结当前 height |
| Monaco 编辑器在极端高度（<100px）下崩溃 | min 200px 已保证；用户仍可改小（仅在父列允许范围内）|
| Esc 在 input/textarea 中有原生行为 | Esc 监听绑在 `document`，全屏时拦截；若 input 中有原生 Esc（如 Monaco 的补全关闭），会先关闭补全再退出全屏（可接受） |

---

## 9. 实施拆分

按"Subagent-Driven Development"流程：

**任务 1：核心拖动 + 持久化**（独立可测）  
- SQLExecutor 加 editorHeight / isDragging state
- 拖动手柄 + mousedown/move/up 逻辑
- 持久化 useEffect
- 单元测试 1-6

**任务 2：全屏覆盖**（依赖任务 1）  
- isFullscreen state + 全屏按钮（SQLEditor 标题栏）
- 全屏时隐藏手柄和结果区
- Esc 键监听
- 单元测试 7-9

**任务 3：按钮文案修复 + i18n**（独立）  
- SQLEditor.tsx:119 一行修复
- zh-CN.ts + en-US.ts 新增 enterFullscreen / exitFullscreen / dragHandleHint
- 单元测试 10

**任务 4：浏览器端到端验证**  
- agent-browser 实际操作
- 截图证明拖动、全屏、Esc、文案全部生效
- console 无 error

---

## 10. 不在范围

- ❌ Monaco 编辑器自身的全屏（与浏览器 F11 冲突，跳过）
- ❌ SQL 编辑器和历史面板的左右拖动（仅上下）
- ❌ 多 Tab/多 SQL 编辑器（MVP 不需要）
- ❌ 编辑器高度预设按钮（如"50/50"、"70/30"快捷切换，未来可加）
- ❌ 全屏时把整个页面（包左侧导航）也覆盖（仅覆盖 SQLExecutor 内部左列）

---

**Spec 完成。请审查后转 writing-plans。**
