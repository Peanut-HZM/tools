# Token Usage 刷新时间、加载准确性与扩展数据源设计

**日期**: 2026-05-16
**状态**: 第二轮增强设计

## 1. 背景

`/tools/token-usage` 页面当前已经具备基础数据链路：CLI 工具同步数据到数据库，页面查询时优先读取 Redis 查询缓存，缓存未命中时从数据库聚合。用户希望页面加载更快、数据更准、能看见数据更新时间，并为 Codex/OpenClaw 类统计留下真实可靠的扩展路径。

当前需要补齐的设计点：

- 页面只能显示“是否命中缓存”，不能解释数据最后同步时间、缓存剩余时间和是否过期。
- 默认加载缺少“先展示、后补新”的明确策略，容易在 CLI 同步慢时拖慢首屏。
- 自动刷新可能被多个页面实例、筛选变化或重复渲染触发，需要并发锁和冷却策略。
- 模型统计不能只从前端行数据猜测，需要后端返回按 `source + model` 聚合的准确结果。
- Codex/OpenClaw 当前没有稳定本地解析器，不能把不可验证数据混入 Claude/OpenCode 统计。
- 中文文案存在乱码风险，需要在实施时统一修复用户可见文案。

## 2. 目标与非目标

### 2.1 目标

- 首屏优先展示 Redis/DB 已有数据，不等待 CLI。
- 后端返回可解释的 `sync_meta`，前端据此展示右上角数据刷新时间组件。
- 数据过期时自动静默刷新，刷新完成后自动重新查询；刷新失败时保留旧数据。
- 通过用户级刷新锁避免重复同步、并发同步和刷新风暴。
- 模型统计以 `source + model` 为唯一维度，保留原始模型名，并提供展示名。
- Codex/OpenClaw 第一阶段只做能力探测和文案说明，不在筛选项中展示为可统计数据源。
- 给第二阶段真实接入 Codex/OpenClaw usage 留出数据源契约。

### 2.2 非目标

- 不重构整个 Token Usage 架构。
- 不新增外部依赖。
- 不伪造 Codex/OpenClaw 数据。
- 不做跨机器自动汇总；现有本地 CLI 数据仍按当前机器和当前用户写入。
- 不在本次设计中修改数据库表结构，除非后续真实 Codex/OpenClaw 数据源证明现有字段不足。

## 3. 核心策略

采用“快速读 + 后台补新”的折中策略：

```text
页面打开
  -> 并行请求健康检查、设备列表、统计查询
  -> 统计查询优先读取 Redis 查询缓存
  -> 未命中 Redis 时查询 DB 聚合并写入 Redis
  -> 立即渲染已有数据
  -> 根据 sync_meta 判断数据是否过期
  -> 过期则尝试获取用户级刷新锁
  -> 锁可用时后台同步 CLI 到 DB，并失效当前用户查询缓存
  -> 同步完成后重新查询并更新页面
```

首屏始终不直接等待 CLI。手动刷新可以等待同步完成，但需要明确展示刷新中和失败状态。

## 4. 数据新鲜度状态机

页面右上角组件使用后端 `sync_meta` 和前端刷新状态组合出以下状态：

| 状态 | 进入条件 | UI 文案 | 行为 |
| --- | --- | --- | --- |
| `fresh` | 最近成功同步时间未超过 TTL | 数据最新 | 只展示时间，不自动刷新 |
| `cached` | Redis 命中且未过期 | 缓存有效 | 展示剩余 TTL |
| `stale` | 最近成功同步时间超过 TTL | 数据已过期 | 自动尝试静默刷新 |
| `refreshing` | 当前页面正在刷新 | 后台更新中 | 禁用刷新按钮 |
| `locked` | 后端提示已有同步在运行 | 其他窗口正在更新 | 轮询或稍后重新查询 |
| `partial` | 部分数据源成功、部分失败 | 部分数据已更新 | 保留成功数据并展示失败来源 |
| `failed` | 刷新失败 | 刷新失败，已保留旧数据 | 不清空图表 |
| `empty` | DB 无记录且 CLI 未返回数据 | 暂无数据 | 显示引导刷新 |

TTL 默认使用 `CACHE_REDIS_TOKEN_USAGE_TTL=3600` 秒。数据过期判断以最近一次成功同步时间为主，Redis TTL 只表示查询结果缓存还剩多久。

## 5. 后端契约

### 5.1 查询响应

`POST /api/token-usage/query` 返回：

```python
{
    "items": [...],
    "summary": {...},
    "devices": [...],
    "cached": True,
    "actual_days": 365,
    "auto_expanded": False,
    "model_summary": [...],
    "sync_meta": {...}
}
```

### 5.2 `sync_meta`

