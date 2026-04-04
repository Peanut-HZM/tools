# 数据库工具表数据内联编辑 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为数据库表数据查看器添加双击单元格编辑、新增行、批量保存功能，支持多语言。

**Architecture:** 后端新增 insert-row 和 update-row 两个 API 端点，基于 SQLAlchemy 执行动态 SQL。前端在 ResultViewer 中新增编辑状态管理（cellEdits Map + newRows 数组），双击单元格切换为输入框，新增行在表格顶部渲染，统一通过"保存"按钮批量提交。数据类型基于 schema.columns 自动识别。

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy, React 18, TypeScript, Tailwind CSS, 项目自研 i18n 系统

---

### Task 1: 新增后端数据模型（InsertRowRequest / UpdateRowRequest）

**Files:**
- Modify: `backend/app/models/database_tool_models.py`

**Step 1: 查看现有模型文件结构**

Run: `grep -n "class Batch" backend/app/models/database_tool_models.py`
Expected: 看到 BatchDeleteRequest 和 BatchDeleteResult 的定义位置

**Step 2: 在 BatchDeleteResult 之后新增两个请求模型**

在 `BatchDeleteResult` 类定义之后，新增：

```python
class InsertRowRequest(BaseModel):
    """插入单行数据请求"""
    database_name: Optional[str] = None
    columns: Dict[str, Any]


class UpdateRowRequest(BaseModel):
    """更新单行数据请求（基于主键）"""
    database_name: Optional[str] = None
    primary_keys: List[str]
    key_values: Dict[str, Any]
    columns: Dict[str, Any]


class RowOperationResult(BaseModel):
    """行操作结果"""
    success: bool
    affected_rows: int = 0
    execution_time_ms: float = 0
    error_message: Optional[str] = None
```

**Step 3: 更新 `__init__.py` 导出**

Modify: `backend/app/models/__init__.py`

在现有导出列表中加入 `InsertRowRequest`, `UpdateRowRequest`, `RowOperationResult`。

**Step 4: 验证 Python 语法**

Run: `cd backend && python -m py_compile app/models/database_tool_models.py`
Expected: 无输出（语法正确）

---

### Task 2: 新增后端服务方法（insert_row / update_row）

**Files:**
- Modify: `backend/app/services/database_tool_service.py`

**Step 1: 在 batch_delete_rows 方法之后新增 insert_row 方法**

在文件末尾（batch_delete_rows 之后）新增：

```python
    @staticmethod
    def insert_row(
        user_id: str, config_id: str, table_name: str, request: "InsertRowRequest"
    ) -> "RowOperationResult":
        from app.models.database_tool_models import (
            InsertRowRequest,
            RowOperationResult,
        )

        start_time = datetime.now()

        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            return RowOperationResult(
                success=False,
                affected_rows=0,
                error_message="Configuration not found",
                execution_time_ms=0,
            )

        try:
            password = EncryptionUtils.decrypt(config_row["password_encrypted"])
        except Exception:
            return RowOperationResult(
                success=False,
                affected_rows=0,
                error_message="Failed to decrypt password",
                execution_time_ms=0,
            )

        target_db = (
            request.database_name
            if request.database_name
            else config_row["database_name"]
        )

        config_dict = {
            "db_type": config_row["db_type"],
            "host": config_row["host"],
            "port": config_row["port"],
            "database_name": target_db,
            "username": config_row["username"],
            "password": password,
            "charset": config_row["charset"],
            "max_pool_size": config_row["max_pool_size"],
        }

        engine_key = f"{config_id}:{target_db}" if request.database_name else config_id
        db_type = config_row["db_type"]

        def quote_ident(name: str) -> str:
            if db_type == DatabaseType.SQLSERVER:
                return f"[{name}]"
            if db_type == DatabaseType.POSTGRESQL:
                return f'"{name}"'
            return f"`{name}`"

        def escape_value(val: Any) -> str:
            if val is None:
                return "NULL"
            if isinstance(val, bool):
                if db_type == DatabaseType.POSTGRESQL:
                    return "TRUE" if val else "FALSE"
                return "1" if val else "0"
            if isinstance(val, (int, float)):
                return str(val)
            escaped = str(val).replace("'", "''")
            return f"'{escaped}'"

        table_quoted = quote_ident(table_name)
        columns = request.columns
        col_names = ", ".join(quote_ident(k) for k in columns.keys())
        col_values = ", ".join(escape_value(v) for v in columns.values())

        sql = f"INSERT INTO {table_quoted} ({col_names}) VALUES ({col_values})"

        logger.info(f"插入行: 表={table_name}, 列={list(columns.keys())}")

        try:
            result = SQLExecutor.execute(engine_key, config_dict, sql)
            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            return RowOperationResult(
                success=result.success,
                affected_rows=result.affected_rows or 0,
                execution_time_ms=elapsed,
                error_message=result.error_message,
            )
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"插入行失败: {e}")
            return RowOperationResult(
                success=False,
                affected_rows=0,
                error_message=str(e),
                execution_time_ms=elapsed,
            )
```

