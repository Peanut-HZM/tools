# 修复 OpenCode 数据丢失 — 设计文档

> 日期：2026-06-05
> 状态：草案 → 待 review
> 作者：Sisyphus (brainstorming → writing-plans → implementation 流程)

## 背景

### 用户报告

token-usage 页面的"明细数据"表的"工具"列只显示 **Claude Code**，但用户同时在使用 OpenCode（基于 `ccusage-opencode` + `opencode-usage` 两个 CLI 工具统计），理应有 OpenCode 数据。

### Root Cause（双重 Bug）

**前置事实**：opencode-usage CLI 与 ccusage-opencode CLI 输出格式**完全不同**，但当前 `_parse_opencode_entries` **仅适配 ccusage-opencode**，opencode-usage 路径上 parser 的输入是错配的。

**Bug 1 — `backend/app/utils/usage_fetcher.py:230`**

`opencode-usage run` 的 `--by` 参数支持 `{model, agent, provider, session, day}`，其中 `day` 才是按日期分组。但当前代码默认传了 `--by=model`，导致：

- 返回的 `rows` 数组里每条记录 `label` 是**模型名**（`"minimax-m3-free"`），不是日期
- 实际验证（`opencode-usage run --json --days=3 --by=model`）：

  ```json
  {"label": "minimax-m3-free", "calls": 1147, "tokens": {...}, "cost": 0}
  ```

- `_parse_opencode_entries` 把 `"minimax-m3-free"` 当日期字符串解析 → `_parse_date` 返回 None → 整条被跳过

**Bug 2 — `_parse_opencode_entries` 错配 opencode-usage 格式**

即使 Bug 1 改为 `--by=day`，opencode-usage 返回的 JSON 是 **snake_case 嵌套结构**：

```json
{
  "label": "2026-06-05",
  "calls": 479,
  "tokens": {
    "input": 2459951,
    "output": 243833,
    "reasoning": 0,
    "cache_read": 58837404,
    "cache_write": 1616736,
    "total": 63157924
  },
  "cost": 0
}
```

但当前 parser（`token_usage_sync_service.py:191-208`）的 fallback 分支读的是 **camelCase 顶层**字段（`entry.inputTokens`、`entry.outputTokens`）— 这是给 **ccusage-opencode daily** 格式设计的。opencode-usage 走到 fallback 分支时，所有 4 个 token 字段全读不到，total 回退为 0。

另外发现：`tokens.reasoning` 字段在 opencode-usage `--by=day` 输出中存在，但 DB schema 没有该字段（应忽略）。

### 触发链

1. `sync_token_usage` 调 `_fetch_opencode_merged` → 调 `_fetch_opencode_current(days=90)`（opencode-usage，line 271 配对）
2. `_fetch_opencode_current` 默认 `--by=model`（**Bug 1**）
3. 返回的 rows 全部是模型聚合，`label="minimax-m3-free"`
4. `_parse_opencode_entries` 拿 "minimax-m3-free" 去 `_parse_date` → None → 跳过（**Bug 1 副作用**）
5. 即使把 `--by` 改成 `day`，rows 是日期聚合，但 parser 的 fallback 分支读 `entry.inputTokens`（camelCase 顶层）→ 全 None → 4 token 字段为 0（**Bug 2**）
6. 总计 0 条入库 → sync_log 记 success → 前端永远看不到新数据

### 现状证据

| 检查项 | 结果 |
|---|---|
| `_parse_opencode_entries` 现有 callers | grep 全工程只有 `sync_token_usage`（line 271）一处 |
| 现有测试 | `tests/test_token_usage_*.py` 6 个文件（freshness/dimensions/split_cache/split_api/background_sync/split_integration），**无 `_parse_opencode_entries` 直接单测** |
| 现有 parser 的 `models` 分支 | 适配 **ccusage-opencode daily** 的 `models: [{modelName, inputTokens, ...}]` 子列表格式 |
| 现有 parser 的 fallback 分支 | 适配 **ccusage-opencode daily** 的 camelCase 顶层字段 |
| opencode-usage 实际 `--by=day` 输出 | `entry.tokens.input/output/cache_read/cache_write/total`（snake_case 嵌套） |
| opencode-usage 实际 `--by=model` 输出 | `entry.label = "minimax-m3-free"`（非日期） |

### 证据

