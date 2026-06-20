# Token Usage 饼图修复 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 `/tools/token-usage` 页面四个饼图的设备名不同步、同名设备未合并、工具维度出现 `other`、模型饼图被工具维度污染四个问题。

**Architecture:** 修改集中在后端两个文件（`backend/app/routes/token_usage.py` 的维度聚合函数、`backend/app/services/token_usage_sync_service.py` 的 agent 推断逻辑）+ 前端一个组件（`frontend/src/components/Tools/TokenUsage.tsx` 的饼图数据合并）。设备筛选同步扩展为"同显示名 device_id 集合"。一次性脚本清理历史 `source='other'` 数据。

**Tech Stack:** Python 3.10+ / FastAPI / SQLAlchemy / Pydantic、React 18 / TypeScript / Vite / Recharts、pytest 单元测试、浏览器验证（http://localhost:5178）

---

## 文件结构

| 文件 | 类型 | 职责 |
|------|------|------|
| `backend/app/routes/token_usage.py` | 修改 | 维度聚合 / 筛选过滤 |
| `backend/app/services/token_usage_sync_service.py` | 修改 | ccusage agent 推断，移除 `other` |
| `backend/scripts/cleanup_other_token_usage.py` | 新建 | 一次性清理 `source='other'` 历史数据 |
| `backend/tests/test_token_usage_pie_fixes.py` | 新建 | 后端维度聚合 / agent 推断的单元测试 |
| `frontend/src/components/Tools/TokenUsage.tsx` | 修改 | 前端饼图数据（`modelCostSlices` 合并 source） |

---

### Task 1: 后端单元测试骨架

**Files:**
- Create: `backend/tests/test_token_usage_pie_fixes.py`
- Create: `backend/tests/__init__.py`（如果不存在）

- [ ] **Step 1: 确保 `backend/tests/` 有 `__init__.py`**

```bash
cd backend && ls tests/__init__.py 2>/dev/null || touch tests/__init__.py
```

Expected: 命令成功（存在则输出路径，不存在则创建空文件）。

- [ ] **Step 2: 写入测试骨架文件**

