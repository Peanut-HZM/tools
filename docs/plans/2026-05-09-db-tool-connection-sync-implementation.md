# 数据库工具：连接列表 ↔ SQL Console 双向联动 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现左侧连接列表与右侧SQL Console Tab的双向联动——点击左侧自动切换当前Tab连接，切换Tab自动展开高亮左侧节点。

**Architecture:** 采用方案B（状态提升），将SQLExecutor的连接/数据库状态提升回DatabaseTool.tsx的Tab.sqlState，SQLExecutor变为受控组件。DatabaseTool.tsx作为唯一状态源，派生activeConfigId/activeDatabaseName传给ConnectionList实现右→左联动，通过handleConnectionSelect回调实现左→右联动。

**Tech Stack:** React 18, TypeScript, Tailwind CSS

**设计文档:** `docs/plans/2026-05-09-db-tool-connection-sync-design.md`

---

### Task 1: SQLExecutor 改为受控组件

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx`

**Step 1: 修改 SQLExecutorProps 接口**

将 `initialConfigId`/`initialDatabase`/`initialSql` 替换为受控 props：

```typescript
interface SQLExecutorProps {
  configId: string;          // 受控：当前连接ID
  database: string;          // 受控：当前数据库名
  sql: string;               // 受控：当前SQL文本
  onStateChange: (state: { configId: string; database: string; sql: string }) => void;
}
```

**Step 2: 重构组件内部状态**

- 移除 `const [localConfigId, setLocalConfigId] = useState<string | null>(initialConfigId || null);`
- 移除 `const [localDatabase, setLocalDatabase] = useState<string>(initialDatabase || '');`
- 移除 `const [sql, setSql] = useState(initialSql || '');`
- 将 `currentConfig` useMemo 改为依赖 `props.configId`：

```typescript
const currentConfig = useMemo(
  () => configs.find(c => c.id === configId) || null,
  [configs, configId]
);
const currentDatabase = database || currentConfig?.database_name || '';
```

**Step 3: 更新下拉框 onChange 处理**

Connection 下拉框：
```tsx
<select
  value={configId || ''}
  onChange={(e) => {
    const newConfigId = e.target.value;
    const newConfig = configs.find(c => c.id === newConfigId);
    onStateChange({
      configId: newConfigId,
      database: newConfig?.database_name || '',
      sql
    });
  }}
>
```

Database 下拉框：
```tsx
<select
  value={database || ''}
  onChange={(e) => onStateChange({ configId, database: e.target.value, sql })}
>
```

**Step 4: 更新 SQL 编辑器 onChange**

```tsx
<SQLEditor
  value={sql}
  onChange={(newSql) => onStateChange({ configId, database, sql: newSql })}
  onExecute={handleExecute}
  loading={loading}
  tables={tables}
/>
```

**Step 5: 更新 handleExecute 中的引用**

将 `localConfigId` 替换为 `configId`：
```typescript
const handleExecute = async (pageOverride?: number) => {
  if (!configId || !sql.trim()) return;
  // ... api.executeSQL({ db_config_id: configId, ... })
};
```

**Step 6: 更新 useEffect 依赖**

将 `[localConfigId]` 替换为 `[configId]`：
```typescript
useEffect(() => {
  setResult(null);
}, [configId]);
```

**Step 7: 更新条件渲染**

将 `!localConfigId` 替换为 `!configId`。

**Step 8: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep SQLExecutor`
Expected: 无输出（无错误）

**Step 9: 浏览器验证**

- 打开 http://localhost:5178/tools/database-tool
- SQL Console 的连接下拉框应仍可正常切换
- 数据库下拉框应仍可正常切换
- 执行 SQL 应仍正常工作
- Console 无 React 错误

---

