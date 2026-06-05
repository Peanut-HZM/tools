# 重构 Token-Usage 统计为 ccusage 统一数据源 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 替换 `ccusage-opencode` + `opencode-usage` 两个 CLI 为单一 `ccusage` 统一数据源，按 (date, agent, model) 三元组存储到 PostgreSQL，APScheduler 每天 00:05 自动同步 + 前端手动触发按钮，让页面查询从 CLI 调用改为纯 DB 读。

**Architecture:** 新增 `UsageFetcherV2` 统一封装 `ccusage` CLI 调用（`ccusage daily` + 动态 per-agent 子命令），`SyncServiceV2` 解析 modelBreakdowns + 通过 per-agent modelsUsed 字典做 agent 归属，APScheduler 通过 `ccusage_scheduler` 守护进程触发 daily_sync_job。所有 `_upsert_records` 复用现有 ON CONFLICT upsert 逻辑，source 字段保留 agent 语义（`source='claude'` / `'opencode'` / `'openclaw'` / ...）以兼容现有前端 label 映射。

**Tech Stack:** Python 3.10+、APScheduler 3.x、FastAPI、PostgreSQL、React 18 + TypeScript、ccusage 20.0.6

**前置条件**：
- 仓库根目录：`/Users/huazhongmin/IdeaProjects/tools`
- 后端运行中（端口 19092）
- `ccusage --version` ≥ 20.0.0（已安装 v20.0.6）
- PostgreSQL 可访问（`39.107.229.30:5432/tools`）
- CLAUDE.md 禁止自动 commit — Task 13 由用户显式触发

**作废关系**：本计划取代 `2026-06-05-opencode-data-flow-fix.md`（基于多 CLI 源方案作废）

---

## File Structure

| 文件 | 类型 | 职责 |
|---|---|---|
| `backend/app/utils/usage_fetcher_v2.py` | **CREATE** | `UsageFetcherV2` 类：`fetch_ccusage_daily` + `fetch_ccusage_agent_daily` 方法 |
| `backend/app/services/token_usage_sync_service.py` | **MODIFY** | 新增 `_infer_agent` + `_parse_ccusage_records`（保留旧 `_parse_opencode_entries` 为 alias） |
| `backend/app/services/ccusage_scheduler.py` | **CREATE** | `init_scheduler()` + `daily_sync_job()` + `asyncio.Lock` |
| `backend/app/main.py` | **MODIFY** | 在 `lifespan` 中调 `init_scheduler()`（含 DESKTOP_MODE 短路） |
| `backend/app/routes/token_usage.py` | **MODIFY** | 新增 `POST /refresh-ccusage` 端点 |
| `backend/scripts/backfill_ccusage.py` | **CREATE** | 一次性全量回填 CLI 脚本 |
| `frontend/src/components/Tools/TokenUsage.tsx` | **MODIFY** | 新增"同步"按钮 + `handleSync` 处理函数 |
| `backend/requirements.txt` | **MODIFY** | 加 `apscheduler>=3.10,<4.0` |
| `backend/tests/test_parse_ccusage_records.py` | **CREATE** | 6 单元测试 |
| `backend/tests/test_usage_fetcher_v2.py` | **CREATE** | 2 集成测试（mock subprocess） |
| `backend/tests/test_ccusage_scheduler.py` | **CREATE** | 2 单元测试（scheduler 初始化 + 锁行为） |

---

## Task 1: 添加 `_parse_ccusage_records` 单元测试（RED）

**Files:**
- Create: `backend/tests/test_parse_ccusage_records.py`

- [ ] **Step 1: 创建测试文件，写 6 个失败测试**

