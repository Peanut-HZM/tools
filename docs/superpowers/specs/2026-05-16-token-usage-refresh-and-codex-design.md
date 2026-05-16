# Token Usage 刷新时间与加载准确性优化设计

**日期**: 2026-05-16
**状态**: 已确认设计

## 1. 背景

`/tools/token-usage` 页面当前已经走“Redis 查询缓存 -> 数据库聚合”的主链路，并通过手动刷新触发 CLI 同步。现有问题集中在四类：

- 页面只能知道本次响应是否命中缓存，无法知道数据最后什么时候同步、缓存还剩多久、是否过期。
- 默认加载不会区分“快速展示旧数据”和“后台补新数据”，用户难判断数据新鲜度。
- 模型统计主要依赖当前查询结果，`models_used` 在 DB 聚合路径下不完整，模型类型展示不够准确。
- 目前只稳定支持 Claude Code 和 OpenCode；Codex/OpenClaw 类统计需要独立数据源，不能从现有字段硬推断。

## 2. 目标

采用折中策略：页面打开后优先快速展示缓存或数据库数据，同时根据同步元信息判断是否过期。若过期，则后台静默同步，完成后自动刷新页面数据。

成功标准：

- 首屏查询不等待 CLI，同步慢时也能快速展示已有数据。
- 页面右上角显示最后同步时间、缓存状态、数据年龄、有效期和刷新进度。
- 后端响应提供可解释的 `sync_meta`，前端不靠猜测判断数据有效期。
- 模型分组统计以 `source + model` 为最小准确维度，避免不同工具模型名混淆。
- 为 Codex/OpenClaw 统计预留独立数据源入口，有真实数据才展示。

## 3. 数据链路

推荐链路：

```text
页面首次加载
  -> POST /api/token-usage/query
  -> Redis 命中则立即返回；未命中则查询 DB 聚合并写缓存
  -> 响应携带 sync_meta
  -> 前端若发现 is_stale=true，则后台调用 refresh
  -> 同步完成后重新 query 并更新图表、表格和刷新时间组件
```

手动刷新仍保留，但语义从“同步并刷新页面”明确为“立即同步当前用户当前设备数据，并失效该用户查询缓存”。

## 4. 后端设计

### 4.1 响应元信息

扩展 `DbUsageResponse`：

```python
sync_meta: {
    "last_synced_at": str | None,
    "last_success_at": str | None,
    "cache_written_at": str | None,
    "cache_ttl_seconds": int,
    "cache_expires_at": str | None,
    "data_age_seconds": int | None,
    "is_stale": bool,
    "stale_reason": str | None,
    "sources_status": [
        {
            "source": "claude",
            "status": "success",
            "records_count": 12,
            "synced_at": "...",
            "error_message": None
        }
    ]
}
```

`last_success_at` 从 `token_usage_sync_log.synced_at` 取当前用户、可选设备、可选 source 的最新成功记录。`is_stale` 默认以 1 小时 TTL 判断，和 `CACHE_REDIS_TOKEN_USAGE_TTL` 保持一致。

### 4.2 缓存有效期

查询缓存 payload 增加：

```python
{
    "items": [...],
    "summary": {...},
    "devices": [...],
    "cache_written_at": datetime.now().isoformat()
}
```

读取缓存时补充 Redis TTL。若 Redis 不可用，返回 DB 聚合结果并标记 `cached=false`，`cache_ttl_seconds=0`。

### 4.3 后台刷新端点

保留 `POST /token-usage/refresh`，增加可选轻量参数：

- `days`: 默认 90，最大 365。
- `background`: 布尔值。前端用于表达这是过期后的静默刷新，后端日志可区分来源。

刷新完成后只失效当前用户查询缓存，不清全局缓存。

### 4.4 模型统计准确性

DB 聚合路径需要在 `group_by=none` 时也返回 `models_used` 汇总，或新增 `model_summary` 字段。推荐新增：

