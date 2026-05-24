---
author: Codex
created_at: 2026-05-24
purpose: 设计 Token Usage 页面首屏快读、后台定时同步与接口错误隔离方案
---

# Token Usage 首屏快读与后台定时同步设计

## 1. 背景

`/tools/token-usage` 页面当前第一次进入仍然较慢，并且会出现接口报错。现有前端逻辑在首屏加载时并行请求健康检查、设备列表和统计查询；当后端返回 `sync_meta.is_stale=true` 时，页面还会自动触发 `/api/token-usage/refresh` 做后台刷新。这个刷新会执行 CLI 同步，容易把首屏体验和后台同步耦合在一起。

用户期望：

- 页面先加载已有统计数据。
- 后台可以更新数据，但不能阻塞首屏。
- 后台需要定时刷新数据，不应依赖用户第一次进入页面才触发。
- 接口报错不能清空已有统计，也不能拖慢主页面。

## 2. 目标

- 首屏只读取 Redis/DB 已有数据，不执行 CLI 同步。
- `/api/token-usage/query` 始终作为快读接口：缓存命中目标小于 500ms，DB 聚合目标小于 1500ms。
- 后端启动后台定时任务，周期性同步 Token Usage 数据并刷新缓存。
- 前端删除 `sync_meta.is_stale` 后自动调用 `/refresh` 的首屏路径。
- 手动刷新仍可保留，但不得影响已有图表和表格。
- 后台同步失败只写入同步状态和日志，不让 `/query` 失败。
- 接口错误分层处理，避免非关键接口拖垮页面。

## 3. 非目标

- 不重写 Token Usage 页面布局。
- 不新增外部任务队列依赖。
- 不改动 Token Usage 数据表结构，除非实施时发现现有字段无法记录必要状态。
- 不把 Codex/OpenClaw usage 统计纳入本次修复。
- 不修复与 Token Usage 无关的接口错误，例如 CrossShare 连接异常。

## 4. 当前问题判断

### 4.1 首屏慢的主要原因

当前前端存在以下链路：

```text
页面进入
  -> checkTokenUsageHealth()
  -> getUserDevices()
  -> getDbTokenUsage()
  -> 如果 sync_meta.is_stale=true
       -> refreshTokenUsage({ background: true })
       -> loadDevices()
       -> fetchData()
```

其中 `/refresh` 会调用 `sync_token_usage`，可能执行 CLI 数据采集、写库、失效缓存。即使前端把它标记为后台刷新，它仍然会占用后端资源，并可能让用户感知到首次进入页面慢、接口错误或页面状态抖动。

### 4.2 接口报错需要分层处理

Token Usage 页面依赖多个接口：

| 接口 | 当前用途 | 页面影响级别 |
| --- | --- | --- |
| `GET /api/token-usage/health` | 展示 CLI 能力状态 | 非关键 |
| `GET /api/token-usage/devices` | 展示设备筛选 | 非关键 |
| `POST /api/token-usage/query` | 查询统计数据 | 关键 |
| `POST /api/token-usage/refresh` | 手动或自动同步数据 | 非首屏关键 |
| `POST /api/token-usage/clear-data` | 清空数据 | 危险操作，不属于首屏 |
| `PUT /api/token-usage/devices/{device_id}/rename` | 设备重命名 | 非首屏关键 |

首屏只有 `query` 是关键接口。`health` 和 `devices` 失败不应阻塞图表展示；`refresh` 不应在首次进入页面时自动触发。

## 5. 总体方案

采用“首屏快读 + 后端定时同步 + 前端状态展示”的方案。

```text
前端首屏
  -> 并行请求 health/devices/query
  -> query 返回后立即渲染已有统计
  -> 如果 sync_meta.is_stale=true，只展示数据可能滞后
  -> 不自动调用 refresh

后端后台任务
  -> 服务启动后创建定时同步循环
  -> 周期性找到需要同步的用户
  -> 获取用户级刷新锁
  -> 调用 sync_token_usage 写入 DB
  -> 失效该用户查询缓存
  -> 写入同步日志

前端后续
  -> 可以低频重新查询 query，看到后台同步后的新数据
  -> 手动刷新只由用户点击触发
```