```python
# backend/tests/test_token_usage_pie_fixes.py
"""饼图修复相关后端函数的单元测试。"""
from types import SimpleNamespace

import pytest


# —— 工具函数：_normalize_record_dimensions ——

def test_device_name_from_map_overrides_record_field():
    """修复问题 1：设备名应从 device_names map 取，不再用记录里落库的旧值。"""
    from app.routes.token_usage import _normalize_record_dimensions

    row = SimpleNamespace(
        source="claude",
        tool_id=None,
        tool_name=None,
        device_id="uuid-111",
        device_name="peanut@old-host",  # 同步时落库的旧快照
        model="claude-sonnet-4-5",
        model_display_name="claude-sonnet-4-5",
    )
    device_names = {"uuid-111": "My Renamed Laptop"}

    result = _normalize_record_dimensions(row, device_names)

    assert result["device_id"] == "uuid-111"
    assert result["device_name"] == "My Renamed Laptop"
    assert result["device_name"] != "peanut@old-host"


def test_device_name_falls_back_to_device_id_when_missing():
    """device_names map 里查不到时回退到 device_id 本身。"""
    from app.routes.token_usage import _normalize_record_dimensions

    row = SimpleNamespace(
        source="opencode", tool_id=None, tool_name=None,
        device_id="uuid-orphan", device_name=None,
        model="m1", model_display_name="m1",
    )
    result = _normalize_record_dimensions(row, {})

    assert result["device_name"] == "uuid-orphan"


# —— 工具函数：_build_dimension_data 设备按显示名合并 ——

def test_dimension_data_merges_devices_with_same_display_name():
    """修复问题 2：两个不同 device_id 但显示名相同 → 合并为一个切片。"""
    from app.routes.token_usage import _build_dimension_data

    rows = [
        SimpleNamespace(
            record_date=None, source="claude", tool_id=None, tool_name=None,
            device_id="uuid-A", device_name="My-Laptop",
            model="m1", model_display_name="m1",
            input_tokens=100, output_tokens=50,
            cache_creation_tokens=0, cache_read_tokens=0,
            total_tokens=150, total_cost=0.01,
            updated_at=None, created_at=None,
        ),
        SimpleNamespace(
            record_date=None, source="claude", tool_id=None, tool_name=None,
            device_id="uuid-B", device_name="My-Laptop",  # 同名，不同 UUID
            model="m1", model_display_name="m1",
            input_tokens=200, output_tokens=100,
            cache_creation_tokens=0, cache_read_tokens=0,
            total_tokens=300, total_cost=0.02,
            updated_at=None, created_at=None,
        ),
    ]
    device_names = {"uuid-A": "My-Laptop", "uuid-B": "My-Laptop"}

    dimension_rows, _ = _build_dimension_data(rows, device_names)

    device_slices = dimension_rows["devices"]
    assert len(device_slices) == 1, f"期望 1 个设备切片，实际 {len(device_slices)}"
    assert device_slices[0]["label"] == "My-Laptop"
    assert device_slices[0]["total_tokens"] == 450
    assert device_slices[0]["total_cost"] == pytest.approx(0.03)


# —— 工具函数：_build_dimension_data 模型按纯 model 分组 ——

def test_dimension_data_models_grouped_by_model_only():
    """修复问题 4：模型维度按 model 单字段分组，不再带 tool_id 前缀。"""
    from app.routes.token_usage import _build_dimension_data

    rows = [
        SimpleNamespace(
            record_date=None, source="claude", tool_id="claude-code", tool_name="Claude Code",
            device_id="uuid-A", device_name="Laptop",
            model="claude-sonnet-4-5", model_display_name="claude-sonnet-4-5",
            input_tokens=100, output_tokens=50,
            cache_creation_tokens=0, cache_read_tokens=0,
            total_tokens=150, total_cost=0.01,
            updated_at=None, created_at=None,
        ),
        SimpleNamespace(
            record_date=None, source="opencode", tool_id="opencode", tool_name="OpenCode",
            device_id="uuid-A", device_name="Laptop",
            model="claude-sonnet-4-5", model_display_name="claude-sonnet-4-5",
            input_tokens=200, output_tokens=100,
            cache_creation_tokens=0, cache_read_tokens=0,
            total_tokens=300, total_cost=0.02,
            updated_at=None, created_at=None,
        ),
    ]
    device_names = {"uuid-A": "Laptop"}

    dimension_rows, _ = _build_dimension_data(rows, device_names)

    model_slices = dimension_rows["models"]
    assert len(model_slices) == 1, f"期望 1 个模型切片，实际 {len(model_slices)}"
    assert model_slices[0]["key"] == "claude-sonnet-4-5"
    assert model_slices[0]["label"] == "claude-sonnet-4-5"
    assert model_slices[0]["total_tokens"] == 450
    assert model_slices[0]["tool_id"] is None
    assert model_slices[0]["source"] is None


# —— _infer_agent ——

def test_infer_agent_picks_by_models_used():
    """模型在某个 agent 的 modelsUsed 中 → 归该 agent。"""
    from app.services.token_usage_sync_service import _infer_agent

    agent_models_dict = {
        "2026-06-19": {
            "claude": {"claude-sonnet-4-5"},
            "opencode": {"qwen3.6-plus"},
        },
    }
    assert _infer_agent("claude-sonnet-4-5", "2026-06-19", agent_models_dict) == "claude"
    assert _infer_agent("qwen3.6-plus", "2026-06-19", agent_models_dict) == "opencode"


def test_infer_agent_raises_when_no_candidates_multi_agent():
    """修复问题 3：多 agent 当日但模型不在任何 modelsUsed → 抛错而非返回 'other'。"""
    from app.services.token_usage_sync_service import _infer_agent

    agent_models_dict = {
        "2026-06-19": {
            "claude": {"claude-sonnet-4-5"},
            "opencode": {"qwen3.6-plus"},
        },
    }
    with pytest.raises(ValueError):
        _infer_agent("unknown-model", "2026-06-19", agent_models_dict)


def test_infer_agent_falls_back_to_single_agent():
    """当日仅 1 个 agent 时，所有模型都归该 agent。"""
    from app.services.token_usage_sync_service import _infer_agent

    agent_models_dict = {"2026-06-19": {"claude": {"claude-sonnet-4-5"}}}
    assert _infer_agent("any-model", "2026-06-19", agent_models_dict) == "claude"
```

