# 重构 Token-Usage 统计为 ccusage 统一数据源 — 设计文档

> 日期：2026-06-05
> 状态：草案 → 待 review
> 作者：Sisyphus (brainstorming → writing-plans → implementation 流程)
> **作废关系**：本文档取代 `2026-06-05-opencode-data-flow-fix-design.md`（基于多 CLI 源的旧方案）

## 背景

### 用户原话

> "需要调整计划，直接使用 ccusage 来统计所有的 Agent 使用的 token 的消耗，不需要使用其他的 ccusage-opencode 和 opencode-usage 了，ccusage 就可以统计所有的，直接使用这个就可以了，现在统计的结果如图所示（ccusage 输出截图，含 Claude / OpenCode / OpenClaw 多 agent 层级表）。需要把这块的统计重构一下，而且历史日期的统计之后，直接保存入库，每次只需统计当天的，更新当天的数据即可，这样页面加载也更快了，性能也更优了"

### 旧方案的痛点

1. **多 CLI 源错配**：旧 spec 用 `ccusage-opencode` + `opencode-usage` 两个 CLI 拼凑，字段格式不一致，存在双 bug（已发现的 `--by=model` 错配 + parser 错配）。
2. **ccusage 自身就是统一源**：v20.0.6 已支持 15+ agent（claude / opencode / openclaw / codex / droid / gemini / ...），单次 `ccusage daily --json` 能列出所有 agent 的当日聚合。
3. **页面查询无缓存**：旧实现每次页面查询都触发 CLI 调用，loading 慢。
4. **历史数据不持久**：只有当日 30 分钟窗口缓存，无 DB 历史。

### ccusage 实际 JSON 结构（关键发现）

**`ccusage daily --json --since X --until Y`**：

```json
{
  "daily": [
    {
      "agent": "all",
      "period": "2026-06-05",
      "inputTokens": 220537565,
      "outputTokens": 539674,
      "cacheCreationTokens": 7682840,
      "cacheReadTokens": 104991445,
      "totalTokens": 333751524,
      "totalCost": 1092.948226999999,
      "modelsUsed": ["claude-opus-4-6", "claude-opus-4-8", "gpt-5.5", "qwen3.6-plus", "deepseek-v4-pro", "minimax-m3-free"],
      "modelBreakdowns": [
        {"modelName": "claude-opus-4-8", "inputTokens": 215984263, "outputTokens": 213810, "cacheCreationTokens": 0, "cacheReadTokens": 0, "cost": 1085.26},
        {"modelName": "gpt-5.5", "inputTokens": 1341214, "outputTokens": 13184, "cacheCreationTokens": 0, "cacheReadTokens": 589824, "cost": 7.40},
        ...
      ],
      "metadata": {"agents": ["claude", "opencode"]}
    }
  ],
  "totals": {...}
}
```

**`ccusage <agent> daily --json --since X --until Y`**（以 opencode 为例）：

```json
{
  "daily": [
    {
      "date": "2026-06-05",
      "inputTokens": 2505712,
      "outputTokens": 268252,
      "cacheCreationTokens": 1616736,
      "cacheReadTokens": 61139668,
      "totalTokens": 65530368,
      "totalCost": 0.0,
      "modelsUsed": ["minimax-m3-free", "qwen3.6-plus"]
    }
  ],
  "totals": {...}
}
```

**关键限制**：
- `ccusage daily` 的 `modelBreakdowns` 包含**每模型 cost**（最精确），但**没有 agent 归属**
- `ccusage <agent> daily` 的 `modelsUsed` 包含**当日该 agent 用了哪些模型**（用于归属字典），但**没有 per-model 拆分**
- 同一模型名（如 `qwen3.6-plus`）在同日可能出现在多个 agent 的 `modelsUsed` 中（截图 2026-06-01 证据）— 需要 tie-breaker 规则

### 现状

