# 数据库工具按钮可见性与多语言优化 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让数据库表数据查看器的操作按钮（Insert、Update、JSON、Delete）始终可见，无选中行时智能禁用，并将所有按钮文字改为多语言支持。

**Architecture:** 移除 `ResultViewer.tsx` 中 `{selectedIndices.size > 0 && (...)}` 条件渲染，改为按钮始终渲染但通过 `disabled` 属性控制可用性。Insert 在无选中行时基于表结构生成空值模板，JSON 在无选中行时显示全部数据。所有按钮文字从硬编码英文改为 `t.database.executor.*`。

**Tech Stack:** React 18, TypeScript, Tailwind CSS, 项目自研 i18n 系统（useI18n hook）

---

### Task 1: 新增 i18n 翻译键（zh-CN）

**Files:**
- Modify: `frontend/src/i18n/locales/zh-CN.ts`

在 `database.executor` 对象中新增 5 个键：

```ts
executor: {
  // ... 现有键保持不变
  copyInsert: '复制 INSERT',
  copyUpdate: '复制 UPDATE',
  viewJson: 'JSON',
  deleteRows: '删除',
  noDataSelected: '请先选择数据',
},
```

**Step 1: 编辑 zh-CN.ts**

找到 `database.executor` 对象（约第 343-355 行），在现有键后面新增上述 5 个键。

**Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增错误（因为 en-US 尚未添加对应键，会报类型不匹配，这是预期的，下一步修复）

---

### Task 2: 新增 i18n 翻译键（en-US）

**Files:**
- Modify: `frontend/src/i18n/locales/en-US.ts`

在 `database.executor` 对象中新增对应 5 个键：

```ts
executor: {
  // ... 现有键保持不变
  copyInsert: 'Copy INSERT',
  copyUpdate: 'Copy UPDATE',
  viewJson: 'JSON',
  deleteRows: 'Delete',
  noDataSelected: 'Please select data first',
},
```

**Step 1: 编辑 en-US.ts**

找到 `database.executor` 对象（约第 342-354 行），在现有键后面新增上述 5 个键。

**Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

---

### Task 3: 修改 ResultViewer.tsx 按钮可见性与多语言

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx`

这是核心变更，包含以下子步骤：

#### Step 3.1: 修改 `handleCopyInsert` 逻辑

当前代码（约第 50-60 行）：
```ts
const handleCopyInsert = async () => {
  const rows = getSelectedRows();
  const sql = generateInsertStatements(tableName || 'table_name', rows);
  // ...
};
```

改为：当无选中行时，基于 `schema.columns` 生成空值模板：

```ts
const handleCopyInsert = async () => {
  let rows = getSelectedRows();
  let sql: string;
  
  if (rows.length === 0 && schema?.columns) {
    // 无选中行时，基于表结构生成空值 INSERT 模板
    const columns = schema.columns.map((c: any) => c.name);
    const values = columns.map(() => 'NULL').join(', ');
    const cols = columns.map((c: string) => `\`${c}\``).join(', ');
    sql = `INSERT INTO \`${tableName || 'table_name'}\` (${cols}) VALUES (${values});`;
  } else {
    sql = generateInsertStatements(tableName || 'table_name', rows);
  }
  
  try {
    await navigator.clipboard.writeText(sql);
    setCopyFeedback('insert');
    setTimeout(() => setCopyFeedback(null), 2000);
  } catch (err) {
    console.error('复制失败', err);
  }
};
```

#### Step 3.2: 修改 `handleBatchViewJson` 逻辑

当前代码（约第 74-77 行）：
```ts
const handleBatchViewJson = () => {
  const rows = getSelectedRows();
  setViewingRow(rows);
};
```

改为：当无选中行时，显示当前页全部数据：

```ts
const handleBatchViewJson = () => {
  const rows = getSelectedRows();
  setViewingRow(rows.length > 0 ? rows : result?.result_data);
};
```

#### Step 3.3: 移除条件渲染，按钮始终可见

将第 210-256 行的条件渲染结构：

```tsx
{selectedIndices.size > 0 && (
  <>
    <span className="text-blue-400 border-l border-slate-600 pl-4">{selectedIndices.size} selected</span>
    <div className="flex gap-2 ml-2">
      {/* 4 个按钮 */}
    </div>
  </>
)}
```

改为：

```tsx
{selectedIndices.size > 0 && (
  <span className="text-blue-400 border-l border-slate-600 pl-4">
    {interpolate(t.database.executor.selectedCount, { count: String(selectedIndices.size) })}
  </span>
)}
<div className="flex gap-2 ml-2">
  {/* 4 个按钮始终渲染 */}
</div>
```

注意：需要在 `zh-CN.ts` 和 `en-US.ts` 的 `database.executor` 中额外新增：
- `selectedCount: '已选 {count} 行'` / `'{count} selected'`

#### Step 3.4: Insert 按钮 — 多语言

```tsx
<button 
  onClick={handleCopyInsert}
  className="px-2 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded flex items-center gap-1 transition-colors"
  title={t.database.executor.copyInsert}