- [ ] **Step 3: 运行测试，确认全部失败（实现还没改）**

```bash
cd backend && python -m pytest tests/test_token_usage_pie_fixes.py -v
```

Expected: 7 个测试 FAIL。问题 1、2、4 对应的测试失败原因是实现还是旧行为；问题 3 测试失败原因是 `_infer_agent` 还没改成抛错。

- [ ] **Step 4: 提交骨架**

```bash
cd /g/IdeaProjects/tools
git add backend/tests/
git commit -m "测试: 添加饼图修复后端单元测试骨架"
```

---

### Task 2: 修复设备名优先级（问题 1）

**Files:**
- Modify: `backend/app/routes/token_usage.py:1498-1520`

- [ ] **Step 1: 修改 `_normalize_record_dimensions`**

在 `backend/app/routes/token_usage.py` 第 1498 行附近找到：

```python
def _normalize_record_dimensions(row, device_names: dict[str, str]) -> dict:
    tool = _map_source_to_tool(getattr(row, "source", None))
    tool_id = getattr(row, "tool_id", None) or tool["tool_id"]
    tool_name = getattr(row, "tool_name", None) or tool["tool_name"]
    device_id = getattr(row, "device_id", None) or "unknown"
    device_name = (
        getattr(row, "device_name", None)
        or device_names.get(device_id)
        or device_id
    )
    ...
```

改为：

```python
def _normalize_record_dimensions(row, device_names: dict[str, str]) -> dict:
    tool = _map_source_to_tool(getattr(row, "source", None))
    tool_id = getattr(row, "tool_id", None) or tool["tool_id"]
    tool_name = getattr(row, "tool_name", None) or tool["tool_name"]
    device_id = getattr(row, "device_id", None) or "unknown"
    # 修复问题 1：设备名权威来源是 device_names map（已合并 alias 与最新 display_name）
    # 不再优先用 row.device_name（那是同步时刻的快照，不会跟随重命名）
    device_name = device_names.get(device_id) or device_id
    model = getattr(row, "model", None) or "unknown"
    model_display_name = getattr(
        row, "model_display_name", None
    ) or _display_model_name(model, tool_name)
    return {
        "source": getattr(row, "source", None) or "unknown",
        "tool_id": tool_id,
        "tool_name": tool_name,
        "device_id": device_id,
        "device_name": device_name,
        "model": model,
        "model_display_name": model_display_name,
    }
```

- [ ] **Step 2: 运行对应测试**

```bash
cd backend && python -m pytest tests/test_token_usage_pie_fixes.py::test_device_name_from_map_overrides_record_field tests/test_token_usage_pie_fixes.py::test_device_name_falls_back_to_device_id_when_missing -v
```

Expected: 2 个测试 PASS。

- [ ] **Step 3: 提交**

```bash
cd /g/IdeaProjects/tools
git add backend/app/routes/token_usage.py
git commit -m "fix(饼图): 设备名优先用最新 display_name，不再用记录里的旧快照"
```

---

### Task 3: 设备维度按显示名合并（问题 2）+ 模型维度按纯 model 分组（问题 4 后端）

**Files:**
- Modify: `backend/app/routes/token_usage.py:1640-1728`

- [ ] **Step 1: 修改 `_build_dimension_data` 中设备桶和模型桶的分桶 key**

在 `backend/app/routes/token_usage.py` 第 1640 行附近的 `_build_dimension_data` 函数中：

