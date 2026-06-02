# Token 消耗统计页面速度优化设计（L1+L2）

**日期**: 2026-06-02
**状态**: 待审批
**作者**: Sisyphus（brainstorming 自动产出）
**版本**: 1.0

---

## 1. 背景与问题

### 1.1 现状

`/tools/token-usage` 页面当前通过单一接口 `GET /api/token-usage/db` 一次性返回：
- 5 个统计卡（总成本 / 日均 / 总 token / 输入 / 输出）
- 3 个维度 Top 5（设备 / 工具 / 模型）
- 趋势图（ComposedChart）
- 模型成本饼图
- 全量明细行（无分页）
- filter_options / sync_meta / devices

页面组件 1059 行，所有筛选变化（source / days / groupBy / sort / 翻页）都触发**整页全量重查**。

### 1.2 痛点诊断

| 痛点 | 现象 | 根因 |
|---|---|---|
| 切筛选要等 1-3 秒 | 用户体验卡顿 | 单接口返回全量数据，response payload 大；前端 `setLoading(true)` → 渲染骨架屏 → 重新挂载图表 |
| 大数据下滚动卡 | 90 天 × 5 模型 = 450 行，明细表格直接渲染所有 DOM 节点 | 未做虚拟化 |
| 缓存粒度太粗 | 任何筛选变化都让旧缓存 key 失效 | cache key 与全部 query 绑定，没有分接口 |
| 轮询拖慢首屏 | 60s 轮询 + 整页请求会阻塞交互 | 轮询和用户操作串行 await |
| 缓存击穿潜在风险 | 热门筛选项 30s TTL 过期瞬间并发 | 未做 singleflight 串行化 |

### 1.3 目标

1. **首屏加载**：从"等 1-3 秒"降到"200-500ms 内出概览"
2. **切筛选**：从"loading 全屏"降到"保留旧数据 + 顶部 1px 进度条"
3. **明细滚动**：10000 行也能流畅滚动
4. **轮询开销**：从"轮询一次 1MB 响应"降到"轮询一次 5KB"
5. **不破坏**：现有用户登录、刷新、清理、设备重命名等所有操作

### 1.4 非目标（明确不做）

- 不改数据库表结构
- 不接入 Codex 真实 usage 数据（健康检查仍显示"待接入"）
- 不改数据源（ccusage、opencode-usage）的采集方式
- 不实现离线 IndexedDB 缓存
- 不做视觉/UI 改版
- 不重写为 React Query 等大框架（保持当前 useState + useEffect 风格）

---

## 2. 方案选型

### 2.1 候选方案对比

| 方案 | 改动范围 | 收益 | 风险 |
|---|---|---|---|
| A. 客户端智能保留 + 防抖 | 仅前端 | 中（治标不治本） | 低 |
| **B. 聚合/明细解耦 + 轮询降级（推荐）** | 前端 + 后端接口 | **高** | 中（兼容期） |
| C. 服务端预聚合 + 物化视图 | 前端 + 后端 + DB | 极高 | 高（迁移 + 竞态） |

**选择 B**：在 2-3 天工期内获得最大收益，且是未来 C 方案的前置依赖。

---

## 3. 架构总览

### 3.1 一句话总结

把"概览数据"和"明细数据"拆成两个独立查询，前端用两个独立 hook 各自管 loading，后端为明细加缓存。

### 3.2 模块边界

