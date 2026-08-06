# Database Tool 字段类型化展示 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 database-tool 表格展示时所有数值字段被强制保留两位小数的问题，按列类型差异化展示。

**Architecture:** 抽取纯函数 `formatCellValue(value, colDef)` 到 `frontend/src/utils/cellFormatter.ts`，`ResultViewer` 在 `renderCell` 内单点调用替代原来的 `formatNumericValue` + `formatDateTimeValue` 双调用。后端契约不变，调用面仅 1 处。

**Tech Stack:** TypeScript, React 18, Vitest, Tailwind(展示样式不变)

## Global Constraints

- 仅修改前端，不动后端 `SQLExecutionResult` 结构
- 纯函数模块化，无 React 依赖，便于单测
- 中文注释、英文标识符
- Vitest 用 `pnpm vitest run <path>` 运行
- 项目启动方式：`python dev_services.py restart frontend`（修改源码后热加载）
- 浏览器验证地址：`http://localhost:5178/tools/database-tool`

---

## File Structure

### 新建文件

- `frontend/src/utils/cellFormatter.ts` — 纯函数模块，导出 `ColumnTypeInfo` 类型和 `formatCellValue` 函数
- `frontend/src/utils/cellFormatter.test.ts` — Vitest 单元测试，覆盖整数/浮点/decimal/未知/日期/null 等矩阵

### 修改文件

- `frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx`
  - 删除 `formatNumericValue` 函数（约 11 行）
  - 删除 `formatDateTimeValue` 函数（约 17 行）
  - 引入 `formatCellValue` 并替换 `renderCell` 内的调用（约 1 行）

---

## Task 1: 实现 cellFormatter 纯函数

**Files:**
- Create: `frontend/src/utils/cellFormatter.ts`
- Test: `frontend/src/utils/cellFormatter.test.ts`

**Interfaces:**
- Consumes: 无依赖（纯函数模块）
- Produces:
  - `ColumnTypeInfo { type?: string }`
  - `formatCellValue(value: unknown, colDef?: ColumnTypeInfo | null): string`

- [ ] **Step 1: 编写失败的测试**

在 `frontend/src/utils/cellFormatter.test.ts` 写入测试矩阵（覆盖整数、浮点、decimal scale、未知类型、null、日期等）：

```ts
import { describe, it, expect } from 'vitest';
import { formatCellValue } from './cellFormatter';

describe('formatCellValue', () => {
  it('整数类型原样输出', () => {
    expect(formatCellValue(123, { type: 'int(11)' })).toBe('123');
    expect(formatCellValue(42, { type: 'bigint(20)' })).toBe('42');
    expect(formatCellValue(1, { type: 'tinyint(4)' })).toBe('1');
    expect(formatCellValue(100, { type: 'INTEGER' })).toBe('100');
  });

  it('浮点类型保留原值', () => {
    expect(formatCellValue(3.14, { type: 'float' })).toBe('3.14');
    expect(formatCellValue(2.718281828, { type: 'double' })).toBe('2.718281828');
    expect(formatCellValue(1.5, { type: 'real' })).toBe('1.5');
  });

  it('decimal/numeric 按 scale 显示', () => {
    expect(formatCellValue(0.0001, { type: 'numeric(8,4)' })).toBe('0.0001');
    expect(formatCellValue(1.5, { type: 'decimal(10,2)' })).toBe('1.50');
    expect(formatCellValue(1.56789, { type: 'decimal(10,2)' })).toBe('1.57');
    expect(formatCellValue(1.5, { type: 'decimal' })).toBe('1.50');
    expect(formatCellValue(1.5, { type: 'DECIMAL(10,2)' })).toBe('1.50');
  });

  it('未知类型不动用 toFixed', () => {
    expect(formatCellValue(42)).toBe('42');
    expect(formatCellValue(42, { type: undefined })).toBe('42');
    expect(formatCellValue(42, null)).toBe('42');
    expect(formatCellValue(42, { type: 'json' })).toBe('42');
  });

  it('非数字原样字符串化', () => {
    expect(formatCellValue('hello', { type: 'int(11)' })).toBe('hello');
    expect(formatCellValue('2025-01-01', { type: 'varchar(255)' })).toBe('2025-01-01');
    expect(formatCellValue(true, { type: 'int(11)' })).toBe('true');
  });

  it('null/undefined 返回空串', () => {
    expect(formatCellValue(null, { type: 'int(11)' })).toBe('');
    expect(formatCellValue(undefined, { type: 'int(11)' })).toBe('');
  });

  it('NaN/Infinity 走 String() 兜底', () => {
    expect(formatCellValue(NaN, { type: 'int(11)' })).toBe('NaN');
    expect(formatCellValue(Infinity, { type: 'int(11)' })).toBe('Infinity');
  });

  it('日期类型本地化', () => {
    const result = formatCellValue('2025-01-01T00:00:00Z', { type: 'datetime' });
    expect(result).not.toBe('2025-01-01T00:00:00Z');
    expect(result).toMatch(/\d{4}/);
  });

  it('无效日期字符串保持原样', () => {
    expect(formatCellValue('not-a-date', { type: 'datetime' })).toBe('not-a-date');
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

运行: `cd frontend && pnpm vitest run src/utils/cellFormatter.test.ts`
预期: FAIL — "Cannot find module './cellFormatter'"

- [ ] **Step 3: 实现 cellFormatter.ts**

```ts
// frontend/src/utils/cellFormatter.ts
/**
 * 单元格格式化工具：按列类型差异化展示数据库字段值。
 * 替代旧的 formatNumericValue / formatDateTimeValue 双函数方案。
 */