把设备桶 key 从 `device_id` 改为 `device_name`：

```python
def _build_dimension_data(records, device_names: dict[str, str]) -> tuple[dict, dict]:
    device_buckets: dict[str, dict] = {}
    tool_buckets: dict[str, dict] = {}
    model_buckets: dict[str, dict] = {}

    for row in records:
        dims = _normalize_record_dimensions(row, device_names)
        device_key = dims["device_name"]          # 修复问题 2：按显示名合并
        tool_key = dims["tool_id"]
        model_key = dims["model"]                 # 修复问题 4：去掉 tool_id 前缀

        device_bucket = device_buckets.setdefault(
            device_key,
            {
                "dimension": "device",
                "key": dims["device_id"],
                "label": dims["device_name"],
                "device_id": dims["device_id"],
                "tool_id": None,
                "source": None,
                "model": None,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0,
                "records_count": 0,
                "last_used_at": None,
            },
        )
        _rollup_dimension(device_bucket, row, {"label": dims["device_name"]})

        tool_bucket = tool_buckets.setdefault(
            tool_key,
            {
                "dimension": "tool",
                "key": tool_key,
                "label": dims["tool_name"],
                "device_id": None,
                "tool_id": tool_key,
                "source": dims["source"],
                "model": None,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0,
                "records_count": 0,
                "last_used_at": None,
            },
        )
        _rollup_dimension(
            tool_bucket, row,
            {"label": dims["tool_name"], "source": dims["source"]},
        )

        # 修复问题 4：模型维度只按 model 分组，不绑定 tool_id/source
        model_bucket = model_buckets.setdefault(
            model_key,
            {
                "dimension": "model",
                "key": model_key,
                "label": dims["model"],
                "device_id": None,
                "tool_id": None,
                "source": None,
                "model": dims["model"],
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0,
                "records_count": 0,
                "last_used_at": None,
            },
        )
        _rollup_dimension(
            model_bucket, row,
            {"label": dims["model"], "tool_id": None, "source": None, "model": dims["model"]},
        )
```

> 注意：`filter_options["models"]` 里的 `tool_id` 字段现在是 `None`，前端 `modelOptions` 已有 `.filter(model => !selectedTool || model.tool_id === selectedTool)` 的兼容逻辑，`tool_id=None` 在选中工具时会被过滤掉——这是预期行为（模型维度不再和工具强绑定）。

- [ ] **Step 2: 运行对应测试**

```bash
cd backend && python -m pytest tests/test_token_usage_pie_fixes.py::test_dimension_data_merges_devices_with_same_display_name tests/test_token_usage_pie_fixes.py::test_dimension_data_models_grouped_by_model_only -v
```

Expected: 2 个测试 PASS。

- [ ] **Step 3: 提交**

```bash
cd /g/IdeaProjects/tools
git add backend/app/routes/token_usage.py
git commit -m "fix(饼图): 设备饼图按显示名合并，模型饼图按纯 model 分组"
```

---

### Task 4: 设备筛选扩展为同显示名集合

**Files:**
- Modify: `backend/app/routes/token_usage.py:1996`（`_build_record_filters`）
- Modify: `backend/app/routes/token_usage.py`（在 `/summary`、`/details`、`/query`、`db_query_token_usage` 四个调用点注入 db 上下文）

- [ ] **Step 1: 新增辅助函数 `_resolve_same_display_name_ids`**

在 `backend/app/routes/token_usage.py` 中（建议放在 `_load_device_names` 下方，约 1538 行附近）：