```
┌─────────────────────────────────────────────────────────────────┐
│                       前端 TokenUsage.tsx                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐        ┌──────────────────┐              │
│  │  useSummaryQuery  │        │  useDetailsQuery  │              │
│  │  (独立 loading)   │        │  (独立 loading)   │              │
│  │  30s 自动轮询     │        │  按需触发         │              │
│  └────────┬─────────┘        └─────────┬────────┘              │
│           │                           │                        │
│           ▼                           ▼                        │
│  ┌──────────────────┐        ┌──────────────────┐              │
│  │  概览 UI 区       │        │  明细 UI 区       │              │
│  │  5 个统计卡       │        │  虚拟列表        │              │
│  │  3 个维度 Top5    │        │  分页器          │              │
│  │  趋势图 + 模型饼图│        │  导出 CSV        │              │
│  └──────────────────┘        └──────────────────┘              │
│                                                                 │
└────────────┬───────────────────────────┬────────────────────────┘
             │                           │
             ▼                           ▼
   ┌────────────────────┐     ┌────────────────────┐
   │  GET /summary      │     │  GET /details      │
   │  (新接口)          │     │  (改造原 /db)       │
   │  Redis 30s 缓存    │     │  Redis 30s 缓存    │
   │  返回 5+3 卡片数据 │     │  limit/offset 分页  │
   └─────────┬──────────┘     └─────────┬──────────┘
             │                           │
             ▼                           ▼
   ┌────────────────────────────────────────────────┐
   │       token_usage_service.aggregate()          │
   │       (现有聚合逻辑，无大改)                    │
   └────────────────────────────────────────────────┘
                          │
                          ▼
                ┌──────────────────┐
                │  SQLite 原始记录  │
                │  (无表结构变更)   │
                └──────────────────┘
```

### 3.3 关键设计决策

1. **接口路径**：新增 `GET /api/token-usage/summary`，原 `GET /api/token-usage/db` 改造为 `GET /details`（保留 `/db` 路径 12 周兼容）
2. **缓存粒度**：
   - `summary` key: `(user_id, source, type, days, group_by, device_id, tool_id, model)`
   - `details` key: summary key + `(sort_by, sort_order, limit, offset)`
   - TTL 统一 30s
3. **数据契约**：`summary` 是 `details` 的**子集+扩展**（多了 dimension_summaries、model_summary、sync_meta、filter_options）
4. **前端不引入新依赖**：用 `useState + useEffect + useRef` 拆成两个自定义 hook

---

## 4. 数据流

### 4.1 首次进入页面（冷启动）

```
用户访问 /tools/token-usage
    │
    ├─→ useSummary.fetch()   [并行]   useDetails.fetch()
    │   (source/days/groupBy 默认)       (page=1)
    │         │                              │
    │         ▼                              ▼
    │   /api/summary                   /api/details?limit=20
    │   (含 5 卡片+3 维度+sync_meta)   (含 20 行明细)
    │         │                              │
    │         ▼                              ▼
    │   概览区渲染（~50ms 命中缓存时）  明细区渲染（~100ms）
    │
    ▼
组件完成首次 paint
```

### 4.2 用户切换"工具"筛选

```
用户改 <select> onChange
    │
    ├─→ useDetails.fetch({ tool_id: newValue, page: 1 })
    │   【关键】旧 items 保留，顶部"正在筛选"提示出现
    │         │
    │         ▼
    │   /api/details (新 cache key)
    │   200-500ms 后返回
    │         │
    │         ▼
    │   items 替换，提示消失
    │
    └─→ useSummary 暂不刷新（同一组筛选下，summary 30s 内不变）
```

### 4.3 后台轮询（每 30s 一次）

```
useEffect 内 setInterval 触发
    │
    ├─→ useSummary.fetch() 静默（不显示 loading）
    │   │
    │   ├─ 命中 Redis 30s 缓存 → 直接返回，无 loading、无网络
    │   └─ 缓存未命中 → 后端计算 → 写回缓存
    │
    └─→ 拿到新 summary 后：
         ├─ sync_meta.last_success_at 变化 → 更新顶部 "最后同步 X 分钟前"
         └─ is_stale=true → 显示 "数据已过期" 黄色徽标，引导手动刷新
```

### 4.4 加载状态三态

