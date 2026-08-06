---
author: Claude
created_at: 2026-08-06
purpose: 修复 database-tool 表格展示时所有数值字段被强制保留两位小数的问题，按列类型差异化展示
---

# Database Tool 字段类型化展示设计

## 背景与问题

`http://localhost:5178/tools/database-tool` 页面的数据表格 (`frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx`) 当前通过 `formatNumericValue` 函数 (ResultViewer.tsx:385-395) 处理所有数字类型单元格：

```ts
const formatNumericValue = (value: any): string => {
  if (typeof value !== 'number' || !isFinite(value)) return String(value);
  const str = value.toString();
  const dotIndex = str.indexOf('.');
  if (dotIndex === -1 || str.length - dotIndex - 1 <= 2) {
    return value.toFixed(2);
  }
  return str;
};
```

该函数无视字段类型，对所有 `typeof === 'number'` 的值都补零或四舍五入到两位小数，导致：

- 整数字段（`int`/`bigint` 等）被错误显示为 `1.00`、`42.00`，损失了"整型"的语义
- 高精度小数（`decimal(10,4)`）的展示与数据库定义精度不一致
- 浮点字段（`float`/`double`）强制两位掩盖了原始精度

## 目标

- 单元格展示遵循数据库定义的列类型
- 后端契约与现有调用面不变（最小变更原则）
- 抽取纯函数 + 单元测试，回归风险可控

## 范围

### 包含

1. 抽取 `formatCellValue(value, colDef)` 到 `frontend/src/utils/cellFormatter.ts`
2. 替换 `ResultViewer.tsx` 中 `formatNumericValue` 的调用
3. 添加 `cellFormatter.test.ts` Vitest 单元测试
4. 浏览器 E2E 人工验证

### 不包含

- 不修改后端 `SQLExecutionResult` 数据结构
- 不重构 `formatDateTimeValue` 之外的 `ResultViewer` 内其他逻辑
- 不动 `SQLExecutor.tsx` 中可能的相同展示问题（本次范围外）
- 不引入新的 i18n 框架（日期格式化沿用 `toLocaleString('zh-CN')`）

## 设计

### 模块边界

- `cellFormatter.ts`：纯函数模块，无 React / 组件依赖
- 暴露 `ColumnTypeInfo`（最小区段）和 `formatCellValue` 单入口
- `ResultViewer` 仅在 `renderCell` 内调用新函数

```ts
// frontend/src/utils/cellFormatter.ts
export interface ColumnTypeInfo {
  type?: string; // 列类型字符串，如 'int(11)' / 'decimal(10,2)' / 'numeric(8,4)'
}

export function formatCellValue(value: unknown, colDef?: ColumnTypeInfo | null): string;
```

### 格式化规则派发

`formatCellValue` 内部按以下顺序派发：

1. `value === null || value === undefined` → 返回 `''`（外层 `<span>` 仍渲染 "NULL" 文案）
2. `typeof value !== 'number'` → 返回 `String(value)`
   - 字符串、布尔、Date ISO、对象等原样
   - 日期类型（`date` / `datetime` / `timestamp`）→ 通过 `new Date(strValue)` 解析后用 `toLocaleString('zh-CN')` 渲染
3. `typeof value === 'number'` 且 `!isFinite(value)`（`NaN` / `Infinity`）→ 返回 `String(value)`
4. `typeof value === 'number'` 且有限值 → 按 `colDef.type`（小写）判断：
   - 含 `int` / `integer` / `smallint` / `tinyint` / `bigint` → `value.toString()`（原样）
   - 含 `float` / `double` / `real` → `value.toString()`（原样）
   - 含 `decimal` / `numeric` → 解析括号提取 `scale`，未提供则默认 2
     - `decimal(10,2)` → scale = 2
     - `numeric(8,4)` → scale = 4
     - `decimal` / `numeric`（无括号）→ scale = 2
     - `decimal(10)`（仅 precision）→ scale = 2（fallback）
     - 调用 `value.toFixed(scale)`（JS toFixed 行为：四舍五入到 scale 位）
   - 其他类型（含 `undefined`）→ `value.toString()`（不动用 `toFixed`）

### scale 解析正则

```ts
const SCALE_RE = /(?:decimal|numeric)\s*\(\s*\d+\s*,\s*(\d+)\s*\)/i;
function extractScale(type: string | undefined): number | null {
  if (!type) return null;
  const m = type.match(SCALE_RE);
  return m ? Number(m[1]) : null;
}
```

仅识别标准 MySQL/PG/SQLite 形态 `decimal(p,s)` / `numeric(p,s)`。非标准写法（罕见）走 fallback 默认 2。