```python
"""测试 _parse_ccusage_records 解析 ccusage daily + per-agent JSON。"""
from app.services.token_usage_sync_service import _infer_agent, _parse_ccusage_records


# ---------- _infer_agent ----------

def test_infer_agent_basic_unique_model():
    """模型名只在 claude 的 modelsUsed 中 → 归属 claude"""
    agent_dict = {
        "2026-06-05": {
            "claude": {"claude-opus-4-8", "gpt-5.5"},
            "opencode": {"minimax-m3-free"},
        }
    }
    assert _infer_agent("claude-opus-4-8", "2026-06-05", agent_dict) == "claude"
    assert _infer_agent("minimax-m3-free", "2026-06-05", agent_dict) == "opencode"


def test_infer_agent_ambiguous_qwen_prefers_claude():
    """qwen3.6-plus 同时在 claude + opencode 列表 → 按优先级选 claude"""
    agent_dict = {
        "2026-06-05": {
            "claude": {"qwen3.6-plus", "claude-opus-4-8"},
            "opencode": {"qwen3.6-plus", "minimax-m3-free"},
        }
    }
    assert _infer_agent("qwen3.6-plus", "2026-06-05", agent_dict) == "claude"


def test_infer_agent_unknown_model_returns_other():
    """模型名不在任何 agent 列表 → 兜底 'other'"""
    agent_dict = {
        "2026-06-05": {
            "claude": {"claude-opus-4-8"},
        }
    }
    assert _infer_agent("unknown-model-xyz", "2026-06-05", agent_dict) == "other"


def test_infer_agent_empty_dict_returns_other():
    """agent 字典为空 → 'other'"""
    assert _infer_agent("any-model", "2026-06-05", {}) == "other"


# ---------- _parse_ccusage_records ----------

def test_parse_ccusage_daily_with_model_breakdowns():
    """1 日完整 JSON（含 modelBreakdowns + 2 agent 归属）→ 多条 (date, agent, model) 记录"""
    daily = [
        {
            "agent": "all",
            "period": "2026-06-05",
            "modelBreakdowns": [
                {"modelName": "claude-opus-4-8", "inputTokens": 215984263, "outputTokens": 213810,
                 "cacheCreationTokens": 0, "cacheReadTokens": 0, "cost": 1085.26},
                {"modelName": "gpt-5.5", "inputTokens": 1341214, "outputTokens": 13184,
                 "cacheCreationTokens": 0, "cacheReadTokens": 589824, "cost": 7.40},
                {"modelName": "minimax-m3-free", "inputTokens": 2504169, "outputTokens": 233288,
                 "cacheCreationTokens": 0, "cacheReadTokens": 51132786, "cost": 0.0},
            ],
            "metadata": {"agents": ["claude", "opencode"]},
        }
    ]
    agent_models = {
        "2026-06-05": {
            "claude": {"claude-opus-4-8", "gpt-5.5"},
            "opencode": {"minimax-m3-free", "qwen3.6-plus"},
        }
    }
    records = _parse_ccusage_records(daily, agent_models)
    assert len(records) == 3
    # claude-opus-4-8 → claude
    r = next(r for r in records if r["model"] == "claude-opus-4-8")
    assert r["source"] == "claude"
    assert r["record_date"].isoformat() == "2026-06-05"
    assert r["input_tokens"] == 215984263
    assert r["output_tokens"] == 213810
    assert r["cache_creation_tokens"] == 0
    assert r["cache_read_tokens"] == 0
    assert r["total_tokens"] == 216198073
    assert r["total_cost"] == 1085.26
    # minimax-m3-free → opencode
    r = next(r for r in records if r["model"] == "minimax-m3-free")
    assert r["source"] == "opencode"
    assert r["total_cost"] == 0.0


def test_parse_ccusage_daily_empty():
    """空 daily 数组 → 0 条"""
    records = _parse_ccusage_records([], {})
    assert records == []


def test_parse_ccusage_daily_with_no_agents_metadata():
    """agent 字典无该日期 → 模型全归 'other'"""
    daily = [
        {
            "agent": "all",
            "period": "2026-06-05",
            "modelBreakdowns": [
                {"modelName": "claude-opus-4-8", "inputTokens": 100, "outputTokens": 10,
                 "cacheCreationTokens": 0, "cacheReadTokens": 0, "cost": 1.0},
            ],
        }
    ]
    records = _parse_ccusage_records(daily, {})  # 空字典
    assert len(records) == 1
    assert records[0]["source"] == "other"
    assert records[0]["model"] == "claude-opus-4-8"
    assert records[0]["total_tokens"] == 110
```

- [ ] **Step 2: 运行测试，验证 6 个全部失败（_infer_agent 和 _parse_ccusage_records 未实现）**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_parse_ccusage_records.py -v
```

**Expected**：6 FAILED（NameError: name '_infer_agent' / '_parse_ccusage_records' is not defined）

- [ ] **Step 3: 不 commit**

---

## Task 2: 实现 `_infer_agent` + `_parse_ccusage_records`（GREEN）

**Files:**
- Modify: `backend/app/services/token_usage_sync_service.py`（在文件末尾添加新函数）

- [ ] **Step 1: 在 `token_usage_sync_service.py` 文件末尾追加新函数**

在文件最末尾添加（先看文件最后一行确认位置）：

```python
# ========================================================================
# ccusage 统一数据源（v2）— 替代 _parse_opencode_entries
# ========================================================================

# Agent 优先级（用于模型归属歧义时的 tie-breaker）
AGENT_PRIORITY = [
    "claude", "opencode", "openclaw", "codex", "amp",
    "droid", "codebuff", "hermes", "pi", "goose",
    "kilo", "copilot", "gemini", "kimi", "qwen",
]

# agent_id → 显示名映射
AGENT_DISPLAY_NAMES = {
    "claude": "Claude Code",
    "opencode": "OpenCode",
    "openclaw": "OpenClaw",
    "codex": "Codex",
    "amp": "Amp",
    "droid": "Droid",
    "codebuff": "Codebuff",
    "hermes": "Hermes",
    "pi": "pi",
    "goose": "Goose",
    "kilo": "Kilo",
    "copilot": "GitHub Copilot",
    "gemini": "Gemini",
    "kimi": "Kimi",
    "qwen": "Qwen",
    "other": "Other",
}


