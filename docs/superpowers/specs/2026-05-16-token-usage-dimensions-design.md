# Token Usage 多维统计设计

日期：2026-05-16

## 背景

`/tools/token-usage` 当前已经可以展示 Token 趋势、模型汇总、设备筛选和数据新鲜度，但统计维度还不够完整。现有数据事实表已经具备 `device_id`、`source`、`model` 三个核心字段，不过页面和接口仍偏向单一查询结果，缺少统一的设备、工具、模型三类维度统计，也缺少排序、筛选和明细字段来支撑交叉分析。

本设计确认“工具”定义为使用来源/客户端，例如 `Claude Code`、`OpenCode`，后续可扩展到 `Codex`、`Cursor`、`Aider`、`API` 等。

## 目标

1. 支持按设备、按工具、按模型统计 Token 和成本。
2. 表结构补充清晰的工具、设备、模型展示字段，同时兼容旧数据。
3. 后端提供统一维度统计结果，避免前端重复猜测和多次请求。
4. 前端增加维度卡、筛选、排序和明细字段。
5. 为后续 Codex 数据接入预留稳定字段和统计路径。

## 非目标

1. 本次不重构为完整 BI 数据仓库。
2. 本次不强制实现 Codex 数据采集器，只预留 `tool_id='codex'` 的写入与展示能力。
3. 本次不删除或重命名现有 `source` 字段，避免破坏现有接口和缓存。

## 方案选择

采用方案 B：保留现有 `token_usage_records` 事实表，新增规范化维度字段和统一统计接口。

不采用只增强现有查询的轻量方案，因为 `source` 与“工具展示名”长期会混在一起；也不采用全量维度表重构，因为迁移成本和风险超过当前页面收益。

## 数据模型

在 `token_usage_records` 上补充以下字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `tool_id` | `String(64)` | 规范化工具 ID，例如 `claude-code`、`opencode`、`codex` |
| `tool_name` | `String(128)` | 页面展示名，例如 `Claude Code`、`OpenCode`、`Codex` |
| `device_name` | `String(128)` | 入库时记录设备展示名 |
| `model_display_name` | `String(128)` | 模型展示名 |
| `source_raw` | `String(128)` | 原始来源字符串，用于排查和兼容 |

兼容规则：

1. 旧数据没有 `tool_id` 时，由 `source` 推导：`claude -> claude-code`，`opencode -> opencode`。
2. 旧数据没有 `tool_name` 时，由 `tool_id/source` 推导展示名。
3. 旧数据没有 `device_name` 时，优先从 `device_registry` 获取，再回退到 `device_id`。
4. 旧数据没有 `model_display_name` 时，由 `model` 推导。
5. `model='_total'` 显示为 `{tool_name} total`，避免误显示为未知模型。

索引建议：

1. 保留现有 `idx_token_usage_query`。
2. 新增组合索引：`user_id, record_date, tool_id, device_id, model`。
3. 如排序性能不足，再补充 `user_id, record_date, total_cost` 和 `user_id, record_date, total_tokens`。

## 后端接口

扩展现有 `POST /api/token-usage/query`，避免前端多次请求。

请求参数新增：

| 参数 | 说明 |
| --- | --- |
| `tool_id` | 工具筛选，空值表示全部 |
| `model` | 模型筛选，空值表示全部 |
| `group_by` | 扩展为 `none | device | tool | model` |
| `sort_by` | `date | total_tokens | total_cost | input_tokens | output_tokens | cache_tokens` |
| `sort_order` | `asc | desc` |

响应新增：

```ts
dimension_summaries: {
  devices: DimensionSummaryItem[];
  tools: DimensionSummaryItem[];
  models: DimensionSummaryItem[];
}
```

`DimensionSummaryItem` 字段：

```ts
{
  dimension: 'device' | 'tool' | 'model';
  key: string;
  label: string;
  device_id?: string;
  tool_id?: string;
  source?: string;
  model?: string;
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  total_tokens: number;
  total_cost: number;
  token_share: number;
  cost_share: number;
  records_count: number;
  last_used_at: string | null;
}
```

统计规则：

1. 主明细列表按当前 `group_by` 聚合。
2. 三个维度汇总始终同时返回，并受时间范围、工具、设备、模型筛选影响。
3. `token_share` 使用当前筛选后的 `summary.total_tokens` 为分母。
4. `cost_share` 使用当前筛选后的 `summary.total_cost` 为分母；若成本全为 0，前端回退展示 Token 占比。
5. `records_count` 统计事实表记录数，不是日期数。
6. `last_used_at` 使用当前维度下记录的最大 `updated_at`，没有时回退 `created_at`。

