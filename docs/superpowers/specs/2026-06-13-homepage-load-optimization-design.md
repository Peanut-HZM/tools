---
author: Peanut
created_at: 2026-06-13
purpose: 首页加载性能优化设计方案，涵盖后端缓存/后台任务优化和前端请求管理/骨架屏
---

# 首页加载性能优化设计

## 背景

首页进入后加载时间较长（截图显示 `/categories` 5.6s、`/tools?platform=pc` 多个 pending 超过 10s），页面长时间显示"加载中..."，影响用户体验。

### 根因分析

| 层级 | 问题 | 表现 |
|------|------|------|
| 后端启动 | Token Usage 后台同步在 lifespan 中立即启动，占用数据库连接和 CPU | 首页 API 响应慢（5-10s） |
| 后端数据层 | `/categories`、`/tools` 每次请求都查数据库，无缓存 | 重复查询浪费资源 |
| 后端连接池 | `get_pooled_db_connection()` 每次都执行 `SELECT 1` 探针 | 每次请求额外增加 5-10ms |
| 前端请求 | 多个 useEffect 同时触发，旧请求未取消，无去重 | 截图显示 6 个 tools 请求 pending |
| 前端体验 | loading 状态只有文字，无骨架屏 | 长时间空白 |

---

## 方案概述（方案三：平衡式）

前后端同时优化，改动量适中，效果显著。

---

## 后端改动

### 1.1 延迟 Token Usage 后台同步

**文件**：`backend/app/services/token_usage_background_sync.py`

**改动**：
- `_background_sync_loop` 的首次延迟从 `TOKEN_USAGE_BACKGROUND_SYNC_INITIAL_DELAY_SECONDS` 调整为至少 **60 秒**（可通过 `TOKEN_USAGE_BACKGROUND_SYNC_INITIAL_DELAY_SECONDS` 配置项控制，最小值 60）
- 限制每轮同步的最大用户数，默认 3 人
- 同步失败时只记日志，不阻塞下一轮循环

### 1.2 进程内 TTL 缓存

**新建文件**：`backend/app/services/simple_cache.py`

**设计**：
```python
class SimpleTTLCache:
    """线程安全的进程内 TTL 缓存。"""
    
    def __init__(self, default_ttl: int = 300):
        self._cache: dict[str, tuple[datetime, Any]] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，过期返回 None 并自动清除。"""
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值，指定 TTL（秒），默认使用构造时的 default_ttl。"""
    
    def invalidate(self, key: str) -> None:
        """手动清除指定缓存。"""
    
    def invalidate_prefix(self, prefix: str) -> None:
        """按前缀批量清除缓存。"""
    
    def cleanup_expired(self) -> int:
        """清理所有过期条目，返回清理数量。"""
```

**使用位置**：`backend/app/services/tools_service.py`

- 给 `get_all_categories()` 加缓存，key = `"categories"`, TTL = 300s
- 给 `get_tools_for_platform(platform, category)` 加缓存，key = `"tools:{platform}:{category}"`, TTL = 300s
- 在管理员增删改工具/分类的接口中调用 `invalidate()` 清除对应缓存

**缓存失效点**：
| 操作 | 清除的缓存 key |
|------|---------------|
| 创建/更新/删除分类 | `"categories"` |
| 创建/更新/删除工具 | `"tools:pc:*"`, `"tools:mobile:*"`（按前缀清除） |

### 1.3 数据库连接健康检查优化

**文件**：`backend/app/config/database.py`

**改动**：
- 新增配置项 `DB_HEALTH_CHECK`（环境变量，默认 `"false"`）
- `get_pooled_db_connection()` 中，当 `DB_HEALTH_CHECK=false` 时跳过 `SELECT 1` 探针
- 保留探针失败时的重试逻辑（`DB_HEALTH_CHECK=true` 时才执行）
- **生产环境建议设为 `"true"`**，开发环境可关闭以减少延迟

### 1.4 后台同步日志优化

**文件**：`backend/app/services/token_usage_background_sync.py`

**改动**：
- `run_background_sync_once` 增加每轮总耗时日志
- 每个用户同步完成后打印单用户耗时
- 便于后续定位慢用户和排查问题

---

## 前端改动

### 2.1 修复 useEffect 重复调用

