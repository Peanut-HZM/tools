# 数据库表数据导出功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在数据库管理工具的表数据查看器中增加导出按钮，支持按当前 WHERE/ORDER BY 筛选条件导出全部数据为 CSV/Excel/JSON/SQL 格式

**Architecture:** 后端已有导出 API（`POST /api/database-tool/configs/{id}/export`），但存在 `request.db_config_id` 字段不存在的 bug。前端需要新增 API 封装、导出按钮 UI、下载逻辑。数据流：前端构造完整 SQL → 调用后端导出 API → 接收文件内容 → 创建 Blob 触发浏览器下载。

**Tech Stack:** Python (FastAPI), React (TypeScript), Tailwind CSS

## Global Constraints

- 所有对话、文档、注释、日志、提交信息必须使用中文
- 变量名、函数名使用英文
- 禁止 `console.log` 在生产代码中
- 禁止 `DROP TABLE` / `TRUNCATE` 等破坏性操作
- DDL 使用 `CREATE TABLE IF NOT EXISTS`，DML 使用幂等模式
- 代码修改后优先利用热加载，非必要不重启服务
- 完成代码修改后，必须使用 `dev-services.py` 重启相关模块
- 使用浏览器进行验证，确认页面正常、无报错

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/app/services/database_tool_service.py:2039-2047` | 修复 `export_data()` 中引用不存在的 `request.db_config_id` 字段 |
| `frontend/src/api/databaseToolApi.ts` | 新增 `exportTableData()` API 封装函数和 `ExportDataResponse` 类型 |
| `frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx` | 添加导出按钮、下拉菜单、下载逻辑 |
| `frontend/src/i18n/locales/zh-CN.ts` | 添加导出相关中文文案 |
| `frontend/src/i18n/locales/en-US.ts` | 添加导出相关英文文案 |

## Task 1: Fix Backend Export Bug

**Files:**
- Modify: `backend/app/services/database_tool_service.py:2043-2047`

**Issue:** `export_data()` method references `request.db_config_id` (line 2044), but `ExportDataRequest` model only has `sql`, `format`, and `database_name` fields — no `db_config_id`. This causes `AttributeError` at runtime.

**Interfaces:**
- Consumes: `config_id` parameter (already passed to the method)
- Produces: Fixed `export_data()` that works correctly

- [ ] **Step 1: Fix the bug**

In `backend/app/services/database_tool_service.py`, line 2044, change:
```python
# Before (broken):
config_row = DatabaseToolService._get_config_with_password(
    request.db_config_id, user_id
)

# After (fixed):
config_row = DatabaseToolService._get_config_with_password(
    config_id, user_id
)
```

The `config_id` parameter is already available in the method signature at line 2040. The URL path variable `id` is passed to `DatabaseToolService.export_data(user_id, id, request)` from the route handler, so `config_id` is the correct value.

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile backend/app/services/database_tool_service.py`
Expected: No output (success)

- [ ] **Step 3: Restart backend**

Run: `python dev-services.py restart backend`
Expected: Backend restarts successfully

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/database_tool_service.py
git commit -m "fix: 修复 export_data 引用不存在的 request.db_config_id 字段"
```

---

## Task 2: Add Frontend Export API and Types

**Files:**
- Modify: `frontend/src/api/databaseToolApi.ts` — add `exportTableData()` function and `ExportDataResponse` type

**Interfaces:**
- Consumes: `API_BASE_URL`, `getAuthHeaders()`, `fetchWithTimeout()`, `handleResponse()` (existing)
- Produces: `exportTableData(configId, request)` returning `Promise<ExportDataResponse>`

- [ ] **Step 1: Add ExportDataResponse type**

In `frontend/src/api/databaseToolApi.ts`, after the existing type imports (around line 28), add:

```typescript
/** 导出数据响应 */
export interface ExportDataResponse {
  file_name: string;
  file_size: number;
  content: string | null;
  download_url: string | null;
  row_count: number;
}

/** 导出格式 */
export type ExportFormat = 'csv' | 'excel' | 'json' | 'sql';
```

- [ ] **Step 2: Add exportTableData function**

After `queryTableData` function (around line 453), add:

```typescript
/** 导出表数据（按筛选条件导出全部数据） */
export async function exportTableData(
  id: string,
  request: {
    sql: string;
    format: ExportFormat;
    database_name?: string;
  }
): Promise<ExportDataResponse> {
  const response = await fetchWithTimeout(
    `${BASE_URL}/configs/${encodeURIComponent(id)}/export`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request),
      timeout: 120000, // 2 minutes for large exports
    }
  );
  return handleResponse<ExportDataResponse>(response);
}
```

Note: Uses `/configs/{id}/export` (not `/databases/{id}/export`) because the backend route is defined as `POST /configs/{id}/export` in `database_tool.py:537`. The timeout is 120s to handle large data exports.

- [ ] **Step 3: Verify no TypeScript errors**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors related to new code

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/databaseToolApi.ts
git commit -m "feat: 新增 exportTableData API 封装函数"
```

