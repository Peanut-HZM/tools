# Token Usage 明细"工具"列空白 Bug 修复

**日期**: 2026-06-03  
**状态**: Draft  
**类型**: Bug 修复  
**影响范围**: 后端 `token_usage.py` + 前端 `TokenUsage.tsx` / `tokenUsageApi.ts`

---

## 问题描述

Token Usage 页面"明细数据"表格中"工具"列始终显示 `-`。

## 根因分析

`getRowToolLabel` 函数的两个条件都无法命中：
1. `groupBy === 'tool'` — 仅在用户选择"按工具对比"时成立
2. `selectedTool` — 仅在用户选择特定工具时成立（且上轮改动已移除来源筛选器）

正常浏览模式下两个条件都为 false，函数总是返回 `-`。

**根本原因**：后端 `/details` 接口返回的 `DbUsageItem` 缺少 `tool_id` 字段。

---

## 修复方案

### 1. 后端 DbUsageItem 添加 tool_id

`backend/app/routes/token_usage.py` — `DbUsageItem` 类（L510-523）

```python
class DbUsageItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    date: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float
    models_used: list[str] = Field(default_factory=list)
    model_breakdowns: list[dict] = Field(default_factory=list)
    tool_id: Optional[str] = Field(default=None, description="工具ID")
    group_key: Optional[str] = Field(
        default=None, description="设备名或模型名（分组时）"
    )
```

### 2. 后端填充 tool_id

`backend/app/routes/token_usage.py` — `get_token_usage_details` 函数（L900-913）

```python
items.append(
    DbUsageItem(
        date=date_key,
        input_tokens=int(r.input_tokens or 0),
        output_tokens=int(r.output_tokens or 0),
        cache_creation_tokens=int(r.cache_creation_tokens or 0),
        cache_read_tokens=int(r.cache_read_tokens or 0),
        total_tokens=int(r.total_tokens or 0),
        total_cost=float(r.total_cost or 0),
        models_used=[r.model] if r.model else [],
        model_breakdowns=[],
        tool_id=r.tool_id,
        group_key=group_key,
    )
)
```

### 3. 前端 DbUsageItem 类型添加 tool_id

`frontend/src/api/tokenUsageApi.ts` — `DbUsageItem` 接口（L150-152）

```typescript
export interface DbUsageItem extends UsageItem {
  group_key?: string;
  tool_id?: string;
}
```

### 4. 前端 getRowToolLabel 使用 tool_id

`frontend/src/components/Tools/TokenUsage.tsx` — `getRowToolLabel` 函数（L472-476）

```tsx
const getRowToolLabel = (item: DbUsageItem) => {
  if (item.tool_id) return getToolLabel(item.tool_id);
  return '-';
};
```