**Step 2: 在 insert_row 之后新增 update_row 方法**

```python
    @staticmethod
    def update_row(
        user_id: str, config_id: str, table_name: str, request: "UpdateRowRequest"
    ) -> "RowOperationResult":
        from app.models.database_tool_models import (
            UpdateRowRequest,
            RowOperationResult,
        )

        start_time = datetime.now()

        config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
        if not config_row:
            return RowOperationResult(
                success=False,
                affected_rows=0,
                error_message="Configuration not found",
                execution_time_ms=0,
            )

        try:
            password = EncryptionUtils.decrypt(config_row["password_encrypted"])
        except Exception:
            return RowOperationResult(
                success=False,
                affected_rows=0,
                error_message="Failed to decrypt password",
                execution_time_ms=0,
            )

        if not request.primary_keys or len(request.primary_keys) == 0:
            return RowOperationResult(
                success=False,
                affected_rows=0,
                error_message="Primary key is required for update",
                execution_time_ms=0,
            )

        target_db = (
            request.database_name
            if request.database_name
            else config_row["database_name"]
        )

        config_dict = {
            "db_type": config_row["db_type"],
            "host": config_row["host"],
            "port": config_row["port"],
            "database_name": target_db,
            "username": config_row["username"],
            "password": password,
            "charset": config_row["charset"],
            "max_pool_size": config_row["max_pool_size"],
        }

        engine_key = f"{config_id}:{target_db}" if request.database_name else config_id
        db_type = config_row["db_type"]

        def quote_ident(name: str) -> str:
            if db_type == DatabaseType.SQLSERVER:
                return f"[{name}]"
            if db_type == DatabaseType.POSTGRESQL:
                return f'"{name}"'
            return f"`{name}`"

        def escape_value(val: Any) -> str:
            if val is None:
                return "NULL"
            if isinstance(val, bool):
                if db_type == DatabaseType.POSTGRESQL:
                    return "TRUE" if val else "FALSE"
                return "1" if val else "0"
            if isinstance(val, (int, float)):
                return str(val)
            escaped = str(val).replace("'", "''")
            return f"'{escaped}'"

        table_quoted = quote_ident(table_name)

        # Build SET clause
        set_parts = []
        for col_name, col_value in request.columns.items():
            set_parts.append(f"{quote_ident(col_name)} = {escape_value(col_value)}")
        set_clause = ", ".join(set_parts)

        # Build WHERE clause (based on primary keys)
        where_parts = []
        for pk in request.primary_keys:
            pk_value = request.key_values.get(pk)
            where_parts.append(f"{quote_ident(pk)} = {escape_value(pk_value)}")
        where_clause = " AND ".join(where_parts)

        sql = f"UPDATE {table_quoted} SET {set_clause} WHERE {where_clause}"

        logger.info(f"更新行: 表={table_name}, 主键={request.primary_keys}, 列={list(request.columns.keys())}")

        try:
            result = SQLExecutor.execute(engine_key, config_dict, sql)
            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            return RowOperationResult(
                success=result.success,
                affected_rows=result.affected_rows or 0,
                execution_time_ms=elapsed,
                error_message=result.error_message,
            )
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"更新行失败: {e}")
            return RowOperationResult(
                success=False,
                affected_rows=0,
                error_message=str(e),
                execution_time_ms=elapsed,
            )
```

