# 修复 OpenCode 数据丢失 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 token-usage 同步逻辑中 opencode 数据丢失的双重 bug，让前端明细表同时显示 Claude Code 和 OpenCode 记录。

**Architecture:** TDD 模式 — 4 个新单元测试覆盖 parser 的 opencode-usage 路径 + 1 个集成测试覆盖 CLI 调用参数。最小变更：1 处 `--by=model` → `--by=day` + parser 增加 snake_case 嵌套 tokens 路径（ccusage 路径完全保留）。日志增强：0 条同步降为 WARNING。

**Tech Stack:** Python 3.10+、pytest、unittest.mock、FastAPI（仅跑测试，不动 API 层）、PostgreSQL（手动 E2E 验证）

**前置条件确认**：
- 仓库根目录：`/Users/huazhongmin/IdeaProjects/tools`
- 后端服务运行中（端口 19092）
- 3 个 CLI 工具已安装：`ccusage`、`opencode-usage`、`ccusage-opencode`
- PostgreSQL 可访问（`39.107.229.30:5432/tools`）
- CLAUDE.md 禁止自动 commit/push — 本计划在 Task 7 由用户显式触发

---

## File Structure

| 文件 | 类型 | 职责 |
|---|---|---|
| `backend/app/utils/usage_fetcher.py:224,230` | MODIFY | 改 `--by=model` → `--by=day`（含 Windows 路径 224） |
| `backend/app/services/token_usage_sync_service.py:179-229` | MODIFY | `_parse_opencode_entries` 新增 opencode-usage 嵌套 `tokens` 路径（path A），保留 ccusage 路径 B/C |
| `backend/app/services/token_usage_sync_service.py:281` | MODIFY | 0 条同步时降为 WARNING 日志 |
| `backend/tests/test_parse_opencode_entries.py` | CREATE | 4 个单元测试覆盖 path A（opencode-usage 嵌套 tokens）+ path B/C 回归 |
| `backend/tests/test_fetch_opencode_current_uses_by_day.py` | CREATE | 1 个集成测试覆盖 CLI cmd 包含 `--by=day` |

---

## Task 1: 添加 `_parse_opencode_entries` 单元测试（RED）

**Files:**
- Create: `backend/tests/test_parse_opencode_entries.py`

- [ ] **Step 1: 创建测试文件，写 4 个失败测试**

```python
"""测试 _parse_opencode_entries 支持 opencode-usage + ccusage-opencode 双格式。"""
from datetime import date

from app.services.token_usage_sync_service import _parse_opencode_entries


def test_parse_opencode_usage_by_day_format():
    """opencode-usage --by=day 返回 snake_case 嵌套 tokens 结构"""
    entries = [
        {
            "label": "2026-06-05",
            "calls": 479,
            "tokens": {
                "input": 2459951,
                "output": 243833,
                "reasoning": 0,  # 应被忽略（DB 无此字段）
                "cache_read": 58837404,
                "cache_write": 1616736,
                "total": 63157924,
            },
            "cost": 0,
        }
    ]
    result = _parse_opencode_entries(entries)
    assert len(result) == 1
    record = result[0]
    assert record["record_date"] == date(2026, 6, 5)
    assert record["model"] == "_total"
    assert record["input_tokens"] == 2459951
    assert record["output_tokens"] == 243833
    assert record["cache_creation_tokens"] == 1616736
    assert record["cache_read_tokens"] == 58837404
    assert record["total_tokens"] == 63157924
    assert record["total_cost"] == 0.0
    # 验证 reasoning 没被误存为 input_tokens
    assert record["input_tokens"] != 0


def test_parse_ccusage_opencode_daily_format_top_level():
    """ccusage-opencode daily 返回 camelCase 顶层字段（回归保护）"""
    entries = [
        {
            "date": "2026-01-23",
            "inputTokens": 137167,
            "outputTokens": 1226,
            "cacheCreationTokens": 0,
            "cacheReadTokens": 78528,
            "totalTokens": 216921,
            "totalCost": 0.0125916,
        }
    ]
    result = _parse_opencode_entries(entries)
    assert len(result) == 1
    record = result[0]
    assert record["record_date"] == date(2026, 1, 23)
    assert record["model"] == "_total"
    assert record["input_tokens"] == 137167
    assert record["output_tokens"] == 1226
    assert record["cache_creation_tokens"] == 0
    assert record["cache_read_tokens"] == 78528
    assert record["total_tokens"] == 216921
    assert record["total_cost"] == 0.0125916


def test_parse_opencode_usage_with_invalid_date_label():
    """opencode-usage --by=model 异常残留的模型名 label 应当跳过"""
    entries = [
        {
            "label": "minimax-m3-free",  # 不是日期
            "calls": 1147,
            "tokens": {"input": 4699352, "output": 476611, "total": 140583376},
            "cost": 0,
        }
    ]
    result = _parse_opencode_entries(entries)
    assert result == []


def test_parse_empty_entries():
    """空 entries 返回空列表"""
    assert _parse_opencode_entries([]) == []
```