| 区域 | 状态 | UI 表现 |
|---|---|---|
| 概览区 | 首次加载 | 5 个统计卡显示骨架屏（`animate-pulse`） |
| 概览区 | 轮询加载 | 不显示 loading，更新瞬间无感（值变化时有 transition） |
| 概览区 | 加载失败 | 卡片显示 `?`，顶部红色提示"概览加载失败，点此重试" |
| 明细区 | 首次加载 | 表格区域显示骨架行（8 行） |
| 明细区 | 切筛选 | **保留旧数据 + 表格顶部 1px 进度条** |
| 明细区 | 切页 | 同切筛选，但保留旧分页数据直到新数据返回 |
| 明细区 | 加载失败 | 表格区域显示空态 + 错误信息，"重试"按钮 |

### 4.5 缓存失效与同步触发

| 触发事件 | 影响 |
|---|---|
| 手动"刷新"按钮 | 清 `summary` 和 `details` 该 user 全部 cache key；调 `/refresh` 后台同步；完成后 `useSummary` 立即重拉 |
| "清理"按钮 | 调 `/clear`；前端直接清空所有 state，不再请求 |
| 切换 source / days / groupBy | 视为筛选变化，仅刷新两个 query，不清缓存 |
| 用户跨设备操作 | 30s 内最多延迟反映（轮询周期）；可接受 |

### 4.6 防抖策略

| 控件 | 防抖时间 | 理由 |
|---|---|---|
| source / days / groupBy / sortBy / sortOrder | 200ms | 单次操作，响应要快 |
| tool_id / model_id / device_id | 300ms | 关联筛选（model 跟着 tool 变） |
| chartType / reportType | 0ms（立即） | 纯前端 UI 切换 |

通过共用一个 `useDebouncedValue` hook（自写，~10 行）实现，不引外部库。

---

## 5. 接口契约

### 5.1 `GET /api/token-usage/summary`

#### Query 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| source | string | 否 | `all` / `claude` / `opencode`，默认 `all` |
| type | string | 否 | `daily` / `weekly` / `monthly`，默认 `daily` |
| days | int | 否 | 时间范围，默认 30 |
| group_by | string | 否 | `none` / `device` / `tool` / `model` |
| device_id | string | 否 | 设备筛选，空=全部 |
| tool_id | string | 否 | 工具筛选，空=全部 |
| model | string | 否 | 模型筛选，空=全部 |

#### 响应体

```typescript
{
  summary: {
    total_input_tokens: number;
    total_output_tokens: number;
    total_cache_creation_tokens: number;   // 新增：之前藏在明细里
    total_cache_read_tokens: number;       // 新增
    total_tokens: number;
    total_cost: number;
    days_count: number;
    avg_daily_cost: number;
  };
  dimension_summaries: {
    devices: DimensionSummaryItem[];
    tools: DimensionSummaryItem[];
    models: DimensionSummaryItem[];
  };
  model_summary: ModelSummaryItem[];
  filter_options: {
    devices: FilterDeviceOption[];
    tools: FilterToolOption[];
    models: FilterModelOption[];
  };
  sync_meta: SyncMeta | null;
  cached: boolean;
  auto_expanded: boolean;
  actual_days: number | null;
  devices: DeviceInfo[];
  // 图表序列：用于渲染趋势图和分组对比图
  // 按 (date, group_key) 预聚合，行数 ≤ 365 × 最多 5 个 group
  chart_series: Array<{
    date: string;
    group_key: string | null;
    total_tokens: number;
    total_cost: number;
  }>;
}
```

**缓存键**：`summary:{user_id}:{source}:{type}:{days}:{group_by}:{device_id|all}:{tool_id|all}:{model|all}`，TTL 30s

### 5.2 `GET /api/token-usage/details`

#### Query 参数

继承 summary 的 7 个参数，**新增**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| limit | int | 否 | 每页数量，默认 50，上限 200 |
| offset | int | 否 | 偏移量，默认 0 |
| sort_by | string | 否 | `date` / `total_tokens` / `total_cost` / `input_tokens` / `output_tokens` / `cache_tokens` |
| sort_order | string | 否 | `asc` / `desc`，默认 `desc` |

