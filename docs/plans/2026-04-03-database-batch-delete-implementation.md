# 表数据批量删除功能 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为数据库管理工具的表数据查看器添加批量删除功能，支持用户通过复选框多选行后基于主键批量删除记录

**Architecture:** 前端在 ResultViewer 组件中添加删除按钮和确认弹窗，调用新增的 batchDeleteRows API；后端新增专用路由和 Service 方法，构建基于主键的 DELETE SQL 并执行

**Tech Stack:** React + TypeScript (前端), FastAPI + Python (后端), MySQL/PostgreSQL/SQLite (数据库)

**Design Doc:** `docs/plans/2026-04-03-database-batch-delete-design.md`

---

## Task 1: 后端 — 新增 BatchDeleteRequest 和 BatchDeleteResult 模型

**Files:**
- Modify: `backend/app/models/database_tool_models.py` (append after line 265)

**Step 1: 在 database_tool_models.py 末尾添加批量删除的请求/响应模型**

在文件末尾（`RestoreDatabaseResponse` 类之后）添加：

```python
# ============ 批量删除模型 ============

class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    database_name: Optional[str] = Field(None, description="数据库名称（多数据库连接时使用）")
    primary_keys: List[str] = Field(..., min_items=1, description="主键列名列表")
    key_values: List[Dict[str, Any]] = Field(..., min_items=1, description="每行的主键值")


class BatchDeleteResult(BaseModel):
    """批量删除结果"""
    success: bool
    deleted_count: int = Field(..., description="成功删除行数")
    failed_count: int = Field(default=0, description="失败行数")
    error_message: Optional[str] = Field(None, description="错误信息")
    execution_time_ms: float = Field(..., description="执行耗时（毫秒）")
```

**Step 2: 验证模型导入**

确认 `database_tool.py` 的 import 语句中已有 `from app.models.database_tool_models import (...)`，需要在其中添加 `BatchDeleteRequest, BatchDeleteResult`。

**Step 3: 验证语法**

Run: `cd backend && python -m py_compile app/models/database_tool_models.py`
Expected: No output (success)

**Step 4: Commit**

```bash
git add backend/app/models/database_tool_models.py
git commit -m "feat(database): add BatchDeleteRequest and BatchDeleteResult models"
```

---

## Task 2: 后端 — 新增 batch_delete_rows Service 方法

**Files:**
- Modify: `backend/app/services/database_tool_service.py` (append at end of class)

**Step 1: 在 DatabaseToolService 类末尾添加 batch_delete_rows 方法**

在文件末尾添加以下方法（在类的最后一个方法之后）：