```python
{
    "last_synced_at": "2026-05-16T12:10:00",
    "last_success_at": "2026-05-16T12:10:00",
    "cache_written_at": "2026-05-16T12:20:00",
    "cache_ttl_seconds": 2400,
    "cache_expires_at": "2026-05-16T13:00:00",
    "data_age_seconds": 900,
    "is_stale": False,
    "stale_reason": None,
    "refresh_lock": {
        "locked": False,
        "owner": None,
        "ttl_seconds": 0
    },
    "sources_status": [
        {
            "source": "claude",
            "status": "success",
            "records_count": 12,
            "synced_at": "2026-05-16T12:10:00",
            "error_message": None
        }
    ]
}
```

规则：

- `last_success_at` 从 `token_usage_sync_log` 中当前用户、当前 source 筛选下最新成功记录取得。
- `data_age_seconds = now - last_success_at`。
- `is_stale = last_success_at is None` 或 `data_age_seconds > CACHE_REDIS_TOKEN_USAGE_TTL`。
- `cache_ttl_seconds` 来自 Redis `TTL key`，Redis 不可用或 DB 直查时为 0。
- `cache_written_at` 是查询缓存写入时间，不等同于数据同步时间。
- `sources_status` 每个 source 只返回最新一条日志，用于解释部分失败。

### 5.3 `model_summary`

```python
[
    {
        "source": "claude",
        "model": "claude-sonnet-4-5-20250929",
        "display_model": "Claude Sonnet 4.5",
        "input_tokens": 100,
        "output_tokens": 50,
        "cache_creation_tokens": 10,
        "cache_read_tokens": 40,
        "total_tokens": 200,
        "total_cost": 0.32
    }
]
```

规则：

- 聚合键必须是 `source + model`，不能只按 model 聚合。
- `model` 保留原始模型名，用于排查与导出。
- `display_model` 只用于 UI 展示，可由后端或前端纯函数生成。
- 未识别模型显示为 `未知模型`，但原始值仍保留。
- 饼图优先展示成本；若成本为 0，则可以降级展示 Token 占比。

### 5.4 刷新接口

`POST /api/token-usage/refresh`

请求：

```python
{
    "days": 90,
    "background": True,
    "reason": "stale"
}
```

响应：

```python
{
    "message": "同步完成，缓存已刷新",
    "sources_synced": ["claude", "opencode"],
    "total_records": 20,
    "errors": [],
    "locked": False
}
```

并发策略：

- 后端使用用户级刷新锁：`token_usage:refresh_lock:{user_id}`。
- 锁 TTL 建议 120 秒，避免异常退出导致永久锁。
- 静默刷新遇到锁时返回 `locked=true`，前端不再重复触发同步。
- 手动刷新遇到锁时展示“已有刷新任务进行中”，并允许用户稍后重试。
- 刷新完成后只失效当前用户查询缓存，不清全局缓存。

## 6. 缓存一致性规则

缓存优先级：

1. Redis 查询缓存命中：立即返回缓存数据，同时补充 Redis TTL 和同步日志元信息。
2. Redis 未命中：查询 DB 聚合，写入 Redis 查询缓存，返回 `cached=false`。
3. Redis 不可用：查询 DB 聚合，返回 `cached=false`、`cache_ttl_seconds=0`。
4. DB 无数据：返回空结果和 `empty` 状态，不自动走 CLI 阻塞查询。

缓存失效：

- 手动刷新成功后：失效当前用户所有 Token Usage 查询缓存。
- 静默刷新成功后：同手动刷新。
- 清理数据后：删除当前用户 DB 记录、同步日志、设备派生数据和当前用户缓存。
- 重命名设备后：失效当前用户查询缓存，因为设备名可能出现在缓存 payload 中。

## 7. 前端设计

### 7.1 页面加载

- 初次进入页面时并行请求健康检查、设备列表、统计查询。
- 查询响应返回后立即渲染，不等待刷新。
- 若 `sync_meta.is_stale=true`，且当前没有本页刷新任务，则触发静默刷新。
- 静默刷新需要前端冷却：同一筛选组合 60 秒内只自动触发一次。
- 筛选变化后重新查询，但不应每次筛选变化都立刻触发 CLI 同步；只有 `is_stale` 且冷却通过时触发。

### 7.2 右上角组件

组件名：`DataFreshnessBadge`

展示：

- 状态：数据最新、缓存有效、数据已过期、后台更新中、刷新失败、其他窗口正在更新。
- 最后同步：相对时间 + 完整时间。
- 缓存有效期：剩余分钟数，或“未命中缓存”。
- 数据来源：Redis 缓存 / 数据库聚合。
- 数据源状态：Claude、OpenCode 最新同步是否成功。
- 操作：刷新按钮，刷新中禁用。

布局：

- 桌面端放在页面右上角，与导出、清理按钮同一操作区。
- 移动端允许换行，占满宽度，避免按钮文字挤压。
- 不使用大面积说明卡片，保持工具页密度。

### 7.3 筛选项

