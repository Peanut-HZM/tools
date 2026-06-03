# Token Usage 明细排序 Bug 修复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复后端 `_sort_usage_items` 函数中 `sort_by="date"` 时使用错误的 ORM 属性名，导致明细数据未按时间倒序排列

**Architecture:** 在 `_sort_usage_items` 函数内部添加字段映射字典，将前端用户语义（如 `"date"`）映射到 ORM 真实字段名（`"record_date"`），然后将 `getattr` 改用映射后的字段名

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy ORM

---

## 文件改动映射

| 动作 | 文件 | 说明 |
|---|---|---|
| 修改 | `backend/app/routes/token_usage.py:1605-1624` | 修复 `_sort_usage_items` 函数，添加字段映射 |
| 验证 | `backend/tests/test_token_usage_split_api.py` | 确认现有测试仍通过 |

---

### Task 1: 修复 `_sort_usage_items` 函数

**Files:**
- Modify: `backend/app/routes/token_usage.py` (函数 L1605-1624)

- [ ] **Step 1: 确认当前排序行为（验证 bug 存在）**

在 `_sort_usage_items` 函数中确认问题根源：当 `sort_by="date"` 时，`selected="date"`，然后 `getattr(item, selected, None)` 返回 `None`（因为 `TokenUsageRecord` 没有 `date` 属性，只有 `record_date`），最终所有记录的排序值都变成 `0`。

运行现有测试确认当前状态：
```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
source venv/bin/activate
python -m pytest tests/test_token_usage_split_api.py -v --tb=short 2>&1 | tail -10
```
预期：`27 passed, 0 failed`（测试可能未覆盖 `sort_by="date"` 的情况）

- [ ] **Step 2: 修改 `_sort_usage_items` 函数**

将函数从 L1605 到 L1624 修改为：

```python
def _sort_usage_items(items, sort_by: str, sort_order: str):
    allowed = {
        "date",
        "total_tokens",
        "total_cost",
        "input_tokens",
        "output_tokens",
        "cache_tokens",
    }
    selected = sort_by if sort_by in allowed else "date"
    reverse = sort_order != "asc"

    # 映射前端用户语义到 ORM 真实字段名
    field_mapping = {
        "date": "record_date",
    }
    orm_field = field_mapping.get(selected, selected)

    def sort_value(item):
        if selected == "cache_tokens":
            return (getattr(item, "cache_creation_tokens", 0) or 0) + (
                getattr(item, "cache_read_tokens", 0) or 0
            )
        return getattr(item, orm_field, None) or 0

    return sorted(items, key=sort_value, reverse=reverse)
```

**关键点：**
- 新增 `field_mapping` 字典，将 `"date"` 映射到 `"record_date"`
- `orm_field = field_mapping.get(selected, selected)` — 如果 mapping 中没有该字段，默认使用原值（如 `total_tokens` → `total_tokens`）
- `getattr(item, orm_field, None) or 0` — 改用 `orm_field` 替代 `selected`
- `cache_tokens` 的特殊逻辑不变（它本身不是 ORM 字段，需要计算）

- [ ] **Step 3: 验证修改后语法正确**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
python -m py_compile backend/app/routes/token_usage.py && echo "✅ 语法检查通过" || echo "❌ 语法错误"
```

- [ ] **Step 4: 运行 ruff lint 检查**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
uv run ruff check backend/app/routes/token_usage.py --select F,E,W && echo "✅ Lint 通过" || echo "⚠️ 有 lint 告警"
```
预期：无错误或警告（如有无关 lint 告警可忽略）

- [ ] **Step 5: 运行现有测试**

```bash
cd /Users/huazhongmin/IdeaProjects/tools/backend
source venv/bin/activate
python -m pytest tests/test_token_usage_split_api.py -v --tb=short 2>&1 | tail -15
```
预期：`27 passed, 0 failed`（测试未覆盖 `sort_by="date"` 的情况，但现有测试应全部通过）

- [ ] **Step 6: Commit 修复**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add backend/app/routes/token_usage.py
git commit -m "fix(backend): 修复 _sort_usage_items 中 sort_by='date' 使用错误 ORM 属性名"
```

---

## Self-Review

| 检查项 | 结果 |
|---|---|
| **规范覆盖** | 全链路调研 → 根因定位 → 修复方案 A（字段映射）→ 所有任务已覆盖 |
| **Placeholder 扫描** | ✅ 无 TBD/TODO/模糊描述 |
| **类型一致性** | ✅ 单一文件修改，类型不变 |
| **无 "Similar to Task N"** | ✅ 仅 1 个 Task，无引用 |
| **步骤可独立验证** | ✅ 每步都有明确命令和预期输出 |