### 调用点变更

`ResultViewer.tsx:529` 当前调用：

```tsx
<TruncatedText
  text={
    typeof displayValue === 'number'
      ? formatNumericValue(displayValue)
      : formatDateTimeValue(displayValue, colDef)
  }
/>
```

变更为：

```tsx
<TruncatedText text={formatCellValue(displayValue, colDef)} />
```

- `formatCellValue` 内部整合日期与数值两类格式化
- 移除 `ResultViewer.tsx` 内 `formatNumericValue` 函数（约 11 行）
- 删除 `formatDateTimeValue` 函数（约 17 行），其逻辑已并入 `formatCellValue`

### 数据流

```
TableDataViewer.tsx
  → api.queryTableData() → SQLExecutionResult{ columns, result_data }
  → <ResultViewer result={...} schema={schema} />

ResultViewer.renderCell(row, idx, col)
  → displayValue 解析（已有逻辑：编辑中取 newValue，否则原值）
  → formatCellValue(displayValue, colDef)  ← 新调用
  → <TruncatedText text=... />

schema?.columns: Array<{ name, type, length, nullable, ... }>
  colDef 来自 schema.columns.find(c => c.name === col)
```

`schema` 由 `TableDataViewer.fetchSchema()` 通过 `api.getTableSchema()` 一次性获取；列类型字段已包含在 `TableSchema.columns` 内，无须后端改动。

### 错误处理

`formatCellValue` 不抛异常。防御性策略：

- 所有未识别类型分支走 `value.toString()`，避免对未知类型误用 `toFixed`
- `new Date(strValue)` 解析失败（无效日期）时 `getTime()` 返回 `NaN`，此时跳过本地化，保留原字符串
- `Number.MAX_SAFE_INTEGER` 等大数虽不会触发（已走字符串路径），但仍提供安全兜底

## 测试策略

### 单元测试（cellFormatter.test.ts）

Vitest，覆盖矩阵：

| 输入 | colDef.type | 期望输出 |
|---|---|---|
| `123` | `'int(11)'` | `'123'` |
| `42` | `'bigint(20)'` | `'42'` |
| `1` | `'tinyint(4)'` | `'1'` |
| `3.14` | `'float'` | `'3.14'` |
| `2.718281828` | `'double'` | `'2.718281828'` |
| `0.0001` | `'numeric(8,4)'` | `'0.0001'` |
| `1.5` | `'decimal(10,2)'` | `'1.50'` |
| `1.56789` | `'decimal(10,2)'` | `'1.57'` |
| `1.5` | `'decimal'` (无括号) | `'1.50'` |
| `42` | `undefined` | `'42'` |
| `'hello'` | `'int(11)'` | `'hello'` |
| `null` | `'int(11)'` | `''` |
| `undefined` | `'int(11)'` | `''` |
| `NaN` | `'int(11)'` | `'NaN'` |
| `'2025-01-01T00:00:00Z'` | `'datetime'` | 非原始 ISO 字符串（含本地化年月日时分） |

### E2E（人工）

启动 dev server，访问 `http://localhost:5178/tools/database-tool`：

1. 选一张同时含 `int` / `decimal` / `datetime` 列的表，确认：
   - 整型列不再补 `.00`
   - decimal 列按 scale 显示（如 `decimal(10,2)` 显示 `1.50`）
   - datetime 列正常本地化
2. 控制台无报错
3. 确认现有 Inline 编辑、批量删除、复制 INSERT/UPDATE 行为未受影响

## 风险与回滚

- 风险低：纯函数替换，调用面仅 1 处
- 回滚成本：恢复 `ResultViewer.tsx` 的 `formatNumericValue` 函数（约 11 行）+ 删除 `cellFormatter.ts`，可单提交回滚

## 实施步骤

1. 新建 `frontend/src/utils/cellFormatter.ts`
2. 新建 `frontend/src/utils/cellFormatter.test.ts`
3. 修改 `frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx`
   - 删除 `formatNumericValue` 函数
   - 删除 `formatDateTimeValue` 函数（逻辑已并入新函数）
   - 引入 `formatCellValue` 并替换 `renderCell` 内的调用
4. 运行 `pnpm vitest run cellFormatter.test.ts` 验证单测
5. 浏览器 E2E 验证

## 不在本设计的关联项

- `SQLExecutor.tsx` 中如果有相同展示问题，留作 follow-up（本次扫描未发现 `formatNumericValue` 的复用，但 SQLExecutor 自有展示代码可能存在）
- `ResultViewer` 内的 `formatDateTimeValue` 删除（已并入 `formatCellValue`）