```python
    @staticmethod
    def batch_delete_rows(
        user_id: str,
        config_id: str,
        table_name: str,
        request: 'BatchDeleteRequest'
    ) -> 'BatchDeleteResult':
        """批量删除表中的多行数据（基于主键）"""
        from app.models.database_tool_models import BatchDeleteRequest, BatchDeleteResult
        
        start_time = datetime.now()
        
        # 1. 获取数据库配置
        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            return BatchDeleteResult(
                success=False, deleted_count=0, failed_count=0,
                error_message="Configuration not found", execution_time_ms=0
            )
        
        try:
            password = EncryptionUtils.decrypt(config_row['password_encrypted'])
        except Exception:
            return BatchDeleteResult(
                success=False, deleted_count=0, failed_count=0,
                error_message="Failed to decrypt password", execution_time_ms=0
            )
        
        target_db = request.database_name if request.database_name else config_row['database_name']
        
        config_dict = {
            "db_type": config_row['db_type'],
            "host": config_row['host'],
            "port": config_row['port'],
            "database_name": target_db,
            "username": config_row['username'],
            "password": password,
            "charset": config_row['charset'],
            "max_pool_size": config_row['max_pool_size']
        }
        
        engine_key = f"{config_id}:{target_db}" if request.database_name else config_id
        db_type = config_row['db_type']
        
        # 2. 构建标识符引用函数
        def quote_ident(name: str) -> str:
            if db_type == DatabaseType.SQLSERVER:
                return f'[{name}]'
            return f'"{name}"'
        
        # 3. 值转义函数
        def escape_value(val: Any) -> str:
            if val is None:
                return 'NULL'
            if isinstance(val, bool):
                if db_type == DatabaseType.POSTGRESQL:
                    return 'TRUE' if val else 'FALSE'
                return '1' if val else '0'
            if isinstance(val, (int, float)):
                return str(val)
            # 字符串：单引号包裹，内部单引号转义
            escaped = str(val).replace("'", "''")
            return f"'{escaped}'"
        
        # 4. 构建 WHERE 子句
        table_quoted = quote_ident(table_name)
        
        if len(request.primary_keys) == 1:
            # 单主键: DELETE FROM "table" WHERE "id" IN (1, 2, 3)
            pk_col = quote_ident(request.primary_keys[0])
            values = [escape_value(row[request.primary_keys[0]]) for row in request.key_values]
            where_clause = f"{pk_col} IN ({', '.join(values)})"
        else:
            # 复合主键: DELETE FROM "table" WHERE ("a", "b") IN ((1, 'x'), (2, 'y'))
            pk_cols = ', '.join(quote_ident(k) for k in request.primary_keys)
            tuples = []
            for row in request.key_values:
                vals = ', '.join(escape_value(row[k]) for k in request.primary_keys)
                tuples.append(f"({vals})")
            where_clause = f"({pk_cols}) IN ({', '.join(tuples)})"
        
        sql = f"DELETE FROM {table_quoted} WHERE {where_clause}"
        
        logger.info(f"批量删除: 表={table_name}, 主键={request.primary_keys}, 行数={len(request.key_values)}")
        
        # 5. 执行 SQL
        try:
            result = SQLExecutor.execute(engine_key, config_dict, sql)
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            
            return BatchDeleteResult(
                success=result.success,
                deleted_count=result.affected_rows or 0,
                failed_count=0 if result.success else len(request.key_values),
                error_message=result.error_message,
                execution_time_ms=elapsed
            )
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"批量删除执行失败: {e}")
            return BatchDeleteResult(
                success=False, deleted_count=0, failed_count=len(request.key_values),
                error_message=str(e), execution_time_ms=elapsed
            )
```

**Step 2: 验证语法**

Run: `cd backend && python -m py_compile app/services/database_tool_service.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add backend/app/services/database_tool_service.py
git commit -m "feat(database): add batch_delete_rows service method"
```

---

## Task 3: 后端 — 新增 batch-delete 路由

**Files:**
- Modify: `backend/app/routes/database_tool.py` (add import + new route)

**Step 1: 更新 import 语句**

在文件顶部的 import 中，找到 `from app.models.database_tool_models import (...)`，在括号内添加 `BatchDeleteRequest, BatchDeleteResult`：

```python
from app.models.database_tool_models import (
    DatabaseConfigResponse, CreateDatabaseRequest, UpdateDatabaseRequest,
    TestConnectionRequest, ConnectionTestResult,
    SQLExecutionRequest, SQLExecutionResult, ExecutionHistory,
    TableSchema, TableData, TableModificationRequest,
    ExportDataRequest, ExportDataResponse, ExportFormat,
    ImportDataRequest, ImportDataResponse,
    ExplainPlanRequest, ExplainPlanResponse,
    TablePreviewRequest, TablePreviewResponse,
    AutoCompleteRequest, AutoCompleteResponse,
    BackupDatabaseRequest, BackupDatabaseResponse,
    RestoreDatabaseRequest, RestoreDatabaseResponse,
    BatchDeleteRequest, BatchDeleteResult
)
```

**Step 2: 在文件末尾添加新路由**

在文件最后（restore_database 路由之后）添加：