```python
def _resolve_same_display_name_ids(
    db, user_id: str, device_id: str, alias_map: Optional[dict[str, str]]
) -> list[str]:
    """
    给定一个 device_id，找出所有在 DeviceRegistry 中 display_name
    与其相同的 device_id（包括 alias 展开后的设备），返回完整集合。

    用途：设备饼图按显示名合并后，点击切片传入的 device_id 仅是一个
    canonical id，但查询应该覆盖所有同名的设备记录。
    """
    from app.utils.device_name_resolver import load_device_name_map

    device_names = load_device_name_map(db, user_id)
    target_name = device_names.get(device_id)
    if not target_name:
        return []

    same_ids = [
        did for did, name in device_names.items() if name == target_name
    ]
    if not same_ids:
        return [device_id]

    # 把 alias 反向也展开：如果某个 device_id 是 alias 且它的 canonical 也同名，加入
    expanded = set(same_ids)
    if alias_map:
        for alias_id, canonical_id in alias_map.items():
            if canonical_id in expanded or alias_id in expanded:
                expanded.add(alias_id)
                expanded.add(canonical_id)
    return list(expanded)
```

- [ ] **Step 2: 改造 `_build_record_filters` 签名，接受 db 和 alias_map**

修改 `_build_record_filters` 的签名（约第 1996 行）：

```python
def _build_record_filters(
    user_id: str,
    req,
    since_date: Optional[datetime] = None,
    alias_map: Optional[dict[str, str]] = None,
    db=None,  # 新增：可选，用于同名设备展开
) -> list:
    """构建 Token Usage 记录查询条件，保证元信息和明细口径一致。"""
    from app.utils.device_name_resolver import build_alias_aware_device_filter

    filters = [TokenUsageRecord.user_id == user_id]
    if since_date is not None:
        filters.append(TokenUsageRecord.record_date >= since_date.date())
    if getattr(req, "source", "all") != "all":
        filters.append(TokenUsageRecord.source == req.source)
    if getattr(req, "device_id", None):
        # 修复问题 2 联动：同名设备筛选时，把所有同显示名的 device_id 都查进来
        same_name_ids = (
            _resolve_same_display_name_ids(db, user_id, req.device_id, alias_map)
            if db is not None else []
        )
        if same_name_ids:
            filters.append(TokenUsageRecord.device_id.in_(same_name_ids))
        elif alias_map:
            filters.extend(
                build_alias_aware_device_filter(req.device_id, alias_map)
            )
        else:
            filters.append(TokenUsageRecord.device_id == req.device_id)
    tool_id = getattr(req, "tool_id", None)
    if tool_id:
        source_matches = [
            source
            for source in ("claude", "opencode", "codex")
            if _map_source_to_tool(source)["tool_id"] == tool_id
        ]
        if tool_id not in source_matches:
            source_matches.append(tool_id)
        fallback_filters = [TokenUsageRecord.tool_id == tool_id]
        if source_matches:
            fallback_filters.append(
                (TokenUsageRecord.tool_id.is_(None))
                & (TokenUsageRecord.source.in_(source_matches))
            )
        filters.append(or_(*fallback_filters))
    if getattr(req, "model", None):
        filters.append(TokenUsageRecord.model == req.model)
    return filters
```

- [ ] **Step 3: 在四个调用点传入 db**

在 `/summary`（约 766 行）、`/details`（约 862 行）、`/query`（约 2378 行、2469 行）、`db_query_token_usage` 内的 `_execute_db_query`（约 2469 行）、以及 `_execute_model_summary_query`（2213 行）、`_latest_record_updated_at`（2040 行）、`_query_item_model_map`（2073 行）中，所有 `_build_record_filters(user_id, req, since_date, alias_map)` 的调用都加上 `db=db`：

```python
# 替换前
_build_record_filters(user_id, req, since_date, alias_map)
# 替换后
_build_record_filters(user_id, req, since_date, alias_map, db=db)
```

全局搜索并替换：
```bash
grep -n "_build_record_filters(" backend/app/routes/token_usage.py
```

对每处调用补上 `db=db`（注意 `db` 变量名已在各路由函数内）。

- [ ] **Step 4: 运行测试，确保无回归**

```bash
cd backend && python -m pytest tests/test_token_usage_pie_fixes.py -v
```

Expected: 所有测试 PASS（本任务不新增测试，只是改动不能破坏现有行为）。

- [ ] **Step 5: 提交**

