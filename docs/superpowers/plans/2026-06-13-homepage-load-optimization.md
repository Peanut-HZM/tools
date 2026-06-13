# 首页加载性能优化 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 解决首页加载慢问题（/categories 5.6s、/tools 多请求 pending），通过后端缓存+后台任务优化和前端请求管理+骨架屏，将首屏加载时间降至 500ms 以内。

**Architecture:** 后端新增进程内 TTL 缓存层拦截高频读请求，延迟 Token Usage 后台同步避免启动期资源竞争，数据库连接健康检查改为可配置；前端通过 AbortController 取消过期请求、Promise 缓存去重、useEffect 守卫修复重复调用，并用骨架屏替代纯文字 loading。

**Tech Stack:** Python 3.10+, FastAPI, psycopg2, threading / React 18, TypeScript, Vite, Tailwind CSS

---

## 文件清单

### 新建文件
| 文件 | 职责 |
|------|------|
| `backend/app/services/simple_cache.py` | 线程安全的进程内 TTL 缓存类 |
| `backend/tests/test_simple_cache.py` | 缓存单元测试 |
| `frontend/src/components/Hero/SkeletonGrid.tsx` | 工具网格骨架屏组件 |

### 修改文件
| 文件 | 改动 |
|------|------|
| `backend/app/services/tools_service.py` | 集成缓存到 get_all_categories / get_tools_for_platform |
| `backend/app/routes/tools.py` | 分类 CRUD 操作时清除缓存 |
| `backend/app/services/token_usage_background_sync.py` | 延迟首次同步 + 单用户耗时日志 |
| `backend/app/config/config.py` | 新增 DB_HEALTH_CHECK 配置项 |
| `backend/app/config/database.py` | 健康检查改为可配置 |
| `frontend/src/services/api.ts` | 新增 AbortSignal 参数 + Promise 缓存 |
| `frontend/src/App.tsx` | 修复 useEffect 重复调用 + AbortController + 分类预加载 |

---

## Task 1: SimpleTTLCache 缓存类（后端核心）

**Files:**
- Create: `backend/app/services/simple_cache.py`
- Create: `backend/tests/test_simple_cache.py`

- [ ] **Step 1: 创建缓存类**

```python
"""
Author: Peanut
Created: 2026-06-13
Purpose: 线程安全的进程内 TTL 缓存，用于高频读接口的缓存加速
"""

import threading
import time
from typing import Any, Optional


class SimpleTTLCache:
    """线程安全的进程内 TTL 缓存。"""

    def __init__(self, default_ttl: int = 300):
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，过期返回 None 并自动清除。"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            expire_at, value = entry
            if time.monotonic() > expire_at:
                del self._cache[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值，指定 TTL（秒），默认使用构造时的 default_ttl。"""
        effective_ttl = ttl if ttl is not None else self._default_ttl
        with self._lock:
            self._cache[key] = (time.monotonic() + effective_ttl, value)

    def invalidate(self, key: str) -> None:
        """手动清除指定缓存。"""
        with self._lock:
            self._cache.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        """按前缀批量清除缓存。"""
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]

    def cleanup_expired(self) -> int:
        """清理所有过期条目，返回清理数量。"""
        now = time.monotonic()
        with self._lock:
            keys_to_remove = [
                k for k, (expire_at, _) in self._cache.items()
                if now > expire_at
            ]
            for k in keys_to_remove:
                del self._cache[k]
            return len(keys_to_remove)

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def clear(self) -> None:
        """清空所有缓存。"""
        with self._lock:
            self._cache.clear()
```

- [ ] **Step 2: 运行 Python 语法检查**

```bash
cd backend
python -m py_compile app/services/simple_cache.py
```

Expected: 无输出（编译通过）

- [ ] **Step 3: 编写缓存测试**