#### 响应体

```typescript
{
  items: DbUsageItem[];                 // 本页明细（不超过 limit）
  total: number;                        // 全量条数（用于前端分页器）
  limit: number;                        // 回显
  offset: number;                       // 回显
  has_more: boolean;                    // (offset + items.length) < total
  cached: boolean;                      // 命中缓存
}
```

**缓存键**：`details:{summary_key}:{sort_by}:{sort_order}:{limit}:{offset}`，TTL 30s  
**失效**：调用 `/refresh` 和 `/clear` 时按 `summary_key` 前缀批量清除

### 5.3 兼容性策略

| 时间 | `/db` 行为 | `/summary` `/details` 行为 | 前端 |
|---|---|---|---|
| 第 1-2 周 | 继续返回原 11 字段（保留 `items` 不分页） | 已上线 | 通过 `VITE_USE_SPLIT_API=true` 切换 |
| 第 3 周起 | 加 deprecation 警告 header | 稳定 | 默认走新接口 |
| 第 12 周 | 下线 `/db` | 稳定 | 移除兼容代码 |

---

## 6. 前端代码组织

```
frontend/src/components/Tools/TokenUsage.tsx           # 减重到 ~700 行
frontend/src/components/Tools/hooks/
  ├── useTokenUsageSummary.ts                           # 概览查询 + 轮询
  ├── useTokenUsageDetails.ts                           # 明细查询 + 防抖
  ├── useDebouncedValue.ts                              # 通用防抖 hook
  └── useTokenUsagePolling.ts                           # 轮询逻辑（含 visibilitychange）
frontend/src/api/tokenUsageApi.ts                       # 新增 getTokenUsageSummary / getTokenUsageDetails
frontend/src/types/tokenUsage.ts                        # 共享响应类型
```

### 6.1 共享类型

```typescript
// frontend/src/types/tokenUsage.ts
export interface TokenUsageSummaryResponse { /* 同 5.1 */ }
export interface TokenUsageDetailsResponse { /* 同 5.2 */ }
export type SummaryQueryParams = { source?: TokenUsageSource; type?: ...; ... };
export type DetailsQueryParams = SummaryQueryParams & { limit?: number; offset?: number; ... };
```

后端用 Pydantic 定义 `SummaryResponse` / `DetailsResponse`，前端用 openapi-typescript 自动生成（项目里若有），否则手维护。

---

## 7. 错误处理与边界

### 7.1 错误分类与处理矩阵

| 错误类型 | HTTP | 前端表现 | 重试策略 |
|---|---|---|---|
| 网络中断 | — | 明细/概览区域显示空态 + "网络异常，点此重试" | 用户手动点重试 |
| 请求超时（>10s） | 504 | 同网络中断 | 手动重试 |
| 服务异常 | 500 | 顶部红色横幅："概览/明细暂时不可用（5xx）" | 自动重试 1 次（间隔 1s） |
| 认证失效 | 401 | 跳转登录页（保留来源 URL） | 不可重试 |
| 权限不足 | 403 | 顶部红色："无权限访问" | 不可重试 |
| 参数非法 | 422 | 重置该筛选为默认值 + toast 提示 | 不可重试（前端校验） |
| 数据为空 | 200 | 显示"暂无数据"友好空态 | 切其他筛选 |
| 数据陈旧 | 200 | 顶部黄色徽标"数据已过期，点击刷新" | 引导手动刷新 |
| 后台同步进行中 | 200 | 顶部蓝色"已有同步任务进行中" | 等待 30s 后再试 |

### 7.2 一致性策略：summary 成功、details 失败

