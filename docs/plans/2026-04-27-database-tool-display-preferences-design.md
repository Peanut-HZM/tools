# 数据库工具 - 显示设置功能设计

## 背景

数据库工具左侧连接列表随着连接数量增加变得拥挤，用户希望：
1. **连接级别**：勾选需要展示的数据源，隐藏不需要的连接
2. **数据库级别**：在每个连接下，勾选需要展示的数据库
3. **按用户保存**：偏好通过后端 API 存储，支持跨设备同步
4. **可多次更改**：用户可以随时重新打开设置修改选择

## 架构设计

### 后端（3 个文件变更）

#### 1. 新增数据库表 `user_display_preferences`

```sql
CREATE TABLE user_display_preferences (
    user_id VARCHAR(50) PRIMARY KEY,
    visible_connections JSON,      -- null=全部显示, ["id1","id2"]=仅显示这些
    visible_databases JSON,        -- {"config_id": ["db1", "db2"]} 每个连接可见的数据库
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**设计决策：**
- 连接级用 `visible_connections`：null 表示全部显示（默认行为），数组表示白名单
- 数据库级用 `visible_databases`：每个连接 ID 映射到可见的数据库名列表，**显式勾选才显示**
- 未配置的连接/数据库默认全部显示（渐进式配置，不影响已有用户）

#### 2. 新增 Pydantic 模型

文件：`backend/app/models/database_tool_models.py`

```python
class DisplayPreference(BaseModel):
    visible_connections: Optional[List[str]] = None
    visible_databases: Optional[Dict[str, List[str]]] = None

class DisplayPreferenceResponse(DisplayPreference):
    updated_at: Optional[datetime] = None
```

#### 3. 新增 API 端点

文件：`backend/app/routes/database_tool.py`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/database-tool/preferences` | GET | 获取当前用户的显示偏好 |
| `/database-tool/preferences` | PUT | 保存当前用户的显示偏好 |

**GET 响应示例：**
```json
{
    "visible_connections": ["conn_1", "conn_3"],
    "visible_databases": {
        "conn_1": ["db_prod", "db_test"],
        "conn_3": ["redis_01"]
    },
    "updated_at": "2026-04-27T12:00:00"
}
```

**PUT 请求体：** 同上结构

#### 4. Service 层

文件：`backend/app/services/database_tool_service.py`

新增方法：
- `get_display_preferences(user_id)` → `DisplayPreferenceResponse`
- `save_display_preferences(user_id, preferences)` → `DisplayPreferenceResponse`

使用直接 SQL 操作（`get_db_connection()`），因为偏好数据独立于连接配置。

### 前端（3 个文件变更）

#### 1. 新增组件 `DisplaySettingsDialog.tsx`

文件：`frontend/src/components/Tools/DatabaseTool/components/DisplaySettingsDialog.tsx`

**Props：**
```typescript
interface DisplaySettingsDialogProps {
    isOpen: boolean;
    onClose: () => void;
    configs: DatabaseConfig[];         // 所有连接配置
    onSave: (preferences: DisplayPreferences) => Promise<void>;
}
```

**内部结构：**
- 顶部：标题 + 关闭按钮 + 搜索框
- 中部：可滚动列表，按连接分组
  - 每个连接项：复选框 + 连接名 + 环境标签
  - 展开后：缩进的数据库复选框列表
- 底部：重置 / 取消 / 确认 按钮

**交互逻辑：**
1. 打开弹窗时，初始化本地 state（从 props 或上一次保存的偏好）
2. 用户勾选/取消 → 更新本地 state（不立即保存）
3. 用户点击「确认」→ 调用 `onSave` → 关闭弹窗
4. 用户点击「取消」→ 丢弃更改 → 关闭弹窗
5. 用户点击「重置」→ 恢复为全部显示（visible_connections = null, visible_databases = {}）

**数据库列表加载策略：**
- 弹窗打开时，批量获取所有连接的数据库列表（`Promise.all` 并行）
- 加载中的连接显示 spinner
- 搜索时实时过滤连接名和数据库名

#### 2. 修改 `ConnectionList.tsx`

- 顶部标题栏新增齿轮图标按钮（`fa-cog`），点击打开 `DisplaySettingsDialog`
- 从 Context 或本地 state 读取当前用户的显示偏好
- 渲染时过滤：只显示 `visible_connections` 中的连接（null 时显示全部）
- 每个连接下的数据库只显示 `visible_databases[config.id]` 中的（null/undefined 时显示全部）