```python
"""SimpleTTLCache 单元测试"""

import time
import threading
from app.services.simple_cache import SimpleTTLCache


def test_set_and_get():
    cache = SimpleTTLCache(default_ttl=60)
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


def test_get_missing_key_returns_none():
    cache = SimpleTTLCache()
    assert cache.get("nonexistent") is None


def test_ttl_expiration():
    cache = SimpleTTLCache(default_ttl=1)
    cache.set("key1", "value1", ttl=1)
    assert cache.get("key1") == "value1"
    time.sleep(1.1)
    assert cache.get("key1") is None


def test_custom_ttl_overrides_default():
    cache = SimpleTTLCache(default_ttl=60)
    cache.set("key1", "value1", ttl=1)
    time.sleep(1.1)
    assert cache.get("key1") is None


def test_invalidate():
    cache = SimpleTTLCache()
    cache.set("key1", "value1")
    cache.invalidate("key1")
    assert cache.get("key1") is None


def test_invalidate_nonexistent_key_no_error():
    cache = SimpleTTLCache()
    cache.invalidate("nonexistent")  # 不应抛异常


def test_invalidate_prefix():
    cache = SimpleTTLCache()
    cache.set("tools:pc:all", ["tool1"])
    cache.set("tools:mobile:all", ["tool2"])
    cache.set("categories", ["cat1"])
    cache.invalidate_prefix("tools:")
    assert cache.get("tools:pc:all") is None
    assert cache.get("tools:mobile:all") is None
    assert cache.get("categories") == ["cat1"]


def test_cleanup_expired():
    cache = SimpleTTLCache()
    cache.set("key1", "v1", ttl=1)
    cache.set("key2", "v2", ttl=1)
    cache.set("key3", "v3", ttl=3600)
    time.sleep(1.1)
    cleaned = cache.cleanup_expired()
    assert cleaned == 2
    assert cache.get("key3") == "v3"


def test_len():
    cache = SimpleTTLCache()
    cache.set("a", 1)
    cache.set("b", 2)
    assert len(cache) == 2


def test_clear():
    cache = SimpleTTLCache()
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert len(cache) == 0


def test_thread_safety():
    cache = SimpleTTLCache(default_ttl=60)
    errors = []

    def writer():
        try:
            for i in range(100):
                cache.set(f"key_{i}", i)
        except Exception as e:
            errors.append(e)

    def reader():
        try:
            for i in range(100):
                cache.get(f"key_{i}")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer) for _ in range(5)]
    threads += [threading.Thread(target=reader) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(errors) == 0
```

- [ ] **Step 4: 运行缓存测试**

```bash
cd backend
python -m pytest tests/test_simple_cache.py -v
```

Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/simple_cache.py backend/tests/test_simple_cache.py
git commit -m "feat: 新增 SimpleTTLCache 线程安全进程内 TTL 缓存"
```

---

## Task 2: 集成缓存到 tools_service.py

**Files:**
- Modify: `backend/app/services/tools_service.py`

- [ ] **Step 1: 在文件顶部导入缓存**

在 `tools_service.py` 顶部（`logger` 定义之后、`ToolsService` 类之前）添加：

```python
from app.services.simple_cache import SimpleTTLCache

