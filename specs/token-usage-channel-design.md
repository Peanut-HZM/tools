# 设计：Token 消耗统计增加「调用渠道」维度

> 2026-11-21 | 状态：已审查通过（人工多轮审查，台账见 docs/reviews/2026-11-21-token-usage-channel-review.md）
>
> 目标：在 Token 消耗统计的**明细**与**全部汇总维度**中增加「调用渠道」。
> 原则（用户明确）：**能统计到哪一层就统计到哪一层；渠道是什么就记什么；不深挖聚合网关的上游账号。**

---

## 1. 需求

### 1.1 要展示的渠道

以本机**实际配置**为准，不虚构、不猜测上游：

| 用户表述 | 渠道标识 | 数据来源 |
|---|---|---|
| OpenCode 里配置的平台渠道 | OpenCode `providerID`：`peanut` / `aliyun-bailian` / `opencode` / `deepseek` / `alibaba-coding-plan-cn` / `minimax-cn-coding-plan` / `magpie` 等 | OpenCode `session_message` / `message` 每条消息的 `model.providerID` |
| Kimi 官方渠道 | `kimi-code` | Kimi `wire.jsonl` 的 `model` 前缀（`kimi-code/...`） |
| 智谱 GLM 官方渠道（用户口语「GM」） | `zhipu` / `account:bigmodel-*` | ZCode `model_usage.provider_id` |
| OpenCode Go 官方渠道 | `opencode`（OpenCode 官方 Zen/Go 同一入口） | OpenCode `providerID=opencode` |
| 本地新增百炼平台渠道 | `aliyun-bailian` | OpenCode `providerID=aliyun-bailian` |

补充原则：
- **聚合网关不拆上游**：`peanut`（TokenProxy）上的 GLM / Kimi / Claude 一律记 `peanut`，不再拆到模型厂商。
- **没有逐条渠道的 Agent**：按该 Agent 当前配置文件解析（见 §3.3）；解析不出就记「未知渠道」，不编造。
- 渠道是**全局维度**，不随工具变化：`peanut` 不论从 OpenCode、Kimi 还是 Claude Code 调用，都归为同一个渠道。

### 1.2 范围

- 后端：采集 → 入库 → 聚合 → `/summary` / `/details`（含已弃用 `/query`）
- 前端 PC：`TokenUsage.tsx`（筛选、饼图、分组、明细列、CSV）
- 小程序：仅做类型兼容（可选加筛选，不阻塞）
- **不做**：跨历史配置回溯、聚合网关上游账号拆分、按 cc-switch rollup 反推历史渠道、渠道手工重命名 UI

---

## 2. 现状与差距（实测）

### 2.1 数据链路

```
Agent 本地文件
  → agent_readers/* 读取（部分读取器已有 provider）
  → base.aggregate_records()   ← 只按 (record_date, model) 聚合，渠道被丢弃
  → token_usage_sync_service._upsert_records()
  → token_usage_records（唯一键 user_id+device_id+record_date+source+model）
  → routes/token_usage.py（devices/tools/models 三个维度）
  → frontend TokenUsage.tsx（3 张饼图 + 明细表）
```

### 2.2 可用渠道数据（本机实测）