```python
model_summary: [
    {
        "source": "claude",
        "model": "claude-sonnet-4-5",
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "total_tokens": 0,
        "total_cost": 0
    }
]
```

前端饼图使用 `model_summary`，表格行继续显示该日期涉及的模型集合。模型展示名称通过前端纯函数规范化，但保留原始模型名用于 tooltip。

### 4.5 Codex/OpenClaw 数据源边界

新增 source 枚举预留：

- `claude`: 由 `ccusage` 同步。
- `opencode`: 由 `opencode-usage` 和 `ccusage-opencode` 同步。
- `codex`: 仅当后端能从真实来源解析到 usage 数据时启用。
- `openclaw`: 可通过 OpenClaw Gateway 的 `usage.status` / `usage.cost` 探测。

第一阶段只做能力探测与 UI 兼容，不伪造 Codex 数据。若 OpenClaw 返回的数据结构足够稳定，再新增解析服务写入 `token_usage_records`，source 使用 `openclaw` 或 `codex`，避免污染 Claude/OpenCode 统计。

## 5. 前端设计

### 5.1 加载逻辑

页面加载流程：

1. 并行请求健康检查、设备列表、统计查询。
2. 查询返回后立即渲染卡片、图表和明细表。
3. 如果 `sync_meta.is_stale` 为 true，右上角显示“数据已过期，后台更新中”，自动触发静默刷新。
4. 静默刷新完成后重新 query；失败则保留旧数据并显示轻量警告。

### 5.2 右上角刷新时间组件

组件名称建议为 `DataFreshnessBadge`，展示内容：

- 状态：最新、缓存中、已过期、后台更新中、刷新失败。
- 最后同步：相对时间和完整时间。
- 缓存有效期：剩余分钟数或已过期。
- 数据来源：Redis 缓存 / 数据库聚合。
- 操作：刷新按钮，刷新中禁用并显示转圈图标。

### 5.3 页面布局

保留当前深色工具页基调，但修正中文乱码和信息层级：

- 顶部左侧：标题、副标题、统计范围说明。
- 顶部右侧：`DataFreshnessBadge` + 刷新/导出/清理按钮。
- 第一行：健康状态与数据源能力，包含 Claude、OpenCode、Codex/OpenClaw 探测状态。
- 第二行：筛选条，按“工具、维度、时间、设备、分组、图表类型”排列。
- 第三行：核心指标卡片，增加缓存 Token 和有效天数。
- 主区域：趋势图 + 模型成本/Token 占比。
- 底部：明细表，支持模型 tooltip、数据源标签和分页。

### 5.4 交互与错误

- 静默刷新失败不清空现有数据。
- 清理数据需要二次确认，文案明确会删除 DB 记录、同步日志和缓存。
- 自动扩展到 365 天时，提示必须说明“当前筛选范围无数据，已扩展展示历史数据”。
- 所有用户可见文案使用中文，避免乱码。

## 6. 验证计划

后端：

- `python -m py_compile app/routes/token_usage.py app/services/token_usage_cache.py app/services/token_usage_sync_service.py`
- `ruff check app/routes/token_usage.py app/services/token_usage_cache.py app/services/token_usage_sync_service.py`
- 有条件时运行 token usage 相关测试。

前端：

- `npm run build`
- 如存在类型检查脚本，运行 `npm run type-check`。
- 浏览器验证 `/tools/token-usage` 首屏加载、静默刷新、手动刷新、筛选、导出和清理确认。

## 7. 风险与约束

- Redis 不可用时仍可走 DB，但无法显示准确剩余 TTL，只能显示 DB 查询时间与同步时间。
- CLI 同步仍可能慢或失败，因此不能阻塞首屏。
- Codex/OpenClaw usage 数据结构需要真实响应确认，第一阶段只展示能力探测，不承诺有统计。
- 当前文件存在中文乱码，实施时需要修正文案，但应避免无关大范围格式化。