# 全局缓存实例（进程级别单例）
_tools_cache = SimpleTTLCache(default_ttl=300)
```

- [ ] **Step 2: 修改 `get_all_categories` 方法**

将 `get_all_categories` 方法从：
```python
    def get_all_categories(self) -> List[Category]:
        conn = None
        try:
            conn = get_pooled_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM tool_categories WHERE deleted = FALSE ORDER BY sort_order"
                )
                rows = cur.fetchall()
                return [Category(**row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            return []
        finally:
            if conn:
                release_db_connection(conn)
```

改为：
```python
    def get_all_categories(self) -> List[Category]:
        # 尝试从缓存获取
        cached = _tools_cache.get("categories")
        if cached is not None:
            return cached

        conn = None
        try:
            conn = get_pooled_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM tool_categories WHERE deleted = FALSE ORDER BY sort_order"
                )
                rows = cur.fetchall()
                result = [Category(**row) for row in rows]
            _tools_cache.set("categories", result)
            return result
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            return []
        finally:
            if conn:
                release_db_connection(conn)
```

- [ ] **Step 3: 修改 `get_tools_for_platform` 方法**

将 `get_tools_for_platform` 方法中的查询逻辑包裹缓存。在 `conn = None` 之前添加缓存检查，在 `return` 之前写入缓存：

```python
    def get_tools_for_platform(self, platform: str, category: Optional[str] = None) -> List[Tool]:
        cache_key = f"tools:{platform}:{category or 'all'}"
        cached = _tools_cache.get(cache_key)
        if cached is not None:
            return cached

        conn = None
        try:
            conn = get_pooled_db_connection()
            with conn.cursor() as cur:
                base_sql = "SELECT * FROM tools WHERE status = 'online'"
                params: list = []

                if platform == "pc":
                    base_sql += " AND show_pc = TRUE"
                elif platform == "mobile":
                    base_sql += " AND show_mobile = TRUE"

                if category and category != "全部工具":
                    base_sql += " AND category = %s"
                    params.append(category)

                base_sql += " ORDER BY usage_count DESC, title ASC"
                cur.execute(base_sql, params)

                rows = cur.fetchall()
                result = [self._row_to_tool(row) for row in rows]
            _tools_cache.set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error fetching tools for platform {platform}: {e}")
            return []
        finally:
            if conn:
                release_db_connection(conn)
```

- [ ] **Step 4: 运行 Python 语法检查**

```bash
cd backend
python -m py_compile app/services/tools_service.py
```

Expected: 无输出

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/tools_service.py
git commit -m "feat(tools_service): 集成 SimpleTTLCache 缓存分类和工具查询"
```

---

## Task 3: 管理员操作时清除缓存

**Files:**
- Modify: `backend/app/routes/tools.py`

- [ ] **Step 1: 在文件顶部导入缓存实例**

在 `tools.py` 顶部（`from app.services.tools_service import tools_service` 之后）添加：

```python
from app.services.tools_service import _tools_cache
```

- [ ] **Step 2: 在分类创建/更新/删除接口中添加缓存清除**

修改 `create_category` 函数，在 `return category` 之前添加：
```python
    _tools_cache.invalidate("categories")
```

修改 `update_category` 函数，在 `return category` 之前添加：
```python
    _tools_cache.invalidate("categories")
```

修改 `delete_category` 函数，在 `return {"success": True}` 之前添加：
```python
    _tools_cache.invalidate("categories")
```

- [ ] **Step 3: 运行 Python 语法检查**

```bash
cd backend
python -m py_compile app/routes/tools.py
```

Expected: 无输出

- [ ] **Step 4: Commit**

```bash
git add backend/app/routes/tools.py
git commit -m "feat(tools_routes): 分类 CRUD 操作时清除缓存"
```

---

## Task 4: 延迟后台同步 + 日志优化

**Files:**
- Modify: `backend/app/services/token_usage_background_sync.py`
- Modify: `backend/app/config/config.py`

- [ ] **Step 1: 修改 config.py 默认延迟和最大用户数**

在 `config.py` 中，将：
```python
    TOKEN_USAGE_BACKGROUND_SYNC_INITIAL_DELAY_SECONDS: int = 30
    TOKEN_USAGE_BACKGROUND_SYNC_MAX_USERS_PER_RUN: int = 50
```

改为：
```python
    TOKEN_USAGE_BACKGROUND_SYNC_INITIAL_DELAY_SECONDS: int = 60
    TOKEN_USAGE_BACKGROUND_SYNC_MAX_USERS_PER_RUN: int = 3
```

- [ ] **Step 2: 修改后台同步函数，增加耗时日志**

在 `token_usage_background_sync.py` 的 `run_background_sync_once` 函数中，将 for 循环部分：

```python
    for user_id in user_ids:
        owner = str(uuid.uuid4())
        lock = acquire_refresh_lock(user_id, owner)
        if not lock.get("acquired"):
            logger.info(
                "Token Usage 后台同步跳过用户 %s: 已有刷新任务, ttl=%s",
                user_id,
                lock.get("ttl_seconds"),
            )
            result["skipped_users"].append(user_id)
            continue

        try:
            sync_result = sync_token_usage(user_id=user_id, days=days)
            invalidate_user_query_cache(user_id)
            result["synced_users"].append(user_id)
            logger.info(
                "Token Usage 后台同步完成: user=%s, records=%s, errors=%s",
                user_id,
                sync_result.get("total_records"),
                len(sync_result.get("errors") or []),
            )
        except Exception as exc:
            result["failed_users"].append(user_id)
            logger.warning(
                "Token Usage 后台同步失败: user=%s, error=%s",
                user_id,
                exc,
                exc_info=True,
            )
        finally:
            release_refresh_lock(user_id, owner)
```

改为：
```python
    for user_id in user_ids:
        user_started = time.perf_counter()
        owner = str(uuid.uuid4())
        lock = acquire_refresh_lock(user_id, owner)
        if not lock.get("acquired"):
            logger.info(
                "Token Usage 后台同步跳过用户 %s: 已有刷新任务, ttl=%s",
                user_id,
                lock.get("ttl_seconds"),
            )
            result["skipped_users"].append(user_id)
            continue

        try:
            sync_result = sync_token_usage(user_id=user_id, days=days)
            invalidate_user_query_cache(user_id)
            result["synced_users"].append(user_id)
            user_elapsed_ms = int((time.perf_counter() - user_started) * 1000)
            logger.info(
                "Token Usage 后台同步完成: user=%s, records=%s, errors=%s, elapsed_ms=%s",
                user_id,
                sync_result.get("total_records"),
                len(sync_result.get("errors") or []),
                user_elapsed_ms,
            )
        except Exception as exc:
            result["failed_users"].append(user_id)
            user_elapsed_ms = int((time.perf_counter() - user_started) * 1000)
            logger.warning(
                "Token Usage 后台同步失败: user=%s, error=%s, elapsed_ms=%s",
                user_id,
                exc,
                user_elapsed_ms,
                exc_info=True,
            )
        finally:
            release_refresh_lock(user_id, owner)
```

- [ ] **Step 3: 运行 Python 语法检查**

```bash
cd backend
python -m py_compile app/config/config.py
python -m py_compile app/services/token_usage_background_sync.py
```

Expected: 无输出

- [ ] **Step 4: Commit**

```bash
git add backend/app/config/config.py backend/app/services/token_usage_background_sync.py
git commit -m "perf: 延迟 Token Usage 后台同步至 60s，限制每轮 3 用户，增加单用户耗时日志"
```

---

## Task 5: 数据库连接健康检查可配置

**Files:**
- Modify: `backend/app/config/config.py`
- Modify: `backend/app/config/database.py`

- [ ] **Step 1: 在 config.py 新增配置项**

在 `DB_SQLALCHEMY_POOL_TIMEOUT: int = 10` 之后添加：

```python
    DB_HEALTH_CHECK: str = "false"  # "true" 开启连接健康检查（生产环境建议），"false" 跳过以减少延迟
```

- [ ] **Step 2: 修改 database.py 的 get_pooled_db_connection**

将 `get_pooled_db_connection` 函数从：
```python
def get_pooled_db_connection():
    """从连接池获取连接，若连接已失效则重取一次"""
    pool = get_connection_pool()
    conn = pool.getconn()

    # 通过轻量查询验证连接是否真正可用
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception as e:
        logger.warning(f"数据库连接健康检查失败，尝试重新获取连接: {e}")
        ...（重试逻辑）
    return conn
```

改为：
```python
def _health_check_enabled() -> bool:
    """判断是否启用数据库连接健康检查"""
    return getattr(settings, "DB_HEALTH_CHECK", "false").lower() == "true"


def get_pooled_db_connection():
    """从连接池获取连接，若连接已失效则重取一次（健康检查可配置）"""
    pool = get_connection_pool()
    conn = pool.getconn()

    if not _health_check_enabled():
        return conn

    # 通过轻量查询验证连接是否真正可用
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception as e:
        logger.warning(f"数据库连接健康检查失败，尝试重新获取连接: {e}")
        # 探针失败时重试一次，避免无限循环
        try:
            pool.putconn(conn, close=True)
        except Exception as close_err:
            logger.debug(f"回收已关闭连接时发生异常: {close_err}")
            try:
                if not getattr(conn, "closed", 0):
                    conn.close()
            except Exception:
                pass
        conn = pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception as retry_err:
            logger.error(f"重新获取的数据库连接仍无效: {retry_err}")
            try:
                pool.putconn(conn, close=True)
            except Exception:
                pass
            raise ConnectionError(f"无法获取有效的数据库连接: {retry_err}")

    return conn
```

- [ ] **Step 3: 运行 Python 语法检查**

```bash
cd backend
python -m py_compile app/config/config.py
python -m py_compile app/config/database.py
```

Expected: 无输出

- [ ] **Step 4: Commit**

```bash
git add backend/app/config/config.py backend/app/config/database.py
git commit -m "perf(database): 数据库连接健康检查改为可配置，默认关闭"
```

---

## Task 6: 前端 api.ts — AbortSignal + Promise 缓存

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: 重写 api.ts，新增 Promise 缓存和 AbortSignal 支持**

将 `frontend/src/services/api.ts` 完整替换为：

```typescript
import { Tool, ToolCategory } from '../types';
import { API_BASE_URL } from '../config/api';

// ==================== Promise 缓存（请求去重） ====================

interface CacheEntry {
  promise: Promise<any>;
  expiry: number;
}

const promiseCache = new Map<string, CacheEntry>();
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

// ==================== API 函数 ====================

export async function fetchCategories(signal?: AbortSignal): Promise<ToolCategory[]> {
  const key = `${API_BASE_URL}/categories`;
  return cachedFetch(key, async () => {
    const response = await fetch(key, { signal });
    if (!response.ok) {
      throw new Error('Failed to fetch categories');
    }
    return await response.json();
  });
}

export async function fetchTools(platform?: string, signal?: AbortSignal): Promise<Tool[]> {
  const url = platform
    ? `${API_BASE_URL}/tools?platform=${platform}`
    : `${API_BASE_URL}/tools`;
  return cachedFetch(url, async () => {
    const response = await fetch(url, { signal });
    if (!response.ok) {
      throw new Error('Failed to fetch tools');
    }
    const data = await response.json();
    return data.tools;
  });
}

export async function searchTools(query: string, signal?: AbortSignal): Promise<Tool[]> {
  const url = `${API_BASE_URL}/tools/search?q=${encodeURIComponent(query)}`;
  return cachedFetch(url, async () => {
    const response = await fetch(url, { signal });
    if (!response.ok) {
      throw new Error('Failed to search tools');
    }
    const data = await response.json();
    return data.tools;
  });
}

export async function fetchToolsByCategory(category: string, platform?: string, signal?: AbortSignal): Promise<Tool[]> {
  const params = new URLSearchParams();
  if (platform) params.append('platform', platform);
  const url = `${API_BASE_URL}/tools/category/${encodeURIComponent(category)}?${params.toString()}`;
  return cachedFetch(url, async () => {
    const response = await fetch(url, { signal });
    if (!response.ok) {
      throw new Error('Failed to fetch tools by category');
    }
    const data = await response.json();
    return data.tools;
  });
}

export async function loadToolsByCategory(category: string, platform?: string, signal?: AbortSignal): Promise<Tool[]> {
  return fetchToolsByCategory(category, platform, signal);
}
```

注意：`fetchCategories` 中 key 的拼写修正为 `${API_BASE_URL}/categories`（原代码中是 `${API_BASE_URL}/categories`，保持一致）。

- [ ] **Step 2: 运行 TypeScript 编译检查**

```bash
cd frontend
npx tsc --noEmit
```

Expected: 无错误（或仅有已存在的无关错误）

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "perf(api): 新增 Promise 缓存去重和 AbortSignal 支持"
```

---

## Task 7: 前端 App.tsx — 修复 useEffect + AbortController + 分类预加载

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 修改 HomePage 组件**

将 `HomePage` 函数从原来的实现替换为以下代码（保持 `LoginPage` 和 `App` 函数不变）：

```tsx
function HomePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [filteredTools, setFilteredTools] = useState<Tool[]>([]);
  const [toolsLoading, setToolsLoading] = useState(true);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categories, setCategories] = useState<string[]>(["全部工具"]);
  const { t } = useI18n();
  const { isAuthenticated } = useContext(AuthContext);

  const { activeCategory, handleCategoryChange } = useCategory();
  const { debouncedValue, handleSearchChange } = useOutletContext<LayoutContext>();

  // 初始化标记，防止 useEffect 重复触发
  const isInitializedRef = useRef(false);
  // AbortController，用于取消过期请求
  const abortControllerRef = useRef<AbortController>();

  // Sync URL query with search state
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const q = params.get('q');
    if (q && q !== debouncedValue) {
       handleSearchChange(q);
    }
  }, [location.search]);

  const abortPreviousRequest = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();
    return abortControllerRef.current.signal;
  };

  const isAbortError = (err: any): boolean => {
    return err?.name === 'AbortError';
  };

  const loadCategories = async () => {
    try {
      setCategoriesLoading(true);
      const cats = await fetchCategories();
      const catNames = ["全部工具", ...cats.map(c => c.name)];
      setCategories(Array.from(new Set(catNames)));
    } catch (e) {
      if (!isAbortError(e)) {
        console.error("Failed to load categories", e);
      }
    } finally {
      setCategoriesLoading(false);
    }
  };

  const loadTools = async (signal?: AbortSignal) => {
    try {
      setToolsLoading(true);
      const data = await fetchTools('pc', signal);
      setFilteredTools(data);
      setError(null);
    } catch (err) {
      if (!isAbortError(err)) {
        setError(t.errors.toolLoadFailed);
        console.error(err);
      }
    } finally {
      setToolsLoading(false);
    }
  };

  const loadToolsDataByCategory = async (category: string, signal?: AbortSignal) => {
    try {
      setToolsLoading(true);
      const data = await loadToolsByCategory(category, 'pc', signal);
      setFilteredTools(data);
      setError(null);
    } catch (err) {
      if (!isAbortError(err)) {
        setError(t.errors.toolLoadFailed);
        console.error(err);
      }
    } finally {
      setToolsLoading(false);
    }
  };

  const searchToolsData = async (query: string, signal?: AbortSignal) => {
    try {
      setToolsLoading(true);
      const data = await searchTools(query, signal);
      setFilteredTools(data);
      setError(null);
    } catch (err) {
      if (!isAbortError(err)) {
        setError(t.errors.toolSearchFailed);
        console.error(err);
      }
    } finally {
      setToolsLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    const signal = abortPreviousRequest();
    loadCategories();
    loadTools(signal);
    isInitializedRef.current = true;
  }, []);

  // 根据分类筛选（初始化完成后才触发）
  useEffect(() => {
    if (!isInitializedRef.current) return;
    const signal = abortPreviousRequest();
    if (activeCategory === "全部工具") {
      loadTools(signal);
    } else {
      loadToolsDataByCategory(activeCategory, signal);
    }
  }, [activeCategory]);

  // 根据搜索关键词筛选
  useEffect(() => {
    if (!isInitializedRef.current) return;
    const signal = abortPreviousRequest();
    if (debouncedValue) {
      searchToolsData(debouncedValue, signal);
    } else if (activeCategory === "全部工具") {
      loadTools(signal);
    } else {
      loadToolsDataByCategory(activeCategory, signal);
    }
  }, [debouncedValue]);

  // 组件卸载时取消请求
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // 处理工具点击 - 使用路由导航
  const handleToolClick = (toolId: string) => {
    // Record tool visit (fire-and-forget，不阻塞页面跳转)
    const tool = filteredTools.find(t => t.id === toolId);
    if (tool) {
      recordToolVisit(toolId, tool.title).catch(() => {});
    }

    // 登录拦截
    if (tool?.require_login && !isAuthenticated) {
      if (window.confirm('该工具需要登录后才能使用，是否前往登录？')) {
        navigate('/login');
      }
      return;
    }

    const toolRoutes: Record<string, string> = {
      'image-downloader': '/tools/image-downloader',
      'video-downloader': '/tools/video-downloader',
      'json-formatter': '/tools/json-formatter',
      'calendar': '/tools/calendar',
      'ai-assistant': '/tools/ai-assistant',
      'key-generator': '/tools/key-generator',
      'markdown-editor': '/tools/markdown-editor',
      'markitdown-converter': '/tools/markitdown-converter',
      'ocr-tool': '/tools/ocr',
      'asr-tool': '/tools/asr',
      'database-tool': '/tools/database-tool',
      'redis-tool': '/tools/redis-tool',
      'ssh-tool': '/tools/ssh-tool',
      'product-manager': '/tools/product-manager',
      'learning-share': '/tools/learning-share',
      'cross-share': '/tools/cross-share',
      'course-platform': '/courses',
      'cursor-history': '/tools/cursor-history',
      'http-api-client': '/tools/http-api-client',
      'system-monitor': '/tools/system-monitor',
      'token-usage': '/tools/token-usage',
      'openclaw': '/tools/openclaw',
    };

    const route = toolRoutes[toolId];
    if (route) {
      navigate(route);
    } else {
      alert(interpolate(t.errors.toolNotImplemented, { toolId }));
    }
  };

  return (
    <div className="container mx-auto px-6 py-8">
      {error && (
        <div className="bg-red-500/10 border border-red-500 text-red-500 px-4 py-3 rounded-lg mb-8">
          {error}
        </div>
      )}

      <div className="flex items-center justify-center mb-8">
        <CategoryTabs
          categories={categories}
          activeCategory={activeCategory}
          onCategoryChange={handleCategoryChange}
        />
        <DeployTimeIndicator />
      </div>

      {toolsLoading ? (
        <SkeletonGrid />
      ) : (
        <ToolGrid tools={filteredTools} onToolClick={handleToolClick} />
      )}
    </div>
  );
}
```

同时需要更新 import 语句。在文件顶部的 import 区域：

1. 添加 `useRef` 到 react 导入（如果还没有）：
```tsx
import { useState, useEffect, useContext, useRef } from 'react';
```

2. 添加 SkeletonGrid 导入（在 Hero 相关导入附近）：
```tsx
import SkeletonGrid from './components/Hero/SkeletonGrid';
```

3. 更新 api 导入，`loadToolsByCategory` 和 `searchTools` 的签名已变更（加了 signal 参数），但调用方式不变，不需要改 import。

4. 由于 HomePage 现在直接渲染 CategoryTabs、DeployTimeIndicator、ToolGrid、SkeletonGrid，需要确保这些导入存在。检查现有 import：
- `CategoryTabs` — 已通过 Hero 导入间接可用，但需要直接导入
- `DeployTimeIndicator` — 同上
- `ToolGrid` — 同上

在 import 区域添加：
```tsx
import CategoryTabs from './components/Hero/CategoryTabs';
import DeployTimeIndicator from './components/Hero/DeployTimeIndicator';
import ToolGrid from './components/Hero/ToolGrid';
```

- [ ] **Step 2: 运行 TypeScript 编译检查**

```bash
cd frontend
npx tsc --noEmit
```

Expected: 无新错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "perf(HomePage): 修复 useEffect 重复调用、AbortController 取消过期请求、分类预加载"
```