**齿轮按钮位置：** 在搜索框上方标题栏右侧，与 `+` 按钮并排

#### 3. 新增 API 调用

文件：`frontend/src/api/databaseToolApi.ts`

```typescript
export interface DisplayPreferences {
    visible_connections: string[] | null;
    visible_databases: Record<string, string[]>;
}

export async function getDisplayPreferences(): Promise<DisplayPreferences>
export async function saveDisplayPreferences(prefs: DisplayPreferences): Promise<DisplayPreferences>
```

## 数据流

```
用户进入页面
    ↓
ConnectionList 加载
    ↓
调用 getDisplayPreferences() → 获取偏好
    ↓
根据偏好过滤 configs 列表显示
    ↓
用户点击齿轮图标
    ↓
DisplaySettingsDialog 打开
    ↓
批量加载所有连接的数据库列表 (Promise.all)
    ↓
用户勾选/取消连接和数据库
    ↓
用户点击「确认」
    ↓
调用 saveDisplayPreferences()
    ↓
后端保存到 user_display_preferences 表
    ↓
刷新 ConnectionList，应用新偏好
```

## 样式规范

遵循项目现有的 slate-800 暗色主题：

| 元素 | Tailwind 类 |
|------|------------|
| 弹窗容器 | `bg-slate-800 rounded-lg shadow-xl border border-slate-700` |
| 遮罩层 | `fixed inset-0 bg-black/50 backdrop-blur-sm z-[100]` |
| 复选框 | `rounded border-slate-600 bg-slate-700 text-blue-500` |
| 连接项（选中） | `bg-blue-500/10 border border-blue-500/30` |
| 连接项（未选中） | `hover:bg-slate-700/50` |
| 连接项（隐藏） | `opacity-40` |
| 数据库项 | `ml-6 text-sm text-slate-400 hover:bg-slate-700/30 rounded px-2 py-1` |
| 搜索框 | `bg-slate-900 border border-slate-700 rounded-md` |
| 确认按钮 | `bg-blue-600 hover:bg-blue-700 text-white rounded-md` |
| 重置按钮 | `text-slate-400 hover:text-white` |
| 过渡 | `transition-colors duration-200` |

## 无障碍

- 所有图标按钮添加 `aria-label`
- 复选框关联 `<label>` 标签
- 支持 ESC 关闭弹窗
- 弹窗内 Tab 焦点不逃逸（focus trap）
- 搜索框有 `role="search"` 和 `aria-label`

## 边界情况处理

| 场景 | 处理方式 |
|------|---------|
| 连接被删除 | 下次加载时自动从偏好中清理该连接 ID |
| 数据库名变更 | 偏好中保留旧名（不自动更新），用户可重新配置 |
| 新增连接 | 默认显示（visible_connections 为 null 时） |
| 新增数据库 | 默认隐藏（visible_databases 有配置时不自动包含新库） |
| 偏好加载失败 | 降级为全部显示，不阻塞页面 |
| 偏好保存失败 | Toast 提示错误，不关闭弹窗，用户可重试 |

## 涉及文件清单

### 后端
- `backend/app/models/database_tool_models.py` — 新增 DisplayPreference 模型
- `backend/app/services/database_tool_service.py` — 新增偏好 CRUD 方法
- `backend/app/routes/database_tool.py` — 新增 /preferences 端点
- `backend/app/utils/db_init.py` 或迁移脚本 — 创建 user_display_preferences 表

### 前端
- `frontend/src/components/Tools/DatabaseTool/components/DisplaySettingsDialog.tsx` — **新文件**
- `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx` — 新增齿轮按钮 + 偏好过滤
- `frontend/src/api/databaseToolApi.ts` — 新增偏好 API 调用
- `frontend/src/types/databaseTool.ts` — 新增 DisplayPreferences 类型

## 验证方案

1. TypeScript 编译检查（无新增错误）
2. 浏览器访问 `/tools/database-tool`
3. 手动测试流程：
   - 点击齿轮图标打开弹窗
   - 取消勾选某个连接，确认列表隐藏
   - 勾选连接的数据库，确认只显示选中的
   - 点击确认，刷新页面验证偏好持久化
   - 切换账号验证偏好按用户隔离
4. Console 无错误