def _infer_agent(
    model_name: str,
    date_str: str,
    agent_models_dict: dict,
) -> str:
    """根据模型名 + 当日各 agent 的 modelsUsed 字典推断归属。

    agent_models_dict 形如:
    {
        "2026-06-05": {
            "claude": {"claude-opus-4-8", "gpt-5.5", ...},
            "opencode": {"minimax-m3-free", "qwen3.6-plus", ...},
        },
    }

    规则:
    1. 模型在当日某 agent 的 modelsUsed 中 → 归属该 agent
    2. 多个 agent 都含该模型（歧义）→ 按 AGENT_PRIORITY 选最高优先级
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


def _parse_ccusage_records(
    daily: list[dict],
    agent_models_dict: dict,
) -> list[dict]:
    """解析 ccusage daily JSON 为 (date, agent, model) 三元组记录。

    Args:
        daily: ccusage daily --json 的 daily 数组
        agent_models_dict: 来自 ccusage <agent> daily --json 的 {date: {agent: modelsUsed set}}

    Returns:
        list of dict, 每条含 record_date, source, model, 4 个 token 字段, total_cost 等
    """
    from datetime import date as _date  # 局部导入避免循环

    results = []
    for day in daily:
        period = day.get("period") or day.get("date")
        if not period:
            continue
        try:
            record_date = _date.fromisoformat(period)
        except (ValueError, TypeError):
            continue

        breakdowns = day.get("modelBreakdowns") or []
        for bd in breakdowns:
            model_name = bd.get("modelName") or bd.get("model") or "_unknown"
            agent = _infer_agent(model_name, period, agent_models_dict)
            if agent == "other":
                logger.warning(
                    f"[ccusage] 模型 {model_name}（{period}）不在任何 per-agent modelsUsed 中，归 'other'"
                )

            input_tokens = _safe_int(bd, "inputTokens", "input_tokens")
            output_tokens = _safe_int(bd, "outputTokens", "output_tokens")
            cache_creation_tokens = _safe_int(bd, "cacheCreationTokens", "cache_creation_tokens")
            cache_read_tokens = _safe_int(bd, "cacheReadTokens", "cache_read_tokens")
            total_tokens = _calc_total_tokens(
                input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
            )
            total_cost = _safe_float(bd, "cost")

            results.append({
                "record_date": record_date,
                "source": agent,
                "tool_id": agent,
                "tool_name": AGENT_DISPLAY_NAMES.get(agent, "Other"),
                "model": model_name,
                "model_display_name": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_tokens": cache_creation_tokens,
                "cache_read_tokens": cache_read_tokens,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "source_raw": "ccusage-daily",
            })
    return results
```

- [ ] **Step 2: 验证 6 个测试全部通过**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_parse_ccusage_records.py -v
```

**Expected**：6 passed

- [ ] **Step 3: 验证现有 6 个 token_usage 测试不破坏**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_token_usage_*.py -v
```

**Expected**：所有现有测试通过

- [ ] **Step 4: 不 commit**

---

## Task 3: 添加 `UsageFetcherV2` 集成测试（RED）

**Files:**
- Create: `backend/tests/test_usage_fetcher_v2.py`

- [ ] **Step 1: 创建测试文件，写 2 个失败测试**

```python
"""测试 UsageFetcherV2 调用 ccusage CLI 的参数正确性。"""
from unittest.mock import patch, MagicMock

from app.utils.usage_fetcher_v2 import UsageFetcherV2


def test_fetch_ccusage_daily_uses_correct_flags():
    """验证 cmd 包含 ccusage daily --json --since X --until Y --offline"""
    fake_result = {
        "daily": [
            {
                "agent": "all",
                "period": "2026-06-05",
                "inputTokens": 100, "outputTokens": 10,
                "cacheCreationTokens": 0, "cacheReadTokens": 0,
                "totalTokens": 110, "totalCost": 0.001,
                "modelsUsed": ["claude-opus-4-8"],
                "modelBreakdowns": [
                    {"modelName": "claude-opus-4-8", "inputTokens": 100, "outputTokens": 10,
                     "cacheCreationTokens": 0, "cacheReadTokens": 0, "cost": 0.001},
                ],
                "metadata": {"agents": ["claude"]},
            }
        ],
        "totals": {"inputTokens": 100, "outputTokens": 10, "totalTokens": 110, "totalCost": 0.001}
    }

    with patch("app.utils.usage_fetcher_v2.shutil.which", return_value="/usr/local/bin/ccusage"), \
         patch("app.utils.usage_fetcher_v2._run_cmd", return_value=fake_result) as mock_run, \
         patch("app.utils.usage_fetcher_v2._get_from_cache", return_value=None), \
         patch("app.utils.usage_fetcher_v2._set_cache"):
        UsageFetcherV2.fetch_ccusage_daily(since="2026-06-05", until="2026-06-05")

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "ccusage"
    assert "daily" in cmd
    assert "--json" in cmd
    assert "--since=2026-06-05" in cmd
    assert "--until=2026-06-05" in cmd
    assert "--offline" in cmd


def test_fetch_ccusage_agent_daily_opencode():
    """验证 ccusage opencode daily 调用参数正确"""
    fake_result = {
        "daily": [
            {
                "date": "2026-06-05",
                "inputTokens": 100, "outputTokens": 10,
                "cacheCreationTokens": 0, "cacheReadTokens": 0,
                "totalTokens": 110, "totalCost": 0.0,
                "modelsUsed": ["minimax-m3-free"],
            }
        ],
        "totals": {"inputTokens": 100, "outputTokens": 10, "totalTokens": 110, "totalCost": 0.0}
    }

    with patch("app.utils.usage_fetcher_v2.shutil.which", return_value="/usr/local/bin/ccusage"), \
         patch("app.utils.usage_fetcher_v2._run_cmd", return_value=fake_result) as mock_run, \
         patch("app.utils.usage_fetcher_v2._get_from_cache", return_value=None), \
         patch("app.utils.usage_fetcher_v2._set_cache"):
        UsageFetcherV2.fetch_ccusage_agent_daily(
            agent="opencode", since="2026-06-05", until="2026-06-05"
        )

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "ccusage"
    assert cmd[1] == "opencode"
    assert cmd[2] == "daily"
    assert "--json" in cmd
    assert "--since=2026-06-05" in cmd
    assert "--until=2026-06-05" in cmd
```

- [ ] **Step 2: 运行测试，验证 2 个失败（UsageFetcherV2 未实现）**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_usage_fetcher_v2.py -v
```

**Expected**：2 FAILED（ModuleNotFoundError: No module named 'app.utils.usage_fetcher_v2'）

- [ ] **Step 3: 不 commit**

---

## Task 4: 实现 `UsageFetcherV2`（GREEN）

**Files:**
- Create: `backend/app/utils/usage_fetcher_v2.py`

- [ ] **Step 1: 创建 `usage_fetcher_v2.py`**

```python
"""ccusage 统一数据源调用层（v2）— 替代 ccusage-opencode + opencode-usage"""

import logging
import shutil
from typing import Optional

# 复用 V1 helpers（DRY）
from app.utils.usage_fetcher import (
    _run_cmd,
    _get_from_cache,
    _set_cache,
    _DESKTOP_MODE,
)

logger = logging.getLogger(__name__)


class UsageFetcherV2:
    """ccusage 统一数据源调用层"""

    @staticmethod
    def fetch_ccusage_daily(since: str, until: str) -> dict:
        """调用 ccusage daily --json 返回所有 agent 的当日聚合 + modelBreakdowns

        Args:
            since: 起始日期 YYYY-MM-DD
            until: 结束日期 YYYY-MM-DD

        Returns:
            dict: ccusage daily --json 的输出，含 daily 数组 + totals
            失败时返回 {"error": "..."}
        """
        if _DESKTOP_MODE:
            return {"error": "Token Usage CLI 功能在桌面模式下不可用"}

        if shutil.which("ccusage") is None:
            return {"error": "CLI 未安装: ccusage（请先 npm i -g ccusage）"}

        cache_key = f"ccusage-daily:{since}:{until}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        cmd = [
            "ccusage", "daily",
            "--json",
            f"--since={since}",
            f"--until={until}",
            "--offline",
        ]
        result = _run_cmd(cmd, timeout=180)
        if "error" not in result:
            _set_cache(cache_key, result)
        return result

    @staticmethod
    def fetch_ccusage_agent_daily(agent: str, since: str, until: str) -> dict:
        """调用 ccusage <agent> daily --json 返回指定 agent 的每日聚合 + modelsUsed

        Args:
            agent: agent 名（claude / opencode / openclaw / codex / ...）
            since: 起始日期 YYYY-MM-DD
            until: 结束日期 YYYY-MM-DD

        Returns:
            dict: ccusage <agent> daily --json 的输出
            失败时返回 {"error": "..."}
        """
        if _DESKTOP_MODE:
            return {"error": "Token Usage CLI 功能在桌面模式下不可用"}

        if shutil.which("ccusage") is None:
            return {"error": "CLI 未安装: ccusage"}

        cache_key = f"ccusage-{agent}-daily:{since}:{until}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        cmd = [
            "ccusage", agent, "daily",
            "--json",
            f"--since={since}",
            f"--until={until}",
            "--offline",
        ]
        result = _run_cmd(cmd, timeout=120)
        if "error" not in result:
            _set_cache(cache_key, result)
        return result
```

- [ ] **Step 2: 验证 2 个集成测试通过**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_usage_fetcher_v2.py -v
```

**Expected**：2 passed

- [ ] **Step 3: 不 commit**

---

## Task 5: 重构 `sync_token_usage` 使用 V2 fetcher

**Files:**
- Modify: `backend/app/services/token_usage_sync_service.py:232`（改 `sync_token_usage` 签名）+ `return result` 之前插入 v2 调用

- [ ] **Step 1: 改 `sync_token_usage` 签名，添加 `since_date` / `until_date` 可选 kwargs**

把第 232 行的：

```python
def sync_token_usage(user_id: str, days: int = 90) -> dict:
```

改为：

```python
def sync_token_usage(
    user_id: str,
    days: int = 90,
    *,
    since_date: Optional[date] = None,
    until_date: Optional[date] = None,
) -> dict:
```

并在函数体**最开头**（line 246 之前）加日期兜底：

```python
    if until_date is None:
        until_date = date.today()
    if since_date is None:
        since_date = until_date - timedelta(days=days - 1)
```

并在文件顶部 import 区追加 `from typing import Optional`（如未导入）。

- [ ] **Step 2: 在 `sync_token_usage` 函数末尾（`return result` 之前）添加 v2 调用**

在 `return result` 上一行添加：

```python
    # ========== V2: ccusage 统一数据源（追加到结果） ==========
    try:
        v2_count = _run_ccusage_v2_sync(db, user_id, device_id, device_name, since_date, until_date)
        result["ccusage_records"] = v2_count
        result["total_records"] += v2_count
    except Exception as e:
        logger.error(f"[ccusage-v2] 同步失败: {e}", exc_info=True)
        result["errors"].append(f"ccusage-v2: {e}")
```

- [ ] **Step 3: 在文件最末尾添加 v2 同步实现函数**

在 Task 2 追加的 `_parse_ccusage_records` 之后添加：

```python
def _run_ccusage_v2_sync(
    db,
    user_id: str,
    device_id: str,
    device_name: str,
    since_date,
    until_date,
) -> int:
    """v2: ccusage 统一数据源同步

    1. 调 ccusage daily（带 modelBreakdowns）
    2. 调 ccusage <agent> daily（每个 metadata.agents 中的 agent）
    3. 解析为 (date, agent, model) 三元组
    4. upsert 到 DB
    """
    from app.utils.usage_fetcher_v2 import UsageFetcherV2

    since_str = since_date.isoformat() if hasattr(since_date, "isoformat") else str(since_date)
    until_str = until_date.isoformat() if hasattr(until_date, "isoformat") else str(until_date)

    # 1. 拉主 daily
    daily_result = UsageFetcherV2.fetch_ccusage_daily(since=since_str, until=until_str)
    if "error" in daily_result:
        logger.warning(f"[ccusage-v2] daily 拉取失败: {daily_result['error']}")
        return 0

    daily_list = daily_result.get("daily", [])
    if not daily_list:
        logger.info(f"[ccusage-v2] {since_str} ~ {until_str} 无数据")
        return 0

    # 2. 收集所有 metadata.agents，调 per-agent 子命令拿 modelsUsed
    all_agents: set[str] = set()
    for day in daily_list:
        meta = day.get("metadata", {}) or {}
        for a in meta.get("agents", []) or []:
            all_agents.add(a)

    agent_models_dict: dict[str, dict[str, set[str]]] = {}
    for agent in sorted(all_agents):
        agent_result = UsageFetcherV2.fetch_ccusage_agent_daily(
            agent=agent, since=since_str, until=until_str
        )
        if "error" in agent_result:
            logger.warning(f"[ccusage-v2] {agent} daily 拉取失败: {agent_result['error']}")
            continue
        for day in (agent_result.get("daily") or []):
            date_key = day.get("date")
            if not date_key:
                continue
            agent_models_dict.setdefault(date_key, {}).setdefault(agent, set()).update(
                day.get("modelsUsed") or []
            )

    # 3. 解析为 (date, agent, model) 记录
    records = _parse_ccusage_records(daily_list, agent_models_dict)
    if not records:
        logger.info(f"[ccusage-v2] 解析后 0 条记录（{since_str} ~ {until_str}）")
        return 0

    # 4. upsert（用现有 _upsert_records）
    count = _upsert_records(db, user_id, device_id, device_name, records)
    logger.info(f"[ccusage-v2] {since_str} ~ {until_str} 同步 {count} 条")
    return count
```

- [ ] **Step 4: 验证现有 token_usage 测试不破坏**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_token_usage_*.py tests/test_parse_ccusage_records.py tests/test_usage_fetcher_v2.py -v
```

**Expected**：所有测试通过（含 6 个新测试 + 6 个旧 token_usage 测试）

- [ ] **Step 5: 不 commit**

---

## Task 6: 添加 `ccusage_scheduler` 单元测试（RED）

**Files:**
- Create: `backend/tests/test_ccusage_scheduler.py`

- [ ] **Step 1: 写 2 个测试**

```python
"""测试 ccusage_scheduler 的调度器初始化 + 锁行为。"""
import asyncio
import os
from unittest.mock import patch


def test_init_scheduler_skips_in_desktop_mode():
    """DESKTOP_MODE=1 时 init_scheduler 应直接返回，不创建 scheduler"""
    with patch.dict(os.environ, {"DESKTOP_MODE": "1"}):
        # 重新导入以触发环境变量读取
        import importlib
        from app.services import ccusage_scheduler
        importlib.reload(ccusage_scheduler)

        result = ccusage_scheduler.init_scheduler()
        assert result is None  # 桌面模式返回 None


def test_init_scheduler_returns_scheduler_in_normal_mode(monkeypatch):
    """非桌面模式 init_scheduler 应创建 AsyncIOScheduler 并添加 daily_sync_job"""
    monkeypatch.delenv("DESKTOP_MODE", raising=False)

    import importlib
    from app.services import ccusage_scheduler
    importlib.reload(ccusage_scheduler)

    with patch("app.services.ccusage_scheduler.AsyncIOScheduler") as mock_scheduler_class:
        mock_instance = mock_scheduler_class.return_value
        result = ccusage_scheduler.init_scheduler()

        assert result is mock_instance
        mock_instance.add_job.assert_called_once()
        # 验证 cron trigger 参数
        call_kwargs = mock_instance.add_job.call_args.kwargs
        assert call_kwargs["id"] == "daily_ccusage_sync"
        assert call_kwargs["coalesce"] is True
        assert call_kwargs["max_instances"] == 1
        mock_instance.start.assert_called_once()
```

- [ ] **Step 2: 运行测试，验证 2 个失败**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_ccusage_scheduler.py -v
```

**Expected**：2 FAILED（ModuleNotFoundError）

- [ ] **Step 3: 不 commit**

---

## Task 7: 实现 `ccusage_scheduler`（GREEN）

**Files:**
- Create: `backend/app/services/ccusage_scheduler.py`

- [ ] **Step 1: 创建 `ccusage_scheduler.py`**

```python
"""APScheduler 守护：每天 00:05 自动同步 ccusage 数据。"""
import asyncio
import logging
import os
from datetime import date, timedelta

logger = logging.getLogger(__name__)

_DESKTOP_MODE = os.environ.get("DESKTOP_MODE") == "1"

# 全局同步锁（保护 daily_sync_job 和手动端点互斥）
_sync_lock = asyncio.Lock()

# scheduler 单例
_scheduler = None


def get_sync_lock() -> asyncio.Lock:
    """返回全局同步锁，供手动端点使用"""
    return _sync_lock


def init_scheduler():
    """初始化并启动 APScheduler。桌面模式直接返回 None。

    Returns:
        AsyncIOScheduler 实例（非桌面模式）或 None（桌面模式）
    """
    global _scheduler

    if _DESKTOP_MODE:
        logger.info("[ccusage-scheduler] 桌面模式，跳过 scheduler 启动")
        return None

    if _scheduler is not None and _scheduler.running:
        return _scheduler

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        daily_sync_job,
        CronTrigger(hour=0, minute=5),
        id="daily_ccusage_sync",
        name="Daily ccusage sync at 00:05",
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info("[ccusage-scheduler] 启动成功，每天 00:05 触发 daily_sync_job")
    return _scheduler


def shutdown_scheduler():
    """关闭 scheduler（应用关闭时调用）"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[ccusage-scheduler] 已关闭")


