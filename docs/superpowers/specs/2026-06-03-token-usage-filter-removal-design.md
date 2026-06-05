# Token Usage 页面筛选组件精简设计

**日期**: 2026-06-03  
**状态**: Approved  
**类型**: UI 优化  
**影响范围**: 前端 `TokenUsage.tsx`

---

## 问题描述

Token Usage 页面当前有 10 个筛选组件，分布在两行（xl:grid-cols-8），导致：
- 布局不整齐，需要换行
- "来源"和"方向"两个筛选器用户不再需要
- 筛选区域过于复杂

---

## 根因分析

当前筛选区域（L628-740）包含 10 个筛选组件：

| # | 组件 | 状态 | 是否保留 |
|---|---|---|---|
| 1 | 来源 (source) | `useState<'all'|'claude'|'opencode'>('all')` | ❌ 移除 |
| 2 | 工具 (selectedTool) | `useState<string>('')` | ✓ |
| 3 | 模型 (selectedModel) | `useState<string>('')` | ✓ |
| 4 | 维度 (reportType) | `useState<'daily'|'weekly'|'monthly'>('daily')` | ✓ |
| 5 | 时间范围 (days) | `useState<number>(30)` | ✓ |
| 6 | 设备 (selectedDevice) | `useState<string>('')` | ✓ |
| 7 | 分组 (groupBy) | `useState<'none'|'device'|'tool'|'model'>('none')` | ✓ |
| 8 | 排序 (sortBy) | `useState<'date'|'total_tokens'|...>('date')` | ✓ |
| 9 | 方向 (sortOrder) | `useState<'asc'|'desc'>('desc')` | ❌ 移除 |
| 10 | 图表 (chartType) | `useState<'bar'|'line'>('bar')` | ✓ |

移除 2 个后剩 8 个，刚好一行显示。

---

## 修复方案

### 改动文件

| 文件 | 说明 |
|---|---|
| `frontend/src/components/Tools/TokenUsage.tsx` | 删除来源/方向状态、UI 组件、debounce 变量；修改 hook 调用和关联代码 |

### 具体改动

#### 1. 删除状态（L151, L159）

```tsx
// 删除
const [source, setSource] = useState<TokenUsageSource>('all');
const [sortOrder, setSortOrder] = useState<TokenUsageSortOrder>('desc');
```

#### 2. 删除 debounce 变量（L217, L221）

```tsx
// 删除
const debouncedSource = useDebouncedValue(source, 200);
const debouncedSortOrder = useDebouncedValue(sortOrder, 200);
```

#### 3. 删除来源筛选框（L629-636）

```tsx
// 删除整个来源筛选 label
<label className="space-y-1">
  <span className="text-xs text-slate-400">来源</span>
  <select value={source} onChange={event => setSource(event.target.value as TokenUsageSource)}>
    ...
  </select>
</label>
```

#### 4. 删除方向筛选框（L725-731）

```tsx
// 删除整个方向筛选 label
<label className="space-y-1">
  <span className="text-xs text-slate-400">方向</span>
  <select value={sortOrder} onChange={event => setSortOrder(event.target.value as TokenUsageSortOrder)}>
    ...
  </select>
</label>
```

#### 5. 修改 hook 调用中的硬编码

```tsx
// useTokenUsageSummary — source 替换为硬编码
summary = useTokenUsageSummary({
  type: reportType,
  days: debouncedDays,
  group_by: debouncedGroupBy,
  source: 'all',  // 原来: debouncedSource
  device_id: debouncedDevice || undefined,
  tool_id: debouncedTool || undefined,
  model: debouncedModel || undefined,
});

// useTokenUsageDetails — source 和 sort_order 替换为硬编码
details = useTokenUsageDetails({
  type: reportType,
  days: debouncedDays,
  group_by: debouncedGroupBy,
  source: 'all',  // 原来: debouncedSource
  device_id: debouncedDevice || undefined,
  tool_id: debouncedTool || undefined,
  model: debouncedModel || undefined,
  sort_by: debouncedSortBy,
  sort_order: 'desc',  // 原来: debouncedSortOrder
  limit: PAGE_SIZE,
  offset: (currentPage - 1) * PAGE_SIZE,
});
```

#### 6. 关联代码修改（设计文档遗漏，审查新增）

`getRowToolLabel` 函数（L486）中 `if (source !== 'all')` 分支变为死代码——因为 `source` 恒为 `'all'`，删除该分支：

```tsx
// 修改前
const getRowToolLabel = (item: DbUsageItem) => {
  if (groupBy === 'tool' && item.group_key) return getToolLabel(item.group_key);
  if (selectedTool) return getToolLabel(selectedTool);
  if (source !== 'all') return sourceLabel(source);  // 删除（source 恒为 'all'）
  return '-';
};

// 修改后
const getRowToolLabel = (item: DbUsageItem) => {
  if (groupBy === 'tool' && item.group_key) return getToolLabel(item.group_key);
  if (selectedTool) return getToolLabel(selectedTool);
  return '-';
};
```

chartTitle（L554）中 `sourceLabel(source)` 改为硬编码：

```tsx
// 修改前
const chartTitle = groupBy === 'none'
  ? `${sourceLabel(source)} 趋势`
  : ...

// 修改后
const chartTitle = groupBy === 'none'
  ? 'Token 消耗趋势'
  : ...
```

如果 `sourceLabel` 函数（L69）不再有引用，一并删除：

```tsx
// 删除整个 sourceLabel 函数
function sourceLabel(source: TokenUsageSource): string {
  if (source === 'claude') return 'Claude Code';
  if (source === 'opencode') return 'OpenCode';
  return '全部工具';
}
```

---

## 验证计划

1. 刷新页面确认筛选区域只显示 8 个组件
2. 所有筛选器在一行显示，无换行
3. 切换各个筛选器确认功能正常
4. 数据默认显示全部来源（source='all'）和降序（sort_order='desc'）
5. 导出 CSV 正常，工具列显示正确
6. Console 无报错
7. 浏览器验证通过
