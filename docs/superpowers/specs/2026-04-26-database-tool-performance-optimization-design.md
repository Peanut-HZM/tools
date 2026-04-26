---
author: Peanut
created_at: 2026-04-26
purpose: Database tool performance optimization design spec
---

# 数据库工具性能优化设计文档

## 1. 问题概述

当前 `http://localhost:5178/tools/database-tool` 页面存在以下性能问题：

1. **每次 API 请求都新建数据库连接** — 后端 `DatabaseToolService` 中每次调用（`getDatabasesList`、`getDatabaseStructure`、`executeSQL` 等）都调用 `create_connection()` 建立新 MySQL 连接，操作完关闭。TCP 握手 + 认证开销导致单次请求额外耗时 200-500ms
2. **串行请求链** — 页面加载时 `refreshConfigs()` 和 `refreshHistory()` 串行执行；SQL Console 切换连接时先请求数据库列表、再请求表结构用于自动补全，形成依赖链
3. **无缓存机制** — 左侧连接树展开/折叠时每次都重新请求数据库列表和表结构
4. **无加载状态反馈** — 用户等待时无视觉反馈，感觉更慢

## 2. 优化目标

- 页面首次加载时间：减少 70%+
- 左侧树展开响应时间：减少 80%+（缓存命中时 < 50ms）
- SQL Console 打开响应时间：减少 50%+
- 优化连接池、前端缓存、请求并行化、骨架屏加载体验

## 3. 架构设计

### 3.1 后端连接池层

#### 3.1.1 连接池管理器

新增文件：`backend/app/services/db_pool_manager.py`

```python
class ConnectionPoolManager:
    """单例连接池管理器，维护所有数据库配置的连接池"""
    
    _instance = None
    _pools: Dict[str, Dict] = {}  # config_id -> pool_info
    _pool_lock = threading.Lock()
    
    def get_connection(self, config: dict) -> pymysql.Connection:
        """根据数据库配置获取连接（自动创建/复用/扩容池）"""
        config_id = config["id"]
        if config_id not in self._pools:
            self._create_pool(config)
        pool_info = self._pools[config_id]
        pool_info["last_used"] = time.time()
        return pool_info["pool"].connection()
    
    def _create_pool(self, config: dict):
        """创建新连接池（使用 pymysql 的 PooledDB 或 DBUtils）"""
        pool = PooledDB(
            creator=pymysql,
            maxconnections=5,     # 每个配置最多 5 个连接
            mincached=1,          # 初始化时至少 1 个
            blocking=True,
            maxusage=None,        # 无使用次数限制
            **self._build_connect_params(config)
        )
        self._pools[config["id"]] = {
            "pool": pool,
            "config_hash": hash(frozenset(config.items())),
            "last_used": time.time(),
            "config": config
        }
    
    def cleanup_idle_pools(self, idle_timeout=900):
        """清理空闲超过 15 分钟的连接池，释放资源"""
        now = time.time()
        to_remove = []
        for cid, info in self._pools.items():
            if now - info["last_used"] > idle_timeout:
                to_remove.append(cid)
        for cid in to_remove:
            pool_info = self._pools.pop(cid)
            try:
                pool_info["pool"].close()
            except: pass
            logger.info(f"清理空闲连接池: {cid}")
```

#### 3.1.2 定时清理任务

新增文件：`backend/app/services/pool_cleanup.py`

```python
# 在 main.py 启动时注册定时任务
# 每 5 分钟清理一次空闲连接池

async def pool_cleanup_task():
    while True:
        await asyncio.sleep(300)
        ConnectionPoolManager.get_instance().cleanup_idle_pools()
```

#### 3.1.3 现有服务层改造

修改文件：`backend/app/services/database_tool_service.py`

将 `DatabaseToolService.get_connection(config)` 替换为 `ConnectionPoolManager.get_connection(config)`。具体变更：
- 删除 `create_connection()` 方法中的直连逻辑
- 改用连接池获取连接
- 保持 `finally: conn.close()` 不变（`PooledDB` 的 `close()` 是归还到池中，不是真正关闭）

#### 3.1.4 依赖

需要添加：
- `DBUtils>=3.0.0`（Python 连接池库，轻量、稳定）
- 或直接用 `pymysql.connections` 手动实现（无新依赖）

**推荐**：使用 DBUtils，`PooledDB` 提供线程安全的连接池，代码量极少。

### 3.2 前端 IndexedDB 缓存层

#### 3.2.1 缓存模块

新增文件：`frontend/src/utils/dbCache.ts`