| 检查项 | 状态 |
|---|---|
| `ccusage` CLI 版本 | 20.0.6（已安装）|
| `ccusage-opencode` / `opencode-usage` | 已安装但本设计不再使用 |
| 后端 APScheduler | **无**（grep `scheduler/apscheduler/cron` 无结果）— 需新增 |
| `token_usage_records` 表 | 251 条（opencode 34 + claude 217），schema 兼容 |
| 唯一约束 | `(user_id, device_id, record_date, source, model)` |
| Schema 字段 | 已含 `tool_id` / `tool_name` / `model_display_name` / `source_raw` — 足够支撑新设计 |
| 旧 `ccusage-opencode` 跑出的 34 条 opencode 记录（2026-01-23~02-27）| 会被新 ccusage 同步自然覆盖（upsert 唯一键匹配） |

---

## 目标

1. 用单一 `ccusage` CLI 替换 `ccusage-opencode` + `opencode-usage`
2. 数据库存储 **(date, agent, model) 三元组**（一行一三元组）
3. 后台定时同步 + 前端手动同步双触发
4. 首次全量回填，后续每天增量同步当天
5. 页面查询走纯 DB（不调 CLI），加载快

## 非目标

- 不改 token-usage 页面前端 UI（明细表 / 4 饼图 / 工具筛选 等）
- 不改 API endpoint 路径（除新增 1 个手动同步端点）
- 不改 DB schema（现有字段已够用）
- 不支持实时秒级同步（只支持日级）
- 不改 ccusage 本身
- 不改 `_upsert_records` 实现（已正确的 upsert 逻辑）

---

## 设计

### 架构 & 数据流

```
┌──────────────────┐
│  APScheduler     │  每天 00:05 触发
│  daily_sync_job  │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────┐
│ sync_token_usage_v2 (refactored) │
│   ├─ 后台任务：拉取当天 ccusage  │
│   └─ 手动任务：拉取指定日期范围  │
└────────┬─────────────────────────┘
         │ 1× N+1 次 CLI 调用（N=当日 active agent 数，N≤5）
         ▼
┌──────────────────────────────────────────────┐
│ UsageFetcherV2                                │
│  _fetch_ccusage_daily(since, until)           │
│  _fetch_ccusage_<agent>_daily(since, until)   │  ← 动态按 metadata.agents 调用
└────────┬─────────────────────────────────────┘
         │ JSON
         ▼
┌──────────────────────────────────────┐
│ _parse_ccusage_records               │
│  - 读 modelBreakdowns（带 cost）     │
│  - agent 归属从 per-agent modelsUsed │
│    字典推断                          │
│  - 写 N 条 (date, agent, model)      │
└────────┬─────────────────────────────┘
         │ dict 列表
         ▼
┌──────────────────────────────────────┐
│ _upsert_records (现有，不动)         │
│  ON CONFLICT (user_id, device_id,    │
│  record_date, source, model)         │
│  DO UPDATE                          │
└────────┬─────────────────────────────┘
         │ SQL
         ▼
   PostgreSQL token_usage_records
```

**前端触发**（手动）：

```
[Token Usage 页面] → 点击"同步"按钮 → POST /api/token-usage/refresh-ccusage
                                              │
                                              ▼
                                        后端调 sync_token_usage_v2(当天)
                                              │
                                              ▼
                                        同步完成后返 200 + 同步条数
                                              │
                                              ▼
                                        前端 refetch 明细表
```

### 新增 / 修改文件