| 来源 | 原始字段 | 本机实测分布 | 逐条精确 |
|---|---|---|---|
| OpenCode | `model.providerID` / `providerID` | `peanut` 18664、`opencode` 3378、`deepseek` 1206、`aliyun-bailian` 334、`alibaba-coding-plan-cn` 24、`minimax-cn-coding-plan` 9、`magpie` 6 | ✅ |
| ZCode | `model_usage.provider_id` | `account:bigmodel-individual-coding-plan` 87806、`account:bigmodel-start-plan` 12852、`account:bigmodel-offpeak-idle-plan` 621、`kimi-code-cn` 336、`new-provider` 26 | ✅ |
| Kimi / Kimi Code | `model` 前缀 | `kimi-code/k3.1-pro`、`kimi-code/kimi-for-coding`、`peanut/claude-opus-5.0` | ✅ |
| Paseo ACP | `provider` | 当前无用量文件，字段结构已就绪 | ✅ |
| OpenClaw | `provider` | 读取器已取到但因注释未写入记录 | ✅（改 1 处） |
| Claude Code | 无逐条字段 | 配置：`~/.claude/settings.json` env.ANTHROPIC_BASE_URL / cc-switch 当前项 | ⚠️ 按当前配置 |
| Codex | 无逐条字段 | 配置：`~/.codex/config.toml` model_provider → base_url | ⚠️ 按当前配置 |
| Copilot / Gemini / MiniMax | 无逐条字段 | 官方登录 | ⚠️ 记官方渠道 |

### 2.3 关键差距

1. `base.aggregate_records()` 聚合键缺渠道 → 同模型跨渠道被合并。
2. `TokenUsageRecord` 唯一键缺渠道 → 同模型跨渠道**只能存一行**，后写覆盖先写。
3. `opencode_reader` 已解析 `provider` 但未输出到 `rows`。
4. `zcode_usage_reader` 的 SQL 未 `GROUP BY provider_id`。
5. `kimi_reader` 只剥 `kimi-code/` 前缀，其他前缀被当作模型名一部分。
6. `openclaw_reader` 明确注释不写 provider。
7. 缓存的查询键不含渠道 → 加筛选后会串缓存。
8. 前端无渠道筛选/饼图/分组/列。

---

## 3. 渠道定义与解析规则

### 3.1 存储与展示分离

- 数据库存**原始渠道 id**（`channel`，最长 64），保证可追溯、可改名。
- 展示名由单一注册表在 API 层计算（`channel_display_name()`），改展示名不需要重新采集。
- 未知/缺失 → `unknown` → 展示「未知渠道」。

### 3.2 注册表（新增 `backend/app/utils/token_usage_channels.py`）

```python
CHANNEL_DISPLAY = {
    "peanut": "花生 TokenProxy",
    "aliyun-bailian": "阿里云百炼",
    "opencode": "OpenCode 官方",
    "deepseek": "DeepSeek 官方",
    "alibaba-coding-plan-cn": "阿里云 Coding Plan",
    "minimax-cn-coding-plan": "MiniMax Coding Plan",
    "magpie": "Magpie 本地网关",
    "open-design": "OpenDesign",
    "kimi-code": "Kimi 官方",
    "zhipu": "智谱 GLM 官方",
    "claude-official": "Claude 官方",
    "codex-official": "Codex 官方",
    "copilot-official": "GitHub Copilot",
    "gemini-official": "Gemini 官方",
    "minimax-official": "MiniMax 官方",
    "local-gateway": "本地网关",
    "unknown": "未知渠道",
}
```

规则：
- `account:bigmodel-*` → 展示「智谱 GLM（<套餐后缀>）」
- `kimi-code-cn` / `kimi-code` → 统一显示「Kimi 官方」
- 未登记值 → 原样展示原 id（不隐藏、不猜测）
- 空值 / NULL → 「未知渠道」

### 3.3 解析优先级

```
1) 记录自带渠道（逐条精确）：
   opencode.providerID / zcode.provider_id / kimi model 前缀 / paseo.provider / openclaw.provider

2) 记录无渠道时，读该 Agent 当前配置（每次同步时解析一次）：
   claude  : ~/.claude/settings.json → env.ANTHROPIC_BASE_URL
   codex   : ~/.codex/config.toml → model_provider → model_providers.<id>.base_url
   minimax : ~/.minimax/config.yaml → base_url
   gemini  : 官方（Gemini CLI OAuth）
   copilot : 官方（GitHub 登录）

3) base_url host → 渠道 id（集中映射）：
   tokenproxy.peanuthzm.com.cn            → peanut
   *.aliyuncs.com / *.maas.aliyuncs.com   → aliyun-bailian
   api.kimi.com / api.moonshot.*          → kimi-code
   open.bigmodel.cn / api.z.ai            → zhipu
   opencode.ai                             → opencode
   api.deepseek.com                        → deepseek
   api.minimaxi.com / api.minimax.io      → minimax-official
   amr-link.open-design.ai                → open-design
   localhost / 127.0.0.1 / [::1]          → local-gateway

4) 都解析不到 → official（按 source）或 unknown
```

