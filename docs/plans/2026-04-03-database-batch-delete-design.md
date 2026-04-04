# 数据库管理工具 — 表数据批量删除功能设计文档

**创建日期**: 2026-04-03
**作者**: AI Assistant
**状态**: 设计中

---

## 1. 概述

### 1.1 目标

为数据库管理工具的表数据查看器（`TableDataViewer`）添加批量删除功能，允许用户通过复选框多选数据行后，基于主键批量删除记录。

### 1.2 背景

当前数据库管理工具已支持：
- ✅ 查看表数据（分页、WHERE 过滤、ORDER BY 排序）
- ✅ 行选择（复选框多选）
- ✅ 选中后复制 INSERT 语句
- ✅ 选中后复制 UPDATE 语句
- ✅ 选中后查看 JSON

缺失功能：
- ❌ 批量删除选中行

### 1.3 使用场景

| 场景 | 描述 |
|------|------|
| 清理测试数据 | 批量删除测试环境中产生的脏数据 |
| 数据维护 | 删除过期、无效或重复的记录 |
| 批量操作 | 配合 WHERE 条件筛选后，一次性删除目标数据 |

---

## 2. 架构设计

### 2.1 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      前端界面层                               │
│  ┌─────────────────────┐    ┌──────────────────────────┐    │
│  │  ResultViewer.tsx   │    │  确认删除弹窗              │    │
│  │  - 删除按钮          │───▶│  - 显示主键条件预览        │    │
│  │  - handleBatchDelete│    │  - 二次确认               │    │
│  └─────────────────────┘    └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       API 层                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  databaseToolApi.ts                                   │   │
│  │  batchDeleteRows(id, table, { primary_keys,          │   │
│  │    key_values, database_name })                       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      后端路由层                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  database_tool.py                                     │   │
│  │  POST /databases/{id}/tables/{table}/batch-delete     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       服务层                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  database_tool_service.py                             │   │
│  │  batch_delete_rows(user_id, config_id, table, req)    │   │
│  │  - 获取数据库连接                                      │   │
│  │  - 构建 DELETE SQL（支持单/复合主键）                   │   │
│  │  - 执行删除，返回统计结果                              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       数据库                                  │
│  MySQL / PostgreSQL / SQLite / SQL Server / Oracle / MariaDB│
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户勾选行 → setSelectedIndices(Set)
    ↓
点击 Delete 按钮 → handleBatchDelete()
    ↓
弹出确认弹窗 → 显示主键条件预览
    ↓
用户确认 → batchDeleteRows(API)
    ↓
后端构建 DELETE SQL → 执行 → 返回结果
    ↓
前端刷新表格 → fetchData(page)
    ↓
Toast 提示 "成功删除 X 条记录"
```

---

## 3. 前端设计

### 3.1 ResultViewer.tsx — 删除按钮

**位置**: 表格顶部操作栏，与现有的 Insert/Update/JSON 按钮并列。

**显示条件**:
- 有选中行 (`selectedIndices.size > 0`)
- 表有主键 (`primaryKey && primaryKey.length > 0`)

**按钮样式**:
```tsx
<button 
  onClick={handleBatchDelete}
  className="px-2 py-1 bg-red-600/80 hover:bg-red-600 text-white text-xs rounded 
             flex items-center gap-1 transition-colors"
  title="Delete selected rows (Requires Primary Key)"
>
  <i className="fas fa-trash"></i>
  Delete
</button>
```

**无主键时**: 按钮禁用，显示提示 "该表无主键，无法批量删除"。

### 3.2 确认弹窗

**弹窗内容**:

```
⚠️ 确认删除

即将删除 5 条记录

表: users
主键: id
条件: id IN (1, 2, 3, 4, 5)

[ 取消 ]  [ 确认删除 ]
```

**复合主键示例**:

```
⚠️ 确认删除

即将删除 3 条记录

表: user_roles
主键: user_id, role_id
条件: 
  (user_id=1, role_id='admin'),
  (user_id=2, role_id='editor'),
  (user_id=3, role_id='viewer')