- **不互相阻塞**：`useSummary` 和 `useDetails` 的 loading 状态完全独立
- **不一致时**：
  - 概览区显示最新 summary（含新 source/days 切换）
  - 明细区显示旧数据 + 顶部"筛选已更新，明细加载失败"提示 + 重试按钮

### 7.3 竞态条件

| 场景 | 处理 |
|---|---|
| 用户在 200ms 内连续切 3 次工具筛选 | 防抖合并为最后一次请求；旧请求到达后 `useRef` 标记为过期，直接丢弃结果 |
| 轮询返回时用户正在切筛选 | 轮询是 `silent: true` 不显示 loading；返回时直接 setState |
| 用户切到 page 5 时，刷新按钮被点击 | 刷新清缓存后，useDetails 自动重拉当前 page=5（通过 `preservePage` 参数） |
| 同时点击"刷新"两次 | 第二个 `handleRefresh` 检测到 `refreshing=true` 直接 return |
| 后台 sync 完成时前端正在轮询 | 轮询命中新缓存的 summary，无冲突 |

### 7.4 边界数据

| 数据量 | 行为 |
|---|---|
| 明细 DB 行数 = 0 | 表格显示空态；5 卡片显示 0；3 维度显示"暂无数据"；图表显示空态 |
| 明细 DB 行数 = 1 | 表格只渲染一行；图表尝试渲染（recharts 自适应） |
| 明细 DB 行数 > 10000 | 后端分页 size 上限 200；前端表格虚拟化（一次只渲染 ~20 行 DOM） |
| `days=365` + `group_by=model` | 后端 SQL 加索引提示；返回前 200 行 + `has_more=true` |

**关于图表数据源的关键说明**：

由于 `details` 接口分页上限 200，**图表不能直接基于 `items` 渲染**（否则切页后图表会重画）。改为：

- 图表数据从 `summary` 响应里的额外字段 `chart_series` 取（按 `(date, group_key)` 维度预聚合的轻量序列）
- `chart_series` 结构：`{ date: string, group_key: string | null, total_tokens: number, total_cost: number }[]`，行数 ≤ 365 × 最多 5 个 group（=1825 行）
- `summary` 响应新增字段（在 5.1 响应体基础上追加）：
  ```typescript
  chart_series: Array<{
    date: string;
    group_key: string | null;
    total_tokens: number;
    total_cost: number;
  }>;
  ```
- 切筛选或切 groupBy 时，`useSummary` 重拉，图表自动重画
- 切 `chartType`（bar/line）不重拉（仅前端图表组件重渲染）

### 7.5 缓存失效竞态

- 简化处理：每次 `useSummary` 轮询都把 `sync_meta.last_success_at` 与前端记录的对比，不一致则提示"数据已变更"
- 兜底：前端 60s 内至少拉 1 次 summary，确保不会出现"长期展示旧数据"

### 7.6 离线 / 弱网

| 情况 | 行为 |
|---|---|
| `navigator.onLine === false` | 顶部黄色横幅"当前离线，显示的是缓存数据"；请求按钮禁用 |
| 网络恢复（`online` 事件） | 自动重试最近失败的请求 1 次 |
| 长时间离线（>5min） | 顶部提示"已离线 X 分钟，部分数据可能已过时" |

### 7.7 后端错误日志

| 事件 | 日志级别 | 关键字段 |
|---|---|---|
| 缓存命中 | DEBUG | `key`, `age_seconds` |
| 缓存未命中 | INFO | `key`, `compute_ms` |
| 缓存写入失败 | WARNING | `key`, `error` |
| 聚合 SQL 慢（>1s） | WARNING | `sql`, `ms`, `row_count` |
| 后端 500 | ERROR | `endpoint`, `params`, `stack` |
| Token 同步失败 | ERROR | `source`, `reason` |

### 7.8 已知风险与缓解

