---
author: Peanut
created_at: 2026-04-26
purpose: Database tool performance optimization design spec
---

# 数据库工具性能优化设计文档

## 1. 问题概述

当前 `http://localhost:5178/tools/database-tool` 页面存在以下性能问题：

1. **后端引擎永久缓存无清理** — `DBConnectionManager` 已使用 SQLAlchemy 连接池（`pool_size=10, pool_recycle=3600, pool_pre_ping=True`），引擎按 `config_id:database_name` 缓存。**但引擎一旦创建永远不会被清理**（除非显式调用 `close_engine`）。当用户修改连接配置或删除连接后，旧引擎仍然占用内存和连接数。多个数据库配置 × 多个数据库名 → 大量空闲引擎长期存活
2. **前端无缓存机制** — 左侧连接树展开/折叠时每次都重新请求数据库列表和表结构（`getDatabasesList`、`getDatabaseStructure`），即使数据未变化也走完整网络请求 + 数据库查询链路
3. **串行请求链** — 页面加载时 `refreshConfigs()` 和 `refreshHistory()` 串行执行（`useEffect` 中先调 `refreshConfigs()` 再调 `refreshHistory()`）；SQL Console 切换连接时先请求数据库列表、再请求表结构用于自动补全，形成依赖链
4. **历史记录预加载但未使用** — `refreshHistory()` 每次页面加载都请求最近 50 条执行历史，但首页并未展示这些数据，白白消耗资源
5. **无加载状态反馈** — 用户等待时无视觉反馈，感知等待时间更长

## 2. 优化目标

- 页面首次加载时间：减少 70%+
- 左侧树展开响应时间：减少 80%+（缓存命中时 < 50ms）
- SQL Console 打开响应时间：减少 50%+
- 优化连接池、前端缓存、请求并行化、骨架屏加载体验

## 3. 架构设计

### 3.1 后端连接池优化

#### 3.1.1 现状分析

`DBConnectionManager`（`backend/app/utils/db_connection_manager.py`）已经实现了 SQLAlchemy 连接池：
- `pool_size=10` — 每个配置最多 10 个连接
- `pool_recycle=3600` — 1 小时回收连接
- `pool_pre_ping=True` — 取连接前先 ping，防止 2013 错误
- 支持 MySQL、PostgreSQL、SQLite、SQLServer、Oracle 多种数据库类型

**问题所在**：
1. **引擎永久缓存** — `_engines` 字典一旦写入就从不清理，引擎和连接池永久占用资源
2. **无配置变更检测** — 用户修改连接地址/密码后，仍使用旧的 Engine 实例
3. **无内存泄漏保护** — 大量连接配置 × 多个数据库名 = 大量空闲 Engine 存活

#### 3.1.2 优化方案

修改文件：`backend/app/utils/db_connection_manager.py`

**1. 添加引擎健康检查与惰性清理**

```python
class DBConnectionManager:
    _engines: Dict[str, Engine] = {}
    _engine_last_used: Dict[str, float] = {}  # 新增：记录最后使用时间
    
    @classmethod
    def get_engine(cls, config_id: str, config: Dict[str, Any]) -> Engine:
        db_name = config.get("database_name", "")
        engine_key = f"{config_id}:{db_name}"

        if engine_key in cls._engines:
            engine = cls._engines[engine_key]
            # 更新使用时间
            cls._engine_last_used[engine_key] = time.time()
            return engine

        engine = cls._create_engine(config)
        cls._engines[engine_key] = engine
        cls._engine_last_used[engine_key] = time.time()
        return engine
    
    @classmethod
    def cleanup_idle_engines(cls, idle_timeout: int = 900) -> int:
        """清理空闲超过指定时间的引擎，返回清理数量"""
        import time
        now = time.time()
        keys_to_remove = [
            k for k, last_used in cls._engine_last_used.items()
            if now - last_used > idle_timeout
        ]
        for key in keys_to_remove:
            if key in cls._engines:
                try:
                    cls._engines[key].dispose()
                except Exception as e:
                    logger.warning(f"清理引擎 {key} 失败: {e}")
                del cls._engines[key]
            cls._engine_last_used.pop(key, None)
        if keys_to_remove:
            logger.info(f"清理空闲引擎: {len(keys_to_remove)} 个 ({', '.join(keys_to_remove)})")
        return len(keys_to_remove)
    
    @classmethod
    def invalidate_engine(cls, engine_key: str):
        """使指定引擎失效，下次 get_engine 时重新创建（用于配置变更后）"""
        if engine_key in cls._engines:
            try:
                cls._engines[engine_key].dispose()
            except: pass
            del cls._engines[engine_key]
            cls._engine_last_used.pop(engine_key, None)
            logger.info(f"引擎失效: {engine_key}")
```

**2. 定时清理任务**

修改文件：`backend/app/main.py`

在 `lifespan` 上下文中注册后台清理任务（如已有 lifespan 则追加）：

