---
author: Peanut
created_at: 2026-06-13
purpose: Token 消耗统计页面修复右上角刷新时间不准及图表横坐标日期重复问题
---

# Token 消耗统计页面 Bug 修复设计

## 问题描述

### Bug 1:右上角刷新时间不准
- **现象**:右上角显示 `2026/6/13 04:50:44`(凌晨),但详情里有最新的刷新时间是下午一点多
- **根因**:当前使用 `summary.data.sync_meta?.last_success_at`(同步任务完成时刻,凌晨 04:50),没有考虑数据后续被增量更新的情况
- **期望**:使用全局最新记录写入时间(`latest_record_at`)

### Bug 2:Token 消耗趋势图横坐标日期重复
- **现象**:X 轴出现 `2026-06-09 / 2026-06-09 / 2026-06-09` 重复日期
- **根因**:`chartData` 使用 `details.data.items`(分页过的明细表),同一天可能因分组维度被拆成多行,前端没有按日期聚合就直接画图
- **期望**:每个日期只出现一次,显示该日总量

## 架构与改动范围

### 改动文件清单(共 3 个文件)

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `backend/app/routes/token_usage.py` | 后端 | 1) 扩展 `ChartSeriesItem` schema 加 input/output/cache 字段;2) `build_chart_series` 聚合逻辑同步加三个字段;3) 在 `SyncMeta` 加 `latest_record_at` 字段;4) `_get_sync_meta` 计算用户全局最新记录时间 |
| `frontend/src/api/tokenUsageApi.ts` | 前端类型 | 同步更新 `ChartSeriesItem` 和 `SyncMeta` 接口 |
| `frontend/src/components/Tools/TokenUsage.tsx` | 前端组件 | 1) 右上角时间用 `latest_record_at`,fallback `last_success_at`;2) `chartData` 数据源从 `details.data.items` 切换到 `summary.data.chart_series` |

### 不改动的部分
- `groupedData`(361-390 行)— 已经按 date Set 去重,本来就没问题
- 明细表(`paginatedItems`)— 维持原样,继续按分页展示
- 同步任务、定时刷新、数据库 schema — 完全不动

## 后端改造细节

### 2.1 扩展 `ChartSeriesItem`(token_usage.py:647-651)

```python
class ChartSeriesItem(BaseModel):
    date: str
    group_key: Optional[str] = None
    total_tokens: int = 0
    total_cost: float = 0.0
    # 新增三个字段(向后兼容,默认 0)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_tokens: int = 0  # = cache_creation_tokens + cache_read_tokens
```

### 2.2 改造 `build_chart_series`(token_usage.py:1759-1831)

在 `series_map` 的 `bucket` 里追加三个累加项:

```python
bucket = series_map.setdefault(
    key, {
        "date": date_key, "group_key": gk,
        "total_tokens": 0, "total_cost": 0.0,
        "input_tokens": 0, "output_tokens": 0, "cache_tokens": 0,  # 新增
    }
)
bucket["total_tokens"] += int(getattr(row, "total_tokens", 0) or 0)
bucket["total_cost"] += float(getattr(row, "total_cost", 0) or 0)
bucket["input_tokens"] += int(getattr(row, "input_tokens", 0) or 0)         # 新增
bucket["output_tokens"] += int(getattr(row, "output_tokens", 0) or 0)       # 新增
bucket["cache_tokens"] += (
    int(getattr(row, "cache_creation_tokens", 0) or 0)
    + int(getattr(row, "cache_read_tokens", 0) or 0)
)                                                                            # 新增
```

并在最终 `result` 字典里输出这三个字段。

### 2.3 扩展 `SyncMeta`(token_usage.py:621-634)

```python
class SyncMeta(BaseModel):
    last_synced_at: Optional[str] = None
    last_success_at: Optional[str] = None
    latest_record_at: Optional[str] = None  # 新增：用户全局最新记录时间
    cache_written_at: Optional[str] = None
    # ... 其余字段不变
```

### 2.4 新增 `_latest_record_at_global` 函数

```python
def _latest_record_at_global(db, user_id: str) -> Optional[datetime]:
    """取该用户全局最新记录的写入时间,不受任何筛选影响。
    优先 updated_at,缺失时 fallback created_at。
    """
    row = (
        db.query(
            func.max(TokenUsageRecord.updated_at).label("updated_at"),
            func.max(TokenUsageRecord.created_at).label("created_at"),
        )
        .filter(TokenUsageRecord.user_id == user_id)
        .first()
    )
    if not row:
        return None
    return row.updated_at or row.created_at
```

### 2.5 在 `_get_sync_meta` 末尾填充 `latest_record_at`

在调用 `_build_sync_meta_from_values` 后,把全局值挂到返回的 dict 上:

```python
result = _build_sync_meta_from_values(...)
result["latest_record_at"] = _to_iso(_latest_record_at_global(db, user_id))
return result
```

## 前端改动细节

### 3.1 扩展 `SyncMeta` 接口(`frontend/src/api/tokenUsageApi.ts:50-58`)

```typescript
export interface SyncMeta {
  last_synced_at?: string | null;
  last_success_at?: string | null;
  latest_record_at?: string | null;  // 新增
  cache_written_at?: string | null;
  cache_ttl_seconds: number;
  cache_expires_at?: string | null;
  data_age_seconds?: number | null;
  is_stale: boolean;
  refresh_lock?: { locked: boolean; owner?: string | null; ttl_seconds: number };
}
```