**已知限制（明确写入文档）**：
- Claude/Codex 没有逐条渠道，只能按**同步时**的当前配置标注；配置切换后，下一次同步窗口内的记录会整体改标为新渠道。
- 跨同步窗口之前的历史记录无法回溯，保留「未知渠道」。
- 不读取 cc-switch `usage_daily_rollups` 反推历史（避免与原生记录重复匹配，属"深入"范畴）。

---

## 4. 数据模型与迁移

### 4.1 ORM（`backend/app/models/token_usage_models.py`）

```python
channel = Column(String(64), nullable=True, index=True)
__table_args__ = (
    UniqueConstraint("user_id", "device_id", "record_date", "source", "channel", "model"),
    Index("idx_token_usage_query", "user_id", "record_date", "source", "device_id"),
    Index("idx_token_usage_dimensions", ...),
    Index("idx_token_usage_channel", "user_id", "record_date", "channel"),
)
```

### 4.2 幂等 DDL（新增 `backend/app/services/token_usage_schema.py`）

生产环境 deploy 不跑 alembic，因此必须在应用启动时幂等执行（参照 `ensure_wechat_columns`）：

PostgreSQL：
1. `ALTER TABLE token_usage_records ADD COLUMN IF NOT EXISTS channel VARCHAR(64)`
2. 查 `pg_constraint`，找到 `token_usage_records` 上**列完全等于** `(user_id, device_id, record_date, source, model)` 的唯一约束并 DROP
3. `CREATE UNIQUE INDEX IF NOT EXISTS uq_token_usage_channel_key ON token_usage_records (user_id, device_id, record_date, source, channel, model)`
4. `CREATE INDEX IF NOT EXISTS idx_token_usage_channel ON token_usage_records (user_id, record_date, channel)`

SQLite（测试/本地）：
1. `PRAGMA table_info` 判断后 `ADD COLUMN`
2. 不重建约束（测试库由 `Base.metadata.create_all` 使用新 ORM 定义）
3. 建普通索引

调用点：`backend/app/main.py` lifespan（`Base.metadata.create_all` 之后）。
另补 `backend/alembic/versions/20261121_token_usage_channel.py` 留档（部署链路未自动执行，仅作可重放记录）。

### 4.3 历史数据策略（不双计）

- **不回填历史渠道**：迁移只加列 / 换唯一约束。历史行 `channel` 保持 NULL，展示「未知渠道」。
- **同步时清理 legacy 行**：对本次同步涉及的每个 `(user_id, device_id, source, record_date)` 执行：
  ```sql
  DELETE FROM token_usage_records
  WHERE user_id=? AND device_id=? AND source=? AND record_date=? AND channel IS NULL
  ```
  再 upsert 带渠道的新行。这样：
  - 同步窗口内自动重建为带渠道数据；
  - 窗口外历史保留、不双计；
  - 重复同步幂等。
  之所以不回填：Claude/Codex 的渠道只能按**同步时**的当前配置解析，预填一个固定值会与后续同步写入的真实渠道并存 → 双计。
- 提供一次性脚本 `backend/scripts/rebuild_token_usage_channels.py`（可选执行）：强制 `days=3650` 重采集，重建本地仍保留的全部历史。

---

## 5. 采集层改造