async def daily_sync_job():
    """00:05 自动任务：同步当天 ccusage 数据。"""
    if _sync_lock.locked():
        logger.warning("[ccusage-daily] 同步进行中，跳过本次触发")
        return

    async with _sync_lock:
        try:
            today = date.today().isoformat()
            count = await asyncio.to_thread(_sync_today, today)
            logger.info(f"[ccusage-daily] 自动同步 {today} 完成: {count} 条")
        except Exception as e:
            logger.error(f"[ccusage-daily] 自动同步失败: {e}", exc_info=True)


def _sync_today(date_str: str) -> int:
    """同步指定日期数据（同步函数，run in thread）"""
    from app.models.base import SessionLocal
    from app.services.token_usage_sync_service import sync_token_usage_v2
    from app.utils.device_id import get_device_id, get_device_display_name

    db = SessionLocal()
    try:
        return sync_token_usage_v2(
            db=db,
            user_id=_resolve_scheduler_user_id(db),
            device_id=get_device_id(),
            device_name=get_device_display_name(),
            since=date_str,
            until=date_str,
        )
    finally:
        db.close()


def _resolve_scheduler_user_id(db) -> str:
    """解析 scheduler 同步用的 user_id。

    优先级：
    1. 环境变量 `SCHEDULER_USER_ID`（运营配置，覆盖 DB 查询）
    2. 数据库中第一个 role='admin' 的用户
    3. 终极兜底：'system'（与现有数据兼容）

    配置示例（写入 backend/.env）：
        SCHEDULER_USER_ID=317efe5a-4a56-4ef2-879b-c96fc7593c08
    """
    env_user = os.environ.get("SCHEDULER_USER_ID")
    if env_user:
        return env_user

    try:
        from app.models.auth_models import User
        admin = db.query(User).filter_by(role="admin").first()
        if admin:
            return admin.user_id
    except Exception as e:
        logger.warning(f"[ccusage-scheduler] 查询 admin 用户失败: {e}，fallback 到 'system'")

    return "system"
