# 多SQL Console窗口 — 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在数据库管理工具中支持多个独立SQL Console Tab，每个Tab绑定独立的连接和数据库，支持右键从树节点打开绑定的Console。

**Architecture:** 扩展现有Tab系统（`DatabaseTool.tsx`），将SQL Console从全局单例改造为自包含组件。`SQLExecutor` 接收 `initialConfigId`/`initialDatabase`/`initialSql` props，内部维护连接状态。右键菜单和Tab栏提供新建入口。

**Tech Stack:** React 18, TypeScript, Tailwind CSS, 现有DatabaseToolContext

---

### Task 1: 扩展Tab数据模型

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/DatabaseTool.tsx`

**Step 1: 更新Tab接口**

在 `DatabaseTool.tsx` 中，扩展 `Tab` 接口添加 SQL Console 专用字段：

```typescript
interface SqlTabState {
  configId: string;
  databaseName: string;
  sql: string;
}

interface Tab {
  id: string;
  type: 'sql' | 'table';
  title: string;
  data?: {
    configId: string;
    databaseName?: string;
    tableName: string;
  };
  sqlState?: SqlTabState;
}
```

**Step 2: 改造 openSqlConsole 函数**

将现有 `handleOpenSqlConsole` 函数扩展为支持参数：

```typescript
const handleOpenSqlConsole = (configId?: string, databaseName?: string, initialSql?: string) => {
  const tabId = `sql-${Date.now()}`;
  
  let title = 'SQL Console';
  if (configId) {
    const config = configs.find(c => c.id === configId);
    if (config) {
      title = databaseName 
        ? `${config.alias}.${databaseName}` 
        : config.alias;
    }
  }
  
  if (title.length > 25) {
    title = title.substring(0, 22) + '...';
  }

  const sqlState: SqlTabState | undefined = configId ? {
    configId,
    databaseName: databaseName || '',
    sql: initialSql || '',
  } : undefined;

  const newTab: Tab = { 
    id: tabId, 
    type: 'sql', 
    title,
    sqlState,
  };
  setTabs(prev => [...prev, newTab]);
  setActiveTabId(tabId);
};
```

**Step 3: 验证**

- 打开数据库工具页，TypeScript编译无错误
- 默认 "SQL Console" Tab正常显示

---

### Task 2: 改造SQLExecutor为自包含组件

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx`

**Step 1: 添加Props接口**

```typescript
interface SQLExecutorProps {
  initialConfigId?: string;
  initialDatabase?: string;
  initialSql?: string;
}
```

**Step 2: 重构组件内部状态**

将依赖 `useDatabaseTool()` 获取的 `currentConfig`/`currentDatabase` 改为组件内部状态：

```typescript
const SQLExecutor: React.FC<SQLExecutorProps> = ({ 
  initialConfigId, 
  initialDatabase,
  initialSql 
}) => {
  const { configs, refreshHistory } = useDatabaseTool();
  const toast = useToast();
  const { t } = useI18n();
  
  const [localConfigId, setLocalConfigId] = useState<string | null>(initialConfigId || null);
  const [localDatabase, setLocalDatabase] = useState<string>(initialDatabase || '');
  
  const currentConfig = useMemo(
    () => configs.find(c => c.id === localConfigId) || null,
    [configs, localConfigId]
  );
  const currentDatabase = localDatabase || currentConfig?.database_name || '';
  
  const [sql, setSql] = useState(initialSql || '');
  // ... 其余状态保持不变
```

**Step 3: 更新连接/数据库选择器绑定**

`<select>` 绑定到 `localConfigId` 和 `localDatabase`。

**Step 4: 更新useEffect依赖和SQL执行逻辑**

所有引用 `currentConfig?.id` → `localConfigId`，`currentDatabase` → 组件的 `currentDatabase` 变量。

**Step 5: 验证**

- TypeScript编译无错误
- 现有SQL Console功能不受影响

---

### Task 3: DatabaseTool组件Tab渲染改造

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/DatabaseTool.tsx`

**Step 1: Tab渲染传入props**

```tsx
{tab.type === 'sql' ? (
  <SQLExecutor
    initialConfigId={tab.sqlState?.configId}
    initialDatabase={tab.sqlState?.databaseName}
    initialSql={tab.sqlState?.sql}
  />
) : (
  tab.data && (
    <TableDataViewer ... />
  )
)}
```

**Step 2: 验证**

- 多Tab切换时各Tab连接独立

---

### Task 4: 右键菜单新增入口

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx`
- Modify: `frontend/src/i18n/locales/zh-CN.ts`
- Modify: `frontend/src/i18n/locales/en-US.ts`

**Step 1: 扩展onOpenSqlConsole类型**

将 `onOpenSqlConsole` 签名从 `(initialSql?: string, databaseName?: string) => void` 改为 `(initialSql?: string, databaseName?: string, configId?: string) => void`。

**Step 2: 在数据库和表节点右键菜单添加入口**

- 数据库节点: "新建SQL Console"（绑定连接+库）
- 表节点: "新建查询"（绑定连接+库+预填SELECT）

**Step 3: 添加i18n翻译**

zh-CN: `newSqlConsole: '新建 SQL Console'`, `newQuery: '新建查询'`
en-US: `newSqlConsole: 'New SQL Console'`, `newQuery: 'New Query'`

**Step 4: 更新prop传递链**

确保 `configId` 从 `ConnectionList` → `ConnectionNode` → `DatabaseStructureNode` → `FolderNode` 正确传递。

**Step 5: 验证**

- 右键菜单显示新选项
- 点击后正确打开绑定Tab