| 文件 | 改动 |
|---|---|
| `agent_readers/base.py` | `make_record(..., channel="")`；`aggregate_records()` 聚合键 `(record_date, channel, model)`；记录保留 `channel` |
| `agent_readers/opencode_reader.py` | `rows` 输出 `channel=usage.provider`；日志统计渠道数 |
| `app/utils/zcode_usage_reader.py` | SQL 增加 `provider_id` 并 `GROUP BY record_date, provider_id, model_id`；输出 `channel`（空→`unknown`） |
| `agent_readers/kimi_reader.py` | 解析 `provider/model` 前缀：`kimi-code/` → `kimi-code`；`peanut/` → `peanut`；`magpie/` → `magpie`；同时把模型名归一为去掉前缀后的值；无前缀 → `kimi-code` |
| `agent_readers/paseo_reader.py` | `channel=provider` |
| `agent_readers/openclaw_reader.py` | `channel=provider`（移除"不进入 DB"注释） |
| `claude_reader/codex_reader/copilot_reader/minimax_reader` | 每条记录填 `channel=_resolve_config_channel(source)`（启动/同步时缓存一次） |
| `services/token_usage_sync_service.py` | `_upsert_records` 查询键与变更检测加入 `channel`；新增 legacy NULL 行清理；`source_raw` 保持不变 |
| `utils/token_usage_channels.py`（新增） | 注册表 + `normalize_channel()` + `channel_display_name()` + `resolve_config_channel()` + host 映射 |

约束：
- 渠道解析**只在一处**（`token_usage_channels.py`），读取器不得各写一套映射。
- 配置读取失败 → 记 `unknown` + warning 日志，不阻断同步。
- 不在读取器里写死路径：统一走 `real_home()` / `expand_user_path()`。

---

## 6. 聚合与 API 改造（`backend/app/routes/token_usage.py`）

### 6.1 请求/响应模型

- `SummaryRequest` / `DetailsRequest` / `DbQueryRequest` 增加 `channel: Optional[str]`
- `DbUsageItem` 增加 `channel: Optional[str]`、`channel_name: Optional[str]`
- `ModelSummaryItem` 增加 `channel` / `channel_name`
- `DimensionSummaryItem` 增加 `channel` / `channel_name`
- `DimensionSummaries` 增加 `channels: list[DimensionSummaryItem]`
- `FilterOptions` 增加 `channels: list[ChannelFilterOption]`

### 6.2 查询与聚合

- `_build_record_filters()`：`channel` 精确过滤（支持值为空表示全部）
- `_query_dimension_data()`：新增 channel 维度聚合（`GROUP BY channel`），其余三个维度不变
- `_execute_model_summary_query()`：`GROUP BY source, channel, model`
- `_rows_to_model_summary()`：输出渠道 + 展示名
- `_build_dimension_data()`（旧 `/query` 兼容路径）：新增 channel 桶与 filter_options
- `build_chart_series()`：支持 `group_by="channel"`
- `/details`：每行填 `channel`/`channel_name`；`group_by=channel` 时 `group_key=channel`
- 总览 `summary` 口径不变（四桶之和），渠道维度仅做拆分，不改变总量

### 6.3 缓存（`backend/app/services/token_usage_cache.py`）

- `_build_query_cache_key()` 增加 `channel` 段
- `get_query_cached_payload` / `set_query_cached_data` 所有调用点透传
- `warm_query_cache()` 的 `req` 增加 `channel=None`
- `/summary`、`/details` 缓存读写与失效逻辑同步

---

## 7. 前端 PC（`frontend/src/components/Tools/TokenUsage.tsx` 等）

- `api/tokenUsageApi.ts`：
  - `TokenUsageGroupBy` 增加 `'channel'`
  - `DbQueryParams` / `TokenUsageDetailsParams` 增加 `channel`
  - `DbUsageItem` / `DimensionSummaryItem` / `DimensionSummaries` / `FilterOptions` / `ModelSummaryItem` 增加渠道字段