| 文件 | 类型 | 职责 |
|---|---|---|
| `backend/app/utils/usage_fetcher_v2.py` | **新增** | ccusage 统一调用层，替代 `_fetch_opencode_current` / `_fetch_opencode_legacy` |
| `backend/app/services/token_usage_sync_service.py` | **重构** | `_parse_opencode_entries` → `_parse_ccusage_records`；新增 `_infer_agent` 函数 |
| `backend/app/services/ccusage_scheduler.py` | **新增** | APScheduler 启动 + `daily_sync_job` + asyncio.Lock 串行化 |
| `backend/app/main.py` | **修改** | 启动时 `init_scheduler()`（含 DESKTOP_MODE 短路） |
| `backend/app/routes/token_usage.py` | **修改** | 新增 `POST /api/token-usage/refresh-ccusage` 端点 |
| `backend/scripts/backfill_ccusage.py` | **新增** | 一次性回填 CLI 脚本（部署时跑一次）|
| `frontend/src/components/Tools/TokenUsage.tsx` | **修改** | 加"同步"按钮，调新端点 |
| `backend/requirements.txt` | **修改** | 加 `apscheduler>=3.10,<4.0` |
| `backend/tests/test_parse_ccusage_records.py` | **新增** | 6 个单元测试 |
| `backend/tests/test_usage_fetcher_v2.py` | **新增** | 2 个集成测试（mock subprocess）|

**废弃但保留兼容**（避免破坏性变更）：
- `_fetch_opencode_current` / `_fetch_opencode_legacy` 函数保留为 alias（标记 deprecated），暂不删
- 旧的 `_parse_opencode_entries` 函数 alias 到 `_parse_ccusage_records`
- `ccusage-opencode` / `opencode-usage` 不再调用，但 CLI 不卸载

### 字段映射

| DB Column | ccusage daily `modelBreakdowns[i]` | ccusage `<agent> daily` `daily[i]`（agent 归属用）|
|---|---|---|
| `record_date` | `period` | `date` |
| `source` | **agent 名**（`claude` / `opencode` / `openclaw` / ...） | 同左（用于归属字典 key） |
| `tool_id` | 同 source | 同左（冗余，与 source 保持一致） |
| `tool_name` | agent 显示名（`Claude Code` / `OpenCode` / ...） | 同左 |
| `model` | `modelName` | `modelsUsed[i]`（仅做归属字典的值）|
| `input_tokens` | `inputTokens` | 不用 |
| `output_tokens` | `outputTokens` | 不用 |
| `cache_creation_tokens` | `cacheCreationTokens` | 不用 |
| `cache_read_tokens` | `cacheReadTokens` | 不用 |
| `total_tokens` | 4 字段求和 | 不用 |
| `total_cost` | `cost` | 不用 |
| `model_display_name` | `modelName` | 不用 |
| `source_raw` | `"ccusage-daily"`（标识 CLI 来源，非 agent） | 不用 |
| `device_name` | 当前设备名 | 同左 |

**`source` 字段语义说明**（重要）：
- `source` = **agent 标识**（哪个 CLI agent 产生的），不是"哪个数据采集工具"
- 值集合：`{'claude', 'opencode', 'openclaw', 'codex', 'amp', 'droid', ...}`
- **与前端 `TokenUsage.tsx:514` 的硬编码 label 映射保持兼容**（`source === 'claude' ? 'Claude' : source === 'opencode' ? 'OpenCode' : ...`）
- **与后端 `routes/token_usage.py:1029` 的 `TokenUsageRecord.source == req.source` 查询兼容**
- 旧 34+217 条记录（`source='claude'`/`'opencode'`）**天然被新数据 upsert 覆盖**（唯一键匹配）
- `source_raw` = CLI 工具标识（本设计中统一填 `"ccusage-daily"`），用于审计/排错，不参与查询过滤

**Tool ID → Tool Name 映射**（硬编码）：

| tool_id | tool_name |
|---|---|
| `claude` | `Claude Code` |
| `opencode` | `OpenCode` |
| `openclaw` | `OpenClaw` |
| `codex` | `Codex` |
| `amp` | `Amp` |
| `droid` | `Droid` |
| `codebuff` | `Codebuff` |
| `hermes` | `Hermes` |
| `pi` | `pi` |
| `goose` | `Goose` |
| `kilo` | `Kilo` |
| `copilot` | `GitHub Copilot` |
| `gemini` | `Gemini` |
| `kimi` | `Kimi` |
| `qwen` | `Qwen` |
| `other` / 未知 | `"Other"` |

