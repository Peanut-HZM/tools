# Token Usage 明细数据排序 Bug 修复设计

**日期**: 2026-06-03  
**状态**: Draft → Approved  
**类型**: Bug 修复  
**影响范围**: 后端 `/api/token-usage/details` 接口

---

## 问题描述

用户反馈：`http://localhost:5178/tools/token-usage` 页面的"明细数据"**没有按时间倒序排列**。

经全链路调研确认：前端传参正确（sort_by='date', sort_order='desc'），后端收到参数也正确，但 `_sort_usage_items` 排序函数内部使用了错误的 ORM 属性名。

---

## 根因分析

### 全链路

| 层级 | 文件 | 状态 |
|---|---|---|
| 前端状态 | `TokenUsage.tsx` L158-159 | ✅ `sortBy='date', sortOrder='desc'` |
| 前端 Hook | `useTokenUsageDetails.ts` L236-248 | ✅ 传递 `sort_by/sort_order` |
| 前端 API | `tokenUsageApi.ts` L279-280 | ✅ 默认 `sort_by='date', sort_order='desc'` |
| 后端路由 | `token_usage.py` L884 | ✅ `sorted_records = _sort_usage_items(records, req.sort_by, req.sort_order)` |
| 排序函数 | `token_usage.py` L1605-1624 | ❌ **bug：`getattr(item, "date", None)` 字段名错误** |
| ORM 模型 | `token_usage_models.py` | 字段名是 `record_date`，不是 `date` |

### Bug 细节

```python
# token_usage.py L1622 (当前错误代码)
def sort_value(item):
    # ...
    return getattr(item, selected, None) or 0   # selected = "date"
```

- `TokenUsageRecord` 模型的日期字段是 `record_date`，不是 `date`
- `getattr(record, "date", None)` → `None` → `or 0` → **排序值 = 0**
- `sorted()` 对所有值相同的元素保持插入顺序（DB 自然顺序）
- 结果：明细数据**看似无序**（实际是 DB 插入顺序）

---

## 修复方案

### 方案 A：在 `_sort_usage_items` 添加字段映射（已批准）

在排序函数内部，将前端用户语义（如 `"date"`）映射到 ORM 真实字段名（如 `"record_date"`）。

#### 改动文件

`backend/app/routes/token_usage.py` — `_sort_usage_items` 函数（约 L1605-1624）

#### 改动内容

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
    
    # 新增：映射前端用户语义到 ORM 字段名
    field_mapping = {
        "date": "record_date",
    }
    orm_field = field_mapping.get(selected, selected)

    def sort_value(item):
        if selected == "cache_tokens":
            return (getattr(item, "cache_creation_tokens", 0) or 0) + (
                getattr(item, "cache_read_tokens", 0) or 0
            )
        return getattr(item, orm_field, None) or 0  # 使用 orm_field

    return sorted(items, key=sort_value, reverse=reverse)
```

#### 影响分析

| 维度 | 评估 |
|---|---|
| 改动量 | 1 行新增 mapping + 1 行改用 orm_field |
| 向后兼容 | ✅ 前端接口不变（仍传 `date`）|
| 其他排序 | ✅ total_tokens/input_tokens 等字段映射到自身，无影响 |
| 缓存 | ✅ 缓存键基于 sort_by/sort_order 字符串，不受影响 |
| 测试 | ✅ 新增集成测试应覆盖 `sort_by="date"` 正确排序 |

---

## 拒绝的替代方案

### 方案 B：ORM 添加 column_property

在 `TokenUsageRecord` 模型添加 `date = column_property(record_date)`。

**拒绝原因**：改动 ORM 模型影响范围比预期大，且 ORM 别名可能在其他地方被意外引用。

### 方案 C：前端传 `record_date`

前端默认值改 `record_date`。

**拒绝原因**：前后端接口语义不统一——前端用户使用业务概念 `date`，不应暴露内部字段名。

---

## 验证计划

1. **语法检查**：`python -m py_compile backend/app/routes/token_usage.py`
2. **Lint 检查**：`ruff check backend/app/routes/token_usage.py`
3. **功能验证**：刷新页面，确认明细数据按日期倒序
4. **浏览器验证**：Console 无报错