```bash
cd /g/IdeaProjects/tools
git add backend/app/routes/token_usage.py
git commit -m "fix(饼图): 设备筛选扩展为同显示名集合，与饼图合并语义对齐"
```

---

### Task 5: 移除 "other" 兜底（问题 3 后端）

**Files:**
- Modify: `backend/app/services/token_usage_sync_service.py:596`（`_infer_agent`）
- Modify: `backend/app/services/token_usage_sync_service.py:626`（`_parse_ccusage_records`）
- Modify: `backend/app/services/token_usage_sync_service.py:568-593`（`AGENT_PRIORITY` / `AGENT_DISPLAY_NAMES`）

- [ ] **Step 1: 修改 `_infer_agent`**

找到第 596 行附近：

```python
def _infer_agent(
    model_name: str,
    date_str: str,
    agent_models_dict: dict,
) -> str:
    """根据模型名 + 当日各 agent 的 modelsUsed 字典推断归属。
    ...
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
```

改为：

```python
def _infer_agent(
    model_name: str,
    date_str: str,
    agent_models_dict: dict,
) -> str:
    """根据模型名 + 当日各 agent 的 modelsUsed 字典推断归属。

    规则:
    1. 模型在当日某 agent 的 modelsUsed 中 → 归属该 agent
    2. 多个 agent 都含该模型（歧义）→ 按 AGENT_PRIORITY 选最高优先级
    3. 都不含且当日有 ≥2 个 agent → 抛 ValueError（上层跳过该条记录）
    4. 都不含且当日仅 1 个 agent → 归该 agent（唯一可选）
    """
    day_agents = agent_models_dict.get(date_str, {})
    candidates = [agent for agent, models in day_agents.items() if model_name in models]
    if candidates:
        for priority_agent in AGENT_PRIORITY:
            if priority_agent in candidates:
                return priority_agent
        return candidates[0]

    # 无候选：当日仅 1 个 agent 时兜底归该 agent，否则抛错
    if len(day_agents) == 1:
        return next(iter(day_agents.keys()))
    raise ValueError(
        f"模型 {model_name}（{date_str}）未在任何 agent 的 modelsUsed 中出现"
    )
```

- [ ] **Step 2: 修改 `_parse_ccusage_records` 捕获 ValueError 并跳过**

找到第 626 行附近的 `_parse_ccusage_records`，把原来的 `agent = _infer_agent(...)` + `if agent == "other": logger.warning(...)` 替换：

```python
def _parse_ccusage_records(
    daily: list[dict],
    agent_models_dict: dict,
) -> list[dict]:
    """解析 ccusage daily JSON 为 (date, agent, model) 三元组记录。"""
    results = []
    skipped = 0
    for day in daily:
        period = day.get("period") or day.get("date")
        if not period:
            continue
        try:
            record_date = date.fromisoformat(period)
        except (ValueError, TypeError):
            continue

        breakdowns = day.get("modelBreakdowns") or []
        for bd in breakdowns:
            model_name = bd.get("modelName") or bd.get("model") or "_unknown"
            try:
                agent = _infer_agent(model_name, period, agent_models_dict)
            except ValueError as exc:
                logger.warning(f"[ccusage] 跳过无法归属的记录: {exc}")
                skipped += 1
                continue

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
                "tool_name": AGENT_DISPLAY_NAMES.get(agent, agent),
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
    if skipped:
        logger.info(f"[ccusage] 共跳过 {skipped} 条无法归属的记录")
    return results
```

- [ ] **Step 3: 清理 `AGENT_DISPLAY_NAMES` 和 `AGENT_PRIORITY` 中的 `other`**

找到第 568-593 行附近：

```python
# Agent 优先级（用于模型归属歧义时的 tie-breaker）
AGENT_PRIORITY = [
    "claude", "opencode", "openclaw", "codex", "amp",
    "droid", "codebuff", "hermes", "pi", "goose",
    "kilo", "copilot", "gemini", "kimi", "qwen",
]

# agent_id → 显示名映射
AGENT_DISPLAY_NAMES = {
    "claude": "Claude Code",
    ...
    "qwen": "Qwen",
    "other": "Other",   # ← 删除这一行
}
```

