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

## 已决事项

1. Codex 数据采集器本次不实现，只预留字段和统计路径。
2. 旧数据先完全依赖查询 fallback，不把批量回填作为上线前置条件。
3. 模型筛选列表展示当前时间范围和其他筛选条件下出现过的真实模型。

## 第二轮审查补充

### 审查结论

第一版方案方向正确，但还需要把几个容易在实现阶段造成返工的边界提前固定：

1. `source` 与 `tool_id` 的职责必须分清，否则后续 Codex、OpenClaw、API 数据接入会再次混乱。
2. 表字段可以增加，但迁移必须先 nullable、后回填，不能因为旧数据缺字段导致线上查询失败。
3. 前端筛选项不能靠硬编码，至少应从查询响应或轻量选项接口中获得真实可用值。
4. 排序必须先在后端确定全量顺序，再分页或前端展示，否则分页后排序会产生错觉。
5. 维度汇总与明细表要共享同一套筛选条件，但筛选选项本身需要能解释“为什么某项消失”。
6. Codex 本次只预留结构，不接入伪数据；没有真实可解析 usage 样例前，不进入统计总额。

### 字段职责修订

`source` 保持为“采集来源”字段，负责兼容现有逻辑和同步日志，例如 `claude`、`opencode`。`tool_id` 是“产品统计维度”字段，负责页面筛选、图表和长期扩展，例如 `claude-code`、`opencode`、`codex`。

映射关系第一阶段如下：

| source | tool_id | tool_name |
| --- | --- | --- |
| `claude` | `claude-code` | `Claude Code` |
| `opencode` | `opencode` | `OpenCode` |
| `codex` | `codex` | `Codex` |
| 其他未知值 | `source` 原值 | 原值或 `Unknown Tool` |

`source_raw` 只在采集器返回了比 `source` 更细的原始来源时写入。若当前采集器没有这个信息，字段可以为空，不强行构造。

### 迁移策略

表结构变更分两步走：

1. 新增字段全部允许为空：
   - `tool_id`
   - `tool_name`
   - `device_name`
   - `model_display_name`
   - `source_raw`
2. 查询层立即提供 fallback：
   - `tool_id = tool_id or map_source_to_tool(source).tool_id`
   - `tool_name = tool_name or map_source_to_tool(source).tool_name`
   - `device_name = device_name or device_registry.display_name or device_registry.default_display_name or device_id`
   - `model_display_name = model_display_name or display_model(model, tool_name)`

旧数据回填不作为首屏依赖。实现完成后可以追加批量回填脚本，但页面必须在未回填时也正常工作。

索引策略：

1. 初始新增普通组合索引：`user_id, record_date, tool_id, device_id, model`。
2. 如果使用 PostgreSQL 且数据量较大，生产迁移应优先使用非阻塞方式创建索引；本地开发可以普通创建。
3. 不修改现有唯一约束，仍使用 `user_id + device_id + record_date + source + model` 去重。`tool_id` 由 `source` 派生时没有必要进入唯一键，避免旧数据迁移风险。

### 统计口径修订

所有统计以 `token_usage_records` 为事实来源，不从前端 `models_used` 反推。

维度汇总的分母规则：

1. `summary` 是当前筛选条件下的总量。
2. `dimension_summaries.devices/tools/models` 的占比都以同一个 `summary` 为分母。
3. 当 `summary.total_cost > 0` 时，默认强调成本占比。
4. 当 `summary.total_cost == 0` 时，默认强调 Token 占比，但仍返回 `cost_share=0`。
5. `records_count` 是事实表行数，用于解释数据密度；不要显示成“天数”。

模型维度必须包含 `tool_id/source + model`，不能只按 `model` 聚合。不同工具下同名模型需要分开显示。

### API 契约补充

`POST /api/token-usage/query` 响应除 `dimension_summaries` 外，建议同时返回筛选选项：

```ts
filter_options: {
  tools: Array<{ tool_id: string; tool_name: string; records_count: number }>;
  devices: Array<{ device_id: string; device_name: string; records_count: number }>;
  models: Array<{
    tool_id: string;
    source: string;
    model: string;
    model_display_name: string;
    records_count: number;
  }>;
}
```