## 6. 前端设计

### 6.1 首屏加载

保留首屏并行请求：

- `checkTokenUsageHealth()`
- `getUserDevices()`
- `getDbTokenUsage()`

但调整错误处理：

- `getDbTokenUsage()` 失败：显示主错误，因为统计数据不可用。
- `getUserDevices()` 失败：不设置主错误，只隐藏设备筛选或显示“设备列表加载失败”。
- `checkTokenUsageHealth()` 失败：不设置主错误，只把能力状态显示为未知。

### 6.2 删除自动刷新首屏路径

删除当前基于 `syncMeta.is_stale` 的自动刷新 effect：

```text
if syncMeta.is_stale:
  refreshTokenUsage({ background: true })
  loadDevices()
  fetchData()
```

替代行为：

- `sync_meta.is_stale=true` 时展示“数据可能滞后，后台同步会自动更新”。
- 如果 `sync_meta.refresh_lock.locked=true`，展示“后台同步中”。
- 不在前端自动调用 `/refresh`。

### 6.3 低频状态刷新

保留一个轻量轮询，但只能重新调用 `/query`，不能调用 `/refresh`。这样后台同步完成后，用户不需要手动刷新页面也能看到新数据。

- 默认 60 秒一次。
- 页面不可见时停止。
- 正在手动刷新时暂停。
- 轮询失败不清空现有数据，只更新轻量错误状态。
- 连续失败时退避到 120 秒，避免接口异常时持续打后端。

### 6.4 手动刷新

手动点击刷新仍调用 `/refresh`，但它不属于首屏路径。

行为要求：

- 刷新按钮显示明确 loading 状态。
- 刷新失败时显示轻量错误，保留旧图表和表格。
- 刷新成功后重新调用 `loadDevices()` 和 `fetchData()`。
- 多窗口并发刷新时，后端返回 `locked=true`，前端提示“已有刷新任务进行中”。

### 6.5 文案与可观测状态

前端需要区分：

- 主查询失败。
- 后台同步中。
- 数据可能滞后。
- 手动刷新失败。
- 设备列表不可用。
- 健康检查不可用。

这些状态不能全部混成一个 `error`。

## 7. 后端设计

### 7.1 `/query` 快读契约

`POST /api/token-usage/query` 必须满足：

- 不执行 CLI。
- 不调用 `sync_token_usage`。
- 优先读 Redis 查询缓存。
- 缓存未命中时只做 DB 聚合并写入查询缓存。
- DB 聚合失败才返回错误。
- DB 无数据时返回空结果和 `sync_meta`，不降级执行 CLI。

如果当前代码仍存在 `_fallback_to_cli_for_query`，本次应确保 `/query` 不调用它。

### 7.2 后台定时同步任务

服务启动时创建一个后台定时同步循环。

建议参数：

| 配置 | 默认值 | 含义 |
| --- | --- | --- |
| `TOKEN_USAGE_BACKGROUND_SYNC_ENABLED` | 开发环境 `true`，测试环境 `false`，生产环境显式配置 | 是否启用后台定时同步 |
| `TOKEN_USAGE_BACKGROUND_SYNC_INTERVAL_SECONDS` | `1800` | 同步间隔，默认 30 分钟 |
| `TOKEN_USAGE_BACKGROUND_SYNC_DAYS` | `90` | 每次同步最近多少天 |
| `TOKEN_USAGE_BACKGROUND_SYNC_INITIAL_DELAY_SECONDS` | `30` | 服务启动后延迟多久开始第一次同步 |
| `TOKEN_USAGE_BACKGROUND_SYNC_MAX_USERS_PER_RUN` | `50` | 每轮最多同步用户数，避免一次扫过多历史用户 |

