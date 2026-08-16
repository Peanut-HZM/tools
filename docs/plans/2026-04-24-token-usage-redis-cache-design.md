# Token 统计数据 Redis 缓存设计方案

## 背景
当前 Token 统计数据页面每次刷新都需要调用 `ccusage`/`opencode-usage` CLI 子进程，执行数据获取、解析、聚合，导致页面加载缓慢（可能数秒）。需要引入 Redis 缓存层加速响应。

## 架构设计

### 后端设计

#### 1. Redis 缓存 Key 策略
格式：`token_usage:{source}:{type}:{days}:{since}:{until}:{breakdown}:{by}`
- 缓存 TTL：1 小时（3600秒）
- 缓存内容：完整的 JSON 序列化响应（包含 items + summary）

#### 2. 定时刷新任务
利用 FastAPI 的 `lifespan` 生命周期，在应用启动时创建后台 asyncio 任务。
每 1 小时自动刷新以下预聚合缓存：
- claude + daily + 7天
- claude + daily + 30天
- claude + daily + 90天
- claude + monthly + 90天
- claude + monthly + 180天
- claude + monthly + 365天
- opencode + daily + 30天

#### 3. API 路由变化
- 原 API 逻辑不变，新增 Redis 缓存读取：
  - 先查 Redis，命中则直接返回（<10ms）
  - 未命中则执行 CLI 调用，结果写入 Redis 后返回
- 新增 `/token-usage/refresh` 手动刷新端点（清除缓存 + 重新获取）

#### 4. 新增文件
- `backend/app/services/token_usage_cache.py` — Redis 缓存服务
- 全局 Redis 客户端初始化在 `lifespan` 中管理

### 前端设计

#### 1. 页面展示
- 在顶部工具栏显示"上次更新时间: XX:XX:XX"或"缓存已刷新: XX:XX:XX"
- 刷新按钮点击时显示 "刷新中..." 状态

## 配置

### Redis 连接配置（.env）
```env
CACHE_REDIS_HOST=<redis-host>
CACHE_REDIS_PORT=6379
CACHE_REDIS_DB=0
CACHE_REDIS_PASSWORD=<redis-password>
CACHE_REDIS_TOKEN_USAGE_TTL=3600
```

### 安全说明
Redis 密码通过 `.env` 文件管理，不硬编码在代码中。

## 实现清单

1. **配置文件更新**
   - [ ] `app/config/config.py` 添加 Redis 配置项
   - [ ] `.env` 添加 Redis 连接配置

2. **Redis 缓存服务**
   - [ ] `app/services/token_usage_cache.py` 封装 Redis 读写操作
   - [ ] 全局 Redis 客户端在 `main.py` lifespan 中初始化

3. **路由修改**
   - [ ] `app/routes/token_usage.py` 整合缓存读写逻辑
   - [ ] 添加手动刷新端点 `/token-usage/refresh`
   - [ ] 添加缓存状态元数据返回

4. **后台定时任务**
   - [ ] `main.py` lifespan 中添加定时刷新任务

5. **前端更新**
   - [ ] `TokenUsage.tsx` 显示缓存更新时间
   - [ ] 刷新按钮增加加载状态

## 错误处理

1. Redis 连接失败时，自动降级到直接 CLI 调用（不阻断功能）
2. CLI 调用失败时，返回已有缓存数据（如果存在）
3. 日志记录所有 Redis 操作结果

## 验证标准

1. 首次加载：从 CLI 获取数据并缓存，记录时间
2. 后续加载：从 Redis 读取，响应时间 < 100ms
3. 1小时后自动刷新缓存
4. 手动刷新按钮正常工作
5. Redis 不可用时降级到 CLI 调用