```

- [ ] **Step 2: 验证 2 个 scheduler 测试通过**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_ccusage_scheduler.py -v
```

**Expected**：2 passed

- [ ] **Step 3: 不 commit**

---

## Task 8: 在 `sync_token_usage_v2` 中暴露公开 API + 添加 `/refresh-ccusage` 端点

**Files:**
- Modify: `backend/app/services/token_usage_sync_service.py`（在文件末尾追加 `sync_token_usage_v2` 公开 API）
- Modify: `backend/app/routes/token_usage.py:1060` 附近（添加新端点）

- [ ] **Step 1: 在 `token_usage_sync_service.py` 文件末尾添加 `sync_token_usage_v2` 公开函数**

在 Task 5 追加的 `_run_ccusage_v2_sync` 之后添加：

```python
def sync_token_usage_v2(
    db,
    user_id: str,
    device_id: str,
    device_name: str,
    since: str,
    until: str,
) -> int:
    """公开 API：v2 ccusage 同步入口，供 scheduler 和手动端点使用。

    Args:
        db: SQLAlchemy session
        user_id: 用户 ID
        device_id: 设备 ID
        device_name: 设备名
        since: 起始日期 YYYY-MM-DD
        until: 结束日期 YYYY-MM-DD

    Returns:
        同步的记录数
    """
    from datetime import date as _date
    since_date = _date.fromisoformat(since)
    until_date = _date.fromisoformat(until)
    return _run_ccusage_v2_sync(
        db=db,
        user_id=user_id,
        device_id=device_id,
        device_name=device_name,
        since_date=since_date,
        until_date=until_date,
    )
```