```typescript
/**
 * 基于 IndexedDB 的离线缓存工具
 * 用于缓存数据库工具的各类数据，减少重复 API 请求
 */

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

// 缓存配置
const CACHE_CONFIG = {
  configs: { ttl: 5 * 60 * 1000 },       // 5 分钟
  databases: { ttl: 3 * 60 * 1000 },      // 3 分钟
  structure: { ttl: 10 * 60 * 1000 },     // 10 分钟
  history: { ttl: 60 * 60 * 1000 },       // 1 小时
};

export class DBCache {
  private static db: IDBDatabase | null = null;
  private static readonly STORE_NAME = 'dbToolCache';
  
  /** 获取缓存数据，过期时返回 undefined */
  static async get<T>(key: string): Promise<T | undefined>
  
  /** 设置缓存数据，自动计算过期时间 */
  static async set<T>(key: string, data: T, ttlKey: keyof typeof CACHE_CONFIG): Promise<void>
  
  /** 清除指定缓存 */
  static async invalidate(key: string): Promise<void>
  
  /** 清除所有缓存 */
  static async clear(): Promise<void>
}
```

#### 3.2.2 API 层集成

修改文件：`frontend/src/api/databaseToolApi.ts`

在各 API 函数中加入缓存读写：

```typescript
export async function getDatabases(includePassword = false): Promise<DatabaseConfig[]> {
  // 先查缓存
  const cached = await DBCache.get<DatabaseConfig[]>('configs');
  if (cached && !includePassword) return cached;
  
  // 缓存未命中，走网络
  const data = await fetch(...);
  
  // 写入缓存
  if (!includePassword) await DBCache.set('configs', data, 'configs');
  return data;
}

export async function getDatabasesList(id: string): Promise<string[]> {
  const cacheKey = `databases:${id}`;
  const cached = await DBCache.get<string[]>(cacheKey);
  if (cached) return cached;
  
  const data = await fetch(...);
  await DBCache.set(cacheKey, data, 'databases');
  return data;
}

export async function getDatabaseStructure(id: string, databaseName: string): Promise<DatabaseStructure> {
  const cacheKey = `structure:${id}:${databaseName}`;
  const cached = await DBCache.get<DatabaseStructure>(cacheKey);
  if (cached) return cached;
  
  const data = await fetch(...);
  await DBCache.set(cacheKey, data, 'structure');
  return data;
}
```

#### 3.2.3 缓存失效策略

- **配置变更**：创建/编辑/删除连接后，`invalidate('configs')` 和 `invalidate('databases:*')`
- **结构变更**：执行 DDL（CREATE TABLE / DROP TABLE / ALTER TABLE）后，`invalidate('structure:*')`
- **手动刷新**：左侧连接列表的刷新按钮触发 `invalidate()` 后重新请求

### 3.3 前端请求优化

#### 3.3.1 并行化改造

修改文件：`frontend/src/contexts/DatabaseToolContext.tsx`

```typescript
// Before (串行)
useEffect(() => {
  refreshConfigs();
  refreshHistory();
}, [isAuthenticated]);

// After (并行)
useEffect(() => {
  if (isAuthenticated) {
    Promise.all([refreshConfigs(), refreshHistory()]).catch(console.error);
  }
}, [isAuthenticated]);
```

修改文件：`frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx`

```typescript
// SQL Console 切换连接时，数据库列表和表结构并行获取（如果当前已有选中数据库）
useEffect(() => {
  const fetchAll = async () => {
    if (!currentConfig) { setDatabases([]); return; }
    const targetDb = currentDatabase || currentConfig?.database_name;
    
    // 并行请求
    const [dbs, structure] = await Promise.allSettled([
      api.getDatabasesList(currentConfig.id),
      targetDb ? api.getDatabaseStructure(currentConfig.id, targetDb) : Promise.resolve(null)
    ]);
    
    if (dbs.status === 'fulfilled') setDatabases(dbs.value);
    if (structure.status === 'fulfilled' && structure.value) {
      setTables([...structure.value.tables.map(t => t.name), ...structure.value.views.map(v => v.name)]);
    }
  };
  fetchAll();
}, [currentConfig?.id, currentDatabase]);
```

#### 3.3.2 历史记录懒加载

`refreshHistory()` 改为按需加载（用户首次点击"执行历史"时才请求），而非页面加载时自动请求。

#### 3.3.3 预取优化

当用户点击连接节点展开时，**提前预取**数据库列表：

```typescript
// ConnectionList.tsx - 鼠标悬停时预取
const handleMouseEnter = () => {
  if (!loaded) {
    // 预取但不显示，存入 IndexedDB 缓存
    api.getDatabasesList(config.id).catch(() => {});
  }
};
```

### 3.4 骨架屏 + 加载状态

#### 3.4.1 连接列表骨架屏

修改文件：`frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx`

```tsx
{isLoading && configs.length === 0 ? (
  <div className="p-4 space-y-3">
    {[1, 2, 3].map(i => (
      <div key={i} className="flex items-center space-x-3 animate-pulse">
        <div className="w-6 h-6 bg-slate-700 rounded"></div>
        <div className="flex-1 h-4 bg-slate-700 rounded"></div>
      </div>
    ))}
  </div>
) : (
  /* 正常渲染 */
)}
```

