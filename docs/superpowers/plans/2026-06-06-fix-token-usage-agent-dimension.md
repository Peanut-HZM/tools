# 修复 Token Usage Agent 维度统计缺失

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 ccusage v2 同步时将所有数据标记为 source="v2" 导致 Agent 维度统计失效的问题。

**Architecture:** 修改 `_run_ccusage_v2_sync` 将解析后的记录按 agent 分组，分别调用 `_upsert_records` 传入正确的 source。同时补全 `_map_source_to_tool` 中缺失的 agent 映射。

**Tech Stack:** Python 3.10+, SQLAlchemy

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/services/token_usage_sync_service.py` | 修改 | `_run_ccusage_v2_sync` 按 agent 分组；`_map_source_to_tool` 补全映射 |

---

### Task 1: 修改 `_run_ccusage_v2_sync` 按 Agent 分组同步

**Files:**
- Modify: `backend/app/services/token_usage_sync_service.py:571-624`

- [ ] **Step 1: 读取当前 `_run_ccusage_v2_sync` 实现**

  确认当前代码结构（约第 571-624 行）：
  - 调用 `UsageFetcherV2.fetch_ccusage_daily()` 获取数据
  - 调用 `_parse_ccusage_records()` 解析记录
  - 当前以 `source="v2"` 调用 `_upsert_records()`

- [ ] **Step 2: 修改 `_run_ccusage_v2_sync` 按 agent 分组**

  找到以下代码（约第 617-624 行）：
  ```python
  records = _parse_ccusage_records(daily_list, agent_models_dict)
  if not records:
      logger.info(f"[ccusage-v2] 解析后 0 条记录（{since_str} ~ {until_str}）")
      return 0

  count = _upsert_records(db, user_id, device_id, "v2", records, device_name)
  logger.info(f"[ccusage-v2] {since_str} ~ {until_str} 同步 {count} 条")
  return count
  ```

  替换为：
  ```python
  records = _parse_ccusage_records(daily_list, agent_models_dict)
  if not records:
      logger.info(f"[ccusage-v2] 解析后 0 条记录（{since_str} ~ {until_str}）")
      return 0

  # 按 agent 分组，分别 upsert，确保每个 Agent 有正确的 source/tool_id/tool_name
  from itertools import groupby

  records_sorted = sorted(records, key=lambda r: r["source"])
  total_count = 0
  for agent, group in groupby(records_sorted, key=lambda r: r["source"]):
      agent_records = list(group)
      count = _upsert_records(db, user_id, device_id, agent, agent_records, device_name)
      total_count += count
      logger.info(f"[ccusage-v2] {agent}: 同步 {count} 条")

  logger.info(f"[ccusage-v2] {since_str} ~ {until_str} 总计同步 {total_count} 条")
  return total_count
  ```

- [ ] **Step 3: 验证语法**

  Run: `cd backend && python -m py_compile app/services/token_usage_sync_service.py`
  Expected: 无语法错误

- [ ] **Step 4: Commit**

  ```bash
  git add backend/app/services/token_usage_sync_service.py
  git commit -m "feat: v2 同步按 Agent 分组，恢复工具维度统计"
  ```

---

### Task 2: 补全 `_map_source_to_tool` 中缺失的 Agent 映射

**Files:**
- Modify: `backend/app/services/token_usage_sync_service.py:89-99`

- [ ] **Step 1: 找到当前 `_map_source_to_tool` 实现**

  当前代码（约第 89-99 行）：
  ```python
  def _map_source_to_tool(source: str) -> dict:
      source_value = source or "unknown"
      mapping = {
          "claude": {"tool_id": "claude-code", "tool_name": "Claude Code"},
          "opencode": {"tool_id": "opencode", "tool_name": "OpenCode"},
          "codex": {"tool_id": "codex", "tool_name": "Codex"},
      }
      return mapping.get(
          source_value,
          {"tool_id": source_value, "tool_name": source_value},
      )
  ```

- [ ] **Step 2: 补全所有 Agent 映射**

  替换 mapping 为完整映射（与 `AGENT_DISPLAY_NAMES` 保持一致）：
  ```python
  def _map_source_to_tool(source: str) -> dict:
      source_value = source or "unknown"
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
      return mapping.get(
          source_value,
          {"tool_id": source_value, "tool_name": source_value},
      )
  ```

- [ ] **Step 3: 验证语法**

  Run: `cd backend && python -m py_compile app/services/token_usage_sync_service.py`
  Expected: 无语法错误

- [ ] **Step 4: Commit**

  ```bash
  git add backend/app/services/token_usage_sync_service.py
  git commit -m "feat: 补全 _map_source_to_tool 中所有 Agent 映射"
  ```

---

### Task 3: 端到端验证

**Files:**
- 无需修改文件，仅验证

- [ ] **Step 1: 重启后端服务**

  ```bash
  python dev-services.py restart backend
  ```

- [ ] **Step 2: 清理旧数据并重新同步**

  1. 打开浏览器访问 http://localhost:5178/tools/token-usage
  2. 点击"清理"按钮清理当前用户的旧数据
  3. 点击"同步数据"按钮重新拉取 ccusage 数据

- [ ] **Step 3: 验证工具维度**

  **预期结果**：
  - 明细表格"工具"列显示不同的 Agent 名称（Claude Code / OpenCode / OpenClaw / Codex 等），不再是全部 "Claude Code"
  - 设备/工具/模型占比饼图正确显示各维度数据
  - 筛选下拉框"工具"选项中有多个 Agent 可选

- [ ] **Step 4: 验证数据库记录**

  ```bash
  cd backend
  .\venv\Scripts\python.exe -c "
  from app.models.base import SessionLocal
  from app.models.token_usage_models import TokenUsageRecord
  from sqlalchemy import func
  db = SessionLocal()
  sources = db.query(TokenUsageRecord.source, func.count()).group_by(TokenUsageRecord.source).all()
  for s, c in sources:
      print(f'{s}: {c} 条')
  db.close()
  "
  ```
  **预期结果**：显示多个 source（claude / opencode / openclaw / codex 等），不再有 source="v2"

- [ ] **Step 5: Commit（如无问题则无需额外提交）**

---

## Self-Review Checklist

- [ ] **Spec 覆盖**：v2 按 agent 分组 ✅、_map_source_to_tool 补全 ✅
- [ ] **无占位符**：所有步骤包含完整代码
- [ ] **类型一致**：函数签名未改变