const SCALE_RE = /(?:decimal|numeric)\s*\(\s*\d+\s*,\s*(\d+)\s*\)/i;
const DATE_TYPES = new Set(['date', 'datetime']);
const TIMESTAMP_RE = /timestamp/i;

/** 列类型的最小可读信息 */
export interface ColumnTypeInfo {
  type?: string;
}

/** 从列类型字符串提取 decimal/numeric 的 scale，未匹配返回 null */
function extractScale(type: string | undefined): number | null {
  if (!type) return null;
  const m = type.match(SCALE_RE);
  return m ? Number(m[1]) : null;
}

/** 判断是否为日期时间类型 */
function isDateTimeType(type: string | undefined): boolean {
  if (!type) return false;
  const t = type.toLowerCase().trim();
  return DATE_TYPES.has(t) || TIMESTAMP_RE.test(t);
}

/**
 * 将数据库字段值格式化为展示字符串。
 *
 * 规则：
 * - null/undefined → ''（外层仍渲染 "NULL" 文案）
 * - 非 number 原样字符串化；日期类型额外本地化
 * - 整数类型（int/bigint 等）原样输出
 * - 浮点类型（float/double/real）原样输出
 * - decimal/numeric 按 (p,s) 括号中的 s 调用 toFixed；无括号默认 scale=2
 * - 其他未知类型原样输出（不调用 toFixed）
 */
export function formatCellValue(value: unknown, colDef?: ColumnTypeInfo | null): string {
  if (value === null || value === undefined) return '';

  if (typeof value !== 'number') {
    const str = String(value);
    if (isDateTimeType(colDef?.type)) {
      const date = new Date(str);
      if (!isNaN(date.getTime())) {
        return date.toLocaleString('zh-CN');
      }
    }
    return str;
  }

  // number 分支
  if (!isFinite(value)) return String(value);

  const type = colDef?.type?.toLowerCase();
  if (!type) return value.toString();

  // 整数类型
  if (/int/.test(type)) return value.toString();

  // 浮点类型
  if (/float|double|real/.test(type)) return value.toString();

  // decimal / numeric
  if (/decimal|numeric/.test(type)) {
    const scale = extractScale(colDef?.type) ?? 2;
    return value.toFixed(scale);
  }

  // 其他未知类型，原样输出
  return value.toString();
}
```

- [ ] **Step 4: 运行测试确认通过**

运行: `cd frontend && pnpm vitest run src/utils/cellFormatter.test.ts`
预期: PASS — 14 个测试全部通过

- [ ] **Step 5: 提交**

```bash
git add frontend/src/utils/cellFormatter.ts frontend/src/utils/cellFormatter.test.ts
git commit -m "feat(frontend): 新增 cellFormatter 工具按列类型格式化单元格"
```

---

## Task 2: 替换 ResultViewer 调用点

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx`
  - 删除 `formatNumericValue` 函数（约 11 行，385-395 行）
  - 删除 `formatDateTimeValue` 函数（约 17 行，363-379 行）
  - 引入 `formatCellValue` 并替换 `renderCell` 内的调用（529 行）

**Interfaces:**
- Consumes: `formatCellValue` from `frontend/src/utils/cellFormatter`
- Produces: 改动后的 `renderCell`（line 529 附近）调用 `formatCellValue(displayValue, colDef)`

- [ ] **Step 1: 引入新函数 import**

在 `ResultViewer.tsx` 顶部 import 区域添加：

```ts
import { formatCellValue } from '../../../../utils/cellFormatter';
```

- [ ] **Step 2: 删除 formatNumericValue 函数**

删除 `ResultViewer.tsx` 中第 381-395 行（含 `formatNumericValue` 函数及其 JSDoc 注释）：

```ts
  /**
   * 格式化数值显示。金额/数值字段默认保留两位小数，
   * 如果实际小数位数超过两位则完整显示。
   */
  const formatNumericValue = (value: any): string => {
    if (typeof value !== 'number' || !isFinite(value)) return String(value);
    // 整数或小数位数 ≤ 2 的，统一显示两位小数
    const str = value.toString();
    const dotIndex = str.indexOf('.');
    if (dotIndex === -1 || str.length - dotIndex - 1 <= 2) {
      return value.toFixed(2);
    }
    // 小数位数 > 2 的，完整显示
    return str;
  };
```

- [ ] **Step 3: 删除 formatDateTimeValue 函数**