---

## Task 3: Add Export UI to TableDataViewer

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx`

**Interfaces:**
- Consumes: `api.exportTableData()` from Task 2
- Produces: Export button UI with quick CSV export and advanced format selection

- [ ] **Step 1: Add export state variables**

In `TableDataViewer.tsx`, after the existing state declarations (around line 30), add:

```typescript
// Export state
const [exporting, setExporting] = useState(false);
const [showExportMenu, setShowExportMenu] = useState(false);
```

- [ ] **Step 2: Add export handler function**

After `handleRefresh` function (around line 118), add:

```typescript
  /** 导出数据 */
  const handleExport = useCallback(async (format: 'csv' | 'excel' | 'json' | 'sql') => {
    if (!result?.success || !tableName) {
      toast.error(t.database.export.noData);
      return;
    }

    setExporting(true);
    setShowExportMenu(false);

    try {
      // Construct full SQL from current filter conditions
      const fullTableName = schemaName
        ? `${schemaName}.${tableName}`
        : tableName;
      const sql = [
        'SELECT *',
        `FROM ${fullTableName}`,
        whereClause ? `WHERE ${whereClause}` : '',
        orderByClause ? `ORDER BY ${orderByClause}` : '',
      ].filter(Boolean).join(' ');

      const response = await api.exportTableData(configId, {
        sql,
        format,
        database_name: databaseName,
      });

      // Create blob and trigger download
      let blob: Blob;
      let mimeType: string;

      if (format === 'excel') {
        // Excel returns Base64-encoded content
        const byteChars = atob(response.content || '');
        const byteNums = new Uint8Array(byteChars.length);
        for (let i = 0; i < byteChars.length; i++) {
          byteNums[i] = byteChars.charCodeAt(i);
        }
        blob = new Blob([byteNums], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        });
      } else {
        mimeType = format === 'csv'
          ? 'text/csv;charset=utf-8'
          : format === 'json'
            ? 'application/json;charset=utf-8'
            : 'text/plain;charset=utf-8';
        blob = new Blob([response.content || ''], { type: mimeType });
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = response.file_name;
      a.click();
      URL.revokeObjectURL(url);

      toast.success(t.database.export.success.replace('{count}', String(response.row_count)));
    } catch (error: unknown) {
      const err = error as { detail?: { message?: string } | string; message?: string };
      const detail = err?.detail;
      const errorMsg = (typeof detail === 'object' && detail?.message)
        || (typeof detail === 'string' && detail)
        || err?.message
        || t.database.export.failed;
      toast.error(errorMsg);
    } finally {
      setExporting(false);
    }
  }, [configId, tableName, databaseName, schemaName, whereClause, orderByClause, result, toast, t]);

  const handleQuickExport = useCallback(() => {
    handleExport('csv');
  }, [handleExport]);
```

- [ ] **Step 3: Add export buttons to toolbar**

In the toolbar area (around line 147-163), after the "Run" and refresh buttons, add export buttons. Replace the existing button div:

```tsx
           <div className="flex items-center space-x-2">
             {/* Run button (existing) */}
             <button
               onClick={handleExecute}
               disabled={loading}
               className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-1"
             >
               <i className="fas fa-play text-xs"></i>
               <span>Run</span>
             </button>

             {/* Refresh button (existing) */}
             <button
               onClick={handleRefresh}
               disabled={loading}
               className="bg-slate-700 text-slate-300 px-3 py-1.5 rounded text-sm hover:bg-slate-600 disabled:opacity-50"
             >
               <i className="fas fa-sync-alt"></i>
             </button>

             {/* Quick Export button */}
             <button
               onClick={handleQuickExport}
               disabled={exporting || !result?.success}
               className="bg-slate-700 text-slate-300 px-3 py-1.5 rounded text-sm hover:bg-slate-600 disabled:opacity-50 flex items-center space-x-1"
               title={t.database.export.quickExport}
             >
               {exporting ? (
                 <><i className="fas fa-spinner fa-spin text-xs"></i><span>{t.database.export.exporting}</span></>
               ) : (
                 <><i className="fas fa-download text-xs"></i><span>{t.database.export.quickExport}</span></>
               )}
             </button>

             {/* Advanced Export dropdown */}
             <div className="relative">
               <button
                 onClick={() => setShowExportMenu(!showExportMenu)}
                 disabled={exporting || !result?.success}
                 className="bg-slate-700 text-slate-300 px-2 py-1.5 rounded text-sm hover:bg-slate-600 disabled:opacity-50"
                 title={t.database.export.advancedExport}
               >
                 <i className="fas fa-chevron-down text-xs"></i>
               </button>

               {showExportMenu && (
                 <div className="absolute right-0 mt-1 w-32 bg-slate-800 rounded shadow-lg border border-slate-600 py-1 z-50">
                   <div className="px-3 py-1 text-xs text-slate-500 border-b border-slate-700">
                     {t.database.export.format}
                   </div>
                   {(['csv', 'excel', 'json', 'sql'] as const).map((fmt) => (
                     <button
                       key={fmt}
                       onClick={() => handleExport(fmt)}
                       disabled={exporting}
                       className="block w-full text-left px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700 hover:text-white disabled:opacity-50"
                     >
                       {fmt.toUpperCase()}
                     </button>
                   ))}
                 </div>
               )}
             </div>
           </div>