| 检查项 | 结果 |
|---|---|
| PostgreSQL `token_usage_records` WHERE `source='opencode'` | 34 条，最新 2026-02-27（3 个多月前） |
| PostgreSQL `token_usage_records` WHERE `source='claude'` | 217 条，最新 2026-06-05（正常） |
| `opencode-usage run --json --days=7 --by=day` 实际输出 | 1636 calls / 215M tokens（数据丰富） |
| backend log | `[opencode] 同步 0 条记录到数据库` 反复出现，状态 success |
| 3 个 CLI 工具是否安装 | ccusage / opencode-usage / ccusage-opencode 全部已安装 |
| `_DESKTOP_MODE` env | 未设置（不是 desktop guard 触发） |

### 历史 34 条数据来源

3 月前的数据来自 **ccusage-opencode daily**，返回结构是 `{daily: [{date, inputTokens, ...}]}`，与 `_parse_opencode_entries` 期望完全匹配。但因为 `model='_total'` 聚合，**模型明细全部丢失**（不在本次修复范围）。

---

## 目标

修复 opencode 数据无法同步的 Bug，让前端"明细数据"表能正确显示 Claude Code 和 OpenCode 两类记录。

## 非目标

- 不做历史数据回填（3 月前的 34 条 _total 记录保留；如需回填，作为单独 follow-up）
- 不改 ccusage-opencode 的 `_total` 聚合行为（保持一致）
- 不改 API endpoint、不改前端、不改数据库 schema
- 不改 `_DESKTOP_MODE` guard 逻辑

---

## 修复设计

### 修改 1：`backend/app/utils/usage_fetcher.py`

**第 226 行附近**（含 Windows 路径 222-224）：

```python
# 修改前
cmd = ["opencode-usage", "run", "--json", f"--days={days}"]
if by:
    cmd.append(f"--by={by}")
else:
    cmd.append("--by=model")

# 修改后
cmd = ["opencode-usage", "run", "--json", f"--days={days}"]
if by:
    cmd.append(f"--by={by}")
else:
    cmd.append("--by=day")
```

**为什么是 `day` 而不是 `model`**：

- `opencode-usage run --help` 列出 `--by {model,agent,provider,session,day}`，`day` 才是按日期
- 同步逻辑按日期分组入库（`record_date` 字段），需要 daily 粒度
- `model` 粒度数据无法按日期对齐，且会丢失日期信息

### 修改 2：`backend/app/services/token_usage_sync_service.py:179-229` `_parse_opencode_entries`

**保留** ccusage-opencode daily 格式处理（line 191-208 fallback 分支 + line 210-228 `models` 子列表分支），**新增** opencode-usage `--by=day` snake_case 嵌套 `tokens` 处理路径：

```python
def _parse_opencode_entries(entries: list[dict]) -> list[dict]:
    """解析 OpenCode CLI 输出为结构化数据

    支持三种数据源格式（按优先级自动识别）：
    1. opencode-usage --by=day:   {label: "YYYY-MM-DD", tokens: {input, output, cache_read, cache_write, total, reasoning}, cost}
    2. ccusage-opencode daily:    {date, inputTokens, outputTokens, ...}（camelCase 顶层）
    3. ccusage-opencode models 子列表: {date, models: [{modelName, inputTokens, ...}]}
    """
    results = []
    for entry in entries:
        # 双格式兼容：ccusage-opencode 用 date，opencode-usage 用 label
        date_val = entry.get("date") or entry.get("label") or ""
        record_date = _parse_date(date_val)
        if not record_date:
            # label 不是有效日期时跳过（如 opencode-usage --by=model 的模型名）
            continue

        # 路径 A: opencode-usage --by=day 格式（snake_case 嵌套 tokens）
        tokens_obj = entry.get("tokens")
        if isinstance(tokens_obj, dict):
            input_tokens = _safe_int(tokens_obj, "input")
            output_tokens = _safe_int(tokens_obj, "output")
            cache_creation_tokens = _safe_int(tokens_obj, "cache_write")
            cache_read_tokens = _safe_int(tokens_obj, "cache_read")
            total_tokens = _safe_int(tokens_obj, "total")
            total_cost = _safe_float(entry, "cost")
            # opencode-usage --by=day 不暴露每日+模型维度，强制 _total
            model_name = "_total"
            results.append({...})  # 1 条 record
            continue

        # 路径 B: ccusage-opencode models 子列表（保留现有逻辑）
        models = entry.get("models", [])
        if models:
            for mod in models:
                # 现有 line 210-228 逻辑保持不变
                ...
            continue

        # 路径 C: ccusage-opencode daily 顶层字段（保留现有逻辑）
        # 现有 line 191-208 逻辑保持不变
        ...
    return results
```