```python
from app.utils.db_connection_manager import DBConnectionManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动清理任务
    async def cleanup_loop():
        while True:
            await asyncio.sleep(300)  # 每 5 分钟
            DBConnectionManager.cleanup_idle_engines(idle_timeout=900)
    
    task = asyncio.create_task(cleanup_loop())
    try:
        yield
    finally:
        task.cancel()
```

**3. 配置变更时主动失效**

修改文件：`backend/app/services/database_tool_service.py`

在 `create_config`、`update_config`、`delete_config` 方法中主动调用 `DBConnectionManager.invalidate_engine()` 使旧引擎失效：

```python
# delete_config 中
DBConnectionManager.close_engine(id)  # 已有，保持不变

# update_config 中
# 配置变更后清理该配置下的所有引擎
for key in list(DBConnectionManager._engines.keys()):
    if key.startswith(f"{config_id}:"):
        DBConnectionManager.invalidate_engine(key)
```

#### 3.1.3 优势

- **零新依赖** — 不引入 DBUtils，使用 SQLAlchemy 原生能力
- **通用** — 适用于 MySQL/PostgreSQL/SQLite/SQLServer/Oracle 所有数据库类型
- **最小改动** — 只需在 `DBConnectionManager` 中添加 2 个方法和 `_engine_last_used` 字典
- **连接池已有** — `pool_size`、`pool_recycle`、`pool_pre_ping` 都已配置，无需额外优化

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
| IndexedDB 数据过期导致展示陈旧数据 | 中 | 设置合理 TTL，提供手动刷新按钮，DDL 操作后主动失效 |
| 缓存键冲突 | 低 | 缓存键包含 config_id + database_name，唯一性强 |
| 并发写入 IndexedDB | 低 | IndexedDB 原生支持事务，同一 store 写入自动排队 |
| `Promise.all` 竞态导致 `isLoading` 状态不一致 | 低 | 使用独立的 loading state 或 `Promise.allSettled` |

## 6. 验证方案

### 6.1 性能指标

| 场景 | 优化前（预估） | 优化后（目标） | 测量方法 |
|------|---------------|---------------|---------|
| 页面首次加载 | ~1500ms | < 500ms | 浏览器 Network 面板 |
| 展开连接树（缓存命中） | ~800ms | < 50ms | 浏览器 Network 面板 |
| 展开连接树（缓存未命中） | ~800ms | ~300ms | 浏览器 Network 面板 |
| SQL Console 打开 | ~1200ms | < 400ms | 浏览器 Network 面板 |
| 后端空闲引擎自动清理 | 无 | 15 分钟空闲自动释放 | 后端日志 |
| 配置变更后旧引擎失效 | 无 | 编辑/删除连接后立即清理 | 后端日志 |

### 6.2 功能验证

- [ ] 连接列表正常加载
- [ ] 展开/折叠连接树正常
- [ ] 编辑/删除连接后缓存正确失效
- [ ] SQL Console 自动补全正常
- [ ] 手动刷新后缓存更新
- [ ] 离线状态下缓存数据仍可浏览
- [ ] 后端空闲引擎定时清理生效
- [ ] 配置变更后旧引擎主动失效
- [ ] 页面加载时不再请求历史记录（懒加载）

## 7. 实施顺序

1. **Phase 1: 后端引擎清理** — 修改 `db_connection_manager.py` 添加 `cleanup_idle_engines` + `invalidate_engine`，修改 `main.py` 注册清理任务，修改 `database_tool_service.py` 在配置变更时主动失效。验证后端正常
2. **Phase 2: 前端 IndexedDB 缓存** — 新建 `dbCache.ts`，修改 `databaseToolApi.ts` 加入缓存读写逻辑
3. **Phase 3: 请求并行化 + 懒加载** — 修改 `DatabaseToolContext.tsx`（并行请求 + 历史记录懒加载）、`SQLExecutor.tsx`（并行请求）
4. **Phase 4: 骨架屏 + 体验优化** — 修改 `ConnectionList.tsx`，添加骨架屏和预取

每个 Phase 独立验证，确认无回归后再进入下一阶段。

## 8. 新增/修改文件清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 修改 | `backend/app/utils/db_connection_manager.py` | 添加引擎清理 + 失效 + 使用时间追踪 |
| 修改 | `backend/app/main.py` | 注册连接池定时清理任务 |
| 修改 | `backend/app/services/database_tool_service.py` | 配置变更时主动使引擎失效 |
| 新增 | `frontend/src/utils/dbCache.ts` | IndexedDB 缓存工具 |
| 修改 | `frontend/src/api/databaseToolApi.ts` | 集成缓存读写 |
| 修改 | `frontend/src/contexts/DatabaseToolContext.tsx` | 并行请求 + 历史记录懒加载 |
| 修改 | `frontend/src/components/Tools/DatabaseTool/SQLExecutor.tsx` | 并行请求优化 |
| 修改 | `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx` | 骨架屏 + 预取 |