```python
# ============ 批量删除 API ============

@router.post("/databases/{id}/tables/{table}/batch-delete", response_model=BatchDeleteResult)
async def batch_delete_rows(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    request: BatchDeleteRequest = Body(...),
    user_id: str = Depends(get_current_user_id)
):
    """批量删除表中的多行数据（基于主键）"""
    try:
        return DatabaseToolService.batch_delete_rows(user_id, id, table, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 3: 验证语法**

Run: `cd backend && python -m py_compile app/routes/database_tool.py`
Expected: No output (success)

**Step 4: 验证后端启动**

Run: `cd backend && uvicorn app.main:app --port 19092 &` then `sleep 3 && curl -s http://localhost:19092/docs | head -5`
Expected: Swagger UI HTML content

**Step 5: Commit**

```bash
git add backend/app/routes/database_tool.py
git commit -m "feat(database): add POST /tables/{table}/batch-delete route"
```

---

## Task 4: 前端 — 新增 batchDeleteRows API 函数

**Files:**
- Modify: `frontend/src/api/databaseToolApi.ts` (append at end)

**Step 1: 在 databaseToolApi.ts 末尾添加批量删除 API 函数**

在文件末尾（`searchTables` 函数之后）添加：

```typescript
// Batch Delete

export interface BatchDeleteRequest {
  database_name?: string;
  primary_keys: string[];
  key_values: Record<string, any>[];
}

export interface BatchDeleteResult {
  success: boolean;
  deleted_count: number;
  failed_count: number;
  error_message?: string;
  execution_time_ms: number;
}

export async function batchDeleteRows(
  id: string,
  table: string,
  params: BatchDeleteRequest
): Promise<BatchDeleteResult> {
  const response = await fetch(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/batch-delete`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(params)
    }
  );
  return handleResponse<BatchDeleteResult>(response);
}
```

**Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`
Expected: No errors related to databaseToolApi.ts

**Step 3: Commit**

```bash
git add frontend/src/api/databaseToolApi.ts
git commit -m "feat(database): add batchDeleteRows API function"
```

---

## Task 5: 前端 — 添加 i18n 翻译

**Files:**
- Modify: `frontend/src/i18n/locales/zh-CN.ts` (add batchDelete section inside database)
- Modify: `frontend/src/i18n/locales/en-US.ts` (add batchDelete section inside database)

**Step 1: 在 zh-CN.ts 的 database 对象中添加 batchDelete**

找到 `database: { ... }` 对象（约在第 398 行的 `},` 之前），在 `dialog` 块之后、`database` 闭合括号之前添加：

```typescript
    batchDelete: {
      confirmTitle: '确认删除',
      confirmMessage: '即将删除 {count} 条记录',
      table: '表',
      primaryKey: '主键',
      condition: '条件',
      deleteButton: '确认删除',
      cancelButton: '取消',
      success: '成功删除 {count} 条记录',
      failed: '删除失败: {error}',
      noPrimaryKey: '该表无主键，无法批量删除',
    },
```

**Step 2: 在 en-US.ts 的 database 对象中添加 batchDelete**

同样位置添加：

```typescript
    batchDelete: {
      confirmTitle: 'Confirm Delete',
      confirmMessage: 'About to delete {count} rows',
      table: 'Table',
      primaryKey: 'Primary Key',
      condition: 'Condition',
      deleteButton: 'Confirm Delete',
      cancelButton: 'Cancel',
      success: 'Successfully deleted {count} rows',
      failed: 'Delete failed: {error}',
      noPrimaryKey: 'No primary key found, batch delete is not available',
    },
```

**Step 3: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --skipLibCheck 2>&1 | grep -i "i18n\|locale" | head -10`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/i18n/locales/zh-CN.ts frontend/src/i18n/locales/en-US.ts
git commit -m "feat(database): add i18n translations for batch delete"
```

---