### Agent 归属算法

```python
AGENT_PRIORITY = [
    "claude", "opencode", "openclaw", "codex", "amp",
    "droid", "codebuff", "hermes", "pi", "goose",
    "kilo", "copilot", "gemini", "kimi", "qwen",
]

def _infer_agent(
    model_name: str,
    date_str: str,
    agent_models_dict: dict[str, dict[str, set[str]]]
) -> str:
    """根据模型名 + 当日各 agent 的 modelsUsed 字典推断归属。

    agent_models_dict 形如:
    {
        "2026-06-05": {
            "claude": {"glm-5.1", "claude-opus-4-8", ...},
            "opencode": {"minimax-m3-free", "qwen3.6-plus"},
        },
        "2026-06-04": {...},
    }

    规则:
    1. 模型在当日某 agent 的 modelsUsed 中 → 归属该 agent
    2. 多个 agent 都含该模型（歧义，如 qwen3.6-plus）→ 按 AGENT_PRIORITY 选最高优先级
    3. 都不含 → "other"（兜底，WARNING 日志）
    """
    day_agents = agent_models_dict.get(date_str, {})
    candidates = [agent for agent, models in day_agents.items() if model_name in models]
    if not candidates:
        return "other"
    for priority_agent in AGENT_PRIORITY:
        if priority_agent in candidates:
            return priority_agent
    return candidates[0]
```

### 同步触发设计

**APScheduler 启动**（`backend/app/main.py`）：

```python
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化调度器
    if not _DESKTOP_MODE:  # 桌面模式不启动后台任务
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            daily_sync_job,
            CronTrigger(hour=0, minute=5),  # 每天 00:05
            id="daily_ccusage_sync",
            name="Daily ccusage sync at 00:05",
            coalesce=True,        # 错过多次只跑一次
            max_instances=1,      # 同时只允许 1 个实例
            misfire_grace_time=3600,  # 1 小时内补跑
        )
        scheduler.start()
    yield
    # 关闭时
    if not _DESKTOP_MODE and scheduler.running:
        scheduler.shutdown(wait=False)
```

**并发保护**（`backend/app/services/ccusage_scheduler.py`）：

```python
_sync_lock = asyncio.Lock()

async def daily_sync_job():
    """00:05 自动任务 + 手动端点共享。"""
    if _sync_lock.locked():
        logger.warning("ccusage 同步进行中，跳过本次触发")
        return
    async with _sync_lock:
        try:
            count = await asyncio.to_thread(sync_token_usage_v2, days=1)
            logger.info(f"[ccusage-daily] 自动同步完成: {count} 条")
        except Exception as e:
            logger.error(f"[ccusage-daily] 自动同步失败: {e}", exc_info=True)
```

**手动端点**（`backend/app/routes/token_usage.py`）：

```python
@router.post("/refresh-ccusage")
async def refresh_ccusage_endpoint(current_user: dict = Depends(get_current_user)):
    """手动触发 ccusage 同步（同步运行，等待完成）。"""
    if _DESKTOP_MODE:
        raise HTTPException(403, "桌面模式不支持后台同步")
    try:
        count = await asyncio.to_thread(sync_token_usage_v2, days=1)
        return {"success": True, "synced_records": count}
    except Exception as e:
        logger.error(f"[ccusage-manual] 手动同步失败: {e}", exc_info=True)
        raise HTTPException(500, f"同步失败: {e}")
```

**前端按钮**（`frontend/src/components/Tools/TokenUsage.tsx`）：

```tsx
const [syncing, setSyncing] = useState(false);
const handleSync = async () => {
    setSyncing(true);
    try {
        const res = await fetch('/api/token-usage/refresh-ccusage', { method: 'POST' });
        const data = await res.json();
        toast.success(`同步完成: ${data.synced_records} 条`);
        refetch();  // 重新拉明细表
    } catch (e) {
        toast.error(`同步失败: ${e.message}`);
    } finally {
        setSyncing(false);
    }
};
// 渲染：<button onClick={handleSync} disabled={syncing}>{syncing ? '同步中...' : '同步'}</button>
```

