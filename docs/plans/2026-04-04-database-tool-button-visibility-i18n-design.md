# 数据库工具按钮可见性与多语言优化设计

## 问题描述

`/tools/database-tool` 页面在查看数据库表数据时，操作按钮（Insert、Update、JSON、Delete）仅在勾选行数据后才显示。用户要求按钮始终可见，且所有按钮文字需支持多语言。

## 当前实现

**文件**: `frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx`

```tsx
// 第 210 行：按钮被条件渲染包裹
{selectedIndices.size > 0 && (
  <div className="flex gap-2 ml-2">
    <button>Insert</button>
    <button>Update</button>
    <button>JSON</button>
    <button>Delete</button>
  </div>
)}
```

**问题**：
1. 按钮仅在 `selectedIndices.size > 0` 时渲染
2. 所有按钮文字硬编码英文，未走 i18n

## 选定方案：方案 A（按钮始终可见，无选中行时智能禁用）

### 按钮行为矩阵

| 按钮 | 无选中行 | 有选中行（有主键） | 有选中行（无主键） |
|---|---|---|---|
| Insert | 基于表结构生成空值模板 | 基于选中行生成 INSERT | 基于选中行生成 INSERT |
| Update | 禁用 | 可用 | 禁用 |
| JSON | 显示当前页全部数据 | 显示选中行数据 | 显示选中行数据 |
| Delete | 禁用 | 可用 | 禁用 |

### i18n 键名

**新增到 `database.executor` 命名空间**：

| 键名 | zh-CN | en-US |
|---|---|---|
| `copyInsert` | 复制 INSERT | Copy INSERT |
| `copyUpdate` | 复制 UPDATE | Copy UPDATE |
| `viewJson` | JSON | JSON |
| `deleteRows` | 删除 | Delete |
| `noDataSelected` | 请先选择数据 | Please select data first |

### 修改文件清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `ResultViewer.tsx` | 修改 | 移除条件渲染、调整按钮行为、替换硬编码文字 |
| `zh-CN.ts` | 修改 | 新增 5 个翻译键 |
| `en-US.ts` | 修改 | 新增 5 个翻译键 |

### 核心变更

1. **移除** `{selectedIndices.size > 0 && (...)}` 条件包裹
2. **Update/Delete 按钮** 增加 `selectedIndices.size === 0` 到 disabled 条件
3. **Insert 按钮** 无选中行时调用 `generateInsertStatements` 传入空数组或基于 schema.columns 生成模板
4. **JSON 按钮** 无选中行时传入 `result.result_data`（全部数据）
5. **所有按钮文字** 替换为 `t.database.executor.*`

### 风险评估

- **低风险**：仅影响按钮可见性和文字，不改变现有选中行时的行为
- **Insert 空模板**：需确认 `generateInsertStatements(tableName, [])` 的返回值，若为空字符串则需额外处理基于 schema 生成模板