## Task 6: 前端 — ResultViewer 添加删除按钮和确认弹窗

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx`

**Step 1: 导入新的依赖**

在文件顶部的 import 区域，添加：

```typescript
import { useI18n, interpolate } from '../../../../i18n';
import * as api from '../../../../api/databaseToolApi';
import { useToast } from '../../../../hooks/useToast';
```

确认 `useToast` 和 `api` 是否已导入（ResultViewer 当前可能没有），如果没有则添加。

**Step 2: 更新组件 Props 接口**

在 `ResultViewerProps` 接口中添加：

```typescript
interface ResultViewerProps {
  result: SQLExecutionResult | null;
  tableName?: string;
  schema?: TableSchema | null;
  enableSelection?: boolean;
  onSelectionChange?: (selectedIndices: number[]) => void;
  configId?: string;           // 新增
  databaseName?: string;       // 新增
  onDeleted?: () => void;      // 新增：删除成功后的回调
}
```

**Step 3: 在组件内部添加状态和处理函数**

在组件函数体内（现有 state 之后）添加：

```typescript
const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
const [deleting, setDeleting] = useState(false);

const getSelectedRows = () => {
  if (!result?.result_data) return [];
  return result.result_data.filter((_, index) => selectedIndices.has(index));
};

const handleBatchDelete = () => {
  if (!primaryKey || primaryKey.length === 0) return;
  setShowDeleteConfirm(true);
};

const confirmDelete = async () => {
  if (!configId || !tableName) return;
  
  setDeleting(true);
  try {
    const selectedRows = getSelectedRows();
    const keyValues = selectedRows.map(row => {
      const keyObj: Record<string, any> = {};
      primaryKey.forEach(pk => { keyObj[pk] = row[pk]; });
      return keyObj;
    });
    
    const deleteResult = await api.batchDeleteRows(configId, tableName, {
      database_name: databaseName,
      primary_keys: primaryKey,
      key_values: keyValues
    });
    
    if (deleteResult.success) {
      toast.success(interpolate(t.database.batchDelete.success, { count: String(deleteResult.deleted_count) }));
      setShowDeleteConfirm(false);
      // 通知父组件刷新
      if (onDeleted) onDeleted();
    } else {
      toast.error(interpolate(t.database.batchDelete.failed, { error: deleteResult.error_message || 'Unknown error' }));
    }
  } catch (error: any) {
    toast.error(error.message || 'Delete failed');
  } finally {
    setDeleting(false);
  }
};
```

**Step 4: 在操作按钮区域添加删除按钮**

找到现有的 Insert/Update/JSON 按钮区域（约在第 164-190 行），在 JSON 按钮之后添加：

```tsx
<button 
  onClick={handleBatchDelete}
  disabled={!primaryKey || primaryKey.length === 0}
  className={`px-2 py-1 text-xs rounded flex items-center gap-1 transition-colors ${
    (!primaryKey || primaryKey.length === 0)
      ? 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
      : 'bg-red-600/80 hover:bg-red-600 text-white'
  }`}
  title={(!primaryKey || primaryKey.length === 0) 
    ? t.database.batchDelete.noPrimaryKey 
    : 'Delete selected rows'}
>
  <i className={`fas ${(!primaryKey || primaryKey.length === 0) ? 'fa-ban' : 'fa-trash'}`}></i>
  Delete