| 风险 | 缓解 |
|---|---|
| Redis 不可用时所有请求退化为直接查库 | `token_usage_cache.py` 已有 try/except；增加 metrics 监控退化次数 |
| 多用户并发触发 `/refresh` 抢锁失败 | 现有 `refresh_lock` 机制；前端提示"其他窗口正在更新" |
| 切到 source=codex（待接入）显示空 | 健康检查已显示"待接入"；前端对 codex 给出"数据收集中"友好提示 |

---

## 8. 测试策略

### 8.1 测试分层

| 层 | 工具 | 范围 |
|---|---|---|
| 后端单元 | pytest | service 层的纯函数（聚合、缓存键生成、TTL 计算） |
| 后端接口 | pytest + FastAPI TestClient | 路由 `/summary` `/details` 的入参/出参、错误码、缓存命中 |
| 后端集成 | pytest + 临时 SQLite | 真实 DB 上跑聚合 SQL，验证 row_count / sum 一致 |
| 前端单元 | （若有 Vitest）hook 测试 | `useDebouncedValue` 边界 |
| 前端 E2E | 手动 + DevTools Network 面板 | 端到端用户流程 |
| 性能基准 | 脚本 | 关键路径的耗时 |

### 8.2 后端测试文件清单

```
tests/test_token_usage_split_api.py           # 路由 + 入参/出参 + 错误码
tests/test_token_usage_split_cache.py         # 缓存键 + TTL + 失效 + 退化
tests/test_token_usage_split_integration.py   # SQL 聚合 + 一致性
```

#### `test_token_usage_split_api.py` 测试项

```
class TestSummaryEndpoint:
    - test_returns_summary_for_default_filters
    - test_summary_excludes_items_field
    - test_summary_caches_on_second_call
    - test_summary_cache_key_includes_all_filters
    - test_summary_handles_empty_data
    - test_summary_auto_expands_to_actual_days
    - test_summary_includes_total_cache_tokens   # 新增字段
    - test_summary_401_when_unauthenticated
    - test_summary_422_when_invalid_source

class TestDetailsEndpoint:
    - test_returns_paginated_items
    - test_details_pagination_offset_limit
    - test_details_limit_capped_at_200
    - test_details_default_sort_by_date_desc
    - test_details_caches_on_second_call
    - test_details_cache_invalidated_on_refresh
    - test_details_404_when_summary_key_orphan

class TestCompatibility:
    - test_db_endpoint_still_returns_legacy_shape
    - test_db_endpoint_adds_deprecation_header
```

#### `test_token_usage_split_cache.py` 测试项

```
class TestCacheKeyStrategy:
    - test_summary_key_omits_pagination_params
    - test_details_key_includes_pagination_params
    - test_cache_ttl_is_30_seconds
    - test_cache_invalidation_clears_both_endpoints
    - test_cache_invalidation_only_affects_user

class TestCacheDegradation:
    - test_request_succeeds_when_redis_down
    - test_redis_failure_logged_as_warning
```

#### `test_token_usage_split_integration.py` 测试项

```
class TestEndToEndFlow (with seeded_database):
    - test_summary_total_matches_details_total
    - test_summary_total_matches_raw_db_sum
    - test_summary_after_refresh_includes_new_records
    - test_concurrent_requests_dont_corrupt_cache
```

### 8.3 前端测试（最小化）

**本次不引入 Vitest**（避免新增依赖）。如未来项目引入，则补：
- `useDebouncedValue.test.ts`：200ms 防抖合并、cleanup 取消 timer
- `useTokenUsageSummary.test.ts`：首次加载、轮询、cleanup、可见性切换
- `useTokenUsageDetails.test.ts`：分页、防抖、竞态保护

### 8.4 手动 E2E 测试清单

启动 dev 服务后逐项过一遍：

