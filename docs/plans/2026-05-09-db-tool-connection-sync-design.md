# 数据库工具：连接列表 ↔ SQL Console 双向联动设计

日期：2026-05-09

## 1. 问题

当前数据库管理工具的左侧连接列表和右侧 SQL Console Tab 之间没有联动：

- **左→右缺失**：点击左侧连接/数据库时，右侧 SQL Console 的连接和数据库不跟随变化
- **右→左缺失**：切换右侧 Tab 时，左侧连接列表不会展开/高亮对应连接

## 2. 需求

1. 点击左侧连接/数据库 → 当前活跃的 SQL Console Tab 切换到对应连接和数据库
2. 切换右侧 Tab → 左侧连接列表自动展开并高亮当前 Tab 绑定的连接和数据库

## 3. 方案选择

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| A: Active Tab 数据源 | SQLExecutor 保持自包含，用 ref/回调双向同步 | SQLExecutor 独立性强 | ref/回调体操，复杂 |
| **B: 状态提升** | 连接状态提升回 DatabaseTool.tsx，SQLExecutor 变为受控组件 | 单向数据流，清晰，与现有 Tab 模型对齐 | SQLExecutor 不再自包含 |
| C: 事件总线 | 创建 useTabSync() hook 或事件总线 | 解耦 | 过度工程化 |

**选择方案B**：符合 React "状态提升" 最佳实践，DatabaseTool.tsx 已有 Tab.sqlState 数据模型。

## 4. 核心数据流

```
左→右：点击连接/数据库 → DatabaseTool 更新活跃Tab的sqlState → SQLExecutor props变更
右→左：切换Tab → DatabaseTool 读取活跃Tab的sqlState → ConnectionList展开/高亮
```

## 5. 数据模型变更

### 5.1 Tab 数据模型（已有，无需修改）

```typescript
interface SqlTabState {
  configId: string;      // 绑定的连接ID（空串=未选择）
  databaseName: string;  // 绑定的数据库名（空串=未选择）
  sql: string;           // 当前SQL文本
}
```

### 5.2 SQLExecutor Props 变更

```typescript
// 之前：自包含（初始化后内部管理）
interface SQLExecutorProps {
  initialConfigId?: string;
  initialDatabase?: string;
  initialSql?: string;
}

// 之后：受控（父组件管理状态）
interface SQLExecutorProps {
  configId: string;          // 受控：当前连接
  database: string;          // 受控：当前数据库
  sql: string;               // 受控：当前SQL文本
  onStateChange: (state: { configId: string; database: string; sql: string }) => void;
}
```

SQLExecutor 内部：
- 移除 `localConfigId`/`localDatabase` state
- 改为直接使用 props 的 `configId`/`database`
- 用户在 SQLExecutor 下拉框切换连接/数据库时，调用 `onStateChange` 通知父组件
- 父组件更新 Tab.sqlState → props 变更 → SQLExecutor 重新渲染

### 5.3 ConnectionList Props 变更

```typescript
interface ConnectionListProps {
  // ... 现有props保持不变
  activeConfigId?: string;      // 新增：当前活跃的连接ID，用于高亮展开
  activeDatabaseName?: string;  // 新增：当前活跃的数据库名，用于高亮
  onConnectionSelect?: (configId: string, databaseName?: string) => void;  // 新增：左侧点击回调
}
```

## 6. 交互设计

### 6.1 左→右联动

| 用户操作 | 行为 |
|----------|------|
| 点击连接节点 | 活跃Tab的configId更新，databaseName重置为该连接默认库 |
| 点击数据库节点 | 活跃Tab的configId + databaseName同时更新 |
| 点击表节点 | 同数据库节点 + 可选生成 `SELECT * FROM table LIMIT 100` |
| 右键"新建SQL Console" | 新建Tab并绑定（现有逻辑，不变） |

### 6.2 右→左联动

| 用户操作 | 行为 |
|----------|------|
| 切换Tab | 读取新活跃Tab的sqlState → ConnectionList展开对应连接、高亮数据库 |
| SQLExecutor内切换连接 | 通过onStateChange更新Tab.sqlState → ConnectionList同步高亮 |
| SQLExecutor内切换数据库 | 同上 |

### 6.3 边界情况

- **活跃Tab是table类型**：左侧点击连接/数据库时，新建SQL Console Tab并绑定
- **没有SQL Tab**：左侧点击连接时，自动新建SQL Console Tab
- **活跃Tab未绑定连接（configId为空）**：左侧不高亮任何节点

## 7. DatabaseTool.tsx 核心逻辑

```typescript
// 从活跃Tab派生左侧高亮状态
const activeTab = tabs.find(t => t.id === activeTabId);
const activeConfigId = activeTab?.type === 'sql' ? activeTab.sqlState?.configId : activeTab?.data?.configId;
const activeDatabaseName = activeTab?.type === 'sql' ? activeTab.sqlState?.databaseName : activeTab?.data?.databaseName;

// 左→右：左侧点击时更新活跃Tab
const handleConnectionSelect = (configId: string, databaseName?: string) => {
  const activeTab = tabs.find(t => t.id === activeTabId);
  if (activeTab?.type === 'sql') {
    // 更新现有SQL Tab
    setTabs(prev => prev.map(t => 
      t.id === activeTabId 
        ? { ...t, sqlState: { ...t.sqlState!, configId, databaseName: databaseName || '', sql: t.sqlState!.sql } }
        : t
    ));
  } else {
    // 当前是table Tab或无Tab，新建SQL Console
    handleOpenSqlConsole('', databaseName, configId);
  }
};

// 右→左：SQLExecutor状态变更时更新Tab
const handleSqlStateChange = (tabId: string, state: { configId: string; database: string; sql: string }) => {
  setTabs(prev => prev.map(t => 
    t.id === tabId 
      ? { ...t, sqlState: { configId: state.configId, databaseName: state.database, sql: state.sql } }
      : t
  ));
};
```

## 8. 涉及文件

| 文件 | 改动 |
|------|------|
| `DatabaseTool.tsx` | 新增 handleConnectionSelect/handleSqlStateChange，派生 activeConfigId/activeDatabaseName，传给子组件 |
| `SQLExecutor.tsx` | 从自包含改为受控组件，props 改为 configId/database/sql + onStateChange |
| `ConnectionList.tsx` | 新增 activeConfigId/activeDatabaseName/onConnectionSelect props，自动展开高亮 |
| `ConnectionNode.tsx`（内嵌） | 根据 activeConfigId 判断展开/高亮状态 |
| `DatabaseStructureNode.tsx`（内嵌） | 根据 activeDatabaseName 高亮数据库节点 |

## 9. 风险与缓解

- **回归风险**：SQLExecutor 改为受控组件可能影响现有下拉框交互 → 逐步测试，确保 onStateChange 回调正确触发
- **性能风险**：Tab.sqlState 频繁更新（如输入SQL时） → sql 字段仅在 onStateChange 中同步，编辑时通过 debounce 或仅在失焦时同步