- `TokenUsage.tsx`：
  - 筛选区新增「渠道」下拉（选项来自 `filter_options.channels`）
  - 新增第 4 张渠道饼图 `DimensionPieCard`，点击联动筛选
  - 分组下拉新增「按渠道对比」
  - 明细表新增「渠道」列（显示展示名，title 显示原始 id）
  - CSV 导出新增「渠道」列
  - 图表标题：`groupBy === 'channel' ? '渠道消耗对比'`
  - 保留现有防抖/轮询逻辑，禁止整页刷新
- hooks：`useTokenUsageSummary` / `useTokenUsageDetails` 透传 `channel`

---

## 8. 小程序兼容

- `mini-program/src/services/tokenUsage.ts`：`DetailItem` 增加可选 `channel` / `channel_name`；`summary` 请求可选 `channel`
- 页面暂不改 UI（新增字段向后兼容）；后续可加渠道筛选

---

## 9. 任务清单

### 阶段 A：模型与迁移
- [ ] A1 ORM 增加 `channel` 列、唯一键、索引
- [ ] A2 新增 `token_usage_schema.py` 幂等 DDL（PG 换约束 / SQLite 补列）
- [ ] A3 `main.py` lifespan 调用
- [ ] A4 新增 alembic 留档迁移
- [ ] A5 无渠道源历史回填 + 有渠道源 legacy 清理策略落库

### 阶段 B：采集
- [ ] B1 新增 `token_usage_channels.py`（注册表 / host 映射 / 配置解析）
- [ ] B2 `base.py` 聚合键加渠道
- [ ] B3 `opencode_reader.py` 输出 provider
- [ ] B4 `zcode_usage_reader.py` 按 provider_id 拆分
- [ ] B5 `kimi_reader.py` 前缀解析
- [ ] B6 `paseo_reader.py` / `openclaw_reader.py` 输出 provider
- [ ] B7 claude/codex/copilot/minimax 官方或配置渠道
- [ ] B8 `_upsert_records` 唯一键 + legacy 清理

### 阶段 C：API
- [ ] C1 请求/响应模型加渠道
- [ ] C2 `_build_record_filters` 渠道过滤
- [ ] C3 维度聚合新增 channels + filter_options.channels
- [ ] C4 模型汇总按渠道拆分
- [ ] C5 图表 `group_by=channel`
- [ ] C6 `/details` 行级渠道 + group_by
- [ ] C7 旧 `/query` 路径同步
- [ ] C8 缓存键与预热加渠道

### 阶段 D：前端
- [ ] D1 API 类型与参数
- [ ] D2 渠道筛选 + 饼图 + 分组 + 明细列 + CSV
- [ ] D3 hooks 透传

### 阶段 E：小程序
- [ ] E1 类型兼容（可选筛选）

### 阶段 F：测试与验收
- [ ] F1 读取器单测（opencode / zcode / kimi / openclaw / paseo）
- [ ] F2 `aggregate_records` 渠道分桶单测
- [ ] F3 同步唯一键 / legacy 清理 / 幂等单测
- [ ] F4 维度与 API 单测（summary / details / filter_options / cache key）
- [ ] F5 数据一致性核对（`Σchannel == 总量`，改造前后总量一致）
- [ ] F6 浏览器验收（1440 / 768 / 390，筛选/饼图/分组/列/CSV）
- [ ] F7 部署后核验产物与服务器行为

---

## 10. 测试与验收标准

必须满足（缺一不可）：

1. **总量不变**：改造前后同一时间范围的总 Token / 总成本差异为 0（渠道只做拆分）。
2. **渠道守恒**：`Σ channels.total_tokens == summary.total_tokens`，`Σ channels.total_cost == summary.total_cost`。
3. **同模型跨渠道不丢**：构造 opencode 同 (日期, 模型) 两个 provider，入库为两行、汇总为两个渠道。
4. **幂等**：同一同步重复执行，记录数不增长。
5. **历史不双计**：legacy NULL 行在同 (日期, 源) 重同步后被替换，不产生重复总量。
6. **筛选正确**：按渠道筛选后，明细/汇总/图表/饼图一致。
7. **缓存正确**：不同 channel 参数不串缓存。
8. **浏览器验收**：真实走通筛选、饼图联动、分组、明细、CSV，Console 无新增错误。