**Step 3: 验证 Python 语法**

Run: `cd backend && python -m py_compile app/services/database_tool_service.py`
Expected: 无输出（语法正确）

---

### Task 3: 新增后端路由（insert-row / update-row）

**Files:**
- Modify: `backend/app/routes/database_tool.py`

**Step 1: 导入新模型**

在文件顶部导入区域，新增：

```python
from app.models.database_tool_models import (
    # ... existing imports ...
    InsertRowRequest,
    UpdateRowRequest,
    RowOperationResult,
)
```

**Step 2: 在 batch_delete_rows 路由之后新增两个路由**

在文件末尾（batch_delete_rows 之后）新增：

```python
# ============ 行数据插入/更新 API ============


@router.post(
    "/databases/{id}/tables/{table}/insert-row", response_model=RowOperationResult
)
async def insert_table_row(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    request: InsertRowRequest = Body(...),
    user_id: str = Depends(get_current_user_id),
):
    """向表中插入一行数据"""
    try:
        return DatabaseToolService.insert_row(user_id, id, table, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/databases/{id}/tables/{table}/update-row", response_model=RowOperationResult
)
async def update_table_row(
    id: str = PathParam(..., description="Configuration ID"),
    table: str = PathParam(..., description="Table Name"),
    request: UpdateRowRequest = Body(...),
    user_id: str = Depends(get_current_user_id),
):
    """基于主键更新表中一行数据"""
    try:
        return DatabaseToolService.update_row(user_id, id, table, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 3: 验证 Python 语法**

Run: `cd backend && python -m py_compile app/routes/database_tool.py`
Expected: 无输出（语法正确）

---

### Task 4: 新增前端 TypeScript 类型

**Files:**
- Modify: `frontend/src/types/databaseTool.ts`

**Step 1: 在文件末尾新增类型定义**

在 `DatabaseStructure` 接口之后新增：

```typescript
export interface InsertRowRequest {
  database_name?: string;
  columns: Record<string, any>;
}

export interface UpdateRowRequest {
  database_name?: string;
  primary_keys: string[];
  key_values: Record<string, any>;
  columns: Record<string, any>;
}

export interface RowOperationResult {
  success: boolean;
  affected_rows: number;
  execution_time_ms: number;
  error_message?: string;
}
```

**Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -i "databaseTool"`
Expected: 无新增错误

---

### Task 5: 新增前端 API 函数

**Files:**
- Modify: `frontend/src/api/databaseToolApi.ts`

**Step 1: 更新导入语句**

将现有导入：
```typescript
import {
  // ... existing types ...
} from '../types/databaseTool';
```

新增 `InsertRowRequest`, `UpdateRowRequest`, `RowOperationResult`。

**Step 2: 在 batchDeleteRows 函数之后新增 API 函数**

```typescript
export async function insertRow(
  id: string,
  table: string,
  params: InsertRowRequest
): Promise<RowOperationResult> {
  const response = await fetch(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/insert-row`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(params)
    }
  );
  return handleResponse<RowOperationResult>(response);
}