</button>
```

**Step 5: 在组件末尾添加确认弹窗**

在 `JsonViewModal` 之后、组件闭合之前添加：

```tsx
{/* Delete Confirmation Modal */}
{showDeleteConfirm && (
  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
    <div className="bg-slate-800 border border-slate-700 rounded-lg shadow-xl max-w-md w-full mx-4">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-700 flex items-center gap-3">
        <i className="fas fa-exclamation-triangle text-yellow-400 text-xl"></i>
        <h3 className="text-lg font-semibold text-slate-100">{t.database.batchDelete.confirmTitle}</h3>
      </div>
      
      {/* Body */}
      <div className="px-6 py-4 space-y-3">
        <p className="text-slate-300">
          {interpolate(t.database.batchDelete.confirmMessage, { count: String(selectedIndices.size) })}
        </p>
        
        <div className="bg-slate-900 rounded p-3 space-y-2 text-sm">
          <div className="flex gap-2">
            <span className="text-slate-500 min-w-[60px]">{t.database.batchDelete.table}:</span>
            <span className="text-slate-200">{tableName}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-slate-500 min-w-[60px]">{t.database.batchDelete.primaryKey}:</span>
            <span className="text-slate-200">{primaryKey?.join(', ')}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-slate-500 min-w-[60px]">{t.database.batchDelete.condition}:</span>
            <span className="text-slate-200 font-mono text-xs break-all">
              {(() => {
                const rows = getSelectedRows();
                if (primaryKey && primaryKey.length === 1) {
                  const pk = primaryKey[0];
                  const vals = rows.map(r => String(r[pk]));
                  return `${pk} IN (${vals.join(', ')})`;
                } else if (primaryKey && primaryKey.length > 1) {
                  return rows.map(r => 
                    `(${primaryKey.map(pk => `${pk}=${String(r[pk])}`).join(', ')})`
                  ).join(', ');
                }
                return '';
              })()}
            </span>
          </div>
        </div>
      </div>
      
      {/* Footer */}
      <div className="px-6 py-4 border-t border-slate-700 flex justify-end gap-3">
        <button
          onClick={() => setShowDeleteConfirm(false)}
          disabled={deleting}
          className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded text-sm disabled:opacity-50"
        >
          {t.database.batchDelete.cancelButton}
        </button>
        <button
          onClick={confirmDelete}
          disabled={deleting}
          className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded text-sm disabled:opacity-50 flex items-center gap-2"
        >
          {deleting && <i className="fas fa-spinner fa-spin"></i>}
          {t.database.batchDelete.deleteButton}
        </button>
      </div>
    </div>
  </div>
)}
```

**Step 6: 更新 TableDataViewer.tsx 传递新 props**

在 `TableDataViewer.tsx` 中，找到 `<ResultViewer ...>` 的调用（约在第 156 行），添加新 props：

```tsx
<ResultViewer 
  result={result} 
  tableName={tableName}
  schema={schema}
  enableSelection={true}
  configId={configId}
  databaseName={databaseName}
  onDeleted={() => fetchData(page)}
/>
```

**Step 7: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit --skipLibCheck 2>&1 | grep -i "ResultViewer\|TableData" | head -10`
Expected: No errors

**Step 8: 验证前端构建**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: Build successful

**Step 9: Commit**

```bash
git add frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx
git commit -m "feat(database): add batch delete button and confirmation modal"
```

---

## Task 7: 端到端验证

**Files:**
- No file changes

**Step 1: 启动后端**

Run: `cd backend && uvicorn app.main:app --reload --port 19092`
Expected: Server running on http://localhost:19092

**Step 2: 启动前端**

Run: `cd frontend && npm run dev`
Expected: Server running on http://localhost:5173 (or configured port)

**Step 3: 浏览器验证**

1. 打开浏览器访问数据库管理工具页面
2. 连接到一个有主键的数据库，查看表数据
3. 勾选多行数据
4. 确认 Delete 按钮出现
5. 点击 Delete，确认弹窗显示正确的主键条件
6. 点击"确认删除"
7. 验证：表格刷新，Toast 显示成功消息
8. 验证：无主键的表 Delete 按钮禁用

**Step 4: 检查后端日志**

确认删除操作被记录到执行历史

---

## Task 8: 运行代码规范检查

**Files:**
- No file changes

**Step 1: 后端代码检查**

Run: `cd backend && ruff check app/models/database_tool_models.py app/services/database_tool_service.py app/routes/database_tool.py`
Expected: All checks passed

**Step 2: 前端代码检查**

Run: `cd frontend && npx eslint src/components/Tools/DatabaseTool/components/ResultViewer.tsx src/api/databaseToolApi.ts 2>&1 | head -20`
Expected: No errors (or only pre-existing warnings)

**Step 3: 最终 Commit**

```bash
git add -A
git commit -m "chore: lint and format batch delete feature"
```
