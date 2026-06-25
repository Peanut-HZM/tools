# 首页性能优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 解决首页和数据库工具页面加载超慢问题（2.3 min → < 1s）

**Architecture:** 阶段 1 增加后端数据库连接池大小（5/20），立即解决连接池耗尽问题；阶段 2 在前端 API 层增加 localStorage 持久化缓存（TTL 5 分钟），减少重复请求。

**Tech Stack:** Python/FastAPI, psycopg2, React/TypeScript, localStorage

---

## 阶段 1：后端连接池优化（5 分钟）

### Task 1: 增加数据库连接池配置

**Files:**
- Modify: `backend/app/config/config.py:70-74`

- [ ] **Step 1: 修改连接池配置**

将 `backend/app/config/config.py` 第 70-74 行：

```python
    DB_PSYCOPG_POOL_MIN_CONN: int = 1
    DB_PSYCOPG_POOL_MAX_CONN: int = 3
    DB_SQLALCHEMY_POOL_SIZE: int = 5
    DB_SQLALCHEMY_MAX_OVERFLOW: int = 10
    DB_SQLALCHEMY_POOL_TIMEOUT: int = 10
```

改为：

```python
    DB_PSYCOPG_POOL_MIN_CONN: int = 5      # 从 1 增加到 5，避免并发请求时连接池耗尽
    DB_PSYCOPG_POOL_MAX_CONN: int = 20     # 从 3 增加到 20，支持更多并发
    DB_SQLALCHEMY_POOL_SIZE: int = 10      # 从 5 增加到 10
    DB_SQLALCHEMY_MAX_OVERFLOW: int = 10   # 保持不变
    DB_SQLALCHEMY_POOL_TIMEOUT: int = 10   # 保持不变
```

- [ ] **Step 2: 重启后端服务**

```bash
python dev-services.py restart backend
```

Expected: 后端服务正常重启，无报错

- [ ] **Step 3: 验证首页加载速度**

在浏览器中打开 `http://localhost:5178`，检查：
- Network 面板中 `/categories` 和 `/tools` 响应时间 < 1s
- Console 无错误
- 后端日志无 `QueuePool limit` 错误

- [ ] **Step 4: 提交**

```bash
git add backend/app/config/config.py
git commit -m "perf: 增加数据库连接池大小 (1/3 → 5/20)，解决并发请求超时"
```

---

## 阶段 2：前端缓存优化（2-3 小时）

### Task 2: 实现 localStorage 持久化缓存

**Files:**
- Modify: `frontend/src/services/api.ts`
- Create: `frontend/src/utils/cache.ts`

- [ ] **Step 1: 创建缓存工具函数**

创建 `frontend/src/utils/cache.ts`：

```typescript
/**
 * localStorage 持久化缓存工具
 * TTL 默认 5 分钟，用于减少重复 API 请求
 */

const DEFAULT_TTL = 5 * 60 * 1000; // 5 分钟

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

/**
 * 从缓存读取数据
 * @param key 缓存键
 * @returns 缓存数据或 null（过期/不存在）
 */
export function getCached<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;

    const entry: CacheEntry<T> = JSON.parse(raw);
    const now = Date.now();

    // 检查是否过期
    if (now - entry.timestamp > entry.ttl) {
      localStorage.removeItem(key);
      return null;
    }

    return entry.data;
  } catch (e) {
    console.warn(`[Cache] 读取缓存失败: ${key}`, e);
    return null;
  }
}

/**
 * 写入缓存
 * @param key 缓存键
 * @param data 缓存数据
 * @param ttl 过期时间（毫秒），默认 5 分钟
 */
export function setCache<T>(key: string, data: T, ttl: number = DEFAULT_TTL): void {
  try {
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      ttl,
    };
    localStorage.setItem(key, JSON.stringify(entry));
  } catch (e) {
    console.warn(`[Cache] 写入缓存失败: ${key}`, e);
  }
}

/**
 * 清除缓存
 * @param key 缓存键
 */
export function clearCache(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch (e) {
    console.warn(`[Cache] 清除缓存失败: ${key}`, e);
  }
}

/**
 * 清除所有工具相关缓存
 */
export function clearToolsCache(): void {
  try {
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith('categories') || key.startsWith('tools:'))) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach(key => localStorage.removeItem(key));
  } catch (e) {
    console.warn('[Cache] 清除工具缓存失败', e);
  }
}
```