- [ ] **Step 2: 在 `routes/token_usage.py` 添加新端点**

在 `routes/token_usage.py` 的导入区追加：

```python
import os  # 现有文件可能未导入，按需添加
from app.services.ccusage_scheduler import get_sync_lock
from app.services.token_usage_sync_service import sync_token_usage_v2
```

并扩展 `from app.utils.device_id import get_device_id` 为：

```python
from app.utils.device_id import get_device_id, get_device_display_name
```

找到 `routes/token_usage.py` 现有的 `@router.post("/sync")` 端点（约 line 1057），在其之前添加：

```python
@router.post("/refresh-ccusage")
async def refresh_ccusage_endpoint(
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """手动触发 ccusage 同步（v2 数据源）。同步运行，等待完成后返回结果。"""
    # 鉴权：复用现有 get_current_user_id 助手（与 /sync 端点同款）
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    if os.environ.get("DESKTOP_MODE") == "1":
        raise HTTPException(403, "桌面模式不支持手动同步")

    lock = get_sync_lock()
    if lock.locked():
        raise HTTPException(429, "同步进行中，请稍后重试")

    db = SessionLocal()
    try:
        today = date.today().isoformat()
        count = await asyncio.to_thread(
            sync_token_usage_v2,
            db=db,
            user_id=user_id,
            device_id=get_device_id(),
            device_name=get_device_display_name(),
            since=today,
            until=today,
        )
        return {"success": True, "synced_records": count, "date": today}
    except Exception as e:
        logger.error(f"[ccusage-manual] 手动同步失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")
    finally:
        db.close()
```

（`get_current_user_id` 已从 `app.routes.auth` 导入（line 31），无需新加 import；`os`、`date`、`asyncio`、`SessionLocal`、`get_device_id`、`logger`、`HTTPException` 全部已在文件中；新增的 `get_sync_lock` 和 `sync_token_usage_v2` 见 Step 1 的 import 追加）

- [ ] **Step 3: 跑全部测试，确认未破坏**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/ -v --tb=short -k "token_usage or ccusage or parse_ccusage or usage_fetcher"
```

**Expected**：所有相关测试通过

- [ ] **Step 4: 不 commit**

---

## Task 9: 启动 scheduler + 添加 requirements 依赖

**Files:**
- Modify: `backend/app/main.py`（lifespan 中启动 scheduler）
- Modify: `backend/requirements.txt`（加 apscheduler）

- [ ] **Step 1: 在 `requirements.txt` 添加 apscheduler**

在文件末尾追加：

```
apscheduler>=3.10,<4.0
```

- [ ] **Step 2: 安装新依赖**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
pip install -r requirements.txt
```

**Expected**：Successfully installed apscheduler-X.X.X

- [ ] **Step 3: 在 `main.py` 的 `lifespan` 中启动 scheduler**

定位 `main.py` 中的 `@asynccontextmanager` lifespan 函数（如不存在则添加）。在 `yield` 之前添加：

```python
    from app.services.ccusage_scheduler import init_scheduler, shutdown_scheduler
    init_scheduler()
```

在 `yield` 之后添加：

```python
    shutdown_scheduler()
```

（如项目已有 `lifespan` 函数，在其 yield 前后插入上述两行）