**文件**：`frontend/src/App.tsx`

**问题**：初始化时 `loadTools()` 被 `useEffect([], [])` 和 `useEffect([activeCategory])` 同时触发两次。

**改动**：
- 新增 `useRef` 标记 `isInitialized`
- 初始化 effect 完成后设置 `isInitialized = true`
- 分类切换 effect 增加守卫：`if (!isInitializedRef.current) return`
- 搜索 effect 同理

### 2.2 AbortController 取消过期请求

**文件**：`frontend/src/services/api.ts` + `frontend/src/App.tsx`

**改动 api.ts**：
- `fetchCategories(signal?: AbortSignal)`
- `fetchTools(platform?: string, signal?: AbortSignal)`
- `loadToolsByCategory(category: string, platform?: string, signal?: AbortSignal)`
- `searchTools(query: string, signal?: AbortSignal)`
- 所有函数把 `signal` 传给 `fetch(url, { signal })`

**改动 App.tsx**：
- 在 `HomePage` 中维护 `abortControllerRef = useRef<AbortController>()`
- 每次发起请求前：`abortControllerRef.current?.abort()`，然后创建新的 `AbortController`
- `catch` 中判断 `error.name === 'AbortError'` 时不设置 error 状态

### 2.3 请求层 Promise 缓存

**文件**：`frontend/src/services/api.ts`

**设计**：
```typescript
const promiseCache = new Map<string, { promise: Promise<any>; expiry: number }>();
const CACHE_TTL = 30_000; // 30 秒

function cachedFetch<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
  const cached = promiseCache.get(key);
  if (cached && Date.now() < cached.expiry) {
    return cached.promise;
  }
  const promise = fetcher();
  promiseCache.set(key, { promise, expiry: Date.now() + CACHE_TTL });
  promise.then(
    () => {
      // 成功：30 秒后自动清除
      setTimeout(() => promiseCache.delete(key), CACHE_TTL);
    },
    () => {
      // 失败：立即清除，不缓存错误结果
      promiseCache.delete(key);
    }
  );
  return promise;
}
```

- 以完整请求 URL 为 key
- 相同参数的并发请求共享同一个 Promise
- 请求完成后 30 秒自动清除缓存
- 不引入第三方库，纯手写约 20 行

### 2.4 骨架屏替换"加载中"

**新建文件**：`frontend/src/components/Hero/SkeletonGrid.tsx`

**设计**：
- 8 个占位卡片，模拟 4 列 2 行网格（与 `ToolGrid` 一致的 `grid-cols-4`）
- 每个卡片包含：图标区域（方形圆角 + `animate-pulse`）+ 标题条 + 描述条
- 使用 Tailwind `bg-slate-700/50` 配色，与深色主题一致
- 在 `HomePage` 中替换 `{loading ? <div>加载中...</div> : ...}` 为 `<SkeletonGrid />`

### 2.5 分类标签栏预加载

**改动**：`frontend/src/App.tsx` 的 `HomePage` 组件

- 引入 `categoriesLoading` 状态（独立于 `toolsLoading`）
- 分类数据先到达时，先渲染分类标签栏（可交互）
- 工具数据未到达时，工具区域显示骨架屏
- 用户可在工具加载期间切换分类

---

## 预期效果

| 指标 | 优化前 | 优化后（预期） |
|------|--------|---------------|
| `/categories` 响应时间 | 5.6s | <200ms（缓存命中） |
| `/tools?platform=pc` 响应时间 | >10s（pending） | <500ms（缓存命中） |
| 重复请求数 | 6+ | 0（去重 + AbortController） |
| 首屏可交互时间 | 等所有数据加载完 | 分类栏先可交互 |
| 视觉空白感 | 纯文字"加载中" | 骨架屏，感知更快 |

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 缓存数据过期 | TTL 5 分钟足够；管理员操作时主动 invalidate |
| Promise 缓存导致数据陈旧 | 30 秒 TTL 很短；用户刷新或切换页面自然清除 |
| 健康检查关闭后连接失效 | 连接池本身有 `ThreadedConnectionPool` 的重连机制；生产环境可开启健康检查 |
| 后台同步延迟导致数据不同步 | 只延迟 60 秒；手动触发同步的入口不受影响 |