删除 `"other": "Other"` 这一行。

- [ ] **Step 4: 运行对应测试**

```bash
cd backend && python -m pytest tests/test_token_usage_pie_fixes.py::test_infer_agent_picks_by_models_used tests/test_token_usage_pie_fixes.py::test_infer_agent_raises_when_no_candidates_multi_agent tests/test_token_usage_pie_fixes.py::test_infer_agent_falls_back_to_single_agent -v
```

Expected: 3 个测试全部 PASS。

- [ ] **Step 5: 运行全部测试确保无回归**

```bash
cd backend && python -m pytest tests/test_token_usage_pie_fixes.py -v
```

Expected: 全部 PASS。

- [ ] **Step 6: 提交**

```bash
cd /g/IdeaProjects/tools
git add backend/app/services/token_usage_sync_service.py
git commit -m "fix(饼图): 移除 'other' 兜底，模型无法归属时跳过并 WARNING"
```

---

### Task 6: 一次性清理历史 `source='other'` 数据

**Files:**
- Create: `backend/scripts/cleanup_other_token_usage.py`

- [ ] **Step 1: 创建清理脚本**

```python
# backend/scripts/cleanup_other_token_usage.py
"""
Author: Peanut
Created: 2026-06-19
Purpose: 一次性清理 token_usage_records / token_usage_sync_log 中
         历史遗留的 source='other' 记录。仅手动执行一次。

用法:
    python backend/scripts/cleanup_other_token_usage.py

确认会打印待删除记录数，要求用户按 y 回车后才真正删除。
"""
import sys
import os

# 让脚本能 import app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.base import SessionLocal
from app.models.token_usage_models import TokenUsageRecord, TokenUsageSyncLog


def main() -> int:
    db = SessionLocal()
    try:
        records_count = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.source == "other")
            .count()
        )
        logs_count = (
            db.query(TokenUsageSyncLog)
            .filter(TokenUsageSyncLog.source == "other")
            .count()
        )
        print(f"即将删除: {records_count} 条 token_usage_records, {logs_count} 条 token_usage_sync_log")
        if records_count == 0 and logs_count == 0:
            print("没有需要清理的数据。")
            return 0

        answer = input("确认删除? (y/N): ").strip().lower()
        if answer != "y":
            print("已取消。")
            return 0

        records_deleted = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.source == "other")
            .delete(synchronize_session=False)
        )
        logs_deleted = (
            db.query(TokenUsageSyncLog)
            .filter(TokenUsageSyncLog.source == "other")
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"已删除 {records_deleted} 条 records, {logs_deleted} 条 sync_log")
        return 0
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130
    except Exception as exc:
        db.rollback()
        print(f"清理失败: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 提交脚本（不执行）**

```bash
cd /g/IdeaProjects/tools
git add backend/scripts/cleanup_other_token_usage.py
git commit -m "工具: 添加一次性脚本清理 source='other' 历史数据"
```

- [ ] **Step 3: 在浏览器验证前手动执行一次**

```bash
cd /g/IdeaProjects/tools/backend
python scripts/cleanup_other_token_usage.py
```

输入 `y` 确认。

Expected: 打印删除数量，数据已清理。

---

### Task 7: 前端 `modelCostSlices` 按 model 二次合并（问题 4 前端）

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx:493-501`

- [ ] **Step 1: 修改 `modelCostSlices` useMemo**

在 `frontend/src/components/Tools/TokenUsage.tsx` 第 493 行附近找到：

```typescript
const modelCostSlices: PieSlice[] = useMemo(
  () => summary.data.model_summary.map(item => ({
    key: item.model,
    label: `${item.source === 'claude' ? 'Claude' : item.source === 'opencode' ? 'OpenCode' : item.source} · ${item.display_model || item.model}`,
    tokens: item.total_tokens,
    cost: item.total_cost,
  })),
  [summary.data.model_summary]
);
```

