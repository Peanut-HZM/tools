# 数据库工具 ColumnSelector 复选框失效 Bug 修复设计

**日期**: 2026-06-04
**状态**: Draft → Approved
**类型**: Bug 修复
**影响范围**: 前端 `ResultViewer` 组件的列可见性管理

---

## 问题描述

用户反馈：在 `http://localhost:5178/tools/database-tool` 数据库工具页面，打开表数据视图后，点击工具栏的"列"按钮（fa-columns 图标，位置在删除按钮左侧）弹出的下拉框里，复选框**无法选择**。

期望行为：勾选/取消勾选列名时，下拉框中的勾选状态、表格中实际显示的列、以及 `1 / 20` 计数都应该**实时同步更新**。

实际行为：点击下拉框中的行或复选框都没有反应，勾选状态不变，表格列也不变。

### 复现步骤
1. 登录 `peanut` 账户
2. 进入 `glodon-hr-dev` 连接
3. 展开 `ehr_onbserviice_dev` → `Tables` → 双击任意有数据的表（如 `gen_table`）
4. 点击工具栏的"列"按钮
5. 尝试点击下拉框中的任一列行或复选框
6. **观察**：勾选状态不变，表格列也不变

---

## 根因分析

### 全链路

| 层级 | 文件 | 行号 | 状态 |
|---|---|---|---|
| ColumnSelector 组件 | `ColumnSelector.tsx` | 71-79 | ✅ `handleToggleColumn` 正确调用 `onColumnChange` |
| ColumnSelector 组件 | `ColumnSelector.tsx` | 133 | ✅ 行 `onClick` 正确触发 toggle |
| ColumnSelector 组件 | `ColumnSelector.tsx` | 138 | ⚠️ input 的 `onChange` 是空函数，但被 `pointer-events-none` 屏蔽 |
| **ResultViewer 状态管理** | `ResultViewer.tsx` | 411-425 | ❌ **bug：`visibleColumns` 是 const 派生值，`handleColumnChange` 只写 localStorage 不 setState** |
| 表格渲染 | `ResultViewer.tsx` | 606, 651, 683 | ⚠️ 依赖 `visibleColumns`，但因上游未更新所以不刷新 |

### 根因详解

`ResultViewer.tsx` 第 400-425 行：

```tsx
// 列显示管理：从 localStorage 加载并过滤
const getStoredColumns = () => {
  if (!storageKey) return [];
  try {
    const saved = localStorage.getItem(storageKey);
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
};

const storedCols = getStoredColumns();
// 过滤掉当前表不存在的列
const displayColumns = storedCols.filter((col: string) => columns.includes(col));
// 如果存储的列全部无效，则显示所有列
const visibleColumns = displayColumns.length > 0 ? displayColumns : columns;

const handleColumnChange = (cols: string[]) => {
  if (storageKey) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(cols));
    } catch (e) {
      console.error('Failed to save column visibility:', e);
    }
  }
};
```

**问题**：
1. `visibleColumns` 是**普通 const 派生值**，每次 render 都从 localStorage 重新读取。
2. `handleColumnChange` **只写 localStorage**，**没有调用任何 setState**。
3. 当用户点击列复选框 → `onColumnChange(newCols)` 被调用 → localStorage 被写入 → 但 React 不知道有变化 → 不会重渲染。
4. 结果：
   - `ColumnSelector` 收到的 `visibleColumns` props 没变 → 复选框视觉状态不变
   - 表格的 `visibleColumns.map((col) => ...)` 用的还是旧值 → 列不变化

### 为什么这是一个 React 状态管理错误

- 列可见性本质是 **UI 状态**（影响渲染），必须用 `useState` 驱动。
- localStorage 是 **持久化层**，应当是 setState 的"副作用"，不是状态的"来源"。
- 之前的写法相当于"localStorage 是状态"，违反了 React 单向数据流。

### 次要问题

`ColumnSelector.tsx` 第 138 行：

```tsx
<input
  type="checkbox"
  checked={isSelected}
  onChange={() => {}}  // 空函数
  className="... pointer-events-none"  // 阻止点击
/>
```

- 这是**设计性选择**而非 bug：通过 `pointer-events-none` 阻止直接点击 checkbox，全部通过行 `onClick` 触发。
- 行 `onClick` 调用 `handleToggleColumn`，逻辑正确。
- 因此 `ColumnSelector` 内部不需要修改。

---

## 修复方案

### 方案 A：用 useState 替换 const 派生值 ✅ 推荐

**核心改动**：
1. 把 `visibleColumns` 改为 `useState<string[]>(...)`，用懒初始化从 localStorage 读取
2. `handleColumnChange` 调用 `setVisibleColumns(cols)` + 写 localStorage
3. 添加 `useEffect`：当 `result`（或 `storageKey`）变化时，重新从 localStorage 同步 state

**优点**：
- 最小改动，仅修改 `ResultViewer.tsx`
- 符合 React 单向数据流
- 与现有 `selectedIndices` / `cellEdits` / `newRows` 等 useState 模式一致
- 性能好，无 force re-render