- [ ] **Step 4: 验证后端启动无报错**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
python dev_services.py restart --backend-only
sleep 5
python dev_services.py logs backend | grep -i "scheduler\|ccusage" | tail -10
```

**Expected**：找到形如 `[ccusage-scheduler] 启动成功，每天 00:05 触发 daily_sync_job` 的日志行

- [ ] **Step 5: 不 commit**

---

## Task 10: 前端"同步"按钮

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`（在工具栏添加"同步"按钮）

- [ ] **Step 1: 定位 TokenUsage.tsx 工具栏区域**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
grep -n "刷新\|refresh\|refreshAllData\|handleRefresh" frontend/src/components/Tools/TokenUsage.tsx | head -10
```

找到工具栏（page header / filter area）所在位置。

- [ ] **Step 2: 添加 handleSync 状态和处理函数**

在 TokenUsage.tsx 的 hooks/state 区域添加：

```tsx
const [syncing, setSyncing] = useState(false);
const [syncMessage, setSyncMessage] = useState<string | null>(null);

const handleSync = async () => {
    setSyncing(true);
    setSyncMessage(null);
    try {
        const token = localStorage.getItem('token') || '';
        const res = await fetch('/api/token-usage/refresh-ccusage', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();
        setSyncMessage(`同步完成: ${data.synced_records} 条`);
        // 重新拉明细表 + 饼图
        refetch();
    } catch (e: any) {
        setSyncMessage(`同步失败: ${e.message}`);
    } finally {
        setSyncing(false);
    }
};
```

（如该文件已有 refetch 函数则复用，否则需添加 `const refetch = async () => { ... }` 包装现有 fetch 逻辑）

- [ ] **Step 3: 在工具栏添加"同步"按钮**

在合适位置（page header 右侧 / filter 区域）添加：

```tsx
<button
    onClick={handleSync}
    disabled={syncing}
    className="px-3 py-1.5 rounded bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 text-sm text-white"
>
    {syncing ? '同步中...' : '同步'}
</button>
{syncMessage && (
    <span className={`ml-2 text-xs ${syncMessage.startsWith('同步完成') ? 'text-green-400' : 'text-red-400'}`}>
        {syncMessage}
    </span>
)}
```

- [ ] **Step 4: 验证前端构建无错**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run build 2>&1 | tail -20
```

**Expected**：构建成功，0 TS 错误

- [ ] **Step 5: 不 commit**

---

## Task 11: 添加回填脚本

**Files:**
- Create: `backend/scripts/backfill_ccusage.py`

- [ ] **Step 1: 创建 `backfill_ccusage.py`**

```python
"""一次性全量回填脚本 — 部署时跑一次。

Usage:
    python -m backend.scripts.backfill_ccusage
    python -m backend.scripts.backfill_ccusage --since 2024-01-01 --batch-days 90
"""
import argparse
import logging
import sys
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="全量回填 ccusage 数据")
    parser.add_argument("--since", default="2024-01-01", help="起始日期 YYYY-MM-DD")
    parser.add_argument("--batch-days", type=int, default=90, help="每批天数")
    args = parser.parse_args()

    if os.environ.get("DESKTOP_MODE") == "1":
        logger.error("桌面模式不支持回填")
        sys.exit(1)

    from app.models.base import SessionLocal
    from app.services.token_usage_sync_service import sync_token_usage_v2
    from app.utils.device_id import get_device_id, get_device_display_name

    today = date.today()
    since = date.fromisoformat(args.since)
    total_synced = 0
    cursor = since

    while cursor <= today:
        until = min(cursor + timedelta(days=args.batch_days - 1), today)
        logger.info(f"回填 {cursor.isoformat()} ~ {until.isoformat()} ...")
        db = SessionLocal()
        try:
            count = sync_token_usage_v2(
                db=db,
                user_id="system_backfill",
                device_id=get_device_id(),
                device_name=get_device_display_name(),
                since=cursor.isoformat(),
                until=until.isoformat(),
            )
            total_synced += count
            logger.info(f"  本批同步 {count} 条")
        except Exception as e:
            logger.error(f"  本批失败: {e}", exc_info=True)
        finally:
            db.close()
        cursor = until + timedelta(days=1)

    logger.info(f"回填完成: 总计 {total_synced} 条")


if __name__ == "__main__":
    import os
    main()
```

- [ ] **Step 2: 验证脚本可执行（dry run 模式，--help）**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m scripts.backfill_ccusage --help
```

**Expected**：显示 usage 帮助，无报错

- [ ] **Step 3: 不 commit**

---

## Task 12: 手动 E2E 验证

**Files:** 无

- [ ] **Step 1: 重启后端让所有改动生效**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
python dev_services.py restart --backend-only
sleep 5
```

- [ ] **Step 2: 验证 scheduler 已启动**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
python dev_services.py logs backend | grep -i "ccusage-scheduler" | tail -3
```

**Expected**：找到 `[ccusage-scheduler] 启动成功`

- [ ] **Step 3: 调手动端点（带 token）**

```bash
TOKEN=$(curl -s -X POST http://localhost:19092/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Peanut2817*#"}' 2>/dev/null | python -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)

# 如上失败，从浏览器 localStorage 复制 token 替换
curl -X POST http://localhost:19092/api/token-usage/refresh-ccusage \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json"
```

**Expected**：
```json
{"success":true,"synced_records":N,"date":"2026-06-05"}
```
（N ≥ 1，至少有 (opencode, minimax-m3-free) + (claude, claude-opus-4-8) 等多行）

- [ ] **Step 4: 查 PostgreSQL 验证数据**

```bash
PGPASSWORD='Peanut2817*#' psql -h 39.107.229.30 -U postgres -d tools -c "
  SELECT source, model, total_tokens, total_cost, record_date
  FROM token_usage_records
  WHERE record_date = '2026-06-05'
  ORDER BY source, total_tokens DESC;
"
```

**Expected**：至少 3 行，包含 (claude, ...)、(opencode, ...) 等不同 source

- [ ] **Step 5: 浏览器前端验证**

访问 `http://localhost:5178/tools/token-usage`：
- 工具栏显示"同步"按钮
- 点击按钮 → 显示"同步中..."
- 完成后显示"同步完成: N 条"
- 明细表自动刷新，显示 Claude Code + OpenCode 多行
- Console 无报错

截图保存到 `docs/superpowers/e2e-evidence/2026-06-05-ccusage-unified-data-flow/`：
- `01-sync-button.png`（工具栏）
- `02-after-sync.png`（同步后明细表）
- `03-source-claude.png`（筛选 Claude）
- `04-source-opencode.png`（筛选 OpenCode）

- [ ] **Step 6: 跑全量回填（可选，验证脚本可用）**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m scripts.backfill_ccusage --since 2026-01-01 --batch-days 30
```

**Expected**：日志显示 6 批（2026-01~02, 03, 04, 05, 06-上, 06-下），总同步数 N > 200

- [ ] **Step 7: 验证回填后旧 34+217 记录被覆盖**

```bash
PGPASSWORD='Peanut2817*#' psql -h 39.107.229.30 -U postgres -d tools -c "
  SELECT source, COUNT(*), MIN(record_date), MAX(record_date)
  FROM token_usage_records
  GROUP BY source
  ORDER BY source;
"
```

**Expected**：opencode 行的 min(record_date) 早于或等于 2026-01-23（覆盖旧 34 条），claude 行的 min 早于或等于 2026-03-15

- [ ] **Step 8: 不 commit**

---

## Task 13: 综合验证 + 用户 commit

**Files:** 无

- [ ] **Step 1: 跑全部 backend 测试**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/ -v --tb=short
```

**Expected**：除已知 pre-existing 失败外全部通过

- [ ] **Step 2: ruff lint 检查**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
ruff check app/utils/usage_fetcher_v2.py app/services/ccusage_scheduler.py app/services/token_usage_sync_service.py scripts/backfill_ccusage.py tests/test_parse_ccusage_records.py tests/test_usage_fetcher_v2.py tests/test_ccusage_scheduler.py
```

**Expected**：无新增 lint 错误

- [ ] **Step 3: 前端构建验证**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run build 2>&1 | tail -5
```

**Expected**：build success，0 TS 错误

- [ ] **Step 4: 检查 git status**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git status
```

**Expected 修改文件**：
- `backend/app/utils/usage_fetcher_v2.py`（新增）
- `backend/app/services/ccusage_scheduler.py`（新增）
- `backend/app/services/token_usage_sync_service.py`（修改）
- `backend/app/main.py`（修改）
- `backend/app/routes/token_usage.py`（修改）
- `backend/scripts/backfill_ccusage.py`（新增）
- `backend/tests/test_parse_ccusage_records.py`（新增）
- `backend/tests/test_usage_fetcher_v2.py`（新增）
- `backend/tests/test_ccusage_scheduler.py`（新增）
- `backend/requirements.txt`（修改）
- `frontend/src/components/Tools/TokenUsage.tsx`（修改）
- `docs/superpowers/specs/2026-06-05-ccusage-unified-data-flow-design.md`（新增，待用户决定是否 commit）

- [ ] **Step 5: 检查 git diff 概览**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git diff --stat
```

**Expected**：~12 个文件，+800/-50 行左右

- [ ] **Step 6: 通知用户 commit**

**重要**：CLAUDE.md 禁止自动 commit，本任务**不**自动 commit。

向用户报告：
- 新增文件数（5 个 .py + 3 个 test + 1 个 spec）
- 修改文件数（5 个 .py + 1 个 .tsx + 1 个 requirements.txt）
- 新增测试数量（6 单元 + 2 集成 + 2 scheduler = 10 个测试）
- E2E 验证结果（DB 行数 + 截图 + 回填后总数）
- 建议 commit message：
  ```
  feat(backend): 重构 token-usage 为 ccusage 统一数据源
  
  - 新增 UsageFetcherV2 统一封装 ccusage CLI
  - 新增 _parse_ccusage_records 解析 (date, agent, model) 三元组
  - 新增 ccusage_scheduler APScheduler 每天 00:05 同步
  - 新增 POST /api/token-usage/refresh-ccusage 手动端点
  - 新增 backfill_ccusage.py 全量回填脚本
  - 前端 Token Usage 页面新增"同步"按钮
  - source 字段保留 agent 语义（claude/opencode/openclaw/...）兼容现有前端
  ```
- 提示用户："代码已就绪，请确认是否执行 commit"

---

## Self-Review Checklist

- [x] Spec 11 个验收标准 → 13 个 Task 全部覆盖
- [x] 无 TBD/TODO/"类似 Task N"
- [x] 文件路径精确
- [x] 命令带预期输出
- [x] 现有 6 个 test_token_usage_*.py 文件不被破坏（Task 2/5 验证步骤）
- [x] DRY：复用 `_safe_int` / `_safe_float` / `_calc_total_tokens` / `_upsert_records`
- [x] YAGNI：未引入新 DB schema、未改 API 路径（除新增 1 个端点）
- [x] TDD：Task 1/3/6 写测试验证 RED，Task 2/4/7 实现验证 GREEN
- [x] Type 一致性：`sync_token_usage_v2` 签名在 Task 5/7/8/11 中保持一致
- [x] Function name 一致性：`_parse_ccusage_records`（Task 1 定义）、`UsageFetcherV2.fetch_ccusage_daily`（Task 3 定义）、`daily_sync_job`（Task 6 定义）— 后续 Task 引用全部匹配
- [x] 频繁 commit：12 个 task 由用户在 Task 13 一次性 commit
- [x] 风险缓解：spec 中 7 项风险全部有缓解措施