替换为：

```typescript
const modelCostSlices: PieSlice[] = useMemo(() => {
  // 修复问题 4: 按纯 model 合并，不再带 source 前缀
  const map = new Map<string, { tokens: number; cost: number }>();
  summary.data.model_summary.forEach(item => {
    const cur = map.get(item.model) || { tokens: 0, cost: 0 };
    map.set(item.model, {
      tokens: cur.tokens + item.total_tokens,
      cost: cur.cost + item.total_cost,
    });
  });
  return Array.from(map.entries()).map(([model, v]) => ({
    key: model,
    label: model,
    tokens: v.tokens,
    cost: v.cost,
  }));
}, [summary.data.model_summary]);
```

- [ ] **Step 2: 前端热加载自动生效（无需重启）**

观察 Vite dev server 终端，确认热更新完成。

- [ ] **Step 3: 提交**

```bash
cd /g/IdeaProjects/tools
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "fix(饼图): 模型成本饼图按 model 二次合并，不再带工具前缀"
```

---

### Task 8: 重启后端 + 浏览器验证四个饼图

- [ ] **Step 1: 重启后端服务**

```bash
cd /g/IdeaProjects/tools
python dev_services.py restart backend
python dev_services.py status
```

Expected: backend 显示 running，端口 19092 监听中。

- [ ] **Step 2: 浏览器打开 token-usage 页面**

使用浏览器工具（`browse` skill 或 `agent-browser`）打开 http://localhost:5178/tools/token-usage，使用账号 `peanut / Peanut2817*#` 登录。

- [ ] **Step 3: 验收检查项**

依次验证：

1. **设备饼图**：显示名称与「设备管理」中重命名后的名称一致（如有重命名操作）
2. **设备饼图合并**：手动把两个不同 `device_id` 命名为相同名字后刷新，饼图只显示一个切片，数值 = 两者之和
3. **工具饼图**：点击"刷新数据"后不再出现 `Other` 切片；如有跳过的模型，后端日志应有 `[ccusage] 跳过无法归属的记录` WARNING
4. **模型 Token 占比饼图**：同一模型只显示一个切片，不再被不同工具拆成多片
5. **模型成本占比饼图**：同上，label 是纯模型名，没有 `"Claude · xxx"` 前缀
6. **Console 无报错**：浏览器 DevTools Console 面板无任何红色错误

- [ ] **Step 4: 检查后端日志**

```bash
python dev_services.py logs backend | tail -50
```

Expected: 无 ERROR 堆栈。如有 `[ccusage] 跳过无法归属的记录` WARNING 是预期的。

- [ ] **Step 5: 最终提交（若发现小问题在这里补）**

```bash
cd /g/IdeaProjects/tools
git status
# 如有未提交的小改动
git add -A
git commit -m "fix(饼图): 浏览器验收后的小修"
```

---

## 验收标准（速查）

| # | 验收项 | 验证方式 |
|---|-------|---------|
| 1 | 设备饼图标签跟随重命名 | 重命名设备后刷新页面 |
| 2 | 同名设备数据合并为 1 个切片 | 两个 device_id 同显示名 |
| 3 | 工具饼图不再出现 `Other` | 刷新数据后观察 |
| 4 | 模型 Token 占比按纯 model 分组 | 观察切片数量 |
| 5 | 模型成本占比按纯 model 分组（前端合并） | 观察切片 label |
| 6 | 设备筛选点击后覆盖所有同名设备记录 | 点击切片后明细表行数 |
| 7 | 浏览器 Console 无报错 | DevTools |
| 8 | 后端日志无 ERROR 堆栈 | `dev_services.py logs` |

## 回滚方案

如发现某修复引入回归：

```bash
git log --oneline -10
git revert <commit-sha>
python dev_services.py restart backend
```

前端改动可通过 `git checkout <prev-sha> -- frontend/src/components/Tools/TokenUsage.tsx` 回滚单文件。