### Task 2: DatabaseTool.tsx 新增联动逻辑

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/DatabaseTool.tsx`

**Step 1: 更新 SQLExecutor 调用方式**

将 SQLExecutor 从 `initial*` 模式改为受控模式：

```tsx
{tab.type === 'sql' ? (
  <SQLExecutor
    configId={tab.sqlState?.configId || ''}
    database={tab.sqlState?.databaseName || ''}
    sql={tab.sqlState?.sql || ''}
    onStateChange={(state) => handleSqlStateChange(tab.id, state)}
  />
) : (
```

**Step 2: 新增 handleSqlStateChange 函数**

```typescript
const handleSqlStateChange = (tabId: string, state: { configId: string; database: string; sql: string }) => {
  setTabs(prev => prev.map(t => 
    t.id === tabId 
      ? { 
          ...t, 
          sqlState: { 
            configId: state.configId, 
            databaseName: state.database, 
            sql: state.sql 
          },
          // 同步更新Tab标题
          title: deriveTabTitle(state.configId, state.database)
        }
      : t
  ));
};
```

**Step 3: 新增 deriveTabTitle 辅助函数**

```typescript
const deriveTabTitle = (configId: string, databaseName: string): string => {
  if (!configId) return 'SQL Console';
  const config = configs.find(c => c.id === configId);
  if (!config) return 'SQL Console';
  const title = databaseName 
    ? `${config.alias}.${databaseName}` 
    : config.alias;
  return title.length > 25 ? title.substring(0, 22) + '...' : title;
};
```

**Step 4: 新增 handleConnectionSelect 函数（左→右联动）**

```typescript
const handleConnectionSelect = (configId: string, databaseName?: string) => {
  const activeTab = tabs.find(t => t.id === activeTabId);
  if (activeTab?.type === 'sql') {
    // 更新现有SQL Tab的连接
    const db = databaseName || configs.find(c => c.id === configId)?.database_name || '';
    setTabs(prev => prev.map(t => 
      t.id === activeTabId 
        ? { 
            ...t, 
            sqlState: { configId, databaseName: db, sql: t.sqlState?.sql || '' },
            title: deriveTabTitle(configId, db)
          }
        : t
    ));
  } else {
    // 当前是table Tab或无Tab，新建SQL Console
    handleOpenSqlConsole('', databaseName, configId);
  }
};
```

**Step 5: 派生左侧高亮状态（右→左联动）**

```typescript
// 从活跃Tab派生左侧高亮状态
const activeTab = tabs.find(t => t.id === activeTabId);
const activeConfigId = activeTab?.type === 'sql' 
  ? activeTab.sqlState?.configId 
  : activeTab?.data?.configId;
const activeDatabaseName = activeTab?.type === 'sql' 
  ? activeTab.sqlState?.databaseName 
  : activeTab?.data?.databaseName;
```

**Step 6: 传递新 props 给 ConnectionList**

```tsx
<ConnectionList
  onAddConfig={handleAddConfig}
  onEditConfig={handleEditConfig}
  onSelectTable={handleSelectTable}
  onOpenSqlConsole={handleOpenSqlConsole}
  activeConfigId={activeConfigId}
  activeDatabaseName={activeDatabaseName}
  onConnectionSelect={handleConnectionSelect}
/>
```

**Step 7: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep DatabaseTool`
Expected: 无输出（无错误）

---

### Task 3: ConnectionList 接收新 props 并实现右→左联动

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx`

**Step 1: 更新 ConnectionListProps 接口**

```typescript
interface ConnectionListProps {
  onAddConfig: () => void;
  onEditConfig: (id: string) => void;
  onSelectTable: (configId: string, databaseName: string | undefined, tableName: string) => void;
  onOpenSqlConsole?: (initialSql?: string, databaseName?: string, configId?: string) => void;
  activeConfigId?: string;      // 新增
  activeDatabaseName?: string;  // 新增
  onConnectionSelect?: (configId: string, databaseName?: string) => void;  // 新增
}
```

**Step 2: 解构新 props**

```typescript
const ConnectionList: React.FC<ConnectionListProps> = ({ 
  onAddConfig, onEditConfig, onSelectTable, onOpenSqlConsole,
  activeConfigId, activeDatabaseName, onConnectionSelect 
}) => {
```

**Step 3: 新增 useEffect 实现右→左自动展开**

当 activeConfigId 变化时，自动展开对应连接节点：

```typescript
// 右→左联动：当活跃Tab的连接变化时，自动展开对应节点
useEffect(() => {
  if (activeConfigId && !expandedNodes[activeConfigId]) {
    setExpandedNodes(prev => ({ ...prev, [activeConfigId]: true }));
  }
}, [activeConfigId]);
```

**Step 4: 修改连接节点的 isSelected 判断**

将 `isSelected={currentConfig?.id === config.id}` 替换为：
```tsx
isSelected={activeConfigId === config.id || currentConfig?.id === config.id}
```

优先使用 `activeConfigId`（来自Tab），回退到 `currentConfig`（全局Context）。

**Step 5: 修改 ConnectionNode 的 onSelect**

将 `onSelect={() => selectConfigById(config.id)}` 替换为：
```tsx
onSelect={() => {
  // 如果有联动回调，使用回调（左→右联动）
  if (onConnectionSelect) {
    onConnectionSelect(config.id);
  } else {
    selectConfigById(config.id);
  }
}}
```

**Step 6: 修改 handleSelectDatabase**

```typescript
const handleSelectDatabase = (configId: string, dbName: string) => {
  // 左→右联动：通知父组件更新活跃Tab
  if (onConnectionSelect) {
    onConnectionSelect(configId, dbName);
  } else {
    // 降级：使用全局Context
    if (currentConfig?.id !== configId) {
      selectConfigById(configId);
    }
    setCurrentDatabase(dbName);
  }
};
```

**Step 7: 传递 activeDatabaseName 到 DatabaseStructureNode**

需要在 ConnectionNode 和 DatabaseStructureNode 中传递 `activeDatabaseName`，用于高亮当前数据库节点。

ConnectionNode 中：
```tsx
<DatabaseStructureNode
  // ... 现有props
  activeDatabaseName={activeDatabaseName}
/>
```

ConnectionNodeProps 中新增：
```typescript
activeDatabaseName?: string;
```

**Step 8: DatabaseStructureNode 高亮当前数据库**

在 DatabaseStructureNode 中，对当前活跃数据库添加高亮样式：

```tsx
<div
  className={`... ${activeDatabaseName === dbName ? 'bg-blue-600/20 text-blue-300' : 'text-slate-300 hover:bg-slate-700/50'}`}
  onClick={onSelectDatabase}
>
```

DatabaseStructureNodeProps 中新增：
```typescript
activeDatabaseName?: string;
```

**Step 9: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep ConnectionList`
Expected: 无输出（无错误）

---

### Task 4: 端到端浏览器测试验证

**Step 1: 验证左→右联动**

1. 打开 http://localhost:5178/tools/database-tool
2. 点击 "+" 按钮新建 SQL Console Tab
3. 点击左侧某个连接节点
4. **验证**：右侧 SQL Console 的 Connection 下拉框自动切换到该连接
5. 点击左侧某个数据库节点
6. **验证**：右侧 SQL Console 的 Database 下拉框自动切换到该数据库

**Step 2: 验证右→左联动**

1. 新建两个 SQL Console Tab，分别绑定不同连接
2. 在右侧切换到 Tab A
3. **验证**：左侧连接列表自动展开并高亮 Tab A 的连接
4. 切换到 Tab B
5. **验证**：左侧连接列表切换高亮到 Tab B 的连接

**Step 3: 验证 SQLExecutor 内部切换**

1. 在 SQL Console 内通过下拉框切换连接
2. **验证**：左侧连接列表高亮跟随变化
3. 在 SQL Console 内切换数据库
4. **验证**：左侧数据库高亮跟随变化

**Step 4: 验证边界情况**

1. 当前活跃 Tab 是 table 类型，点击左侧连接 → 应新建 SQL Console Tab
2. 所有 Tab 关闭后点击左侧连接 → 应新建 SQL Console Tab

**Step 5: 验证控制台无错误**

Run: 在浏览器 DevTools Console 中检查，无 React 错误和未捕获异常

---

### Task 5: 最终验证与清理

**Step 1: TypeScript 完整编译检查**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -E "DatabaseTool|SQLExecutor|ConnectionList"`
Expected: 无输出（无错误）

**Step 2: 检查是否有残留的全局 Context 引用**

在 SQLExecutor 中不应再使用 `selectConfigById`、`setCurrentDatabase` 等全局 Context 方法（仅 `configs` 和 `refreshHistory` 仍然需要）。

Run: `grep -n "selectConfigById\|setCurrentDatabase\|setCurrentConfig" frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx`
Expected: 无输出

**Step 3: 确认 ConnectionList 中全局 Context 使用已降级**

ConnectionList 仍可使用 `selectConfigById`/`setCurrentDatabase` 作为降级方案（当 `onConnectionSelect` 未提供时），但优先使用 `onConnectionSelect` 回调。