- [ ] **冷启动**：Network 面板确认只发 `/summary` 和 `/details` 各 1 次
- [ ] **缓存命中**：30s 内再次轮询，`cached: true` 且耗时 < 5ms
- [ ] **切工具**：改工具下拉，只发 `/details`（不发 `/summary`），UI 不出现空白
- [ ] **切页**：翻到第 2 页，只发 `/details?offset=50`
- [ ] **轮询**：打开 Network 面板等 30s，看到 `/summary` 静默请求（不带 loading 指示）
- [ ] **后台标签页**：切到其他标签 30s 后切回，立即触发一次 `/summary`
- [ ] **快速连切**：1 秒内改 5 次 source 筛选，最终只发 1 次 `/details`（防抖生效）
- [ ] **手动刷新**：点刷新按钮，所有缓存清空，重新发 2 个请求
- [ ] **清理数据**：点清理，2 个接口都重新发，UI 完全清空
- [ ] **离线**：浏览器 DevTools 切到 Offline，UI 显示"离线"提示
- [ ] **慢网络**：DevTools 切 Slow 3G，UI 保留旧数据 + 进度条
- [ ] **空数据**：切换到一个没有数据的 source，UI 显示"暂无数据"
- [ ] **大数据**：切到 days=365 + group_by=model，确认有 `has_more` 提示
- [ ] **跨用户隔离**：登录 A 看数据，登录 B 后看到的应该完全是 B 的
- [ ] **跨设备**：A、B 两个设备的 Claude Code 用量都同步到 summary

### 8.5 性能基准

`scripts/bench_token_usage.py`：

```python
"""基准测试：summary 和 details 接口在不同数据量下的耗时"""
CASES = [
    {"days": 7,   "group_by": "none",  "expected_items": 7},
    {"days": 30,  "group_by": "none",  "expected_items": 30},
    {"days": 30,  "group_by": "model", "expected_items": 90},
    {"days": 90,  "group_by": "model", "expected_items": 270},
    {"days": 365, "group_by": "model", "expected_items": 200},  # 上限截断
]

# 断言：
# - summary 在所有 case 下 < 200ms（命中缓存时 < 10ms）
# - details 在所有 case 下 < 300ms
# - 大数据 case 实际返回 ≤ 200 行
```

跑前注入 seed 数据（10 万条 token_usage 记录）。

### 8.6 上线 Checklist

- [ ] 后端单测 + 集成测试全部通过（`pytest tests/test_token_usage_split*`）
- [ ] 手动 E2E 全过
- [ ] 性能基准达标（summary < 200ms，details < 300ms）
- [ ] 前端 TypeScript 编译通过（`npm run type-check`）
- [ ] 前端构建通过（`npm run build`）
- [ ] 后端 ruff 通过
- [ ] 浏览器 Console 无 error/warn
- [ ] OpenAPI 文档更新（`/docs` 路径）
- [ ] i18n 文案更新（zh-CN / en-US）
- [ ] 部署到本地 `local_deploy.sh` 验证

### 8.7 不在测试范围

- 视觉回归（无 Storybook/Percy 基础设施）
- 跨浏览器兼容（只测 Chrome 系）
- 移动端适配（PC 端为主）
- 压力测试（用户量小）
- 渗透测试（鉴权逻辑未改）

---

## 9. 实施风险与回滚

### 9.1 主要风险

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| 缓存键设计错误导致脏数据 | 中 | 高 | 单测覆盖所有 cache key 组合；集成测试验证 summary 与 details 一致性 |
| 兼容性切换期间前端 / 后端不匹配 | 中 | 中 | 通过 `VITE_USE_SPLIT_API` 特性开关；保留 `/db` 12 周 |
| 大量并发击穿缓存 | 低 | 中 | 用户量小，先不做 singleflight；监控命中/未命中比 |
| 分页 SQL 性能差 | 中 | 中 | 加索引 `index_token_usage_user_date_source`；SQL 走 `EXPLAIN` 验证 |

### 9.2 回滚方案