缓存规则：

查询缓存 key 必须加入：

1. `tool_id`
2. `model`
3. `sort_by`
4. `sort_order`
5. 现有 `source/type/days/group_by/user_id/device_id`

避免不同筛选或排序命中同一份缓存。

## 同步入库

同步服务写入 `TokenUsageRecord` 时补齐维度字段：

1. `source` 保持原值，用于兼容。
2. `tool_id/tool_name` 由 source 映射生成。
3. `device_name` 从 `get_device_display_name()` 或 `DeviceRegistry.default_display_name` 获取。
4. `model_display_name` 由模型名和工具名推导。
5. 后续 Codex 接入时只需新增 fetch/parse 逻辑，并写入 `source='codex'`、`tool_id='codex'`、`tool_name='Codex'`。

旧数据无需一次性强迁移。查询层必须提供 fallback，保证旧记录也能统计。可在后续维护任务中追加后台回填。

## 前端设计

顶部筛选区调整为紧凑控制组：

1. 时间粒度：日、周、月。
2. 时间范围：7、14、30、90、180、365。
3. 工具：全部、Claude Code、OpenCode，未来自动出现 Codex。
4. 设备：全部设备。
5. 模型：全部模型。
6. 分组：日期、设备、工具、模型。
7. 排序：日期、总 Token、成本、输入、输出、缓存。
8. 排序方向：正序、倒序。

中部增加三张维度统计卡：

1. 设备排行：展示设备消耗、占比、最近使用时间。
2. 工具排行：展示 Claude Code、OpenCode、未来 Codex 的占比。
3. 模型排行：展示模型 Token/成本占比。

维度卡交互：

1. 每张卡显示 Top N。
2. 每项展示 label、Token、成本、占比。
3. 点击某项自动应用对应筛选。
4. 成本为 0 时展示 Token 占比。
5. 空数据时显示明确空状态，不显示空图。

图表区：

1. `group_by=none` 时继续显示输入、输出、缓存、成本趋势。
2. `group_by=device/tool/model` 时显示对应维度随时间变化。
3. Tooltip 统一展示日期、设备、工具、模型、Token、成本。

明细表新增列：

1. 日期
2. 设备
3. 工具
4. 模型
5. 输入
6. 输出
7. 缓存创建
8. 缓存读取
9. 总 Token
10. 成本
11. 占比
12. 最近更新时间

明细表交互：

1. 表头点击排序。
2. 保留分页。
3. 显示当前筛选下总条数。
4. 设备、工具、模型列可点击快速筛选。

## 错误处理

1. 字段缺失时使用 fallback，不让接口 500。
2. 维度统计为空时返回空数组，前端显示空状态。
3. Redis 不可用时继续直连数据库查询。
4. 同步失败时保留已有数据，并在 `sync_meta.sources_status` 中展示错误来源。

## 测试计划

后端测试：

1. 设备维度聚合正确。
2. 工具维度聚合正确。
3. 模型维度聚合正确。
4. 工具、设备、模型组合筛选正确。
5. `group_by=tool` 返回按工具聚合的明细。
6. 旧数据只有 `source/device_id/model` 时仍能生成维度汇总。
7. 缓存 key 包含新增筛选和排序字段。
8. `_total` 展示名转换为 `{tool_name} total`。

前端验证：

1. 页面首次加载三张维度卡都有数据。
2. 切换工具/设备/模型筛选后请求参数正确。
3. 点击维度卡能快速筛选。
4. 表头排序能更新数据。
5. 明细表显示设备、工具、模型。
6. 成本为 0 时模型卡仍按 Token 展示。
7. `npm run build` 通过。

## 实施顺序

1. 后端模型和兼容字段：增加字段、fallback 映射、查询 schema。
2. 统计服务：抽出维度聚合 helper，统一计算 devices/tools/models。
3. 查询接口：扩展请求、响应、缓存 key、排序逻辑。
4. 同步服务：入库时补齐工具、设备、模型展示字段。
5. 前端 API 类型：增加筛选参数和维度响应类型。
6. 前端页面：新增筛选、维度卡、明细列、排序交互。
7. 测试与验证：后端单测、前端构建、接口实测。

## 待确认事项

1. Codex 数据采集器是否在本次实现，还是只预留字段。
2. 是否需要做一次旧数据后台回填，或先完全依赖查询 fallback。
3. 模型筛选列表是否只展示当前筛选范围内出现过的模型。