>
  <i className={`fas ${copyFeedback === 'insert' ? 'fa-check text-green-400' : 'fa-copy'}`}></i>
  {t.database.executor.copyInsert}
</button>
```

#### Step 3.5: Update 按钮 — 多语言 + 增强禁用条件

```tsx
<button 
  onClick={handleCopyUpdate}
  disabled={!primaryKey || primaryKey.length === 0 || selectedIndices.size === 0}
  className={`px-2 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded flex items-center gap-1 transition-colors ${(!primaryKey || primaryKey.length === 0 || selectedIndices.size === 0) ? 'opacity-50 cursor-not-allowed' : ''}`}
  title={selectedIndices.size === 0 
    ? t.database.executor.noDataSelected 
    : (!primaryKey || primaryKey.length === 0) 
      ? t.database.batchDelete.noPrimaryKey 
      : t.database.executor.copyUpdate}
>
  <i className={`fas ${copyFeedback === 'update' ? 'fa-check text-green-400' : 'fa-pen-to-square'}`}></i>
  {t.database.executor.copyUpdate}
</button>
```

#### Step 3.6: JSON 按钮 — 多语言

```tsx
<button 
  onClick={handleBatchViewJson}
  className="px-2 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded flex items-center gap-1 transition-colors"
  title={selectedIndices.size === 0 ? t.database.executor.viewJson : t.database.executor.viewSelectedJson || t.database.executor.viewJson}
>
  <i className="fas fa-code"></i>
  {t.database.executor.viewJson}
</button>
```

需要在 i18n 中新增：
- `viewSelectedJson: '查看选中行 JSON'` / `'View Selected JSON'`

#### Step 3.7: Delete 按钮 — 多语言 + 增强禁用条件

```tsx
<button 
  onClick={handleBatchDelete}
  disabled={!primaryKey || primaryKey.length === 0 || selectedIndices.size === 0}
  className={`px-2 py-1 text-xs rounded flex items-center gap-1 transition-colors ${
    (!primaryKey || primaryKey.length === 0 || selectedIndices.size === 0)
      ? 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
      : 'bg-red-600/80 hover:bg-red-600 text-white'
  }`}
  title={selectedIndices.size === 0 
    ? t.database.executor.noDataSelected 
    : (!primaryKey || primaryKey.length === 0) 
      ? t.database.batchDelete.noPrimaryKey 
      : t.database.executor.deleteRows}
>
  <i className={`fas ${(!primaryKey || primaryKey.length === 0) ? 'fa-ban' : 'fa-trash'}`}></i>
  {t.database.executor.deleteRows}
</button>
```

**Step 3.8: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

---

### Task 4: 浏览器验证

**Step 1: 启动前端（如未启动）**

Run: `cd frontend && npm run dev`

**Step 2: 打开数据库工具页面**

使用浏览器工具打开 `http://localhost:5178/tools/database-tool`

**Step 3: 验证按钮始终可见**

- 连接数据库并打开表数据查看
- 确认不勾选任何行时，Insert、Update、JSON、Delete 按钮仍然显示
- 确认 Update 和 Delete 在无选中行时显示为禁用状态（灰色、不可点击）
- 确认 Insert 和 JSON 在无选中行时可点击

**Step 4: 验证多语言切换**

- 切换语言到中文，确认按钮显示为"复制 INSERT"、"复制 UPDATE"、"JSON"、"删除"
- 切换语言到英文，确认按钮显示为"Copy INSERT"、"Copy UPDATE"、"JSON"、"Delete"

**Step 5: 验证功能正确性**

- 无选中行时点击 Insert → 剪贴板包含空值 INSERT 模板
- 无选中行时点击 JSON → 弹窗显示当前页全部数据
- 选中行后点击 Insert → 剪贴板包含基于选中行的 INSERT 语句（原有行为不变）
- 选中行后点击 Update → 剪贴板包含 UPDATE 语句（原有行为不变）
- 选中行后点击 Delete → 弹出删除确认对话框（原有行为不变）

**Step 6: 检查浏览器 Console**

- 确认 Console 中无任何报错

---

### Task 5: 提交

**Step 1: 查看变更**

```bash
git status
git diff
```

**Step 2: 提交**

```bash
git add frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx frontend/src/i18n/locales/zh-CN.ts frontend/src/i18n/locales/en-US.ts
git commit -m "feat(database-tool): 按钮始终可见且支持多语言"
```

---

## 变更摘要

| 文件 | 变更 |
|---|---|
| `ResultViewer.tsx` | 移除条件渲染、调整 4 个按钮的 disabled 逻辑、替换硬编码文字为 i18n 键 |
| `zh-CN.ts` | 新增 7 个翻译键（copyInsert, copyUpdate, viewJson, deleteRows, noDataSelected, selectedCount, viewSelectedJson） |
| `en-US.ts` | 新增 7 个对应英文翻译键 |
