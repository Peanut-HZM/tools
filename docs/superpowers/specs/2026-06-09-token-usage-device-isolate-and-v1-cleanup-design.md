# Token Usage 同步隔离与 v1 精简

> 最后更新: 2026-06-09

## 目标

1. 数据写入已按 `device_id` 隔离（现状）
2. 缓存清除按设备粒度（新增）
3. 移除 v1 `opencode-usage` 逻辑（已废弃）

## 背景

- v2 流程（`UsageFetcherV2` + `sync_token_usage_v2`）已覆盖所有 agents（claude/codex/openclaw/opencode）
- v1 的 `opencode-usage run --json --days=N --by=model` 是冗余逻辑
- 当前缓存清除 `invalidate_user_query_cache(user_id)` 通配 `{user_id}`，会把同用户下其他设备的缓存也清掉

## 修改清单

### A. 设备级缓存清除（新增 `invalidate_device_query_cache`）

**文件**: `backend/app/services/token_usage_cache.py`

新增接口：
```python
def invalidate_device_query_cache(user_id: str, device_id: str) -> bool:
    """仅清除该用户指定设备的查询与摘要缓存。"""
    patterns = [
        f"token_usage:query:*:{user_id}*:{device_id}*",
        f"token_usage:query:*:{user_id}*:{device_id}",
        f"token_usage:summary:*:{user_id}*:{device_id}*",
        f"token_usage:summary:*:{user_id}*:{device_id}",
    ]
    ...
```

**调用点替换**：

| 端点 | 原调用 | 新调用 |
|------|--------|--------|
| `POST /api/token-usage/refresh` | `invalidate_user_query_cache(user_id)` | 保留 + 追加 `invalidate_device_query_cache(user_id, get_device_id())` |
| `POST /api/token-usage/refresh-ccusage` | 无缓存清除 | 同步成功后调用 `invalidate_device_query_cache(user_id, device_id)` |
| `POST /api/token-usage/sync` | `invalidate_user_query_cache(user_id)` | 追加设备级缓存清除 |
| 后台同步 `ccusage_scheduler._daily_sync_job` | 无 | 同步成功后调用设备级缓存清除 |

### B. 移除 v1 `opencode-usage` 逻辑

**文件**: `backend/app/services/token_usage_sync_service.py`

修改 `sources` 列表：

```python
sources = [
    ("claude", _fetch_claude_daily, _parse_claude_entries),
    # 移除 ("opencode", _fetch_opencode_daily, _parse_opencode_entries)
]
```

**删除/保留决策**：

| 函数 | 保留/移除 | 理由 |
|------|-----------|------|
| `_fetch_opencode_daily` | 移除 | 仅被 `sync_token_usage.sources` 调用 |
| `_parse_opencode_entries` | 移除 | 同上 |
| `_fetch_opencode_current` | 移除 | 仅被 `UsageFetcher.fetch_opencode` 调用 |
| `_fetch_opencode_legacy` | 移除 | 同上 |
| `UsageFetcher.fetch_opencode` | 移除 | 无外部调用者 |
| `OPCODE_CUTOFF` | 移除（如仅用于 v1） | 同上 |

搜索确认无其他引用后再删除。

### C. `/refresh-ccusage` 补充缓存清除

当前行为：仅执行 v2 同步，不清缓存，不刷新设备列表（这是合理的，保持）。

新增：在 `sync_token_usage_v2` 返回后调用 `invalidate_device_query_cache(user_id, device_id)`。

### D. 前端刷新逻辑不变

- `handleRefresh` 已调用 `loadDevices()` + `summary.refresh()` + `details.refresh()` → 不变
- `handleSync` 只调用 `summary.refresh()` + `details.refresh()` → 不变

## 风险评估

| 修改 | 风险 | 缓解 |
|------|------|------|
| 移除 `_fetch_opencode_daily` | 可能有未知调用者 | 先用 `rg` 全量搜索再删 |
| 缓存 key 通配不全 | 漏清 | 用 4 层通配，覆盖 summary/query |
| 移除后 v1 只剩 claude 数据 | 但 v2 会补上所有 agents | 验证 v2 返回所有 agents |
| cache TTL 过长 | 旧数据残留 | 刷新后立即清该设备缓存 |

## 验证

1. 后端 `pytest` 全部通过
2. `python -c "from app.services.token_usage_sync_service import sync_token_usage; ..."` 启动无报错
3. Mac 上点"刷新" → 只清 Mac 的缓存，Win 端缓存不被影响
4. `ccusage daily` 返回所有 agents（claude/codex/openclaw/opencode 均有数据）
5. 数据库 `SELECT DISTINCT source FROM token_usage_records WHERE user_id=... AND device_id=...` 仍包含 `opencode` 且数据被 v2 填充

## 决策记录

- **保留 v1 `claude` 源?** 是。`UsageFetcher.fetch_claude` 仍被其他地方调用；且 v1 源能 fallback 覆盖 v2 遗漏的场景。
- **v1 opencode 是否彻底移除?** 是。`UsageFetcherV2.fetch_ccusage_agent_daily(agent="opencode")` 已覆盖。
- **`invalidate_user_query_cache` 保留?** 保留。用于 `clear-data` 场景需要清全用户缓存。

---

## 实施清单

- [ ] A. `token_usage_cache.py` 新增 `invalidate_device_query_cache`
- [ ] B. 三处调用点（/refresh, /refresh-ccusage, /sync）+ 后台调度器追加设备级缓存清除
- [ ] C. 移除 v1 opencode 源（确认无引用后删除 `sources` 中的 opencode 行）
- [ ] D. 移除仅被 v1 opencode 依赖的函数（`_fetch_opencode_daily`, `_parse_opencode_entries`, `_fetch_opencode_current`, `_fetch_opencode_legacy`, `fetch_opencode`, `OPCODE_CUTOFF`）
- [ ] E. pytest + 启动验证