[ 取消 ]  [ 确认删除 ]
```

### 3.3 新增 API 函数

**文件**: `frontend/src/api/databaseToolApi.ts`

```typescript
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

### 3.4 删除后行为

- **成功**: 刷新当前页数据 (`fetchData(page)`)，Toast 提示 "成功删除 X 条记录"
- **失败**: Toast 显示错误信息，不刷新数据
- **清空当前页**: 如果删除后当前页无数据且页码 > 1，自动跳转到上一页

---

## 4. 后端设计

### 4.1 新增路由

**文件**: `backend/app/routes/database_tool.py`

```python
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

### 4.2 请求/响应模型

**文件**: `backend/app/models/database_tool_models.py`

```python
class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    database_name: Optional[str] = Field(None, description="数据库名称（多数据库连接时使用）")
    primary_keys: List[str] = Field(..., description="主键列名列表")
    key_values: List[Dict[str, Any]] = Field(..., description="每行的主键值")

class BatchDeleteResult(BaseModel):
    """批量删除结果"""
    success: bool
    deleted_count: int = Field(..., description="成功删除行数")
    failed_count: int = Field(default=0, description="失败行数")
    error_message: Optional[str] = Field(None, description="错误信息")
    execution_time_ms: float = Field(..., description="执行耗时（毫秒）")
```

### 4.3 Service 层实现

**文件**: `backend/app/services/database_tool_service.py`

**核心逻辑**:

```python
@staticmethod
def batch_delete_rows(
    user_id: str,
    config_id: str,
    table_name: str,
    request: BatchDeleteRequest
) -> BatchDeleteResult:
    start_time = datetime.now()
    
    # 1. 获取数据库连接（复用现有 _get_config_with_password 逻辑）
    config_row = DatabaseToolService._get_config_with_password(config_id, user_id)
    if not config_row:
        return BatchDeleteResult(success=False, deleted_count=0, failed_count=0,
                                  error_message="Configuration not found", execution_time_ms=0)
    
    # 2. 构建 DELETE SQL
    db_type = config_row['db_type']
    quote = _quote_identifier(db_type)  # MySQL: `, PG: ", SQLServer: []
    
    if len(request.primary_keys) == 1:
        # 单主键: DELETE FROM table WHERE id IN (1, 2, 3)
        pk = quote(request.primary_keys[0])
        values = [row[request.primary_keys[0]] for row in request.key_values]
        where_clause = f"{pk} IN ({', '.join(_escape_value(v, db_type) for v in values)})"
    else:
        # 复合主键: DELETE FROM table WHERE (a, b) IN ((1, 'x'), (2, 'y'))
        pk_cols = ', '.join(quote(k) for k in request.primary_keys)
        tuples = []
        for row in request.key_values:
            vals = ', '.join(_escape_value(row[k], db_type) for k in request.primary_keys)
            tuples.append(f"({vals})")
        where_clause = f"({pk_cols}) IN ({', '.join(tuples)})"
    
    sql = f"DELETE FROM {quote(table_name)} WHERE {where_clause}"
    
    # 3. 执行 SQL
    engine_key = f"{config_id}:{request.database_name}" if request.database_name else config_id
    result = SQLExecutor.execute(engine_key, config_dict, sql)
    
    elapsed = (datetime.now() - start_time).total_seconds() * 1000
    
    return BatchDeleteResult(
        success=result.success,
        deleted_count=result.affected_rows or 0,
        failed_count=0 if result.success else len(request.key_values),
        error_message=result.error_message,
        execution_time_ms=elapsed
    )
