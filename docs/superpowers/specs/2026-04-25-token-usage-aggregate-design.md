---
author: Claude Code
created_at: 2026-04-25
purpose: Token 消耗统计页面新增"合计"功能设计 — 聚合所有工具数据 + 后台定时预计算缓存
---

# Token 消耗统计"合计"功能设计

## 背景

当前 `http://localhost:5178/tools/token-usage` 页面支持选择单个工具（Claude Code 或 OpenCode）查看 Token 消耗统计。用户希望新增"合计"选项，一次查看所有工具的聚合数据。

## 目标

- 工具下拉框新增"合计"选项，选择后展示 Claude Code + OpenCode 所有工具的聚合统计
- 通过后台定时任务预计算合计数据并写入 Redis 缓存，前端秒级响应
- 确保 Windows 和 macOS 跨平台兼容

## 架构设计

### 1. 后端聚合端点

**文件**: `backend/app/routes/token_usage.py`

新增 `POST /token-usage/aggregate` 端点：
- 接收 `type`（daily/weekly/monthly）、`days`、`breakdown`、`by` 参数
- 优先从 Redis 缓存读取（key 前缀 `token_usage:aggregate:`，与现有 `token_usage:` 保持一致，确保 `invalidate_cache()` 的 `token_usage:*` 模式能匹配到）
- 缓存未命中时：并发获取两个数据源 → 合并 items → 求和 summary → 写入缓存 → 返回

合并逻辑：
- `items`: 按日期分组，同一天有两个工具的数据时，各项 token（input/output/cache_creation/cache_read/total）和 cost 相加，`models_used` 去重合并
- `model_breakdowns`: 同日期的两个工具的 breakdown 列表直接拼接（保留原始工具来源，不合并同名模型）
- `summary`: 直接求和两个数据源的 `total_*` 字段
- `days_count`: 取合并后的 items 数量（即聚合后的数据点数量，与现有 `compute_summary` 逻辑一致）
- `avg_daily_cost`: 总成本 / days_count（与现有逻辑一致）

**重要**：aggregate 的 weekly/monthly 数据获取方式与现有逻辑一致 —— 从两个数据源获取 daily 原始数据，规范化后使用 `apply_aggregation` 按周/月聚合，再合并结果。

缓存键设计：
```
token_usage:aggregate:{report_type}:{days}:{since}:{until}:{breakdown}:{by}
```
TTL 与现有保持一致（3600 秒）。

### 2. 后台定时预计算

**文件**: `backend/app/main.py`

扩展 `refresh_token_usage_cache_periodically` 函数：

在原有 queries 循环之后，追加 aggregate 查询：
```python
aggregate_queries = [
    {"report_type": "daily", "days": 7},
    {"report_type": "daily", "days": 14},
    {"report_type": "daily", "days": 30},
    {"report_type": "daily", "days": 90},
    {"report_type": "weekly", "days": 56},
    {"report_type": "monthly", "days": 180},
]
```

新增 `_refresh_aggregate_cache(report_type: str, days: int)` 函数：
1. 使用 `asyncio.gather` 并发获取两个数据源的原始数据：
   - `_fetch_raw_data("claude", "daily", days)`（注意：始终取 daily 原始数据）
   - `_fetch_raw_data("opencode", "daily", days)`
2. 分别规范化两个数据源：`normalize_entries(raw, report_type)`
3. 分别应用聚合：`apply_aggregation(items, report_type)`（如果是 weekly 则按周聚合，如果是 monthly 则按月聚合）
4. 合并两个聚合后的结果：按日期分组，同日期的各项指标相加
5. 计算 summary：`compute_summary(merged_items)`
6. 写入 Redis（key: `token_usage:aggregate:{report_type}:{days}:::0:`）

错误处理：
- 单个数据源获取失败时：日志警告，继续使用另一个数据源的数据
- 两个数据源都失败时：日志错误，跳过该条缓存刷新

### 3. 前端 API 层

**文件**: `frontend/src/api/tokenUsageApi.ts`

新增函数：
```typescript
export async function getAggregatedTokenUsage(params: {
  type: 'daily' | 'weekly' | 'monthly';
  days?: number;
  breakdown?: boolean;
}): Promise<UsageResponse>
```

调用 `POST /api/token-usage/aggregate`，请求体包含 `{ type, days, breakdown }`。

### 4. 前端 UI 层

**文件**: `frontend/src/components/Tools/TokenUsage.tsx`

改动点：
- `source` 状态类型扩展：`useState<'claude' | 'opencode' | 'all'>('claude')`
- 工具下拉框新增 `<option value="all">工具合计</option>`
- `fetchData` 逻辑：`source === 'all'` 时调用 `getAggregatedTokenUsage({ type: reportType, days })`，否则调用 `getTokenUsage({ source, ... })`
- 数据来源显示修改为三元表达式：`source === 'all' ? '工具合计' : source === 'claude' ? 'ccusage' : 'opencode-usage'`
- CSV 导出文件名：当 `source === 'all'` 时使用 `token-usage-all-{reportType}-{date}.csv`
- `select` 的 `onChange` 类型改为 `e.target.value as 'claude' | 'opencode' | 'all'`

## 数据流

```
前端选择"合计" → getAggregatedTokenUsage() → POST /api/token-usage/aggregate
  ↓
后端: 检查 Redis 缓存 token_usage:aggregate:*
  ↓ (缓存命中)
  直接返回缓存数据（前端秒级响应）
  ↓ (缓存未命中)
  并发获取 ccusage + opencode-usage → 规范化 → 聚合 → 合并 → 写入缓存 → 返回
  ↓
后台定时任务 (每小时) 预计算并更新所有 aggregate 缓存
  ↓
前端后续请求直接命中缓存
```

## 错误处理

- **后端**：单个数据源获取失败时，继续使用另一个数据源的数据，在日志中警告；两个都失败时返回 HTTP 500
- **前端**：加载状态、错误提示保持现有逻辑不变
- **缓存刷新**：单个查询失败不影响其他查询，错误记录到日志后继续

## 跨平台兼容

- CLI 调用已封装在 `UsageFetcher` 中，已处理 Windows/Mac 路径差异（node.exe 路径、HOME 目录等）
- 前端为纯 React 逻辑，无平台差异
- 后端合并逻辑使用标准 Python，跨平台无差异
