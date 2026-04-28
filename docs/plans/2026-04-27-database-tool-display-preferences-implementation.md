# 数据库工具显示偏好功能实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为数据库工具连接列表添加用户级显示偏好功能，支持连接级别和数据库级别的勾选过滤，通过后端 API 持久化。

**Architecture:** 新增 `user_display_preferences` 表存储偏好，后端提供 GET/PUT API，前端新增弹窗组件进行勾选配置，连接列表根据偏好过滤渲染。

**Tech Stack:** Python/FastAPI/psycopg2 (后端), React/TypeScript/Tailwind (前端)

---

### Task 1: 创建数据库表

**文件:** `backend/app/utils/database_tool_db_init.py` 或独立迁移脚本

在数据库初始化中添加 `user_display_preferences` 表创建逻辑（CREATE TABLE IF NOT EXISTS）。

表结构：
```sql
CREATE TABLE IF NOT EXISTS user_display_preferences (
    user_id VARCHAR(50) PRIMARY KEY,
    visible_connections JSON,
    visible_databases JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Step 1: 找到数据库初始化文件**

运行: 查找 `backend/app/utils/` 下包含 `db_init` 或 `init_db` 的文件
预期: 找到数据库工具相关的初始化脚本

**Step 2: 添加表创建逻辑**

在现有表创建逻辑后添加 user_display_preferences 表的 CREATE TABLE IF NOT EXISTS 语句。

**Step 3: 验证表创建成功**

启动后端服务，检查日志确认表已创建。

---

### Task 2: 新增 Pydantic 模型

**文件:** `backend/app/models/database_tool_models.py`

**Step 1: 读取现有模型文件**

读取 `backend/app/models/database_tool_models.py`

**Step 2: 添加模型**

在文件末尾添加：
```python
from typing import Optional, List, Dict
from datetime import datetime

class DisplayPreference(BaseModel):
    visible_connections: Optional[List[str]] = None
    visible_databases: Optional[Dict[str, List[str]]] = None

class DisplayPreferenceResponse(DisplayPreference):
    updated_at: Optional[datetime] = None
```

**Step 3: 验证编译**

运行: `cd backend && python -m py_compile app/models/database_tool_models.py`
预期: 无输出（编译成功）

---

### Task 3: 新增 Service 层方法

**文件:** `backend/app/services/database_tool_service.py`

**Step 1: 读取现有 Service 文件**

读取 `backend/app/services/database_tool_service.py`，了解 `get_db_connection()` 的使用模式。

**Step 2: 添加 get_display_preferences 方法**

```python
@staticmethod
def get_display_preferences(user_id: str) -> DisplayPreferenceResponse:
    from app.models.database_tool_models import DisplayPreferenceResponse
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT visible_connections, visible_databases, updated_at "
                "FROM user_display_preferences WHERE user_id = %s",
                (user_id,)
            )
            row = cur.fetchone()
            if row:
                return DisplayPreferenceResponse(
                    visible_connections=row['visible_connections'],
                    visible_databases=row['visible_databases'],
                    updated_at=row['updated_at']
                )
            return DisplayPreferenceResponse()
    finally:
        conn.close()
```

**Step 3: 添加 save_display_preferences 方法**

```python
@staticmethod
def save_display_preferences(user_id: str, preferences: dict) -> DisplayPreferenceResponse:
    from app.models.database_tool_models import DisplayPreferenceResponse
    import json
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_display_preferences (user_id, visible_connections, visible_databases) "
                "VALUES (%s, %s, %s) "
                "ON CONFLICT (user_id) DO UPDATE SET "
                "visible_connections = EXCLUDED.visible_connections, "
                "visible_databases = EXCLUDED.visible_databases, "
                "updated_at = CURRENT_TIMESTAMP "
                "RETURNING visible_connections, visible_databases, updated_at",
                (user_id,
                 json.dumps(preferences.get('visible_connections')) if preferences.get('visible_connections') is not None else None,
                 json.dumps(preferences.get('visible_databases')) if preferences.get('visible_databases') else None)
            )
            row = cur.fetchone()
            conn.commit()
            return DisplayPreferenceResponse(
                visible_connections=row['visible_connections'],
                visible_databases=row['visible_databases'],
                updated_at=row['updated_at']
            )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

**Step 4: 验证编译**

运行: `cd backend && python -m py_compile app/services/database_tool_service.py`
预期: 无输出

---

### Task 4: 新增 API 路由端点

**文件:** `backend/app/routes/database_tool.py`

**Step 1: 读取现有路由文件**

读取 `backend/app/routes/database_tool.py`，了解路由模式。

**Step 2: 添加导入**

在文件顶部导入中添加：
```python
from app.models.database_tool_models import DisplayPreference, DisplayPreferenceResponse
```

**Step 3: 添加 GET 端点**

```python
@router.get("/preferences", response_model=DisplayPreferenceResponse)
async def get_display_preferences(user_id: str = Depends(get_current_user_id)):
    """获取当前用户的显示偏好"""
    from app.services.database_tool_service import DatabaseToolService
    return DatabaseToolService.get_display_preferences(user_id)
```

**Step 4: 添加 PUT 端点**

```python
@router.put("/preferences", response_model=DisplayPreferenceResponse)
async def save_display_preferences(
    preferences: DisplayPreference,
    user_id: str = Depends(get_current_user_id)
):
    """保存当前用户的显示偏好"""
    from app.services.database_tool_service import DatabaseToolService
    return DatabaseToolService.save_display_preferences(user_id, preferences.model_dump())
```

