---
author: Peanut
created_at: 2026-06-06
purpose: 修复 Token Usage v2 同步时 Agent 维度丢失导致工具统计不显示的问题
---

# 修复 Token Usage Agent 维度统计缺失

## 背景

ccusage v2 统一数据源同步时，`_run_ccusage_v2_sync` 将所有数据以 `source="v2"` 传入 `_upsert_records`，导致：
1. 数据库中所有记录的 `source` 都是 "v2"
2. `_build_dimension_fields("v2", ...)` 返回 `tool_id="v2"`, `tool_name="v2"`
3. 前端无法区分 claude/opencode/openclaw/codex 等不同 Agent 的数据
4. 工具占比、模型占比等统计维度失效

## 目标

让 v2 同步的数据正确按 Agent（claude/opencode/openclaw/codex 等）区分，恢复工具/模型/占比统计。

## 方案

采用**方案 B：v2 同步前按 Agent 拆分数据**。

### 核心修改

在 `_run_ccusage_v2_sync` 中，将 `_parse_ccusage_records` 返回的记录按 `source`（agent）字段分组，然后对每个 agent 分别调用 `_upsert_records`：

```python
records = _parse_ccusage_records(daily_list, agent_models_dict)
if not records:
    return 0

# 按 agent 分组，分别 upsert
total_count = 0
from itertools import groupby
records_sorted = sorted(records, key=lambda r: r["source"])
for agent, group in groupby(records_sorted, key=lambda r: r["source"]):
    agent_records = list(group)
    count = _upsert_records(db, user_id, device_id, agent, agent_records, device_name)
    total_count += count
```

### 辅助修改

**`_map_source_to_tool`** 补充缺失的 agent 映射：

```python
mapping = {
    "claude": {"tool_id": "claude-code", "tool_name": "Claude Code"},
    "opencode": {"tool_id": "opencode", "tool_name": "OpenCode"},
    "codex": {"tool_id": "codex", "tool_name": "Codex"},
    "openclaw": {"tool_id": "openclaw", "tool_name": "OpenClaw"},
    "amp": {"tool_id": "amp", "tool_name": "Amp"},
    "droid": {"tool_id": "droid", "tool_name": "Droid"},
    "codebuff": {"tool_id": "codebuff", "tool_name": "Codebuff"},
    "hermes": {"tool_id": "hermes", "tool_name": "Hermes"},
    "pi": {"tool_id": "pi", "tool_name": "pi"},
    "goose": {"tool_id": "goose", "tool_name": "Goose"},
    "kilo": {"tool_id": "kilo", "tool_name": "Kilo"},
    "copilot": {"tool_id": "copilot", "tool_name": "GitHub Copilot"},
    "gemini": {"tool_id": "gemini", "tool_name": "Gemini"},
    "kimi": {"tool_id": "kimi", "tool_name": "Kimi"},
    "qwen": {"tool_id": "qwen", "tool_name": "Qwen"},
}
```

### 数据迁移

旧数据（source="v2"）需要清理后重新同步。用户可通过页面上的"清理数据"按钮清理，然后点击"同步数据"重新拉取。

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/services/token_usage_sync_service.py` | 修改 | `_run_ccusage_v2_sync` 按 agent 分组；`_map_source_to_tool` 补全映射 |

## 验收标准

1. v2 同步后，数据库中不同 Agent 的数据有正确的 `source`、`tool_id`、`tool_name`
2. 前端 Token Usage 页面工具列正确显示各 Agent 名称（Claude Code / OpenCode / OpenClaw / Codex 等）
3. 工具占比、模型占比饼图正确显示各维度数据