#### 3.4.2 树节点加载优化

现有 `DatabaseStructureNode` 已有 `loading` spinner，保持不变。但增加缓存命中时的**瞬时渲染**：

```typescript
const handleToggle = async (e: React.MouseEvent) => {
  e.stopPropagation();
  onSelectDatabase();
  
  const nextState = !isExpanded;
  setIsExpanded(nextState);
  
  if (nextState && !structure) {
    // 先尝试从缓存读取（同步渲染），再后台刷新
    await fetchStructure();
  }
};
```

## 4. 数据流图

```
页面加载
    │
    ├─ [并行] GET /api/database-tool/databases
    │         │
    │         ├─ 查 IndexedDB 缓存 → 命中 → 立即渲染
    │         └─ 未命中 → 请求后端 → 写入缓存 → 渲染
    │
    └─ [并行] 历史记录 (改为懒加载，不再自动请求)

用户展开连接树
    │
    ├─ 查 IndexedDB 缓存 → 命中 → 立即渲染（无网络请求）
    └─ 未命中 → GET /api/database-tool/{id}/databases
              → 写入缓存 → 渲染

用户打开 SQL Console
    │
    ├─ [并行] GET /api/database-tool/{id}/databases (数据库列表)
    └─ [并行] GET /api/database-tool/{id}/structure (表结构, 如果有默认库)
              │
              ├─ 均查缓存 → 命中 → 50ms 内完成
              └─ 均未命中 → 后端连接池处理 → 约 300ms 完成
```

## 5. 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| DBUtils 引入新依赖 | 低 | DBUtils 是成熟库，PyPI 周下载量 500K+，零依赖 |
| IndexedDB 数据过期导致展示陈旧数据 | 中 | 设置合理 TTL，提供手动刷新按钮，DDL 操作后主动失效 |
| 连接池泄漏（未归还连接） | 中 | PooledDB 的 `close()` 自动归还，增加 `maxusage` 限制 |
| 缓存键冲突 | 低 | 缓存键包含 config_id + database_name，唯一性强 |
| 并发写入 IndexedDB | 低 | IndexedDB 原生支持事务，同一 store 写入自动排队 |

## 6. 验证方案

### 6.1 性能指标

| 场景 | 优化前（预估） | 优化后（目标） | 测量方法 |
|------|---------------|---------------|---------|
| 页面首次加载 | ~1500ms | < 500ms | 浏览器 Network 面板 |
| 展开连接树（缓存命中） | ~800ms | < 50ms | 浏览器 Network 面板 |
| 展开连接树（缓存未命中） | ~800ms | ~300ms | 浏览器 Network 面板 |
| SQL Console 打开 | ~1200ms | < 400ms | 浏览器 Network 面板 |

### 6.2 功能验证

- [ ] 连接列表正常加载
- [ ] 展开/折叠连接树正常
- [ ] 编辑/删除连接后缓存正确失效
- [ ] SQL Console 自动补全正常
- [ ] 手动刷新后缓存更新
- [ ] 离线状态下缓存数据仍可浏览
- [ ] 后端连接池正常创建和回收

## 7. 实施顺序

1. **Phase 1: 后端连接池** — 新建 `db_pool_manager.py`，修改 `database_tool_service.py`，验证后端正常
2. **Phase 2: 前端 IndexedDB 缓存** — 新建 `dbCache.ts`，修改 `databaseToolApi.ts` 加入缓存逻辑
3. **Phase 3: 请求并行化 + 懒加载** — 修改 `DatabaseToolContext.tsx`、`SQLExecutor.tsx`
4. **Phase 4: 骨架屏 + 体验优化** — 修改 `ConnectionList.tsx`，添加加载状态

每个 Phase 独立验证，确认无回归后再进入下一阶段。

## 8. 新增/修改文件清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `backend/app/services/db_pool_manager.py` | 连接池管理器 |
| 新增 | `backend/app/services/pool_cleanup.py` | 连接池定时清理 |
| 修改 | `backend/app/services/database_tool_service.py` | 替换直连为连接池 |
| 修改 | `backend/requirements.txt` | 添加 DBUtils 依赖 |
| 修改 | `backend/app/main.py` | 注册连接池清理任务 |
| 新增 | `frontend/src/utils/dbCache.ts` | IndexedDB 缓存工具 |
| 修改 | `frontend/src/api/databaseToolApi.ts` | 集成缓存读写 |
| 修改 | `frontend/src/contexts/DatabaseToolContext.tsx` | 并行请求 + 懒加载 |
| 修改 | `frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx` | 并行请求优化 |
| 修改 | `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx` | 骨架屏 + 预取 |