### 3.2 扩展 `ChartSeriesItem` 接口(`frontend/src/api/tokenUsageApi.ts:177-182`)

```typescript
export interface ChartSeriesItem {
  date: string;
  group_key?: string | null;
  total_tokens: number;
  total_cost: number;
  input_tokens?: number;    // 新增
  output_tokens?: number;   // 新增
  cache_tokens?: number;    // 新增
}
```

### 3.3 右上角时间(`TokenUsage.tsx:521`)

```tsx
// 当前:
<span className="text-xs text-slate-400">
  {formatDateTime(summary.data.sync_meta?.last_success_at)}
</span>

// 改为:
<span className="text-xs text-slate-400">
  {formatDateTime(
    summary.data.sync_meta?.latest_record_at ||
    summary.data.sync_meta?.last_success_at
  )}
</span>
```

语义:`latest_record_at` 是全局最新记录时间(下午 13:xx);若后端未返回(版本兼容),降级到 `last_success_at`(凌晨)。

### 3.4 图表数据源切换(`TokenUsage.tsx:351-361`)

```tsx
// 当前:
const chartData = useMemo(
  () => [...details.data.items].sort((a, b) => a.date.localeCompare(b.date)).map(item => ({
    date: item.date,
    inputTokens: item.input_tokens,
    outputTokens: item.output_tokens,
    cacheTokens: item.cache_creation_tokens + item.cache_read_tokens,
    totalTokens: item.total_tokens,
    cost: item.total_cost,
  })),
  [details.data.items]
);

// 改为:
const chartData = useMemo(
  () =>
    [...summary.data.chart_series]
      // groupBy === 'none' 时 series 已经聚合好,无需二次聚合
      // 但 chart_series 在 groupBy !== 'none' 时带 group_key,此时不用这个分支
      .filter(s => s.group_key == null)
      .sort((a, b) => a.date.localeCompare(b.date))
      .map(item => ({
        date: item.date,
        inputTokens: item.input_tokens ?? 0,
        outputTokens: item.output_tokens ?? 0,
        cacheTokens: item.cache_tokens ?? 0,
        totalTokens: item.total_tokens,
        cost: item.total_cost,
      })),
  [summary.data.chart_series]
);
```

**说明**:`chart_series` 在 `groupBy === 'none'` 时返回的 `group_key` 是 `null`,刚好匹配当前 `chartData` 的语义(显示总量)。`groupBy !== 'none'` 时图表走的是另一条 `groupedData` 分支(361-390),那段已经用 date Set 去重,**不会重复**,不需要改。

### 3.5 依赖调整

由于 `chartData` 不再依赖 `details.data.items`,`details` 的 `limit` 参数可以维持现状(明细表分页需要),不需要调整。`details` 的请求仍然保留,只是不再驱动图表。

## 测试与回归验证

### 4.1 后端单元测试(可选但推荐)

在 `backend/tests/` 下新建或追加 1-2 个用例:

| 测试 | 验证点 |
|------|--------|
| `test_build_chart_series_includes_input_output_cache` | 构造几条 `TokenUsageRecord` mock,断言 `chart_series` 输出里 `input_tokens / output_tokens / cache_tokens` 字段被正确聚合 |
| `test_get_sync_meta_latest_record_at` | mock 两条记录(一条旧一条新),断言 `sync_meta.latest_record_at` 取最大值,不受同步日志影响 |

### 4.2 前端验证要点

1. **右上角时间**
   - 加载后显示的是下午时间(对应最新记录的 `created_at`/`updated_at`)
   - 切换筛选(工具/模型/设备/时间范围)时,**右上角时间不应变化**(全局字段,不随筛选变)
   - 点击「刷新」后,时间应该更新

2. **图表日期不重复**
   - X 轴 `2026-06-09` 只出现一次,不再重复
   - 柱形是 `input(蓝) + cache(黄) + output(绿)` 堆叠,**不是** 同一日期的多个并排柱
   - `groupBy` 切换为非 none 时,图表走 `groupedData` 分支,验证不受本次改动影响

3. **回归检查**
   - `groupBy !== 'none'` 时的分组柱状图(设备/工具/模型)不受影响
   - 明细表分页翻页正常
   - 导出 CSV、同步数据、手动刷新按钮功能不受影响
   - 时间筛选范围变更时图表正常刷新

## 数据流图

```
[数据库 TokenUsageRecord]
    │
    ├──► _latest_record_at_global() ──► sync_meta.latest_record_at ──► 前端右上角时间
    │
    └──► build_chart_series() ──► chart_series[] ──► 前端 chartData ──► Token 消耗趋势图
```

## 风险评估

| 风险 | 缓解措施 |
|------|---------|
| 后端 `chart_series` 字段扩展可能导致旧版前端解析失败 | 新增字段有默认值 0,前端用 `?? 0` fallback |
| `_latest_record_at_global` 查询可能慢(全表 MAX) | `TokenUsageRecord` 表有 `user_id + created_at` 索引,查询快 |
| `groupBy !== 'none'` 时图表数据源切换可能破坏分组柱状图 | 只改 `chartData`,`groupedData` 分支完全不动 |

## 验收标准

- [ ] 右上角显示的时间与详情里最新记录的时间一致(下午 13:xx)
- [ ] 切换筛选条件时右上角时间不变
- [ ] Token 消耗趋势图 X 轴无重复日期
- [ ] 图表保留 input/output/cache 三色堆叠柱
- [ ] 所有现有功能(分组图表、明细表、导出、刷新、同步)回归测试通过