```

### 4.4 SQL 生成策略

| 数据库类型 | 标识符引用 | 示例 |
|-----------|-----------|------|
| MySQL/MariaDB | `` `name` `` | `` DELETE FROM `users` WHERE `id` IN (1,2,3) `` |
| PostgreSQL | `"name"` | `DELETE FROM "users" WHERE "id" IN (1,2,3)` |
| SQLite | `"name"` | `DELETE FROM "users" WHERE "id" IN (1,2,3)` |
| SQL Server | `[name]` | `DELETE FROM [users] WHERE [id] IN (1,2,3)` |
| Oracle | `"name"` | `DELETE FROM "users" WHERE "id" IN (1,2,3)` |

### 4.5 值转义策略

| 值类型 | 转义方式 |
|--------|---------|
| 整数 | 直接输出 `123` |
| 字符串 | 单引号包裹 + 转义 `'it''s'` |
| NULL | 输出 `NULL` |
| 布尔 | 转为 `1`/`0` (MySQL) 或 `TRUE`/`FALSE` (PG) |

---

## 5. 错误处理

### 5.1 前端错误处理

| 场景 | 处理方式 |
|------|----------|
| 无主键 | 按钮禁用，hover 提示 "该表无主键，无法批量删除" |
| 选中 0 行 | 按钮不显示 |
| API 调用失败 | Toast 显示错误信息 |
| 外键约束冲突 | Toast 显示后端返回的具体错误 |
| 删除后当前页为空 | 自动跳转到上一页 |

### 5.2 后端错误处理

| 场景 | 处理方式 |
|------|----------|
| 配置不存在 | 返回 404 |
| 表不存在 | 返回 400 + 错误信息 |
| 主键不匹配 | 返回 400 + 错误信息 |
| 外键约束 | 返回 500 + 数据库错误详情 |
| 连接超时 | 返回 500 + 超时信息 |

---

## 6. 安全考虑

### 6.1 权限控制

- 复用现有 JWT 认证中间件 (`get_current_user_id`)
- 用户只能操作自己有权限的数据库配置

### 6.2 SQL 注入防护

- 表名和列名使用标识符引用（反引号/双引号/方括号）
- 值使用参数化转义或严格格式化
- 不允许用户直接传入 WHERE 子句

### 6.3 操作审计

- 删除操作自动记录到 `sql_execution_history` 表
- 包含 SQL 语句、影响行数、执行时间、用户 ID

---

## 7. 国际化 (i18n)

需要在 `frontend/src/i18n/locales/zh-CN.ts` 中添加：

```typescript
database: {
  // ... 现有翻译
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
  }
}
```

---

## 8. 改动文件清单

### 前端 (3 个文件)

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx` | 修改 | 新增删除按钮 + 确认弹窗 + handleBatchDelete |
| `frontend/src/api/databaseToolApi.ts` | 新增 | `batchDeleteRows()` 函数 + 类型定义 |
| `frontend/src/i18n/locales/zh-CN.ts` | 新增 | 批量删除相关翻译 |

### 后端 (3 个文件)

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `backend/app/models/database_tool_models.py` | 新增 | `BatchDeleteRequest`, `BatchDeleteResult` 模型 |
| `backend/app/routes/database_tool.py` | 新增 | `POST /tables/{table}/batch-delete` 路由 |
| `backend/app/services/database_tool_service.py` | 新增 | `batch_delete_rows()` 方法 |

---

## 9. 测试计划

### 9.1 前端测试

- [ ] 有主键的表显示删除按钮
- [ ] 无主键的表删除按钮禁用
- [ ] 选中行后显示删除按钮
- [ ] 确认弹窗显示正确的主键条件
- [ ] 删除成功后表格刷新
- [ ] 删除失败显示错误 Toast
- [ ] 删除后当前页为空时自动跳转上一页

### 9.2 后端测试

- [ ] 单主键批量删除成功
- [ ] 复合主键批量删除成功
- [ ] 不存在的配置返回 404
- [ ] 不存在的表返回 400
- [ ] 外键约束冲突返回 500
- [ ] 删除操作记录到执行历史

---

## 10. 后续扩展

- [ ] 支持软删除（标记删除而非物理删除）
- [ ] 支持批量更新（类似批量删除的交互）
- [ ] 支持导出 DELETE 语句（类似现有的 INSERT/UPDATE）
- [ ] 支持删除前的影响范围预览（Dry Run）
