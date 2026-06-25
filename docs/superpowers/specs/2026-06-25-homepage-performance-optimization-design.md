---
author: peanut
created_at: 2026-06-25
purpose: 解决首页和数据库工具页面加载超慢问题（2.3 min → < 1s）
---

# 首页性能优化设计文档

## 问题描述

首页和数据库工具页面加载极慢，部分接口响应时间超过 2 分钟。

### 症状

| 接口 | 状态码 | 耗时 | 数据量 |
|------|--------|------|--------|
| `/categories` | 200 | 2.3 min | 2.0 kB |
| `/tools?platform=pc` | 200 | 2.3 min | 8.6 kB |
| `/visit` | 200 | 19.05 s | 0.3 kB |
| `/databases` | 200 | pending | - |
| `/history` | 200 | pending | - |

### 根因分析

**核心问题：数据库连接池耗尽 + 前端并发请求过多**

1. **连接池配置过小**
   ```python
   # backend/app/config/config.py
   DB_PSYCOPG_POOL_MIN_CONN: int = 1  # 最小 1 个连接
   DB_PSYCOPG_POOL_MAX_CONN: int = 3  # 最大 3 个连接
   ```

2. **前端并发请求**
   - 首页同时请求 `/categories`、`/tools`、`/visit`
   - 数据库工具页请求 `/databases`、`/history` 等
   - 多个组件 `useEffect` 并发执行

3. **连锁反应**
   ```
   4+ 并发请求 → 连接池耗尽 → 等待超时 (10s) → 前端重试 → 更多请求 → 恶性循环
   ```

4. **日志证据**
   ```
   QueuePool limit of size 2 overflow 1 reached, connection timed out, timeout 10.00
   ```

---

## 优化方案

### 方案 A：增加连接池大小（立即执行）

**改动文件：** `backend/app/config/config.py`

```python
DB_PSYCOPG_POOL_MIN_CONN: int = 5      # 从 1 改为 5
DB_PSYCOPG_POOL_MAX_CONN: int = 20     # 从 3 改为 20
DB_SQLALCHEMY_POOL_SIZE: int = 10      # 从 5 改为 10
DB_SQLALCHEMY_MAX_OVERFLOW: int = 10   # 新增
```

**优点：**
- ✅ 立即解决问题，无需改代码
- ✅ 改动风险极低
- ✅ 5 分钟部署生效

**缺点：**
-  治标不治本
- ❌ 连接数过多消耗数据库资源

**效果预估：** 解决 90% 超时问题，响应时间降至 < 1s

---

### 方案 B：前端缓存 + 请求合并（本周内）

#### B.1 前端缓存优化

**改动文件：** `frontend/src/services/api.ts`

```typescript
const CACHE_TTL = 5 * 60 * 1000; // 5 分钟

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

function getCached<T>(key: string): T | null {
  const entry = localStorage.getItem(key);
  if (!entry) return null;
  
  const parsed: CacheEntry<T> = JSON.parse(entry);
  if (Date.now() - parsed.timestamp > CACHE_TTL) {
    localStorage.removeItem(key);
    return null;
  }
  return parsed.data;
}

function setCache<T>(key: string, data: T) {
  localStorage.setItem(key, JSON.stringify({
    data,
    timestamp: Date.now()
  }));
}

export async function fetchCategories(): Promise<Category[]> {
  const cached = getCached<Category[]>('categories');
  if (cached) return cached;
  
  const response = await fetch(`${API_BASE_URL}/categories`);
  const data = await response.json();
  setCache('categories', data);
  return data;
}

export async function fetchTools(platform: string): Promise<Tool[]> {
  const cached = getCached<Tool[]>(`tools:${platform}`);
  if (cached) return cached;
  
  const response = await fetch(`${API_BASE_URL}/tools?platform=${platform}`);
  const data = await response.json();
  setCache(`tools:${platform}`, data.tools);
  return data.tools;
}
```

#### B.2 接口合并（可选）

**改动文件：** `backend/app/routes/tools.py`

```python
@router.get("/tools-with-categories", response_model=ToolsWithCategoriesResponse)
def get_tools_with_categories(
    platform: Optional[str] = Query(None),
):
    """一次性返回分类和工具列表，减少请求数"""
    categories = tools_service.get_all_categories()
    tools = tools_service.get_tools_for_platform(platform)
    return ToolsWithCategoriesResponse(categories=categories, tools=tools)
```

**优点：**
- ✅ 减少 50% 请求数
- ✅ 二次加载瞬间完成
- ✅ 用户体验显著提升

**缺点：**
- ❌ 需要改动前端代码
- ❌ 缓存一致性需要处理

**效果预估：** 首页加载时间从 2.3 min → 0.5s（缓存命中）

---

## 实施步骤

### 阶段 1：立即执行（5 分钟）

| 步骤 | 操作 | 耗时 |
|------|------|------|
| 1 | 修改 `backend/app/config/config.py` | 2 分钟 |
| 2 | 重启后端服务 `python dev-services.py restart backend` | 1 分钟 |
| 3 | 验证首页加载速度 | 2 分钟 |

### 阶段 2：前端优化（2-3 小时）

| 步骤 | 操作 | 耗时 |
|------|------|------|
| 1 | 实现前端缓存逻辑 | 1 小时 |
| 2 | 修改 `fetchCategories` 和 `fetchTools` | 30 分钟 |
| 3 | 浏览器验证 | 30 分钟 |

### 阶段 3：接口合并（可选，1-2 小时）

| 步骤 | 操作 | 耗时 |
|------|------|------|
| 1 | 后端新增 `/tools-with-categories` 接口 | 30 分钟 |
| 2 | 前端改用新接口 | 30 分钟 |
| 3 | 浏览器验证 | 30 分钟 |

---

## 验证标准

- ✅ 首页加载时间 < 1s
- ✅ 数据库工具页加载时间 < 2s
- ✅ 浏览器 Console 无错误
- ✅ 后端日志无连接池超时
- ✅ 连续刷新 5 次无性能退化
- ✅ 缓存命中时响应时间 < 100ms

---

## 回滚方案

### 方案 A 回滚

```python
# 恢复原配置
DB_PSYCOPG_POOL_MIN_CONN: int = 1
DB_PSYCOPG_POOL_MAX_CONN: int = 3
```

重启后端即可。

### 方案 B 回滚

清除浏览器 localStorage 缓存，前端代码回退到上一版本。

---

## 后续优化（可选）

### 方案 C：Redis 缓存层

- 增加 Redis 缓存（TTL 5 分钟）
- 使用 `asyncio` 并发查询数据库
- 增加连接池监控告警

**效果：** 支持 100+ 并发，响应时间 < 100ms

### 方案 D：数据库查询优化

- 为 `tools` 表添加索引
- 优化慢查询 SQL
- 使用数据库连接池监控工具

---

## 相关文件

- `backend/app/config/config.py` - 数据库连接池配置
- `backend/app/config/database.py` - 连接池实现
- `backend/app/services/tools_service.py` - 工具服务（含缓存）
- `backend/app/routes/tools.py` - 工具路由
- `frontend/src/services/api.ts` - 前端 API 调用
- `frontend/src/App.tsx` - 首页组件

---

## 决策记录

- **选择方案：** A + B 组合
- **决策时间：** 2026-06-25
- **决策理由：** 方案 A 立即见效，方案 B 提升用户体验，两者互补
- **预期收益：** 首页加载时间从 2.3 min 降至 < 1s