第一阶段筛选项只展示已有真实统计源：

- 全部工具
- Claude Code
- OpenCode

Codex/OpenClaw 第一阶段只在“数据源能力”区展示为“待接入真实 usage 数据”，不作为统计筛选项，避免用户误以为已有数据。

### 7.4 数据源能力区

展示四类能力：

- `ccusage`: Claude Code 数据采集能力。
- `opencode-usage`: OpenCode 新数据采集能力。
- `ccusage-opencode`: OpenCode 历史数据补充能力。
- `Codex/OpenClaw`: 待接入真实 usage 数据，不显示为失败。

## 8. Codex/OpenClaw 分阶段策略

### 8.1 第一阶段：能力探测

- 不写入 `token_usage_records`。
- 不进入 source 筛选。
- UI 显示“待接入真实 usage 数据”。
- 如果 OpenClaw Gateway 已连接且暴露 `usage.status` / `usage.cost`，只显示“可探测”，不参与总额统计。

### 8.2 第二阶段：真实接入

只有满足以下条件才启用：

- 已获取真实 `usage.cost` 响应样例。
- 能稳定解析日期、模型、输入、输出、缓存、成本字段。
- 能区分 Codex、OpenClaw 或其他工具来源。
- 能定义去重键，避免重复写入。

写入规则：

- `source` 使用 `codex` 或 `openclaw`。
- `model` 保存原始模型名。
- 同步日志写入 `token_usage_sync_log`。
- 前端筛选项只有在健康检查返回能力可用且 DB 有数据时才展示。

## 9. 失败场景与用户体验

| 场景 | 后端行为 | 前端行为 |
| --- | --- | --- |
| Redis 不可用 | DB 聚合，返回缓存 TTL 为 0 | 显示“数据库聚合”，不报错 |
| CLI 同步失败 | 写失败日志，保留旧数据 | 显示失败来源，图表不清空 |
| 部分 source 成功 | 成功数据入库，失败写日志 | 显示“部分数据已更新” |
| DB 无数据 | 返回空 items 和 empty 状态 | 显示暂无数据和刷新按钮 |
| 刷新锁已存在 | 返回 `locked=true` | 显示其他窗口正在更新 |
| 用户未登录 | 返回 401 | 由现有鉴权逻辑处理 |
| 设备无数据 | 返回空结果，不自动扩大到其他设备 | 明确提示当前设备无数据 |
| 查询范围无数据但历史有数据 | 可自动扩展到 365 天 | 提示“已扩展展示历史数据” |

## 10. 可观测性

后端日志必须包含：

- 查询入口：用户、source、days、group_by、device_id、request_id。
- 缓存状态：命中/未命中、TTL、key 维度，不记录敏感 token。
- 刷新入口：用户、days、background、reason、是否拿到锁。
- 同步结果：每个 source 的记录数、耗时、错误。
- DB 聚合耗时：超过 1 秒用 warning。

前端不在生产环境使用裸 `console.log`。刷新失败通过页面轻量提示呈现。

## 11. 验收标准

| 类别 | 标准 |
| --- | --- |
| 首屏速度 | Redis 命中时统计接口目标 < 500ms；DB 聚合目标 < 1500ms |
| 准确性 | 总 Token = 输入 + 输出 + 缓存创建 + 缓存读取 |
| 模型统计 | 模型饼图使用 `model_summary`，不同 source 的同名模型不合并 |
| 刷新时间 | 右上角显示最后同步时间、缓存剩余时间、数据状态 |
| 自动刷新 | 数据过期时自动刷新一次，60 秒内不重复触发同筛选组合 |
| 并发控制 | 多窗口同时打开只允许一个用户级刷新任务运行 |
| 失败处理 | 同步失败不清空已有图表和表格 |
| Codex/OpenClaw | 第一阶段不展示为筛选项，不混入总统计 |
| 文案 | 页面用户可见中文无乱码 |
| 验证 | 后端编译、ruff、相关 pytest、前端 build 通过 |

## 12. 实施顺序建议

1. 后端新增 `sync_meta`、Redis TTL 读取和模型汇总。
2. 后端新增用户级刷新锁和刷新参数。
3. 前端接入 `sync_meta`，实现右上角刷新时间组件。
4. 前端实现静默刷新冷却和失败保留旧数据。
5. 修复页面中文文案和数据源能力区。
6. 运行后端、前端和浏览器验证。

## 13. 风险

- CLI 工具输出字段可能变化，解析器需要保持容错。
- Redis 不可用时无法展示准确缓存剩余时间，但不能影响 DB 查询。
- 用户级刷新锁如果 TTL 太短，长同步可能被第二个刷新抢占；TTL 太长则失败恢复慢，建议 120 秒起步并结合日志观察。
- Codex/OpenClaw 响应结构未确认前，任何总成本统计都可能误导用户，必须保持第一阶段只探测不统计。