**Step 5: 验证编译**

运行: `cd backend && python -m py_compile app/routes/database_tool.py`
预期: 无输出

---

### Task 5: 新增前端 API 调用

**文件:** `frontend/src/api/databaseToolApi.ts`

**Step 1: 读取现有 API 文件**

读取 `frontend/src/api/databaseToolApi.ts`

**Step 2: 添加类型和函数**

在文件末尾添加：
```typescript
export interface DisplayPreferences {
  visible_connections: string[] | null;
  visible_databases: Record<string, string[]>;
  updated_at?: string;
}

export async function getDisplayPreferences(): Promise<DisplayPreferences> {
  const response = await fetch(`${BASE_URL}/preferences`, {
    headers: getAuthHeaders(),
  });
  return handleResponse<DisplayPreferences>(response);
}

export async function saveDisplayPreferences(
  prefs: DisplayPreferences
): Promise<DisplayPreferences> {
  const response = await fetch(`${BASE_URL}/preferences`, {
    method: 'PUT',
    headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({
      visible_connections: prefs.visible_connections,
      visible_databases: prefs.visible_databases,
    }),
  });
  return handleResponse<DisplayPreferences>(response);
}
```

---

### Task 6: 新增前端类型定义

**文件:** `frontend/src/types/databaseTool.ts`

**Step 1: 读取现有类型文件**

读取 `frontend/src/types/databaseTool.ts`

**Step 2: 添加类型**

```typescript
export interface DisplayPreferences {
  visible_connections: string[] | null;
  visible_databases: Record<string, string[]>;
  updated_at?: string;
}
```

---

### Task 7: 创建 DisplaySettingsDialog 组件

**文件:** `frontend/src/components/Tools/DatabaseTool/components/DisplaySettingsDialog.tsx` — 新文件

**要点:**
- Props: `isOpen`, `onClose`, `configs`, `onSave`
- 内部状态：本地勾选状态（不立即保存）
- 搜索框过滤连接名
- 每个连接：复选框 + 连接名 + 环境标签
- 展开连接后：缩进显示数据库复选框列表
- 底部：重置 / 取消 / 确认 按钮
- 弹窗打开时批量加载所有连接的数据库列表
- 样式：slate-800 暗色主题，遵循设计文档样式规范
- 支持 ESC 关闭，focus trap

**样式类参考:**
- 弹窗容器: `bg-slate-800 rounded-lg shadow-xl border border-slate-700`
- 遮罩层: `fixed inset-0 bg-black/50 backdrop-blur-sm z-[100]`
- 复选框: `rounded border-slate-600 bg-slate-700 text-blue-500`
- 连接项（选中）: `bg-blue-500/10 border border-blue-500/30`
- 确认按钮: `bg-blue-600 hover:bg-blue-700 text-white rounded-md`

---

### Task 8: 修改 ConnectionList 组件

**文件:** `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx`

**Step 1: 添加齿轮按钮**

在标题栏右侧添加齿轮图标按钮，点击打开 DisplaySettingsDialog。

```tsx
<button
  onClick={() => setShowDisplaySettings(true)}
  aria-label="显示设置"
  className="p-2 text-slate-400 hover:text-white transition-colors rounded hover:bg-slate-700/50 cursor-pointer"
>
  <i className="fas fa-cog"></i>
</button>
```

**Step 2: 添加显示偏好状态**

```tsx
const [displayPreferences, setDisplayPreferences] = useState<DisplayPreferences | null>(null);
const [showDisplaySettings, setShowDisplaySettings] = useState(false);
```

**Step 3: 加载偏好**

在 useEffect 中调用 `getDisplayPreferences()` 获取偏好。

**Step 4: 过滤连接列表**

```tsx
const filteredConfigs = useMemo(() => {
  if (!displayPreferences?.visible_connections) return configs;
  return configs.filter(c => displayPreferences.visible_connections!.includes(c.id));
}, [configs, displayPreferences]);
```

**Step 5: 过滤数据库列表**

在每个连接节点中，根据 `displayPreferences.visible_databases[config.id]` 过滤数据库。

**Step 6: 渲染弹窗**

```tsx
{showDisplaySettings && (
  <DisplaySettingsDialog
    isOpen={showDisplaySettings}
    onClose={() => setShowDisplaySettings(false)}
    configs={configs}
    onSave={async (prefs) => {
      await saveDisplayPreferences(prefs);
      setDisplayPreferences(prefs);
      setShowDisplaySettings(false);
    }}
  />
)}
```

---

### Task 9: TypeScript 编译验证

**Step 1: 运行 TypeScript 检查**

运行: `cd frontend && npx tsc --noEmit 2>&1 | head -30`
预期: 无新增类型错误

---

### Task 10: 浏览器验证

**Step 1: 启动服务**

确保前后端服务运行。

**Step 2: 访问数据库工具页面**

访问 `http://localhost:5178/tools/database-tool`

**Step 3: 验证流程**
- 点击齿轮图标打开弹窗
- 取消勾选某个连接，确认左侧列表隐藏该连接
- 展开连接，勾选部分数据库，确认只显示选中的
- 点击确认，刷新页面验证偏好持久化
- Console 无错误