### 回填脚本

`backend/scripts/backfill_ccusage.py`：

```python
"""一次性全量回填脚本。部署时跑一次。

Usage（在 backend/ 目录下执行，确保 app.* 绝对导入可解析）:
    cd backend
    python -m scripts.backfill_ccusage
    python -m scripts.backfill_ccusage --since 2024-01-01
"""
import argparse
import sys
from app.services.token_usage_sync_service import sync_token_usage_v2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="2024-01-01", help="起始日期 YYYY-MM-DD")
    parser.add_argument("--batch-days", type=int, default=90, help="每批天数（避免单次 CLI 跨度过大）")
    args = parser.parse_args()

    today = date.today()
    since = date.fromisoformat(args.since)
    total_synced = 0

    cursor = since
    while cursor <= today:
        until = min(cursor + timedelta(days=args.batch_days - 1), today)
        logger.info(f"回填 {cursor} ~ {until} ...")
        count = sync_token_usage_v2(since=cursor.isoformat(), until=until.isoformat())
        total_synced += count
        cursor = until + timedelta(days=1)

    logger.info(f"回填完成: 总计 {total_synced} 条")


if __name__ == "__main__":
    main()
```

### 错误处理 & 边界

| 场景 | 行为 |
|---|---|
| ccusage 未安装 | 同步返回 `{"error": "ccusage 未安装"}` + 前端弹提示 |
| ccusage 返回空 daily 数组 | 0 条入库 + WARNING 日志 |
| `--since/--until` 跨度太大 | 单次最大 180 天（与 `usage_fetcher_v2` 内部 batch 处理），超出自动分批 |
| APScheduler 重复触发 | `coalesce=True` + `max_instances=1` 防并发 |
| 同步进行中用户又点按钮 | 后端 `_sync_lock` 串行化；前端按钮 disable |
| agent 归属失败（model 不在任何 per-agent 列表）| `agent="other"`，WARNING 日志（含 model 名） |
| DB upsert 失败 | 单条失败不中断整批，ERROR 日志记录 `record_date` |
| 回填时遇到 unique 冲突 | 已有 34+217 条旧记录自然被 upsert 覆盖（无数据丢失） |
| ccusage 新增了未知 agent | 自动通过 `metadata.agents` 发现，调 `ccusage <new-agent> daily` |
| `_DESKTOP_MODE=1` | 不启动调度器；手动端点返回 403 |
| 前端按钮点击 | 同步中显示 loading + disable 状态 |

**幂等保证**：
- `_upsert_records` 用 `ON CONFLICT ... DO UPDATE`：同 (date, source, model) 重复同步会覆盖
- 每日重复跑同步是安全的
- 跨设备：`device_id` 参与唯一约束

### 测试策略

**单元测试**（`backend/tests/test_parse_ccusage_records.py`，6 个）：

1. `test_infer_agent_basic` — 模型名只在一个 agent 列表中 → 正确归属
2. `test_infer_agent_ambiguous_qwen` — `qwen3.6-plus` 同时在 claude + opencode 列表 → 按优先级选 claude
3. `test_infer_agent_unknown` — 模型名不在任何列表 → "other"
4. `test_parse_ccusage_daily_with_model_breakdowns` — 1 日完整 JSON（带 modelBreakdowns + 2 agent 归属）→ 6 条 (date, agent, model) 记录
5. `test_parse_ccusage_daily_empty` — 空 daily 数组 → 0 条
6. `test_parse_ccusage_daily_with_no_agents_metadata` — 旧版 ccusage 无 metadata.agents → 全归 "other"

**集成测试**（`backend/tests/test_usage_fetcher_v2.py`，2 个）：

