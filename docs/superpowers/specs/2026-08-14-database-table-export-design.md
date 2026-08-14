# 数据库表数据导出功能设计

**日期**: 2026-08-14
**状态**: 已批准
**实现**: Phase 13

## 背景

数据库管理工具当前缺少数据导出功能。用户在使用 WHERE 条件筛选表数据后，无法将筛选结果导出为文件。需要增加按筛选条件导出全部数据的功能。

## 功能需求

### 核心功能

1. **快速导出**: 一键以 CSV 格式导出当前筛选条件的全部数据
2. **高级导出**: 可选择导出格式（CSV / Excel / JSON / SQL）和自定义文件名
3. **基于筛选条件**: 使用当前页面的 WHERE 和 ORDER BY 条件，导出全量数据（不受分页限制）

### 数据格式支持

- **CSV**: 通用格式，适合数据分析工具
- **Excel (.xlsx)**: 需要 openpyxl 库
- **JSON**: 适合程序处理
- **SQL**: INSERT 语句，适合数据迁移

### 数据量限制

- 后端限制单次最多 100 万行
- 超出限制时提示用户缩小筛选范围

## 技术方案

### 后端修复（Bug Fix）

**问题**: `ExportDataRequest` 模型缺少 `db_config_id` 字段，但 `export_data()` 服务方法访问了 `request.db_config_id`

**修复**: 修改 `database_tool_service.py`，使用 `config_id` 参数而不是 `request.db_config_id`

**文件**: `backend/app/services/database_tool_service.py`

```python
# 修改前（错误）
config_row = DatabaseToolService._get_config_with_password(
    request.db_config_id, user_id
)

# 修改后（正确）
config_row = DatabaseToolService._get_config_with_password(
    config_id, user_id
)
```

### 前端实现

#### 1. API 封装

**文件**: `frontend/src/api/databaseToolApi.ts`

新增 `exportTableData()` 函数：

```typescript
export async function exportTableData(
  configId: string,
  request: {
    sql: string;
    format: 'csv' | 'excel' | 'json' | 'sql';
    database_name?: string;
  }
): Promise<ExportDataResponse> {
  const response = await fetch(
    `${API_BASE_URL}/configs/${encodeURIComponent(configId)}/export`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify(request),
    }
  );
  
  if (!response.ok) {
    throw new Error(`导出失败：${response.status}`);
  }
  
  return response.json();
}
```

#### 2. UI 组件

**文件**: `frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx`

**新增状态**:

```typescript
const [exporting, setExporting] = useState(false);
const [exportFormat, setExportFormat] = useState<'csv' | 'excel' | 'json' | 'sql'>('csv');
const [showExportMenu, setShowExportMenu] = useState(false);
```

**新增按钮**（在工具栏"Run"按钮旁边）:

```tsx
{/* 快速导出按钮 */}
<button
  onClick={handleQuickExport}
  disabled={exporting || !result}
  className="btn btn-secondary"
  title="快速导出 CSV"
>
  {exporting ? <LoadingSpinner /> : <DownloadIcon />}
</button>

{/* 高级导出下拉菜单 */}
<div className="relative">
  <button
    onClick={() => setShowExportMenu(!showExportMenu)}
    disabled={exporting || !result}
    className="btn btn-secondary btn-sm"
  >
    <ChevronDownIcon />
  </button>
  
  {showExportMenu && (
    <div className="absolute right-0 mt-1 bg-slate-800 rounded shadow-lg border border-slate-700 p-2 z-50">
      <div className="text-xs text-slate-400 mb-2 px-2">导出格式</div>
      {(['csv', 'excel', 'json', 'sql'] as const).map((fmt) => (
        <button
          key={fmt}
          onClick={() => handleExport(fmt)}
          className="block w-full text-left px-3 py-1.5 hover:bg-slate-700 rounded text-sm"
        >
          {fmt.toUpperCase()}
        </button>
      ))}
    </div>
  )}
</div>
```

**导出逻辑**:

