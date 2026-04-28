# Token Usage UI Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enhance Token Usage Stats tool with readable units, chart toggling, dynamic filters, and pagination.

**Architecture:** Frontend-only enhancements. Modify `TokenUsage.tsx` to handle new states and rendering logic.

**Tech Stack:** React 18 + Tailwind CSS + recharts

---

### Task 1: Chinese Unit Formatting

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

**Logic:**
Add `formatToken` helper:
```tsx
const formatToken = (num: number) => {
  if (num >= 100_0000_0000) return `${(num / 100_0000_0000).toFixed(1)}亿`;
  if (num >= 1000_0000) return `${(num / 1000_0000).toFixed(1)}千万`;
  if (num >= 100_0000) return `${(num / 100_0000).toFixed(1)}百万`;
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
  return num.toLocaleString();
};
```
Replace `formatNumber` in cards and table with `formatToken`.

---

### Task 2: Chart Type Toggle

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

**State:**
`const [chartType, setChartType] = useState<'bar' | 'line'>('bar');`

**UI:**
Add buttons next to filter bar:
```tsx
<button onClick={() => setChartType('bar')} className={chartType === 'bar' ? 'bg-blue-600' : 'bg-slate-700'}>📊 条形图</button>
<button onClick={() => setChartType('line')} className={chartType === 'line' ? 'bg-blue-600' : 'bg-slate-700'}>📈 折线图</button>
```

**Rendering Logic:**
- If `bar`: Keep existing `ComposedChart` with bars (stacked) + cost line.
- If `line`: Switch to `ComposedChart` with 3 `Line` components (Input, Output, Cache).

---

### Task 3: Dynamic Time Range

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

**Logic:**
Define options based on `reportType`:
```tsx
const TIME_OPTIONS = {
  daily: [{ label: '近 7 天', val: 7 }, { label: '近 30 天', val: 30 }, { label: '近 90 天', val: 90 }],
  weekly: [{ label: '近 4 周', val: 28 }, { label: '近 12 周', val: 84 }, { label: '近 24 周', val: 168 }],
  monthly: [{ label: '近 3 月', val: 90 }, { label: '近 6 月', val: 180 }, { label: '近 12 月', val: 365 }],
};
// When reportType changes, reset days to first option.
```

---

### Task 4: Table Pagination

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

**State:**
`const [page, setPage] = useState(1);`
`const [pageSize, setPageSize] = useState(10);`

**Rendering:**
- `currentPageItems = items.slice((page - 1) * pageSize, page * pageSize)`
- Use `currentPageItems` for `map` in table body.
- Add pagination footer component with page numbers and page size selector (10/20/50).

---

### Task 5: Verification

**Step 1:**
Run `npm run build` in `/Users/huazhongmin/IdeaProjects/tools/frontend`.
Expected: Success, no errors.