任务行为：

1. 延迟 `initial_delay` 后开始。
2. 找到需要同步的用户。
3. 对每个用户尝试获取用户级刷新锁。
4. 获取锁成功后调用 `sync_token_usage(user_id=user_id, days=days)`。
5. 同步完成后调用 `invalidate_user_query_cache(user_id)`。
6. 捕获并记录异常，不让后台任务退出。
7. 每轮之间 sleep `interval_seconds`。
8. 启动日志必须打印 enabled、interval、days、initial_delay、max_users_per_run、用户发现策略。

### 7.3 同步用户范围

第一版同步用户来自三个来源：

| 来源 | 用途 |
| --- | --- |
| `token_usage_records` 中已有记录的用户 | 保持已有数据持续更新 |
| `token_usage_sync_log` 中已有日志的用户 | 覆盖同步过但当前无记录的用户 |
| 本进程内待同步用户集合 | 覆盖“首次进入但还没有历史记录或日志”的用户 |

`/query` 在完成认证后，应把当前 `user_id` 注册到“待同步用户集合”。这个注册动作只写入内存集合，不执行 CLI，不阻塞首屏。后台定时任务下一轮会看到该用户并尝试同步。同步成功或失败后，该用户仍可保留在集合中，由用户级锁和同步间隔控制频率。

如果未来需要跨进程持久化待同步用户，可再引入轻量表或复用用户活跃记录；本次第一版不新增表结构。

后续可扩展为同步活跃登录用户，但不在本次范围内。

### 7.4 任务生命周期与多进程边界

后台同步任务通过 FastAPI lifespan 启动和关闭：

- 启动时如果 `TOKEN_USAGE_BACKGROUND_SYNC_ENABLED=false`，只打印禁用日志，不创建任务。
- 启动时如果已存在任务，不重复创建。
- 关闭时 cancel task，并等待任务退出，记录停止日志。
- 任务循环内部必须捕获每轮异常，避免单次失败导致循环退出。

第一版后台定时同步按单进程模式设计。当前开发环境使用单进程运行，允许本进程维护待同步用户集合。

多 worker 或多实例部署时，需要增加全局调度锁，例如 Redis 锁：

- 全局锁 key 建议为 `token_usage:background_sync:leader`。
- 待同步用户集合必须放入共享存储，例如 Redis set 或数据库表。
- `/query` 注册待同步用户时写入共享集合，而不是进程内内存。
- 获得全局锁的进程从共享集合和历史数据中发现用户并执行扫描。
- 即使多个进程同时运行，用户级刷新锁仍作为第二层保护。

如果无法提供共享待同步集合，生产多 worker 或多实例环境必须禁用后台定时同步并记录 warning，避免出现“用户被登记在非 leader 进程中但 leader 看不到”的问题。开发环境可退化为单进程内执行。

### 7.5 锁与并发

复用现有用户级刷新锁：

- 定时同步、手动刷新共用同一把用户锁。
- 某用户正在手动刷新时，定时同步跳过该用户。
- 某用户正在定时同步时，手动刷新返回 `locked=true`。
- 锁必须有 TTL，避免异常退出后永久锁住。

### 7.6 同步状态

复用 `token_usage_sync_log`：

- 每个 source 成功或失败都写日志。
- `records_count` 记录写入数量。
- `error_message` 记录失败原因。
- `_get_sync_meta` 读取最新日志，提供 `sources_status`。

后台同步失败时：

- 不清空已有 DB 数据。
- 不清空已有查询缓存，除非同步成功后需要失效。
- `/query` 仍返回旧数据和同步状态。

### 7.7 日志要求

后端必须记录关键日志：

- 后台同步循环启动和停止。
- 每轮同步开始、结束、耗时。
- 每个用户是否获取到锁。
- 每个用户同步成功、失败、跳过原因。
- `/query` 请求耗时，超过 1 秒打印 warning。
- Redis 缓存命中、未命中和写入状态。