- [ ] **Step 2: 修改 fetchCategories 使用缓存**

修改 `frontend/src/services/api.ts`，在文件顶部添加 import：

```typescript
import { getCached, setCache } from '../utils/cache';
```

修改 `fetchCategories` 函数（第 36-45 行）：

```typescript
export async function fetchCategories(signal?: AbortSignal): Promise<ToolCategory[]> {
  // 1. 尝试从 localStorage 缓存读取
  const cached = getCached<ToolCategory[]>('categories');
  if (cached) {
    return cached;
  }

  // 2. 缓存未命中，发起请求
  const key = `${API_BASE_URL}/categories`;
  const data = await cachedFetch(key, async () => {
    const response = await fetch(key, { signal });
    if (!response.ok) {
      throw new Error('Failed to fetch categories');
    }
    return await response.json();
  });

  // 3. 写入 localStorage 缓存
  setCache('categories', data);

  return data;
}
```

- [ ] **Step 3: 修改 fetchTools 使用缓存**

修改 `fetchTools` 函数（第 47-59 行）：

```typescript
export async function fetchTools(platform?: string, signal?: AbortSignal): Promise<Tool[]> {
  const cacheKey = `tools:${platform || 'all'}`;

  // 1. 尝试从 localStorage 缓存读取
  const cached = getCached<Tool[]>(cacheKey);
  if (cached) {
    return cached;
  }

  // 2. 缓存未命中，发起请求
  const url = platform
    ? `${API_BASE_URL}/tools?platform=${platform}`
    : `${API_BASE_URL}/tools`;
  const data = await cachedFetch(url, async () => {
    const response = await fetch(url, { signal });
    if (!response.ok) {
      throw new Error('Failed to fetch tools');
    }
    const result = await response.json();
    return result.tools;
  });

  // 3. 写入 localStorage 缓存
  setCache(cacheKey, data);

  return data;
}
```

- [ ] **Step 4: 运行前端开发服务器验证**

```bash
cd frontend
npm run dev
```

在浏览器中：
1. 打开 `http://localhost:5178`
2. 首次加载：检查 Network 面板，确认 `/categories` 和 `/tools` 正常请求
3. 刷新页面：确认请求从 localStorage 缓存读取（Network 面板无请求）
4. 等待 5 分钟后刷新：确认缓存过期后重新请求
5. 检查 Console 无错误

- [ ] **Step 5: 提交**

```bash
git add frontend/src/utils/cache.ts frontend/src/services/api.ts
git commit -m "feat: 前端增加 localStorage 持久化缓存 (TTL 5 分钟)

- 新增 cache.ts 缓存工具函数
- fetchCategories 和 fetchTools 使用缓存
- 二次加载从 2.3 min 降至 < 100ms"
```

---

## 验证清单

完成所有 Task 后，执行以下验证：

- [ ] 首页首次加载时间 < 1s
- [ ] 首页二次加载（缓存命中）时间 < 100ms
- [ ] 数据库工具页加载时间 < 2s
- [ ] 浏览器 Console 无错误
- [ ] 后端日志无 `QueuePool limit` 错误
- [ ] 连续刷新 5 次无性能退化
- [ ] 缓存过期后（5 分钟）自动刷新

---

## 回滚方案

### 阶段 1 回滚

```python
# backend/app/config/config.py
DB_PSYCOPG_POOL_MIN_CONN: int = 1
DB_PSYCOPG_POOL_MAX_CONN: int = 3
```

重启后端：`python dev-services.py restart backend`

### 阶段 2 回滚

1. 清除浏览器 localStorage：`localStorage.clear()`
2. Git 回退：`git revert HEAD`

---

## 相关文件

- `backend/app/config/config.py:70-74` - 数据库连接池配置
- `backend/app/config/database.py:110-128` - 连接池实现
- `frontend/src/services/api.ts` - 前端 API 调用（已有 Promise 缓存）
- `frontend/src/utils/cache.ts` - 新增 localStorage 缓存工具
- `frontend/src/App.tsx:114-143` - 首页组件（调用 fetchCategories/fetchTools）
