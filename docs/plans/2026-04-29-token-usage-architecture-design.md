# Token Usage 统计架构优化设计

**日期**: 2026-04-29
**状态**: 待审批

## 1. 背景与问题

### 1.1 当前架构痛点
| 问题 | 现状 | 影响 |
|------|------|------|
| 页面查询慢 | CLI 直查每次执行 shell 命令，耗时长 | 用户体验差，等待时间长 |
| 远程 DB 超时 | db-query 直连远程 PostgreSQL，连接不稳定 | 报错 "网络连接失败" |
| 双模式割裂 | "CLI 直查" 和 "数据库查询" 两个按钮 | 用户困惑，不知该选哪个 |
| 缓存覆盖不全 | Redis 缓存只有 CLI 维度和聚合维度，无用户/设备粒度 | 多设备场景无法正确统计 |
| 定时同步局限 | 只同步 user_id="system" 的数据 | 不支持按用户/设备维度查询 |

### 1.2 目标架构
```
CLI 工具 → 后台定时采集 → PostgreSQL（持久化） → Redis（缓存） → 页面查询
```
- 页面**不再直接调用 CLI**，所有查询走缓存 → DB 降级链路
- 删除"CLI 直查"和"数据库查询"按钮，统一查询入口

## 2. 设计方案

### 2.1 数据流设计（新）

```
┌─────────────┐     ┌─────────────────────────┐     ┌──────────────────┐
│  CLI 工具   │ ──→ │  后台定时采集（每小时）   │ ──→ │  PostgreSQL      │
│ ccusage     │     │  - fetch_claude()       │     │  token_usage_    │
│ opencode    │ ──→ │  - fetch_opencode()     │ ──→ │  records 表      │
│ ccusage-opencode│  │  - sync_token_usage()    │     │                  │
└─────────────┘     └──────────┬──────────────┘     └────────┬─────────┘
                               │                             │
                               ▼                             ▼
                    ┌──────────────────┐            ┌──────────────────┐
                    │   Redis 缓存     │ ←───────── │  页面查询         │
                    │ - 统计类数据      │            │  - 优先查 Redis    │
                    │ - 用户+设备维度   │            │  - 降级查 DB       │
                    └──────────────────┘            └──────────────────┘
```

### 2.2 缓存 Key 设计

| 缓存 Key 模板 | 示例 | TTL | 说明 |
|---|---|---|---|
| `token_usage:query:{source}:{type}:{days}:{user_id}:{device_id}` | `token_usage:query:opencode:daily:30:user_abc:device_01` | 3600s | 用户+设备维度的按天查询 |
| `token_usage:query:aggregate:{type}:{days}:{user_id}` | `token_usage:query:aggregate:daily:30:user_abc` | 3600s | 用户级别的聚合查询（所有工具合计） |
| `token_usage:summary:{source}:{user_id}:{device_id}` | `token_usage:summary:opencode:user_abc:device_01` | 1800s | 统计卡片摘要数据 |
| `token_usage:devices:{user_id}` | `token_usage:devices:user_abc` | 600s | 用户设备列表 |

**缓存未命中降级策略**：
1. 先查 Redis → 命中则直接返回
2. Redis 未命中 → 查询 PostgreSQL
3. DB 查询结果写入 Redis（下一次请求命中）
4. DB 也无数据 → 返回空结果（不再降级到 CLI）

### 2.3 端点设计（新）

| 旧端点 | 新端点 | 说明 |
|--------|--------|------|
| GET /token-usage (CLI) | **移除** | CLI 直查端点下线 |
| POST /token-usage/db-query | POST /token-usage/query | 统一查询入口（Redis → DB 降级） |
| POST /token-usage/aggregate (CLI) | **移除** | CLI 聚合端点下线 |
| POST /token-usage/refresh | 保留 | 手动清除 Redis 缓存 |
| - | GET /token-usage/devices | 获取当前用户的设备列表 |

### 2.4 UI 变更

**删除项**：
- [ ] "CLI 直查" / "数据库查询" 模式切换按钮
- [ ] 所有 CLI 相关的前端状态（`useDbQuery` 等）

**保留项**：
- [ ] "同步数据" 按钮 → 改为"刷新缓存"，触发手动 Redis 缓存刷新
- [ ] "数据管理" 按钮 → 进入管理页面
- [ ] 工具选择、维度、时间范围、设备、分组等筛选控件

### 2.5 定时采集优化

**当前问题**：`sync_token_usage(user_id="system", ...)` 只写入 system 用户

**优化方案**：
```python
# 定时任务改为采集所有在线用户的数据
async def refresh_token_usage_cache_periodically():
    # 1. 获取当前登录用户列表（从活跃会话或已注册设备）
    active_users = get_active_user_ids()
    
    for user_id in active_users:
        # 2. 同步该用户的 CLI 数据到 DB
        sync_token_usage(user_id=user_id, days=90)
        
        # 3. 刷新该用户的 Redis 缓存
        await refresh_user_cache(user_id)
```

**用户身份映射**：CLI 工具数据是本地机器级别的，通过 `device_id` 和 `user_id` 关联。
- 设备 ID：从 CLI 工具的本地存储中读取（与现有 `get_device_id()` 一致）
- 用户 ID：从 JWT token 或活跃会话中获取

### 2.6 多设备支持

现有 `token_usage_records` 表已有 `device_id` 字段，无需改表结构。

**查询逻辑**：
```python
# 前端不传 device_id → 查用户所有设备聚合
# 前端传 device_id → 查该设备的数据
```

**设备选择器**：页面顶部设备下拉框从 `/devices` 接口获取，用户可选"全部设备"或指定设备。

## 3. 改造步骤（概要）

### Phase 1: 后端重构
1. 新增 POST /token-usage/query 统一查询端点（Redis → DB 降级）
2. 新增 GET /token-usage/devices 设备列表端点
3. 扩展定时采集逻辑，支持按用户维度采集
4. 移除 CLI 查询端点（/token-usage 和 /token-usage/aggregate）

### Phase 2: 前端重构
1. 删除 `useDbQuery` 状态和相关模式切换 UI
2. 所有数据请求统一走 `/query` 端点
3. 设备选择器接入 `/devices` 接口
4. "同步数据"按钮改为"刷新缓存"

### Phase 3: 验证与清理
1. 浏览器验证所有模式正常
2. 验证 Redis 缓存命中率和降级逻辑
3. 清理无用的 CLI 相关 API 和前端代码
4. Lsp diagnostics 检查

## 4. 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Redis 连接失败 | 查询降级到 DB，可能慢 | 已有降级逻辑，不影响功能 |
| 定时采集失败 | 缓存可能过期 | CLI 降级已移除，需要采集成功 |
| 多用户场景 | CLI 是本地数据，天然一对一 | 不跨机器共享数据，每机器独立 |

## 5. 验证标准

- [ ] 页面不显示"CLI 直查"和"数据库查询"按钮
- [ ] "工具合计"模式不报远程 PG 超时错误
- [ ] 统计数据加载时间 < 500ms（Redis 命中）
- [ ] 按设备筛选正确过滤数据
- [ ] 按模型分组正确聚合数据
- [ ] 手动刷新缓存后，新数据在 1 分钟内生效