export async function updateRow(
  id: string,
  table: string,
  params: UpdateRowRequest
): Promise<RowOperationResult> {
  const response = await fetch(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/update-row`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(params)
    }
  );
  return handleResponse<RowOperationResult>(response);
}
```

**Step 3: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -i "databaseToolApi"`
Expected: 无新增错误

---

### Task 6: 新增 i18n 翻译键

**Files:**
- Modify: `frontend/src/i18n/locales/zh-CN.ts`
- Modify: `frontend/src/i18n/locales/en-US.ts`

**Step 1: 在 zh-CN.ts 的 `database.executor` 中新增**

找到 `database.executor` 对象（已在之前的任务中扩展），新增：

```ts
executor: {
  // ... existing keys ...
  addRow: '新增行',
  saveChanges: '保存 ({count})',
  discardChanges: '取消',
  saveSuccess: '保存成功',
  saveFailed: '保存失败: {error}',
  newRow: '新',
},
```

同时在 `database` 下新增 `editor` 对象：

```ts
database: {
  // ... existing sections ...
  editor: {
    noPrimaryKey: '该表无主键，无法编辑',
  },
},
```

**Step 2: 在 en-US.ts 中对应新增**

```ts
executor: {
  // ... existing keys ...
  addRow: 'Add Row',
  saveChanges: 'Save ({count})',
  discardChanges: 'Discard',
  saveSuccess: 'Save successful',
  saveFailed: 'Save failed: {error}',
  newRow: 'New',
},
```

```ts
database: {
  // ... existing sections ...
  editor: {
    noPrimaryKey: 'No primary key, editing disabled',
  },
},
```

**Step 3: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -i "zh-CN\|en-US"`
Expected: 无新增错误

---

### Task 7: 核心前端实现 — ResultViewer.tsx 内联编辑

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx`

这是最大的变更，分多个子步骤。

#### Step 7.1: 新增状态声明

在现有 `useState` 声明区域（约第 33-36 行之后）新增：

```typescript
// 内联编辑状态
const [cellEdits, setCellEdits] = useState<Map<string, { oldValue: any; newValue: any }>>(new Map());
const [newRows, setNewRows] = useState<Record<string, any>[]>([]);
const [editingCell, setEditingCell] = useState<string | null>(null);
const [saving, setSaving] = useState(false);
```

#### Step 7.2: 新增辅助函数

在 `confirmDelete` 函数之后，新增以下函数：

```typescript
// --- 内联编辑辅助函数 ---

const getEditKey = (rowIndex: number, colName: string) => `${rowIndex}:${colName}`;

const handleCellDoubleClick = (rowIndex: number, colName: string) => {
  if (!primaryKey || primaryKey.length === 0) return;
  const key = getEditKey(rowIndex, colName);
  if (!cellEdits.has(key)) {
    const row = result?.result_data?.[rowIndex];
    if (row) {
      setCellEdits(prev => new Map(prev).set(key, {
        oldValue: row[colName],
        newValue: row[colName]
      }));
    }
  }
  setEditingCell(key);
};

const handleCellChange = (rowIndex: number, colName: string, value: string) => {
  const key = getEditKey(rowIndex, colName);
  setCellEdits(prev => {
    const next = new Map(prev);
    const existing = next.get(key);
    if (existing) {
      // 根据列类型转换值
      const colDef = schema?.columns?.find((c: any) => c.name === colName);
      let converted: any = value;
      if (value === '' || value.toLowerCase() === 'null') {
        converted = null;
      } else if (colDef?.type?.toLowerCase().includes('int') || colDef?.type?.toLowerCase().includes('float') || colDef?.type?.toLowerCase().includes('decimal')) {
        converted = isNaN(Number(value)) ? value : Number(value);
      }
      next.set(key, { ...existing, newValue: converted });
    }
    return next;
  });
};

const handleNewRowChange = (rowIndex: number, colName: string, value: string) => {
  setNewRows(prev => {
    const next = [...prev];
    const row = { ...next[rowIndex] };
    let converted: any = value;
    if (value === '' || value.toLowerCase() === 'null') {
      converted = null;
    } else {
      const colDef = schema?.columns?.find((c: any) => c.name === colName);
      if (colDef?.type?.toLowerCase().includes('int') || colDef?.type?.toLowerCase().includes('float') || colDef?.type?.toLowerCase().includes('decimal')) {
        converted = isNaN(Number(value)) ? value : Number(value);
      }
    }
    row[colName] = converted;
    next[rowIndex] = row;
    return next;
  });
};

const finishEdit = () => {
  setEditingCell(null);
};

const handleAddRow = () => {
  if (!schema?.columns) return;
  const emptyRow: Record<string, any> = {};
  schema.columns.forEach((col: any) => {
    emptyRow[col.name] = null;
  });
  setNewRows(prev => [emptyRow, ...prev]);
};

const handleRemoveNewRow = (index: number) => {
  setNewRows(prev => prev.filter((_, i) => i !== index));
};

const handleDiscardChanges = () => {
  setCellEdits(new Map());
  setNewRows([]);
  setEditingCell(null);
};

const handleSave = async () => {
  if (!configId || !tableName) return;
  
  setSaving(true);
  try {
    // 1. 保存新增行
    for (const newRow of newRows) {
      const insertResult = await api.insertRow(configId, tableName, {
        database_name: databaseName,
        columns: newRow
      });
      if (!insertResult.success) {
        toast.error(interpolate(t.database.executor.saveFailed, { error: insertResult.error_message || 'Unknown error' }));
        return;
      }
    }
    
    // 2. 保存单元格修改
    for (const [key, { newValue }] of cellEdits) {
      const [rowIndexStr, colName] = key.split(':');
      const rowIndex = parseInt(rowIndexStr);
      const row = result?.result_data?.[rowIndex];
      if (!row || !primaryKey || primaryKey.length === 0) continue;
      
      const keyValues: Record<string, any> = {};
      primaryKey.forEach(pk => { keyValues[pk] = row[pk]; });
      
      const updateResult = await api.updateRow(configId, tableName, {
        database_name: databaseName,
        primary_keys: primaryKey,
        key_values: keyValues,
        columns: { [colName]: newValue }
      });
      
      if (!updateResult.success) {
        toast.error(interpolate(t.database.executor.saveFailed, { error: updateResult.error_message || 'Unknown error' }));
        return;
      }
    }
    
    toast.success(t.database.executor.saveSuccess);
    setCellEdits(new Map());
    setNewRows([]);
    setEditingCell(null);
    if (onDeleted) onDeleted(); // 复用刷新逻辑
  } catch (error: any) {
    toast.error(error.message || 'Save failed');
  } finally {
    setSaving(false);
  }
};

// 根据列类型获取 HTML input type
const getColumnInputType = (colDef: any): string => {
  if (!colDef?.type) return 'text';
  const type = colDef.type.toLowerCase();
  if (type.includes('int') || type.includes('float') || type.includes('double') || type.includes('decimal') || type.includes('numeric')) return 'number';
  if (type === 'date') return 'date';
  if (type === 'datetime' || type.includes('timestamp')) return 'datetime-local';
  if (type === 'boolean' || type === 'tinyint(1)') return 'checkbox';
  if (type.includes('json')) return 'text';
  return 'text';
};

// 计算总变更数
const totalChanges = cellEdits.size + newRows.length;
```

#### Step 7.3: 在工具栏新增编辑按钮

找到现有按钮区域（约第 224-271 行的按钮组 `div`），在 Delete 按钮之后新增：

```tsx
{/* 编辑功能按钮 */}
{primaryKey && primaryKey.length > 0 && (
  <>
    <button
      onClick={handleAddRow}
      className="px-2 py-1 bg-green-700/80 hover:bg-green-600 text-white text-xs rounded flex items-center gap-1 transition-colors"
      title={t.database.executor.addRow}
    >
      <i className="fas fa-plus"></i>
      {t.database.executor.addRow}
    </button>
    {totalChanges > 0 && (
      <>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded flex items-center gap-1 transition-colors disabled:opacity-50"
          title={t.database.executor.saveChanges}
        >
          <i className={`fas ${saving ? 'fa-spinner fa-spin' : 'fa-save'}`}></i>
          {interpolate(t.database.executor.saveChanges, { count: String(totalChanges) })}
        </button>
        <button
          onClick={handleDiscardChanges}
          disabled={saving}
          className="px-2 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs rounded flex items-center gap-1 transition-colors disabled:opacity-50"
          title={t.database.executor.discardChanges}
        >
          <i className="fas fa-undo"></i>
          {t.database.executor.discardChanges}
        </button>
      </>
    )}
  </>
)}
```

#### Step 7.4: 修改表头 — 新增操作列

在 `<thead>` 的列定义中，在现有 checkbox 列之后、数据列之前，新增"操作"列头：

```tsx
{enableSelection && (
  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase w-16">
    {t.common.edit || 'Edit'}
  </th>
)}
```

#### Step 7.5: 修改表体 — 单元格可编辑 + 新增行渲染

找到 `<tbody>` 区域（约第 307-341 行），替换为：

```tsx
<tbody className="bg-slate-800 divide-y divide-slate-700">
  {/* 新增行渲染（在顶部） */}
  {newRows.map((newRow, newRowIdx) => (
    <tr key={`new-${newRowIdx}`} className="bg-green-900/10 hover:bg-green-900/20 transition-colors">
      {enableSelection && (
        <td className="px-4 py-2 w-10">
          <span className="text-xs text-green-400 font-medium">{t.database.executor.newRow}</span>
        </td>
      )}
      {enableSelection && (
        <td className="px-4 py-2 w-16">
          <button
            onClick={() => handleRemoveNewRow(newRowIdx)}
            className="text-slate-400 hover:text-red-400 transition-colors p-1"
            title="Remove row"
          >
            <i className="fas fa-times"></i>
          </button>
        </td>
      )}
      {columns.map((col) => {
        const colDef = schema?.columns?.find((c: any) => c.name === col);
        const editKey = `new-${newRowIdx}:${col}`;
        const isEditing = editingCell === editKey;
        
        return (
          <td key={`new-${newRowIdx}-${col}`} className="px-6 py-2 whitespace-nowrap text-sm text-slate-300 max-w-xs">
            {isEditing ? (
              <input
                type={getColumnInputType(colDef)}
                value={newRow[col] ?? ''}
                onChange={(e) => handleNewRowChange(newRowIdx, col, e.target.value)}
                onBlur={finishEdit}
                onKeyDown={(e) => { if (e.key === 'Enter') finishEdit(); }}
                className="w-full bg-slate-700 border border-blue-500 rounded px-1 py-0.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
                autoFocus
              />
            ) : (
              <span
                onDoubleClick={() => { setEditingCell(editKey); }}
                className="cursor-text block"
              >
                {newRow[col] === null ? (
                  <span className="text-slate-600 italic">NULL</span>
                ) : (
                  String(newRow[col])
                )}
              </span>
            )}
          </td>
        );
      })}
    </tr>
  ))}
  
  {/* 现有数据行 */}
  {result.result_data?.map((row, idx) => (
    <tr key={idx} className={`hover:bg-slate-700/50 transition-colors ${selectedIndices.has(idx) ? 'bg-blue-900/10' : ''}`}>
      {enableSelection && (
        <td className="px-4 py-4 w-10">
          <input
            type="checkbox"
            checked={selectedIndices.has(idx)}
            onChange={() => handleSelectRow(idx)}
            className="rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-blue-500 focus:ring-offset-slate-800"
          />
        </td>
      )}
      {enableSelection && (
        <td className="px-4 py-4 w-16">
          <button 
            onClick={() => setViewingRow(row)}
            className="text-slate-400 hover:text-blue-400 transition-colors p-1"
            title="View JSON"
          >
            <i className="fas fa-eye"></i>
          </button>
        </td>
      )}
      {columns.map((col) => {
        const colDef = schema?.columns?.find((c: any) => c.name === col);
        const editKey = getEditKey(idx, col);
        const edit = cellEdits.get(editKey);
        const isEditing = editingCell === editKey;
        const isDirty = cellEdits.has(editKey);
        
        return (
          <td 
            key={`${idx}-${col}`} 
            className={`px-6 py-4 whitespace-nowrap text-sm max-w-xs ${
              isDirty ? 'bg-yellow-900/20' : 'text-slate-300'
            }`}
          >
            {isEditing ? (
              <input
                type={getColumnInputType(colDef)}
                value={edit?.newValue ?? ''}
                onChange={(e) => handleCellChange(idx, col, e.target.value)}
                onBlur={finishEdit}
                onKeyDown={(e) => { if (e.key === 'Enter') finishEdit(); }}
                className="w-full bg-slate-700 border border-blue-500 rounded px-1 py-0.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
                autoFocus
              />
            ) : (
              <span
                onDoubleClick={() => {
                  if (primaryKey && primaryKey.length > 0) {
                    handleCellDoubleClick(idx, col);
                  }
                }}
                className={`block ${primaryKey && primaryKey.length > 0 ? 'cursor-text' : ''}`}
                title={primaryKey && primaryKey.length > 0 ? '双击编辑' : undefined}
              >
                {edit?.newValue === null ? (
                  <span className="text-slate-600 italic">NULL</span>
                ) : edit?.newValue !== undefined ? (
                  String(edit.newValue)
                ) : row[col] === null ? (
                  <span className="text-slate-600 italic">NULL</span>
                ) : (
                  <TruncatedText text={String(row[col])} />
                )}
              </span>
            )}
          </td>
        );
      })}
    </tr>
  ))}
</tbody>
```

**Step 7.6: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep "ResultViewer"`
Expected: 无新增错误

---

### Task 8: 后端验证

**Step 1: 验证所有 Python 文件语法**

Run: `cd backend && python -m py_compile app/models/database_tool_models.py app/services/database_tool_service.py app/routes/database_tool.py`
Expected: 无输出

**Step 2: 启动后端服务（热重载）**

Run: `cd backend && uvicorn app.main:app --reload --port 19092`
Expected: 服务正常启动，无报错

**Step 3: 验证新 API 端点可用**

打开 http://localhost:19092/docs，确认以下端点存在：
- `POST /database-tool/databases/{id}/tables/{table}/insert-row`
- `POST /database-tool/databases/{id}/tables/{table}/update-row`

---

### Task 9: 前端构建验证

**Step 1: 构建前端**

Run: `cd frontend && npm run build`
Expected: 构建成功，无错误

**Step 2: 检查浏览器 Console**

打开 http://localhost:5178/tools/database-tool，连接数据库并打开表数据：
- 确认无 Console 报错
- 确认双击单元格可进入编辑模式
- 确认"新增行"按钮可用
- 确认修改后有黄色背景标记
- 确认"保存"按钮显示变更数量
- 确认保存后数据刷新

---

### Task 10: 提交

**Step 1: 查看变更**

```bash
git status
git diff --stat
```

**Step 2: 提交**

```bash
git add backend/app/models/database_tool_models.py backend/app/services/database_tool_service.py backend/app/routes/database_tool.py frontend/src/types/databaseTool.ts frontend/src/api/databaseToolApi.ts frontend/src/i18n/locales/zh-CN.ts frontend/src/i18n/locales/en-US.ts frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx
git commit -m "feat(database-tool): 支持表数据内联编辑、新增行和批量保存"
```

---

## 变更摘要

| 文件 | 变更 |
|---|---|
| `backend/app/models/database_tool_models.py` | 新增 InsertRowRequest, UpdateRowRequest, RowOperationResult 模型 |
| `backend/app/services/database_tool_service.py` | 新增 insert_row 和 update_row 服务方法（约 150 行） |
| `backend/app/routes/database_tool.py` | 新增 insert-row 和 update-row 路由端点 |
| `frontend/src/types/databaseTool.ts` | 新增 InsertRowRequest, UpdateRowRequest, RowOperationResult 类型 |
| `frontend/src/api/databaseToolApi.ts` | 新增 insertRow 和 updateRow API 函数 |
| `frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx` | 核心变更：新增编辑状态、双击编辑、新增行、保存/取消逻辑（约 200 行） |
| `frontend/src/i18n/locales/zh-CN.ts` | 新增 7 个编辑相关翻译键 |
| `frontend/src/i18n/locales/en-US.ts` | 新增 7 个对应英文翻译键 |