---

### Task 5: Tab标题与样式优化

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/DatabaseTool.tsx`

**Step 1: Tab标题逻辑**

- 无连接: "SQL Console"
- 有连接: "{别名}.{库名}"（截断>25字符）

**Step 2: 持久显示 + 按钮**

Tab栏末尾始终显示"+"按钮，点击创建新SQL Console Tab。

**Step 3: 验证**

- Tab标题正确，"+"按钮可用

---

### Task 6: 端到端测试

1. 打开数据库工具页
2. 点击"+"打开新Console Tab → 选择不同连接/库 → 执行SQL → 切换Tab状态保持
3. 右键数据库节点 → "新建SQL Console" → 验证绑定正确
4. 右键表节点 → "新建查询" → 验证预填SQL和绑定
5. 关闭Tab → 无报错

---

**设计文档**: 同文件前半部分已包含完整设计

## 问题

当前数据库管理工具只有一个全局SQL Console，无法同时连接不同数据库执行SQL。用户需要能够在多个连接/库之间快速切换，并保留每个窗口的SQL和执行结果。

## 需求

1. 支持多个SQL Console Tab，每个绑定独立的连接和数据库
2. 右键数据库/表节点可打开绑定的Console
3. Tab栏支持新增空白Console
4. 每个Console窗口保留独立的执行历史
5. 切换Tab时保留各自的SQL和结果状态
6. 工具栏内可切换连接和数据库

## 设计决策

**方案选择**: 自包含Tab组件（方案A）

每个SQL Console Tab自带完整的连接/数据库选择器 + SQL编辑器 + 结果面板。`SQLExecutor` 从依赖全局Context改为接收 `initialConfigId`/`initialDatabase` props，并在组件内部维护自己的连接状态。

**理由**: 改动最小、风险最低、与现有代码风格一致。

## 数据模型

### Tab接口扩展

```typescript
interface Tab {
  id: string;
  type: 'sql' | 'table';
  title: string;
  data?: {
    configId: string;
    databaseName?: string;
    tableName: string;
  };
  // SQL Console 专用状态
  sqlState?: {
    configId: string;
    databaseName: string;
    sql: string;
    result: SQLExecutionResult | null;
    page: number;
  };
}
```

关键设计点：
- `sqlState` 只在 `type === 'sql'` 时存在
- Tab关闭时状态随组件销毁
- 全局执行历史仍保留在 `DatabaseToolContext`，不随Tab销毁

## 组件架构

```
DatabaseTool.tsx (Tab管理)
├── ConnectionList (左侧栏)
│   └── 右键菜单: "新建SQL Console"
├── TabBar (顶部)
│   ├── SqlConsoleTab (独立状态)
│   └── TableTab (现有)
├── SQLExecutor (改造)
│   ├── Props: initialConfigId, initialDatabase, initialSql
│   └── 内部状态: currentConfig, currentDatabase, sql, result, page
└── TableDataViewer (无改动)
```

### SQLExecutor改造

**改动**: 从依赖 `useDatabaseTool()` 获取连接 → 接收 props 初始化 + 内部管理连接状态

```typescript
interface SQLExecutorProps {
  initialConfigId?: string;      // 右键打开时传入
  initialDatabase?: string;      // 右键打开时传入
  initialSql?: string;           // 预填SQL（如SELECT模板）
}
```

组件行为：
- 若传入 `initialConfigId`，自动选中该连接
- 若传入 `initialDatabase`，自动选中该数据库
- 若传入 `initialSql`，预填SQL编辑器
- 工具栏中的连接/数据库选择器仍然可用，允许用户切换

### Tab生命周期

```
新建Tab:
  1. 生成唯一ID (sql-{timestamp})
  2. 设置 title = "SQL Console" 或 "{alias}.{db}"
  3. 创建 <SQLExecutor initialConfigId={...} initialDatabase={...} />
  4. 切换到新Tab

关闭Tab:
  1. 从tabs数组移除
  2. 若关闭的是activeTab，切换到最后一个Tab
  3. 若无Tab，显示空状态或创建默认Console

切换Tab:
  1. 更新activeTabId
  2. 所有Tab DOM已渲染（display:none/block切换），状态自然保留
```

## 入口点

| 触发方式 | 行为 | 传入参数 |
|----------|------|----------|
| 左侧栏Terminal按钮 | 打开空白Console | 无（使用当前全局连接） |
| 右键数据库节点 → "新建SQL Console" | 打开绑定的Console | configId, databaseName |
| 右键表节点 → "新建查询" | 打开Console+预填SELECT | configId, databaseName, initialSql |
| Tab栏 + 按钮 | 新增空白Console | 无 |

## 后端影响

**无需后端改动**。现有 `executeSQL` API 已支持 `db_config_id` + `database_name` 参数。

## 实现清单

1. **Tab接口扩展** — `DatabaseTool.tsx` 中增加sqlState字段
2. **新增Tab函数** — `handleOpenSqlConsole(configId?, dbName?, initialSql?)` 
3. **SQLExecutor改造** — 新增props（initialConfigId, initialDatabase, initialSql），内部管理连接状态
4. **ConnectionList改造** — 右键菜单增加"新建SQL Console"选项
5. **Tab渲染改造** — SQL Tab传入props而非依赖全局Context
6. **Tab标题** — 显示连接别名+库名（如"prod.ehr_portal_dev"）

## 不在范围内

- Tab拖拽排序
- 分屏显示
- SQL执行历史按Tab过滤（保留全局历史）
- Tab状态持久化到localStorage