1. **代码回滚**：`git revert` 即可
2. **接口回滚**：
   - 前端关掉 `VITE_USE_SPLIT_API`，切回 `/db` 旧接口
   - 后端 `/summary` `/details` 保留但前端不再调用
3. **缓存回滚**：Redis 不需要清；新 key 30s 自动过期

### 9.3 监控指标（建议）

| 指标 | 阈值 | 告警 |
|---|---|---|
| `/summary` P95 响应时间 | < 200ms | > 500ms 告警 |
| `/details` P95 响应时间 | < 300ms | > 800ms 告警 |
| 缓存命中率 | > 80% | < 50% 告警 |
| 缓存退化次数 | < 5/h | > 50/h 告警 |
| 前端首屏时间 | < 1s | > 2s 告警 |

---

## 10. 后续迭代（不在本次范围）

- **C 阶段**（推荐下一轮）：服务端预聚合表 + 物化视图
- **Codex 真实数据接入**：补全健康检查中"待接入"那块
- **会话/项目维度**：从原始记录里提取 session_id / project 字段
- **环比/同比/预算告警**：基于预聚合数据做时间对比
- **导出完整数据集**：当前导出仅当前可见，需要支持全量导出

---

## 11. 关键文件改动清单（实施参考）

### 11.1 后端

| 文件 | 改动 |
|---|---|
| `backend/app/routes/token_usage.py` | 新增 `/summary` 路由；改造 `/db` 为 `/details`；保留 `/db` 12 周 |
| `backend/app/services/token_usage_sync_service.py` | 抽出 `get_summary_aggregate()` 和 `get_details_paginated()` 两个纯函数 |
| `backend/app/services/token_usage_cache.py` | 新增 `make_summary_key()` / `make_details_key()`；按 user_id 前缀批量失效 |
| `backend/tests/test_token_usage_split_api.py` | 新建 |
| `backend/tests/test_token_usage_split_cache.py` | 新建 |
| `backend/tests/test_token_usage_split_integration.py` | 新建 |
| `backend/scripts/bench_token_usage.py` | 新建 |

### 11.2 前端

| 文件 | 改动 |
|---|---|
| `frontend/src/components/Tools/TokenUsage.tsx` | 重构：把 useEffect 拆成两个；保留旧 data 显示；保留 PAGE_SIZE=20 改 50 |
| `frontend/src/components/Tools/hooks/useTokenUsageSummary.ts` | 新建 |
| `frontend/src/components/Tools/hooks/useTokenUsageDetails.ts` | 新建 |
| `frontend/src/components/Tools/hooks/useDebouncedValue.ts` | 新建 |
| `frontend/src/components/Tools/hooks/useTokenUsagePolling.ts` | 新建（从 TokenUsage.tsx 抽出） |
| `frontend/src/api/tokenUsageApi.ts` | 新增 `getTokenUsageSummary` / `getTokenUsageDetails`；保留 `getDbTokenUsage` 12 周 |
| `frontend/src/types/tokenUsage.ts` | 新建（或扩展 tokenUsageApi.ts 中的 type） |
| `frontend/src/i18n/locales/zh-CN.ts` | 新增"正在筛选"、"明细加载失败"等文案 |
| `frontend/src/i18n/locales/en-US.ts` | 同上 |

---

## 12. 时间估算

| 任务 | 工时 |
|---|---|
| 后端：拆接口 + 缓存键 + 兼容 `/db` | 1.0 天 |
| 后端：测试用例（单元 + 集成） | 0.5 天 |
| 前端：拆 hook + 保留旧数据 + 防抖 | 1.0 天 |
| 前端：手动 E2E + 修小问题 | 0.5 天 |
| 性能基准脚本 + 调优 | 0.3 天 |
| 文档 + i18n | 0.2 天 |
| **合计** | **3.5 天** |

---

**文档版本**: v1.0  
**审阅人**: 待指定  
**下一步**: 审阅通过后调用 `writing-plans` skill 制定实施计划