```

- [ ] **Step 4: Add click-outside handler to close dropdown**

Add a `useEffect` after the existing state declarations to close the export menu when clicking outside:

```typescript
  // Close export menu when clicking outside
  useEffect(() => {
    if (!showExportMenu) return;
    const handleClick = () => setShowExportMenu(false);
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, [showExportMenu]);
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx
git commit -m "feat: 表数据查看器增加导出按钮和高级导出下拉菜单"
```

---

## Task 4: Add i18n Strings

**Files:**
- Modify: `frontend/src/i18n/locales/zh-CN.ts`
- Modify: `frontend/src/i18n/locales/en-US.ts`

**Interfaces:**
- Consumes: None
- Produces: `t.database.export.*` keys used in Task 3

- [ ] **Step 1: Add Chinese strings**

In `frontend/src/i18n/locales/zh-CN.ts`, inside the `database` object (after `executor` section, around line 620), add:

```typescript
    export: {
      quickExport: '快速导出',
      advancedExport: '高级导出',
      exporting: '导出中...',
      success: '导出成功：{count} 行',
      failed: '导出失败',
      format: '导出格式',
      noData: '没有可导出的数据，请先执行查询',
    },
```

- [ ] **Step 2: Add English strings**

In `frontend/src/i18n/locales/en-US.ts`, inside the `database` object (after `executor` section, in the same position as Chinese), add:

```typescript
    export: {
      quickExport: 'Quick Export',
      advancedExport: 'Advanced Export',
      exporting: 'Exporting...',
      success: 'Exported: {count} rows',
      failed: 'Export failed',
      format: 'Export Format',
      noData: 'No data to export. Please run a query first',
    },
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/i18n/locales/zh-CN.ts frontend/src/i18n/locales/en-US.ts
git commit -m "feat: 添加数据库导出功能国际化文案"
```

---

## Task 5: Verification

**Files:**
- No code changes, browser verification only

- [ ] **Step 1: Restart services**

Run: `python dev-services.py restart`
Expected: Both frontend and backend restart successfully

- [ ] **Step 2: Open browser to database tool**

Open http://localhost:5178, navigate to Database Tool, connect to a database, open a table

- [ ] **Step 3: Verify quick export (CSV)**

1. Enter a WHERE clause (e.g., `sales_type = '01'`)
2. Click "Run"
3. Verify data loads
4. Click "快速导出" button
5. Verify: file downloads automatically, contains all matching rows (not just current page), has header row

- [ ] **Step 4: Verify advanced export (Excel)**

1. Click the dropdown arrow next to quick export
2. Select "EXCEL"
3. Verify: `.xlsx` file downloads, opens correctly in spreadsheet app

- [ ] **Step 5: Verify advanced export (JSON)**

1. Select "JSON" from dropdown
2. Verify: `.json` file downloads with proper formatting

- [ ] **Step 6: Verify advanced export (SQL)**

1. Select "SQL" from dropdown
2. Verify: `.sql` file downloads with INSERT statements

- [ ] **Step 7: Verify edge cases**

1. Empty result (WHERE matches nothing): clicking export shows "没有可导出的数据"
2. No WHERE clause: exports entire table
3. Browser console has no errors

- [ ] **Step 8: Final commit (if any hotfixes needed)**

```bash
git add -A
git commit -m "fix: 导出功能验证修复"
```