---

## Task 8: 骨架屏组件

**Files:**
- Create: `frontend/src/components/Hero/SkeletonGrid.tsx`

- [ ] **Step 1: 创建骨架屏组件**

```tsx
/**
 * 工具网格骨架屏 — 替代"加载中..."文字
 * 模拟 8 个工具卡片的占位布局，带闪烁动画
 */

export default function SkeletonGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {Array.from({ length: 8 }).map((_, index) => (
        <div
          key={index}
          className="bg-slate-800 rounded-xl p-5 border border-slate-700/50"
        >
          {/* 图标占位 */}
          <div className="w-12 h-12 rounded-lg bg-slate-700/50 animate-pulse mb-4" />
          {/* 标题占位 */}
          <div className="h-5 bg-slate-700/50 rounded animate-pulse mb-2 w-3/4" />
          {/* 描述占位 */}
          <div className="h-4 bg-slate-700/50 rounded animate-pulse mb-1 w-full" />
          <div className="h-4 bg-slate-700/50 rounded animate-pulse w-2/3" />
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: 运行 TypeScript 编译检查**

```bash
cd frontend
npx tsc --noEmit
```

Expected: 无新错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Hero/SkeletonGrid.tsx
git commit -m "feat(SkeletonGrid): 新增工具网格骨架屏组件"
```