7. `test_fetch_ccusage_daily_uses_correct_flags` — mock subprocess，验证 `ccusage daily --json --since X --until Y --offline`
8. `test_fetch_ccusage_agent_daily_opencode` — 验证 `ccusage opencode daily --json --since X --until Y --offline`

**E2E 验证**（手动，4 个）：

9. **回填脚本**：在 `backend/` 目录下跑 `python -m scripts.backfill_ccusage --since 2026-01-01`（依赖 `backend/` 在 sys.path 以解析 `app.*` 绝对导入），查 PostgreSQL 验证 2026-01-23 之后 opencode 行被更新
10. **APScheduler**：启动后端，验证 00:05（或立即测试）触发同步
11. **手动按钮**：浏览器点 Token Usage 页面"同步"按钮，验证调通新端点 + 同步条数 + refetch 后明细表更新
12. **页面性能**：对比旧实现（CLI 调用）与新实现（DB 查询）的 P95 响应时间

### 验收标准

- [ ] 新增 `backend/app/utils/usage_fetcher_v2.py` 实现 ccusage 统一调用
- [ ] `sync_token_usage_v2` 函数支持单日 / 多日范围同步
- [ ] APScheduler 启动配置在 `backend/app/main.py` lifespan 中
- [ ] 桌面模式（`DESKTOP_MODE=1`）跳过调度器，手动端点返 403
- [ ] 新增 `POST /api/token-usage/refresh-ccusage` 端点（鉴权）
- [ ] 前端 Token Usage 页面新增"同步"按钮（带 loading 状态）
- [ ] 回填脚本 `backend/scripts/backfill_ccusage.py` 可独立运行
- [ ] 6 个单元测试 + 2 个集成测试全部通过
- [ ] 现有 6 个 `test_token_usage_*.py` 不破坏
- [ ] 手动回填后 PostgreSQL 中 `(2026-06-05, opencode, minimax-m3-free)` 等行存在
- [ ] 浏览器前端：明细表同时显示 Claude Code / OpenCode / 未来可能 OpenClaw 行
- [ ] 旧 34 条 `model='_total'` opencode 记录（2026-01-23~02-27）被新数据正确覆盖或保留兼容
- [ ] **不自动 commit**（CLAUDE.md 禁止，由用户显式触发）

### 风险与回滚

| 风险 | 缓解 |
|---|---|
| 旧 217 条 claude 记录被新数据覆盖后数据不一致 | 新 ccusage 同一模型 cost 计算口径可能与旧 ccusage-opencode 不同；先对比一次再回填 |
| APScheduler 与现有任何任务冲突 | 引入前 grep 全文确认无 scheduler 关键字 |
| `apscheduler` 依赖体积/版本问题 | 锁版本 `>=3.10,<4.0`；3.x API 稳定 |
| agent 归属歧义（qwen3.6-plus 同日多 agent）| AGENT_PRIORITY tie-breaker + WARNING 日志，便于人工审计 |
| ccusage 输出格式升级导致解析失败 | `metadata.agents` 缺失时全归 "other"（不崩溃），`modelBreakdowns` 缺失时回退到 agent-level data |
| 同步锁导致凌晨 00:05 任务死锁 | `coalesce=True` + `misfire_grace_time=3600` + try/except 包裹 |
| 前端 label 映射硬编码 `source ∈ {claude, opencode}` 导致新 agent 显示原始名 | 新 agent 进入时手动更新 `TokenUsage.tsx:514` 的 label 映射（单文件小改动） |

**回滚**：所有改动在 1-2 个 commit 内，`git revert` 即可。

### 不在本次范围（Follow-up）

- 实时同步（分钟级）— 用户没要求
- 跨设备数据合并 — 用户没要求
- token-usage 页面前端 UI 改版（明细表列调整、agent 切换器等）— 用户没要求
- 删 `ccusage-opencode` / `opencode-usage` CLI — 保留兼容
- 历史 token-usage-dimensions 表数据迁移 — 现有 schema 已兼容