**关键决策**：
- **保留** ccusage-opencode 路径 B 和 C 不动（这些字段映射正确，34 条历史数据已用此路径）
- **新增** opencode-usage 路径 A 为优先路径（`isinstance(tokens_obj, dict)`）
- **保留** `model='_total'` 行为（opencode-usage `--by=day` 不暴露每日+模型维度；CLI 不支持）
- **忽略** `tokens.reasoning`（DB schema 无此字段，如需后续支持则需 DB 迁移）

### 修改 3：日志增强（可选，但建议）

**`backend/app/services/token_usage_sync_service.py` 第 281 行附近**：

```python
# 修改前
count = _upsert_records(db, ...)
logger.info(f"[opencode] 同步 {count} 条记录到数据库")

# 修改后
count = _upsert_records(db, ...)
if count == 0:
    logger.warning(f"[opencode] 同步 0 条记录到数据库（请检查 CLI 输出和 parser 字段映射）")
else:
    logger.info(f"[opencode] 同步 {count} 条记录到数据库")
```

**为什么**：现有 `INFO` 级别 + records_count=0 反复出现，让"同步失败"看起来"成功"，难以发现新 bug。

---

## 字段映射表

| DB Column | opencode-usage `--by=day` | ccusage-opencode `daily` |
|---|---|---|
| `record_date` | `entry.label` | `entry.date` |
| `model` | `"_total"`（CLI 不支持每日+模型） | 优先 `mod.modelName`（models 子列表），否则 `"_total"` |
| `input_tokens` | `entry.tokens.input` | `entry.inputTokens`（顶层）或 `mod.inputTokens`（子列表） |
| `output_tokens` | `entry.tokens.output` | `entry.outputTokens`（顶层）或 `mod.outputTokens`（子列表） |
| `cache_creation_tokens` | `entry.tokens.cache_write` | `entry.cacheCreationTokens`（顶层）或 `mod.cacheCreationTokens`（子列表） |
| `cache_read_tokens` | `entry.tokens.cache_read` | `entry.cacheReadTokens`（顶层）或 `mod.cacheReadTokens`（子列表） |
| `total_tokens` | `entry.tokens.total`（0 时 4 字段求和） | `entry.totalTokens`（0 时 4 字段求和） |
| `total_cost` | `entry.cost` | `entry.totalCost` |
| `source` | `"opencode"` | `"opencode"` |
| `source_raw` | `"opencode-usage"` | `"ccusage-opencode"` |
| `tool_id` | `"opencode"` | `"opencode"` |
| `tool_name` | `"OpenCode"` | `"OpenCode"` |
| 忽略 | `entry.tokens.reasoning`（DB 无此字段） | `entry.modelsUsed`（字符串列表，无 token 数值） |

---

## 边界与错误处理

| 场景 | 行为 | 状态 |
|---|---|---|
| opencode-usage CLI 未安装 | 返回 `{"error": "CLI 未安装: opencode-usage"}`，跳过 | 已有，不改 |
| opencode-usage CLI 调用失败（非 bun 错误） | 返回 `{"error": stderr}`，跳过 | 已有，不改 |
| opencode-usage 报 bun 协议错误 | 返回 `{"error": "opencode-usage 需要 bun 运行时，当前环境不支持"}`，跳过 | 已有，不改 |
| `_DESKTOP_MODE=1` 环境 | 返回 `{"error": "Token Usage CLI 功能在桌面模式下不可用"}`，跳过 | 已有，不改 |
| rows 为空数组 | 0 条入库 + WARNING 日志 | 修改后 |
| label 不是有效日期（如 `"minimax-m3-free"`） | 跳过该 entry | 已有（`_parse_date` 失败） |
| `entry.tokens` 缺失或非 dict | 走 ccusage-opencode 分支，token 全 0 | 修改后兼容 |
| 唯一约束冲突（user+device+date+source+model） | `_upsert_records` UPDATE 已有记录 | 已有，不改 |

---

## 测试策略

### 单元测试 — `backend/tests/services/test_token_usage_sync_service.py`

新增 4 个测试用例：