- [ ] **Step 2: 运行测试，验证 2 个失败（新格式未支持）**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_parse_opencode_entries.py -v
```

**Expected output**（含 2 FAIL）：
```
test_parse_opencode_usage_by_day_format FAILED
test_parse_ccusage_opencode_daily_format_top_level PASSED  # 回归保护，现状已通过
test_parse_opencode_usage_with_invalid_date_label PASSED  # 现状已通过
test_parse_empty_entries PASSED  # 现状已通过
```

- [ ] **Step 3: 不 commit**（先等 Task 2 把测试跑绿）

---

## Task 2: 实现 opencode-usage 嵌套 tokens 路径（GREEN）

**Files:**
- Modify: `backend/app/services/token_usage_sync_service.py:179-229`

- [ ] **Step 1: 替换 `_parse_opencode_entries` 函数体**

将 `token_usage_sync_service.py:179-229` 的整个函数替换为：

```python
def _parse_opencode_entries(entries: list[dict]) -> list[dict]:
    """解析 OpenCode CLI 输出为结构化数据

    支持三种数据源格式（按优先级自动识别）：
    1. opencode-usage --by=day:   {label: "YYYY-MM-DD", tokens: {input, output, cache_read, cache_write, total, reasoning}, cost}
    2. ccusage-opencode models 子列表: {date, models: [{modelName, inputTokens, ...}]}
    3. ccusage-opencode daily 顶层:    {date, inputTokens, outputTokens, ...}
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
            if total_tokens == 0:
                total_tokens = _calc_total_tokens(
                    input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
                )
            results.append({
                "record_date": record_date,
                "model": "_total",  # CLI 不暴露每日+模型维度
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_tokens": cache_creation_tokens,
                "cache_read_tokens": cache_read_tokens,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
            })
            continue

        # 路径 B: ccusage-opencode models 子列表（保留现有逻辑）
        models = entry.get("models", [])
        if models:
            for mod in models:
                model_name = mod.get("modelName") or mod.get("model") or mod.get("name") or "unknown"
                input_tokens = _safe_int(mod, "inputTokens", "input_tokens")
                output_tokens = _safe_int(mod, "outputTokens", "output_tokens")
                cache_creation_tokens = _safe_int(mod, "cacheCreationTokens", "cache_creation_tokens")
                cache_read_tokens = _safe_int(mod, "cacheReadTokens", "cache_read_tokens")
                total_tokens = _safe_int(mod, "totalTokens", "total_tokens")
                if total_tokens == 0:
                    total_tokens = _calc_total_tokens(input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens)
                results.append({
                    "record_date": record_date,
                    "model": model_name,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_creation_tokens": cache_creation_tokens,
                    "cache_read_tokens": cache_read_tokens,
                    "total_tokens": total_tokens,
                    "total_cost": _safe_float(mod, "totalCost", "costUSD", "cost"),
                })
            continue

        # 路径 C: ccusage-opencode daily 顶层字段（保留现有逻辑）
        input_tokens = _safe_int(entry, "inputTokens", "input_tokens")
        output_tokens = _safe_int(entry, "outputTokens", "output_tokens")
        cache_creation_tokens = _safe_int(entry, "cacheCreationTokens", "cache_creation_tokens")
        cache_read_tokens = _safe_int(entry, "cacheReadTokens", "cache_read_tokens")
        total_tokens = _safe_int(entry, "totalTokens", "total_tokens")
        if total_tokens == 0:
            total_tokens = _calc_total_tokens(input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens)
        results.append({
            "record_date": record_date,
            "model": entry.get("model") or "_total",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_tokens": cache_creation_tokens,
            "cache_read_tokens": cache_read_tokens,
            "total_tokens": total_tokens,
            "total_cost": _safe_float(entry, "totalCost", "costUSD", "cost"),
        })
    return results
```

- [ ] **Step 2: 验证 4 个测试全部通过**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_parse_opencode_entries.py -v
```

**Expected**：4 passed

- [ ] **Step 3: 验证现有 token_usage 测试未破坏**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_token_usage_*.py -v
```

**Expected**：所有现有测试通过（含 6 个 test_token_usage_*.py 文件）

- [ ] **Step 4: 不 commit**（后续 Task 一起 commit）

---

## Task 3: 添加 `_fetch_opencode_current` 集成测试（RED）

**Files:**
- Create: `backend/tests/test_fetch_opencode_current_uses_by_day.py`

- [ ] **Step 1: 写集成测试，验证 cmd 包含 `--by=day`**

```python
"""测试 UsageFetcher._fetch_opencode_current 使用 --by=day 而非 --by=model。"""
from unittest.mock import patch, MagicMock

from app.utils.usage_fetcher import UsageFetcher


def test_fetch_opencode_current_uses_by_day_default():
    """默认调用应传 --by=day（修复 Bug 1）"""
    fake_result = {
        "period": "Last 7 days",
        "total": {"label": "total", "calls": 0, "tokens": {}, "cost": 0},
        "rows": [
            {
                "label": "2026-06-05",
                "calls": 479,
                "tokens": {"input": 2459951, "output": 243833, "cache_read": 58837404, "cache_write": 1616736, "total": 63157924},
                "cost": 0,
            }
        ],
    }

    with patch("app.utils.usage_fetcher.shutil.which", return_value="/usr/local/bin/opencode-usage"), \
         patch("app.utils.usage_fetcher._run_cmd", return_value=fake_result) as mock_run, \
         patch("app.utils.usage_fetcher._get_from_cache", return_value=None), \
         patch("app.utils.usage_fetcher._set_cache"):
        UsageFetcher._fetch_opencode_current(days=7)

    # 断言 cmd 包含 --by=day
    cmd = mock_run.call_args[0][0]
    assert "--by=day" in cmd
    assert "--by=model" not in cmd, f"cmd 仍包含 --by=model: {cmd}"


def test_fetch_opencode_current_respects_explicit_by():
    """显式传 by 参数时不被默认值覆盖"""
    fake_result = {
        "period": "Last 7 days",
        "total": {"label": "total", "calls": 0, "tokens": {}, "cost": 0},
        "rows": [],
    }

    with patch("app.utils.usage_fetcher.shutil.which", return_value="/usr/local/bin/opencode-usage"), \
         patch("app.utils.usage_fetcher._run_cmd", return_value=fake_result) as mock_run, \
         patch("app.utils.usage_fetcher._get_from_cache", return_value=None), \
         patch("app.utils.usage_fetcher._set_cache"):
        UsageFetcher._fetch_opencode_current(days=7, by="model")

    cmd = mock_run.call_args[0][0]
    assert "--by=model" in cmd
    assert "--by=day" not in cmd
```

- [ ] **Step 2: 运行测试，验证第 1 个失败**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_fetch_opencode_current_uses_by_day.py -v
```

**Expected output**（含 1 FAIL）：
```
test_fetch_opencode_current_uses_by_day_default FAILED
test_fetch_opencode_current_respects_explicit_by PASSED
```

- [ ] **Step 3: 不 commit**（先等 Task 4 把测试跑绿）

---

## Task 4: 修复 `usage_fetcher.py` 默认 `--by=day`（GREEN）

**Files:**
- Modify: `backend/app/utils/usage_fetcher.py:224-230`

- [ ] **Step 1: 改 line 230 的 `--by=model` 为 `--by=day`**

将 `usage_fetcher.py:230`：

```python
        else:
            cmd.append("--by=model")
```

替换为：

```python
        else:
            cmd.append("--by=day")
```

- [ ] **Step 2: 验证集成测试全部通过**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_fetch_opencode_current_uses_by_day.py -v
```

**Expected**：2 passed

- [ ] **Step 3: 跑所有 backend 测试，确认未破坏现有逻辑**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_token_usage_*.py tests/test_parse_opencode_entries.py tests/test_fetch_opencode_current_uses_by_day.py -v
```

**Expected**：所有测试通过（含 6 个 test_token_usage_*.py + 2 个新文件）

- [ ] **Step 4: 不 commit**（后续 Task 一起 commit）

---

## Task 5: 0 条同步时降为 WARNING 日志

**Files:**
- Modify: `backend/app/services/token_usage_sync_service.py:281` 附近

- [ ] **Step 1: 定位 sync log 位置**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
grep -n "同步.*条记录到数据库" app/services/token_usage_sync_service.py
```

找到 `logger.info(f"[opencode] 同步 {count} 条记录到数据库")` 类似的行。

- [ ] **Step 2: 替换为 conditional log level**

把单行 `logger.info(...)` 替换为：

```python
        if count == 0:
            logger.warning(f"[opencode] 同步 0 条记录到数据库（请检查 CLI 输出和 parser 字段映射）")
        else:
            logger.info(f"[opencode] 同步 {count} 条记录到数据库")
```

（如该行缩进或前缀不同，按现有代码风格调整）

- [ ] **Step 3: 验证相关测试未破坏**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/test_token_usage_*.py -v
```

**Expected**：所有现有测试通过

- [ ] **Step 4: 不 commit**（后续 Task 一起 commit）

---

## Task 6: 手动 E2E 验证

**Files:** 无（仅验证）

- [ ] **Step 1: 重启后端让代码生效**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
python dev_services.py restart --backend-only
```

- [ ] **Step 2: 触发同步（任选其一）**

**方式 A：调用 API 端点**

```bash
curl -X POST http://localhost:19092/api/token-usage/refresh \
  -H "Authorization: Bearer $(cat /tmp/jwt_token 2>/dev/null || echo '')" \
  -H "Content-Type: application/json"
```

**方式 B：等 30 分钟自动同步**（不推荐，耗时）

- [ ] **Step 3: 查 PostgreSQL 验证**

```bash
PGPASSWORD='Peanut2817*#' psql -h 39.107.229.30 -U postgres -d tools -c "
  SELECT record_date, source, model, total_tokens, total_cost
  FROM token_usage_records
  WHERE source='opencode' AND record_date >= '2026-06-01'
  ORDER BY record_date DESC
  LIMIT 10;
"
```

**Expected**：至少返回 1 行 `source='opencode'` 且 `record_date >= '2026-06-01'`

- [ ] **Step 4: 浏览器前端验证**

访问 `http://localhost:5178/tools/token-usage`：
- 明细数据表应同时显示 **Claude Code** 和 **OpenCode** 两类行
- 工具筛选下拉框应包含 "OpenCode" 选项
- Console 无报错

截图保存到 `docs/superpowers/e2e-evidence/2026-06-05-opencode-data-flow-fix/`：
- `01-details-table.png`（全量明细表）
- `02-tool-filter-opencode.png`（筛选 OpenCode）

- [ ] **Step 5: 验证后端日志**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
python dev_services.py logs backend | grep -i "opencode" | tail -20
```

**Expected**：找到形如 `[opencode] 同步 N 条记录到数据库` 的日志行，N > 0（不再是 0）

- [ ] **Step 6: 不 commit**（后续 Task 一起 commit）

---

## Task 7: 综合验证 + 用户 commit

**Files:** 无

- [ ] **Step 1: 跑全部 backend 测试**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
python -m pytest tests/ -v --tb=short
```

**Expected**：全部通过（除已知 pre-existing 失败）

- [ ] **Step 2: ruff lint 检查**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
ruff check app/utils/usage_fetcher.py app/services/token_usage_sync_service.py tests/test_parse_opencode_entries.py tests/test_fetch_opencode_current_uses_by_day.py
```

**Expected**：无新增 lint 错误

- [ ] **Step 3: 检查 git status**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git status
```

**Expected 修改文件**：
- `backend/app/utils/usage_fetcher.py`
- `backend/app/services/token_usage_sync_service.py`
- `backend/tests/test_parse_opencode_entries.py`（新增）
- `backend/tests/test_fetch_opencode_current_uses_by_day.py`（新增）
- `docs/superpowers/specs/2026-06-05-opencode-data-flow-fix-design.md`（新增，待用户决定是否 commit）

- [ ] **Step 4: 检查 git diff 概览**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git diff --stat
```

**Expected**：~4-6 个文件，+120/-30 行左右

- [ ] **Step 5: 通知用户 commit**

**重要**：CLAUDE.md 禁止自动 commit，本任务**不**自动 commit。

向用户报告：
- 修复的 bug 数量（2 个：--by=model 错配 + parser 字段错配）
- 新增测试数量（4 单元 + 2 集成 = 6 个）
- E2E 验证结果（DB 行数 + 截图）
- 提示用户："代码已就绪，请确认是否执行 `git add . && git commit -m 'fix(backend): 修复 opencode 数据丢失 bug'`"

---

## Self-Review Checklist（执行后核对）

- [x] Spec 6 节验收标准 → 6 个 Task 全部对应
- [x] 每个 step 含完整代码，无 "TBD/TODO/类似 Task N"
- [x] 文件路径精确（含行号范围）
- [x] 命令带预期输出
- [x] 现有 6 个 test_token_usage_*.py 文件不被破坏（Task 2/4/5 验证步骤）
- [x] DRY：parser 路径 B/C 完全复用现有代码
- [x] YAGNI：未引入 DB 迁移、未引入新依赖、未改 API
- [x] TDD：Task 1/3 写测试验证 RED，Task 2/4 实现验证 GREEN
- [x] 频繁 commit：5 个代码/测试 task 合并为 1 个 commit（用户触发）
- [x] Type 一致性：`_parse_opencode_entries` 签名 `(list[dict]) -> list[dict]` 在 Task 1 测试和 Task 2 实现中保持一致