```typescript
const handleExport = async (format: 'csv' | 'excel' | 'json' | 'sql') => {
  if (!result || !tableName) return;
  
  setExporting(true);
  setShowExportMenu(false);
  
  try {
    // 构造完整 SQL
    const sql = `SELECT * FROM ${tableName}${whereClause ? ` WHERE ${whereClause}` : ''}${orderByClause ? ` ORDER BY ${orderByClause}` : ''}`;
    
    const response = await api.exportTableData(configId, {
      sql,
      format,
      database_name: databaseName,
    });
    
    // 下载文件
    if (format === 'excel') {
      // Excel 返回 Base64，需要解码
      const byteCharacters = atob(response.content || '');
      const byteNumbers = new Uint8Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const blob = new Blob([byteNumbers], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      triggerDownload(blob, response.file_name);
    } else {
      // CSV/JSON/SQL 直接返回文本
      const blob = new Blob([response.content || ''], {
        type: format === 'csv' ? 'text/csv' : format === 'json' ? 'application/json' : 'text/plain',
      });
      triggerDownload(blob, response.file_name);
    }
    
    toast.success(`导出成功：${response.row_count} 行`);
  } catch (error) {
    const msg = error instanceof Error ? error.message : '导出失败';
    toast.error(msg);
  } finally {
    setExporting(false);
  }
};

const handleQuickExport = () => handleExport('csv');

const triggerDownload = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};
```

#### 3. 国际化文案

**文件**: `frontend/src/i18n/locales/zh-CN.ts`

```typescript
database: {
  // ... 现有文案
  export: {
    quickExport: '快速导出',
    advancedExport: '高级导出',
    exporting: '导出中...',
    success: '导出成功：{count} 行',
    failed: '导出失败',
    format: '导出格式',
    tooManyRows: '数据量过大，请缩小筛选范围',
  },
}
```

## 数据流

```
用户点击导出按钮
    ↓
前端构造 SQL: SELECT * FROM {table} WHERE {where} ORDER BY {order}
    ↓
调用 POST /api/database-tool/configs/{id}/export
    ↓
后端执行查询，生成文件内容
    ↓
返回 {file_name, file_size, content, row_count}
    ↓
前端创建 Blob，触发浏览器下载
```

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 查询超时 | 显示"导出失败：查询超时，请缩小筛选范围" |
| 数据量超过 100 万行 | 后端拒绝，前端显示"数据量过大，请缩小筛选范围" |
| 格式转换失败 | 显示具体错误信息 |
| 网络错误 | 显示"网络错误，请重试" |

## 测试场景

### 功能测试

1. 无筛选条件时导出全表数据
2. 有 WHERE 条件时只导出符合条件的数据
3. 有 ORDER BY 时按指定顺序导出
4. 导出 CSV 格式
5. 导出 Excel 格式
6. 导出 JSON 格式
7. 导出 SQL 格式
8. 导出过程中显示加载状态
9. 导出完成后显示成功提示

### 边界测试

1. 空表导出（0 行）
2. 大数据量导出（10 万+ 行）
3. 包含特殊字符的数据导出
4. 包含 NULL 值的数据导出
5. 包含中文的数据导出

## 影响范围

### 修改的文件

- `backend/app/services/database_tool_service.py` — 修复 `db_config_id` bug
- `frontend/src/api/databaseToolApi.ts` — 新增 `exportTableData()` 函数
- `frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx` — 添加导出按钮和逻辑
- `frontend/src/i18n/locales/zh-CN.ts` — 添加导出文案
- `frontend/src/i18n/locales/en-US.ts` — 添加导出文案（英文）

### 不需要修改

- 后端路由（已有 `/configs/{id}/export`）
- 后端模型（`ExportDataRequest` 和 `ExportDataResponse` 已存在）
- 数据库 schema

## 后续优化（可选）

- 导出进度条（大数据量时）
- 后台导出 + 完成通知（超大数据量）
- 导出历史记录
- 自定义列选择（只导出部分列）