日志不记录 Authorization token 或敏感本机路径。

## 8. 接口错误修复策略

实施时按优先级排查：

1. `/query` response model 是否和实际返回完全一致。
2. Redis 缓存 payload 是否缺少新字段，例如 `sync_meta`、`dimension_summaries`、`filter_options`。
3. `devices` 是否因认证或数据库连接失败而影响主页面。
4. `_query_dimension_data` 是否在空数据时返回结构完整的空对象。
5. `_get_sync_meta` 是否在没有同步日志时仍能返回完整默认结构。
6. DB 连接断开时是否有合理异常处理和日志。
7. `/query` 是否注册当前用户到待同步集合，但没有执行 CLI。

如果发现非 Token Usage 接口报错，只记录为旁路问题，不纳入本次修复。

## 9. 验证标准

### 9.1 前端验收

- 第一次打开 `/tools/token-usage` 时，Network 中不能自动出现 `/api/token-usage/refresh`。
- `/api/token-usage/query` 返回后页面立即显示已有统计。
- `health` 失败时，统计图表仍可显示。
- `devices` 失败时，统计图表仍可显示。
- 手动刷新失败时，图表和表格保留旧数据。
- `sync_meta.is_stale=true` 时，只显示数据滞后提示，不自动刷新。
- 后台同步成功并失效缓存后，页面在下一次 60 秒 `/query` 轮询中展示新数据。

### 9.2 后端验收

- 服务启动后日志显示后台同步任务启动。
- 服务关闭时后台同步任务会被取消并记录停止日志。
- 到达同步间隔后，日志显示同步开始、锁获取、同步完成或失败。
- 同步失败不会导致后台任务退出。
- 手动刷新和定时同步不能同时同步同一用户。
- `/query` 不调用 `sync_token_usage`。
- `/query` 超过 1 秒有 warning 日志。
- 无历史记录且无同步日志的用户首次访问 `/query` 后，会进入待同步用户集合，并在下一轮后台任务中被尝试同步。
- 缓存命中旧 payload、DB 空数据、无同步日志、Redis 不可用、设备列表失败时，`/query` 不返回 500。
- `/query` 的 response model 校验覆盖空数据和缓存命中两种场景。

### 9.3 命令验证

前端：

```bash
cd frontend
npm run build
```

后端：

```bash
cd backend
python -m py_compile app/main.py
ruff check .
pytest
```

如只修改 Token Usage 相关测试，可优先运行：

```bash
cd backend
pytest tests/test_token_usage_freshness.py tests/test_token_usage_dimensions.py
```

服务状态与重启使用当前仓库实际脚本：

```bash
python dev-services.py status
python dev-services.py restart
```

当前仓库实际文件名是 `dev-services.py`。如果后续按项目规范统一为 `dev_services.py`，实施计划和命令应同步更新为实际可执行脚本名。

普通代码变更优先依赖热重载；新增或修改后台定时任务配置后需要重启后端验证。

## 10. 风险

- 后台定时任务如果没有异常保护，失败一次可能停止循环。
- 同步间隔过短会增加 CLI 和数据库压力。
- 同步用户范围过大可能导致长时间占用后端资源。
- Redis 不可用时 `/query` 只能走 DB 聚合，仍需保证不触发 CLI。
- 手动刷新和定时同步共用锁后，用户可能看到“已有刷新任务进行中”，需要清晰提示。

## 11. 实施顺序建议

1. 前端删除首屏自动 `/refresh` effect，调整错误分层。
2. 后端确保 `/query` 不触发 CLI，并补充耗时日志。
3. 后端新增后台定时同步循环和配置项。
4. 后端补充或调整 Token Usage 相关测试。
5. 前端构建和后端测试验证。
6. 使用 `dev-services.py restart` 重启后端，观察后台任务日志和页面首屏 Network。
