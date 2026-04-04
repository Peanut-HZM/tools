# 数据库工具表数据内联编辑设计

## 问题描述

数据库管理工具在查看表数据时，不支持直接添加或修改行数据。用户需要通过复制 SQL → 粘贴到 SQL 执行器 → 手动执行的方式间接操作，效率低下。

## 选定方案：方案 A（双击编辑 + 批量保存）

### 核心交互

1. **双击单元格** → 变为输入框，编辑后按 Enter 或失焦确认
2. **新增行** → 点击"新增行"按钮，表格顶部插入可编辑空行
3. **批量保存** → 点击"保存"按钮，一次性提交所有新增行和单元格修改
4. **取消变更** → 点击"取消"按钮，丢弃所有未保存变更

### 后端 API 设计

**新增 2 个端点：**

```
POST /database-tool/databases/{id}/tables/{table}/insert-row
POST /database-tool/databases/{id}/tables/{table}/update-row
```

**insert-row 请求体：**
```json
{
  "database_name": "mydb",
  "columns": { "name": "张三", "age": 25, "email": null }
}
```

**update-row 请求体：**
```json
{
  "database_name": "mydb",
  "primary_keys": ["id"],
  "key_values": { "id": 42 },
  "columns": { "name": "李四", "age": 26 }
}
```

**响应体（两者相同）：**
```json
{
  "success": true,
  "affected_rows": 1,
  "execution_time_ms": 15.3,
  "error_message": null
}
```

### 前端状态管理

```ts
// 追踪单元格变更: key = "rowIndex:columnName", value = { oldValue, newValue }
const [cellEdits, setCellEdits] = useState<Map<string, { oldValue: any; newValue: any }>>(new Map());

// 追踪新增行: 每行是一个空对象
const [newRows, setNewRows] = useState<Record<string, any>[]>([]);

// 编辑中的单元格: key = "rowIndex:columnName"
const [editingCell, setEditingCell] = useState<string | null>(null);
```

### 数据类型处理

基于 `schema.columns` 的 `type` 字段自动识别输入类型：

| MySQL 类型 | 输入类型 | 处理方式 |
|---|---|---|
| INT, BIGINT, FLOAT, DECIMAL | `number` | 数字输入，空值存 NULL |
| DATE | `date` | 日期选择器 |
| DATETIME, TIMESTAMP | `datetime-local` | 日期时间选择器 |
| BOOLEAN, TINYINT(1) | `checkbox` | 复选框 |
| JSON | `textarea` | 多行文本，JSON 校验 |
| 其他（VARCHAR, TEXT 等） | `text` | 普通文本输入 |

### 保存逻辑

```ts
const handleSave = async () => {
  // 1. 先保存新增行
  for (const newRow of newRows) {
    await api.insertRow(configId, tableName, {
      database_name: databaseName,
      columns: newRow
    });
  }
  
  // 2. 再保存单元格修改
  for (const [key, { newValue }] of cellEdits) {
    const [rowIndex, col] = parseKey(key);
    const row = result.result_data[parseInt(rowIndex)];
    await api.updateRow(configId, tableName, {
      database_name: databaseName,
      primary_keys: primaryKey,
      key_values: extractPrimaryKey(row, primaryKey),
      columns: { [col]: newValue }
    });
  }
  
  // 3. 刷新数据
  fetchData(page);
  setCellEdits(new Map());
  setNewRows([]);
};
```

### i18n 键名

| 键名 | zh-CN | en-US |
|---|---|---|
| `database.executor.addRow` | 新增行 | Add Row |
| `database.executor.saveChanges` | 保存 ({count}) | Save ({count}) |
| `database.executor.discardChanges` | 取消 | Discard |
| `database.executor.saveSuccess` | 保存成功 | Save successful |
| `database.executor.saveFailed` | 保存失败 | Save failed |
| `database.executor.newRow` | 新 | New |
| `database.editor.noPrimaryKey` | 该表无主键，无法编辑 | No primary key, editing disabled |

### 修改文件清单

| 文件 | 变更 |
|---|---|
| `backend/app/routes/database_tool.py` | 新增 insert-row 和 update-row 路由 |
| `backend/app/services/database_tool_service.py` | 新增 insert_row 和 update_row 服务方法 |
| `backend/app/models/database_tool_models.py` | 新增 InsertRowRequest 和 UpdateRowRequest 模型 |
| `frontend/src/api/databaseToolApi.ts` | 新增 insertRow 和 updateRow API 函数 |
| `frontend/src/types/databaseTool.ts` | 新增 InsertRowRequest 和 UpdateRowRequest 类型 |
| `frontend/src/components/Tools/DatabaseTool/components/ResultViewer.tsx` | 核心变更：新增编辑状态、EditableCell、新增行、保存逻辑 |
| `frontend/src/i18n/locales/zh-CN.ts` | 新增编辑相关翻译键 |
| `frontend/src/i18n/locales/en-US.ts` | 新增对应英文翻译键 |

### 风险评估

- **中风险**：涉及前后端全链路变更
- **数据安全性**：update-row 必须基于主键，防止误更新
- **事务处理**：批量保存时若中间某条失败，需回滚已提交的变更
- **并发编辑**：多用户同时编辑同一行可能导致数据覆盖（暂不处理，后续可加乐观锁）