1. `test_parse_opencode_entries_with_ccusage_opencode_format`
   - 样本：`{"date": "2026-01-23", "inputTokens": 137167, "outputTokens": 1226, "totalTokens": 216921, "totalCost": 0.0125916}`
   - 期望：1 条 record, `record_date=2026-01-23`, `model="_total"`, tokens 正确

2. `test_parse_opencode_entries_with_opencode_usage_by_day`
   - 样本：`{"label": "2026-06-05", "tokens": {"input": 2312238, "output": 224119, "cache_write": 1616736, "cache_read": 57855517, "total": 62008610}, "cost": 0}`
   - 期望：1 条 record, `record_date=2026-06-05`, `model="_total"`, `input_tokens=2312238`, `cache_creation_tokens=1616736`

3. `test_parse_opencode_entries_with_empty_rows`
   - 样本：`[]`
   - 期望：返回 `[]`

4. `test_parse_opencode_entries_with_invalid_date_label`
   - 样本：`[{"label": "minimax-m3-free", "tokens": {...}}]`（--by=model 异常残留）
   - 期望：跳过（`record_date` 为 None）

### 集成测试 — `backend/tests/utils/test_usage_fetcher.py`（如不存在则新建）

新增 1 个测试：

5. `test_fetch_opencode_merged_uses_by_day`
   - Mock `subprocess.run` 返回 opencode-usage 真实 JSON
   - 调用 `_fetch_opencode_merged(days=7)`
   - 验证 `cmd` 包含 `--by=day`（断言 `mock.call_args`）

### E2E 验证（手动）

6. 触发同步
   - 浏览器调 `POST http://localhost:19092/api/token-usage/refresh`
   - 或等待 30 分钟自动同步

7. 数据库验证
   ```sql
   SELECT COUNT(*), MIN(record_date), MAX(record_date)
   FROM token_usage_records
   WHERE source='opencode' AND record_date >= '2026-06-01';
   ```
   - 期望：count > 0，max(record_date) = 今天

8. 前端验证
   - 刷新 http://localhost:5178/tools/token-usage
   - 明细表应同时显示 Claude Code 和 OpenCode 行

---

## 验收标准

- [ ] 后端 `usage_fetcher.py` 默认调用 `opencode-usage run --by=day`（含 Windows 路径 line 224）
- [ ] `_parse_opencode_entries` 三路径并存：opencode-usage 嵌套 `tokens`（新增）+ ccusage-opencode `models` 子列表（保留）+ ccusage-opencode 顶层字段（保留）
- [ ] 4 个新单元测试 + 1 个集成测试全部通过
- [ ] 现有 6 个 `test_token_usage_*.py` 测试不破坏（freshness/dimensions/split_cache/split_api/background_sync/split_integration）
- [ ] 手动触发同步后，PostgreSQL 中 `WHERE source='opencode' AND record_date >= '2026-06-01'` 返回 > 0 行
- [ ] 前端明细表同时显示 Claude Code 和 OpenCode 行
- [ ] 0 条同步时降为 WARNING 日志
- [ ] 不破坏 ccusage（claude）数据流
- [ ] 不修改 API endpoint / 前端代码 / 数据库 schema
- [ ] **不自动 commit**（CLAUDE.md 禁止，由用户显式触发）

---

## 风险与回滚

| 风险 | 缓解 |
|---|---|
| 改 `--by=day` 后 ccusage-opencode 合并逻辑仍正确 | 单元测试覆盖两种 JSON 样本；现有 34 条历史数据不会回写（已存在则 update） |
| `_parse_opencode_entries` 改动影响其他 caller | grep 全文只有 `sync_token_usage` 一处调用 |
| 字段映射遗漏 | 4 个 token 字段 + cost 全部单独测试 |

**回滚**：`git revert` 1 个 commit 即可（所有改动在 1-2 个文件内）。

---

## 实施 Task 列表（待 writing-plans skill 输出详细 plan）

- Task 1: 修复 `usage_fetcher.py:226`（改 `--by=day`）
- Task 2: 重构 `_parse_opencode_entries`（双解析路径）
- Task 3: 增强日志（0 条 → WARNING）
- Task 4: 添加 4 单元测试 + 1 集成测试
- Task 5: 手动 E2E 验证（触发同步 + DB 验证 + 前端截图）
- Task 6: 提交（feat(backend): 修复 opencode 数据丢失 bug）