**缺点**：
- 需要小心 `useEffect` 依赖：必须基于 `storageKey` 或 `result` 触发，不能每次 render 都重新同步

### 方案 B：forceUpdate 强制重渲染

```tsx
const [, forceUpdate] = useReducer(x => x + 1, 0);
const handleColumnChange = (cols: string[]) => {
  if (storageKey) localStorage.setItem(storageKey, JSON.stringify(cols));
  forceUpdate();
};
```

**优点**：改动最小。
**缺点**：反模式，每次 toggle 都重渲染整个组件树，性能差。

### 方案 C：把状态移入 ColumnSelector

让 `ColumnSelector` 自己管理 `visibleColumns` state。

**优点**：职责清晰。
**缺点**：表格和 dropdown 都需要这个状态，需要状态提升或 Context，又回到方案 A。

### 推荐方案 A

理由：与现有代码模式一致，改动局部、可控、性能良好。

---

## 详细设计

### 文件变更清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx` | 修改 | 列可见性改为 useState 管理 |

**`ColumnSelector.tsx` 不修改**（已经正确处理 props）。

### 状态管理设计

```tsx
// 初始值：懒初始化，从 localStorage 读取并过滤无效列
const [visibleColumns, setVisibleColumns] = useState<string[]>(() => {
  if (!storageKey) return columns;
  try {
    const saved = localStorage.getItem(storageKey);
    if (!saved) return columns;
    const parsed: string[] = JSON.parse(saved);
    // 过滤掉已不存在的列
    const filtered = parsed.filter((col) => columns.includes(col));
    return filtered.length > 0 ? filtered : columns;
  } catch {
    return columns;
  }
});

// 当 result/columns 变化时（如切换表），重新从 localStorage 加载
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
    const filtered = parsed.filter((col) => columns.includes(col));
    setVisibleColumns(filtered.length > 0 ? filtered : columns);
  } catch {
    setVisibleColumns(columns);
  }
}, [storageKey, columns]);

const handleColumnChange = (cols: string[]) => {
  // 1. 立即更新 React state，触发重渲染
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

### 数据流

```
用户点击复选框 / 行
    ↓
ColumnSelector.handleToggleColumn(col)
    ↓ 校验 (至少 1 列约束保留)
ColumnSelector 调 onColumnChange(newCols)
    ↓
ResultViewer.handleColumnChange(newCols)
    ├─ setVisibleColumns(newCols)  ← 关键：触发 React 重渲染
    └─ localStorage.setItem(...)    ← 持久化
    ↓
React 重渲染：
    ├─ ColumnSelector 收到新 visibleColumns props → 复选框视觉更新
    └─ 表格 visibleColumns.map(...) 重新执行 → 列变化
```

### 错误处理

| 场景 | 行为 |
|---|---|
| `localStorage` 读取失败 | catch 块返回 `columns`（全部显示） |
| `localStorage` 写入失败 | `console.error`，UI 仍正常更新（state 已 set） |
| `storageKey` 为 null（无 tableName） | 跳过持久化，只用内存 state |
| `JSON.parse` 失败 | catch 块返回 `columns` |
| 存储的列全部无效（如切换表结构） | 过滤后 `filtered.length === 0`，回退到 `columns` |

### 边界情况

1. **首次打开新表**：`localStorage` 无记录 → 默认显示所有列
2. **切换表**：`storageKey` 变化 → `useEffect` 触发 → 重新加载对应 localStorage
3. **同表刷新**：`storageKey` 不变 → `useEffect` 不触发（依赖未变） → state 保持
4. **取消勾选最后一个列**：`ColumnSelector.handleToggleColumn` 已有 `if (visibleColumns.length === 1) return` 守卫，**至少 1 列约束保留**

### 不需要修改的地方

- `ColumnSelector.tsx`（props 接口、handleToggleColumn、handleToggleAll 不变）
- 后端 API
- i18n 文件
- localStorage key 格式（保持兼容）

---

## 测试要点

### 单元测试（手动验证即可，无需新加测试框架）

- [ ] 打开表 → 默认所有列都显示
- [ ] 打开列 dropdown → 默认所有复选框都勾选
- [ ] 取消勾选某列 → dropdown 中该复选框立即取消勾选，表格立即少一列
- [ ] 全选 checkbox 点击 → 切到 1 列时保留一列
- [ ] 关闭 tab 再打开同表 → 列可见性保持
- [ ] 切换到另一个表 → 列可见性独立（按 storageKey 隔离）
- [ ] 浏览器刷新页面 → 列可见性保持（localStorage 持久化）

### 集成验证

- [ ] TypeScript 类型检查通过
- [ ] Vite 构建成功
- [ ] 浏览器实际操作：勾选/取消勾选/全选/关闭再打开，行为符合预期
- [ ] 浏览器 console 无错误

---

## 风险与回退

### 风险
- 低：仅修改 `ResultViewer.tsx` 内部状态管理，不影响 ColumnSelector 组件契约
- 现有 localStorage 数据格式不变，向后兼容

### 回退方案
如果出现异常，可通过 `git checkout frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx` 一键回退到原版本。

---

## 实施计划

将使用 `superpowers:writing-plans` skill 编写详细实施计划。