---

## Task 9: 浏览器验证

- [ ] **Step 1: 重启前后端服务**

```bash
python dev_services.py restart
```

等待服务完全启动，观察终端无报错。

- [ ] **Step 2: 打开浏览器访问首页**

打开 `http://localhost:5178`（或项目实际端口），验证：
- 页面加载时显示骨架屏而非"加载中..."文字
- 分类标签栏在工具数据到达前先渲染
- 快速切换分类不会产生多个 pending 请求（DevTools Network 面板验证）
- 页面最终正常显示工具列表

- [ ] **Step 3: 验证缓存生效**

在浏览器 DevTools Network 面板中：
- 刷新页面，观察 `/categories` 和 `/tools?platform=pc` 响应时间 <500ms
- 连续刷新两次，第二次应该更快（缓存命中）

- [ ] **Step 4: 验证后端日志**

```bash
python dev_services.py logs backend
```

观察日志中：
- Token Usage 后台同步在启动 60 秒后才开始
- 数据库连接获取无 `SELECT 1` 探针日志（健康检查已关闭）

---

## Self-Review Checklist

### 1. Spec coverage

| Spec 要求 | 对应 Task |
|-----------|----------|
| 延迟 Token Usage 后台同步至 60s | Task 4 |
| 限制每轮同步最大用户数为 3 | Task 4 |
| 同步失败不阻塞下一轮 | Task 4（已有逻辑） |
| SimpleTTLCache 进程内缓存 | Task 1 |
| get_all_categories 缓存 | Task 2 |
| get_tools_for_platform 缓存 | Task 2 |
| 管理员操作清除缓存 | Task 3 |
| DB_HEALTH_CHECK 可配置 | Task 5 |
| 后台同步单用户耗时日志 | Task 4 |
| 修复 useEffect 重复调用 | Task 7 |
| AbortController 取消过期请求 | Task 6 + Task 7 |
| Promise 缓存去重 | Task 6 |
| 骨架屏替换"加载中" | Task 8 |
| 分类标签栏预加载 | Task 7 |

### 2. Placeholder scan

无 TBD、TODO 或占位符。所有步骤包含完整代码。

### 3. Type consistency

- `SimpleTTLCache` 方法签名在 Task 1 定义，Task 2 使用一致
- `fetchCategories`/`fetchTools`/`searchTools`/`loadToolsByCategory` 的 `signal` 参数在 Task 6 定义，Task 7 调用一致
- `toolsLoading` / `categoriesLoading` 状态在 Task 7 定义，与 Task 8 骨架屏使用一致