筛选选项口径：

1. 受时间范围影响。
2. 受用户权限影响。
3. 不受当前同维度筛选影响，避免用户选中某个模型后模型下拉只剩自己。
4. 受其他维度筛选影响，例如选择某个工具后，模型列表只显示该工具下的模型。

请求参数进一步明确：

```ts
{
  type: 'daily' | 'weekly' | 'monthly';
  days: number;
  source?: 'claude' | 'opencode' | 'all';
  tool_id?: string;
  device_id?: string;
  model?: string;
  group_by: 'none' | 'device' | 'tool' | 'model';
  sort_by: 'date' | 'total_tokens' | 'total_cost' | 'input_tokens' | 'output_tokens' | 'cache_tokens';
  sort_order: 'asc' | 'desc';
}
```

兼容规则：当 `source` 与 `tool_id` 同时传入时，后端取交集；如果交集为空，返回空结果而不是报错。

### 排序与分页

第一阶段继续沿用前端分页，但排序必须由后端对完整结果执行。原因是当前数据量不大，前端分页足够简单；但如果只对当前页排序，用户会误以为全量已排序。

实现规则：

1. 后端按 `sort_by/sort_order` 排好 `items`。
2. 前端只对后端返回顺序分页，不再二次改变全局顺序。
3. 明细表表头点击时更新 `sort_by/sort_order` 并重新请求。
4. 若后续 `items` 数量过大，再扩展 `page/page_size/total_count` 做服务端分页。

### 前端交互补充

筛选区建议拆成两层：

1. 主筛选：时间、工具、设备、模型。
2. 视图控制：分组、排序、图表类型。

维度卡点击行为：

1. 点击设备卡项：设置 `device_id`。
2. 点击工具卡项：设置 `tool_id`，并清空不属于该工具的 `model`。
3. 点击模型卡项：设置 `tool_id + model`，保证同名模型不会跨工具误筛。
4. 再次点击已选项：取消该筛选。

明细表字段展示规则：

1. `group_by=none`：每行展示日期级聚合，设备/工具/模型列显示“多项”或用 chips 展示 Top 3。
2. `group_by=device`：设备列显示具体设备，工具/模型列显示该设备下汇总的 Top 值。
3. `group_by=tool`：工具列显示具体工具，设备/模型列显示 Top 值。
4. `group_by=model`：模型列显示具体模型，工具列必须显示对应工具。

### 性能与缓存补充

维度汇总可能带来三组聚合查询。后端实现时优先复用同一套基础过滤条件，分别执行轻量 group by；不建议为了“少一次查询”写过度复杂 SQL。

缓存 payload 应包含：

1. `items`
2. `summary`
3. `devices`
4. `model_summary`
5. `dimension_summaries`
6. `filter_options`
7. `cache_written_at`

缓存 key 必须覆盖所有会影响结果的参数。排序会影响 `items` 顺序，也必须进入 key。若后续维度卡不受排序影响，也仍可以整体缓存，先保持实现简单。

### 实施决策

本轮设计固定以下决策，减少后续反复确认：

1. Codex 本次不实现采集器，只预留 `tool_id/tool_name/source` 结构。
2. 旧数据先依赖查询 fallback，不把批量回填作为页面上线前置条件。
3. 模型筛选列表展示当前时间范围和其他筛选条件下出现过的真实模型。
4. `source` 继续保留，`tool_id` 成为新的主要页面统计维度。
5. 排序在后端完成，分页第一阶段仍在前端完成。

### 增补验收标准

1. 页面能同时看到设备排行、工具排行、模型排行，且三者总量与 summary 对齐。
2. 选择工具后，设备和模型统计同步收敛到该工具范围。
3. 选择模型后，不会把其他工具下同名模型混入结果。
4. 旧记录即使 `tool_id/device_name/model_display_name` 为空，也能展示正确工具、设备、模型名称。
5. 缓存命中时，筛选选项和维度汇总不会丢失。
6. 表头排序改变后，第一页展示的是全量排序后的第一页，不是当前页局部排序。
7. 没有真实 Codex 数据时，页面不把 Codex 计入总 Token 或总成本。