---

## 11. 风险与限制

| 风险 | 处置 |
|---|---|
| PG 唯一约束名不固定，DROP 失败 | 通过 `pg_constraint` 按列集合查找；找不到则记录 warning 并继续建唯一索引；测试覆盖该分支 |
| 历史数据双计 | 同步前按 `(user, device, source, date)` 删 NULL 行；总量对账校验 |
| Claude/Codex 只能按当前配置归渠道 | 文档明示；历史无法回溯的显示「未知渠道」 |
| `peanut` 内多模型厂商无法拆分 | 按用户要求不拆，统一记 `peanut` |
| 渠道 id 改名 | 原始 id 入库，展示名集中注册表；改名无需重采集 |
| 缓存串号 | 缓存键加 channel 段，单测覆盖 |
| 小程序旧版本 | 新增字段均可选，向后兼容 |

---

## 12. 明确不做

- 不拆分 `peanut` / `magpie` 等聚合网关的上游真实账号。
- 不为 Claude/Codex 回溯历史配置（不做 cc-switch rollup 反推）。
- 不做渠道手工重命名 UI（本期用注册表）。
- 不改变现有 Token 四桶 / total 口径。
- 不新增数据来源，不引入 cc-switch 用量表参与统计。

---

## 13. 实施与验收结果（2026-11-21）

已实现文件：

- 数据模型 / 迁移：`backend/app/models/token_usage_models.py`、`backend/app/services/token_usage_schema.py`、`backend/app/main.py`、`backend/alembic/versions/20261121_token_usage_channel.py`
- 渠道解析：`backend/app/utils/token_usage_channels.py`
- 采集：`agent_readers/base.py`、`opencode_reader.py`、`kimi_reader.py`、`paseo_reader.py`、`openclaw_reader.py`、`app/utils/zcode_usage_reader.py`
- 同步：`backend/app/services/token_usage_sync_service.py`
- 接口 / 缓存：`backend/app/routes/token_usage.py`、`backend/app/services/token_usage_cache.py`
- 前端：`frontend/src/api/tokenUsageApi.ts`、`frontend/src/components/Tools/TokenUsage.tsx`、`frontend/src/components/Tools/hooks/useTokenUsage{Summary,Details}.ts`
- 小程序：`mini-program/src/services/tokenUsage.ts`
- 维护脚本：`backend/scripts/rebuild_token_usage_channels.py`
- 测试：`backend/tests/test_token_usage_channels.py`

实测结果：

- PG 启动迁移成功：旧 5 列唯一约束已删除，`uq_token_usage_channel_key` 已创建。
- 渠道分布（本机真实数据）：OpenCode `peanut/opencode/aliyun-bailian/magpie/minimax-cn-coding-plan`；ZCode `account:bigmodel-* / kimi-code / new-provider`；Kimi `kimi-code / peanut`；Claude/Codex 由 cc-switch 当前配置解析为 `open-design`。
- 同用户内不存在「NULL + 渠道」同 (date, model) 双行（跨用户同 device 的查询假阳性已排除）。
- 渠道维度合计与总 Token 一致（UI 实测 11 个渠道合计 505.5亿 = 顶栏总量）。
- 缓存键已含渠道：`...:all-models:all-channels:date:desc` 与 `...:peanut:...` 分流。
- 浏览器验收（1440/1000、768/900、390/844）：渠道筛选、渠道饼图、按渠道分组、明细渠道列、CSV 导出均可用；三档均无页面级横向溢出；明细表在窄屏内横向滚动（预期）。
- 单测：`test_token_usage_channels.py` 11 passed；token-usage / reader 相关 181 passed；4 个失败均为 Windows 环境既有问题（2 个路径分隔符断言、2 个 symlink 权限），与本次改动无关。