删除 `ResultViewer.tsx` 中第 360-379 行（含 `formatDateTimeValue` 函数及其 JSDoc 注释）：

```ts
  /**
   * 格式化日期时间值。对于日期/时间类型的列，将 ISO 格式字符串转为可读的本地化格式。
   */
  const formatDateTimeValue = (value: any, colDef: any): string => {
    if (value === null || value === undefined) return '';
    const strValue = String(value);
    // 仅对日期/时间类型的列进行格式化
    if (colDef?.type) {
      const type = colDef.type.toLowerCase();
      const isDateTime = type === 'date' || type === 'datetime' || type.includes('timestamp');
      if (isDateTime) {
        // 尝试解析为 Date 对象，如果解析失败则返回原始值
        const date = new Date(strValue);
        if (!isNaN(date.getTime())) {
          return date.toLocaleString('zh-CN');
        }
      }
    }
    return strValue;
  };
```

- [ ] **Step 4: 替换 renderCell 中的调用**

将第 529 行：

```tsx
          <TruncatedText text={typeof displayValue === 'number' ? formatNumericValue(displayValue) : formatDateTimeValue(displayValue, colDef)} />
```

改为：

```tsx
          <TruncatedText text={formatCellValue(displayValue, colDef)} />
```

- [ ] **Step 5: 类型检查**

运行: `cd frontend && pnpm tsc --noEmit`
预期: PASS，无类型错误

- [ ] **Step 6: 重新运行单测**

运行: `cd frontend && pnpm vitest run src/utils/cellFormatter.test.ts`
预期: PASS — cellFormatter 单测不受影响

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx
git commit -m "refactor(database-tool): 用 cellFormatter 替换 formatNumericValue/formatDateTimeValue"
```

---

## Task 3: 浏览器 E2E 验证

**Files:** 无（仅验证）

**Interfaces:** 无

- [ ] **Step 1: 确认前端服务运行**

运行: `cd frontend && pnpm dev`
访问: `http://localhost:5178/tools/database-tool`
（如果端口被占用，先 `python dev_services.py restart frontend`）

- [ ] **Step 2: 选一张含 int 列的表验证**

选取一张含 `id int(11)` 或类似整型字段的表，确认：
- 整型列不再显示 `1.00`、`42.00`，而是 `1`、`42`
- 其他列（如 decimal、datetime）展示正确

- [ ] **Step 3: 选一张含 decimal 列的表验证**

选取一张含 `decimal(10,2)` 字段的表，确认：
- decimal 列显示符合数据库定义精度（如 `1.50`）
- 数据库存储 `0.0001` 在 `numeric(8,4)` 列中显示为 `0.0001`

- [ ] **Step 4: 选一张含 datetime 列的表验证**

选取一张含 `datetime` 或 `timestamp` 字段的表，确认：
- 日期列显示本地化格式（如 `2025/1/1 08:00:00`）
- 不是原始 ISO 字符串

- [ ] **Step 5: 控制台无报错**

在浏览器 DevTools Console 中确认无 JS 报错。

- [ ] **Step 6: 现有功能未受影响**

抽查以下功能未回归：
- Inline 编辑（双击单元格）
- 批量删除（勾选行 → 删除按钮）
- 复制 INSERT/UPDATE 按钮
- 批量查看 JSON
- 列选择器

- [ ] **Step 7: 提交（无代码改动则跳过）**

如未发现需要修复的问题，本任务无提交。

---

## Self-Review

### 1. Spec 覆盖

| Spec 项 | 对应 Task |
|---|---|
| 抽 `formatCellValue` 到 `cellFormatter.ts` | Task 1 |
| 替换 `ResultViewer.tsx` 调用点 | Task 2 |
| 删除 `formatNumericValue` 与 `formatDateTimeValue` | Task 2 |
| 单元测试覆盖矩阵 | Task 1 |
| E2E 人工验证 | Task 3 |
| 浏览器验证 | Task 3 |

无遗漏。

### 2. 占位符扫描

- 无 "TBD" / "TODO" / "implement later"
- 测试代码完整（Step 1 完整 Vitest 用例）
- 实现代码完整（Step 3 完整 `cellFormatter.ts` 主体）
- 无 "Similar to Task N"
- 步骤含具体命令路径

### 3. 类型一致性

- `ColumnTypeInfo` 在 Task 1 定义并 export，Task 2 通过 import 使用 — 一致
- `formatCellValue` 签名 `(value: unknown, colDef?: ColumnTypeInfo | null): string` 在 Task 1 Step 3 定义，Task 2 Step 4 调用方式 `formatCellValue(displayValue, colDef)` — 一致（`colDef` 可能为 undefined，符合可选参数）

### 4. 范围与依赖

- 后端零改动 ✓
- 仅修改 `ResultViewer.tsx` 一处 ✓
- 新增 `cellFormatter.ts` 单文件模块 ✓
- Vitest 依赖项目已具备（`frontend/package.json` 含 `vitest`），无需新增依赖