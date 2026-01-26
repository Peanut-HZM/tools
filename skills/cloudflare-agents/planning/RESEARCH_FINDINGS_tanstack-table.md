# Community Knowledge Research: TanStack Table

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/tanstack-table/SKILL.md
**Packages Researched**: @tanstack/react-table@8.21.3, @tanstack/react-virtual@3.13.18
**Official Repo**: TanStack/table
**Time Window**: January 2024 - January 2026 (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 12 |
| TIER 1 (Official) | 8 |
| TIER 2 (High-Quality Community) | 2 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 1 |
| Recommended to Add | 9 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: React Compiler Incompatibility (React 19+)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #5567](https://github.com/TanStack/table/issues/5567) | [Maintainer Comment (KevinVandy)](https://github.com/TanStack/table/issues/5567#issuecomment-2130174161)
**Date**: 2024-05-18
**Verified**: Yes - Maintainer confirmed
**Impact**: HIGH
**Already in Skill**: No

**Description**:
TanStack Table v8 is incompatible with React 19's new compiler. The table core instance returned from `useReactTable` doesn't re-render as expected when the React Compiler's memoization is applied, causing table data changes to not reflect in the UI.

**Reproduction**:
```typescript
// With React Compiler enabled
function TableComponent() {
  const [data, setData] = useState([...initialData])
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() })

  // Data changes but table.getRowModel().rows doesn't update
  const addRow = () => setData([...data, newRow])

  return <table>...</table> // Table doesn't re-render
}
```

**Solution/Workaround**:
```typescript
// Add "use no memo" directive at the top of any component using useReactTable
"use no memo"

function TableComponent() {
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() })
  // Now works correctly with React Compiler
}
```

**Official Status**:
- [x] Documented behavior
- [x] Known issue, workaround required
- [ ] Fixed in v9 alpha (in progress)

**Cross-Reference**:
- Also affects: Column visibility, row selection (Issue #6117)
- Related to: Issue #5871 (mutation comment statement)
- Maintainer quote: "use no memo on table components for now. A v9 alpha branch was recently created where we will focus on version bumping the peer dependencies"

---

### Finding 1.2: Server-Side Pagination Row Selection Bug

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #5929](https://github.com/TanStack/table/issues/5929) | [GitHub Issue #6039](https://github.com/TanStack/table/issues/6039)
**Date**: 2025-02-24 (5929), 2025-06-17 (6039)
**Verified**: Yes - With reproducible examples
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using manual server-side pagination with row selection:
1. **toggleAllRowsSelected** only deselects current page, not all selected rows across pages
2. **Header checkbox state** (indeterminate/checked) is incorrect because it compares total selected rows against `getFilteredRowModel().flatRows.length` (current page row count) instead of total row count

**Reproduction**:
```typescript
// Server-side pagination with selection
const table = useReactTable({
  data: currentPageData,
  columns,
  manualPagination: true,
  pageCount,
  // User selects 3 rows on page 1
  // Navigates to page 2
  // Clicks "Deselect All" → only page 2 is deselected, page 1 remains selected
})
```

**Solution/Workaround**:
```typescript
// Manual fix: Clear all selection state when toggling off
const toggleAllRows = (value: boolean) => {
  if (!value) {
    table.setRowSelection({}) // Clear entire selection object
  } else {
    table.toggleAllRowsSelected(true)
  }
}
```

**Official Status**:
- [ ] Not yet fixed
- [x] Known issue with reproducible examples
- [ ] Under investigation

**Cross-Reference**:
- Related to: Issue #5850 (row selection not cleaned up when data removed)
- Related discussion: #5875 (similar "Select all" behavior issue)

---

### Finding 1.3: Virtualized Rows Break Inside Hidden Tabs/Modals

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #6109](https://github.com/TanStack/table/issues/6109)
**Date**: 2025-10-12
**Verified**: Yes - With CodeSandbox reproduction
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When TanStack Table + TanStack Virtual are used together inside tabbed content or modals where inactive content is hidden via `display: none`, the virtualizer continues performing layout calculations while hidden, leading to:
- Infinite re-render loops (large datasets: 50k+ rows)
- Incorrect scroll position when tab becomes visible again
- Empty table or reset scroll (small datasets: <100 rows)

**Reproduction**:
```typescript
// Tab 1: Virtualized table
<div style={{ display: activeTab === 'tab1' ? 'block' : 'none' }}>
  <VirtualizedTable data={50000rows} />
</div>

// Switch to tab 2 → Error: Maximum update depth exceeded
```

**Solution/Workaround**:
```typescript
// Check if container is hidden before virtualizer calculations
const rowVirtualizer = useVirtualizer({
  count: rows.length,
  getScrollElement: () => containerRef.current,
  estimateSize: () => 50,
  // Add enabled flag based on visibility
  enabled: containerRef.current?.getClientRects().length !== 0,
})

// OR: Conditionally render table instead of hiding with CSS
{activeTab === 'tab1' && <VirtualizedTable />}
```

**Official Status**:
- [ ] Not yet fixed
- [x] Known issue with reproducible example
- [ ] Workaround: Skip calculations when hidden

**Cross-Reference**:
- Affects: Any setup with hidden containers (modals, accordions, collapsible panels)
- Browser differences: Firefox shows empty table, Chrome resets scroll

---

### Finding 1.4: onPaginationChange Returns Incorrect pageIndex (Client-Side)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #5970](https://github.com/TanStack/table/issues/5970)
**Date**: 2025-03-17
**Verified**: Yes - With CodeSandbox
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using client-side pagination with custom `onPaginationChange` (e.g., for URL synchronization), the handler:
- Fires even when only sorting is applied (not pagination)
- Always returns `pageIndex: 0` instead of current page
- Only occurs in client mode (works correctly in server/manual mode)

**Reproduction**:
```typescript
// Client-side pagination with URL sync
const [pagination, setPagination] = useState({ pageIndex: 2, pageSize: 10 })

const table = useReactTable({
  data,
  columns,
  state: { pagination },
  onPaginationChange: (updater) => {
    const newState = typeof updater === 'function' ? updater(pagination) : updater
    console.log(newState) // Always shows pageIndex: 0 when clicking "Next"
    setPagination(newState)
    updateURL(newState)
  },
})
```

**Solution/Workaround**:
```typescript
// Switch to manual pagination to get correct behavior
const table = useReactTable({
  data,
  columns,
  manualPagination: true, // Forces correct state tracking
  pageCount: Math.ceil(data.length / pagination.pageSize),
  state: { pagination },
  onPaginationChange: setPagination,
})
```

**Official Status**:
- [ ] Not yet fixed
- [x] Known issue
- [ ] Workaround: Use manual pagination

---

### Finding 1.5: Column Pinning Breaks with Column Groups

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #5397](https://github.com/TanStack/table/issues/5397)
**Date**: 2024-03-07
**Verified**: Yes - With StackBlitz reproduction
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using column groups (via `columnHelper.group()`) with sticky column pinning, pinning the parent group column causes:
- Group header position is incorrect (doesn't stick properly)
- Duplicated group headers when grouping multiple columns
- `column.getStart('left')` returns wrong values for group headers

**Reproduction**:
```typescript
const columns = [
  columnHelper.group({
    id: 'info',
    header: 'Info',
    columns: [
      { accessorKey: 'firstName', header: 'First Name' },
      { accessorKey: 'lastName', header: 'Last Name' },
    ],
  }),
  { accessorKey: 'age', header: 'Age' },
]

// Try to pin 'info' group to left → group header doesn't stick correctly
table.getColumn('info')?.pin('left')
```

**Solution/Workaround**:
```typescript
// Disable pinning for grouped columns
const isPinnable = (column) => !column.parent

// OR: Pin individual columns within group, not the group itself
table.getColumn('firstName')?.pin('left')
table.getColumn('lastName')?.pin('left')
```

**Official Status**:
- [ ] Not yet fixed
- [x] Known issue
- [ ] Multiple users confirmed

**Cross-Reference**:
- Related: Issue #5783 (space between adjacent pinned columns)
- Related: Issue #6131 (fixed columns overlap adjacent columns)

---

### Finding 1.6: Row Selection Not Cleaned Up When Data Removed

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #5850](https://github.com/TanStack/table/issues/5850)
**Date**: 2024-12-28
**Verified**: Yes - Maintainer confirmed intentional behavior
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When table data is updated and rows are removed (e.g., via WebSockets or real-time updates), row selection state is not automatically cleaned up. Selected rows that no longer exist in the data remain in the selection state.

This is **intentional behavior** to support server-side pagination (where rows disappear from current page but should stay selected), but causes confusion for client-side/real-time scenarios.

**Reproduction**:
```typescript
const [data, setData] = useState(initialData)
const table = useReactTable({ data, columns, enableRowSelection: true })

// User selects row with id "123"
// Data is updated, row "123" is removed
setData(data.filter(row => row.id !== "123"))

// Row selection state still contains "123"
console.log(table.getState().rowSelection) // { "123": true }
```

**Solution/Workaround**:
```typescript
// When removing data, manually clean up selection
const removeRow = (idToRemove: string) => {
  // Remove from data
  setData(data.filter(row => row.id !== idToRemove))

  // Clean up selection if it was selected
  const { rowSelection } = table.getState()
  if (rowSelection[idToRemove]) {
    table.setRowSelection((old) => {
      const filtered = Object.entries(old).filter(([id]) => id !== idToRemove)
      return Object.fromEntries(filtered)
    })
  }
}

// OR: Use table.resetRowSelection(true) to clear all
```

**Official Status**:
- [x] Intentional behavior (for server-side pagination support)
- [ ] API improvement considered for v9

**Cross-Reference**:
- Maintainer quote: "80% of TanStack Table implementations use manual/server-side patterns"
- Related: Issue #5929 (toggleAllRowsSelected server-side behavior)

---

### Finding 1.7: Performance Issue with DevTools Open

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #5988](https://github.com/TanStack/table/issues/5988)
**Date**: 2025-04-13
**Verified**: Yes
**Impact**: LOW (development only)
**Already in Skill**: No

**Description**:
Table performance significantly degrades when React DevTools are open, especially with medium-to-large datasets (500+ rows). This is due to DevTools inspecting the table instance and row models on every render.

**Reproduction**:
```typescript
// With 1000 rows and React DevTools open
const table = useReactTable({
  data: data1000Rows,
  columns,
  getCoreRowModel: getCoreRowModel(),
})
// Noticeable lag on sort/filter/pagination
```

**Solution/Workaround**:
```typescript
// Close React DevTools during performance testing
// OR: Use React DevTools Profiler to identify bottlenecks, then close for normal development
```

**Official Status**:
- [x] Known behavior
- [x] React DevTools issue, not table issue
- [ ] No fix needed

**Cross-Reference**:
- Not a production issue (only affects development)

---

### Finding 1.8: TypeScript getValue() Type Inference with Grouped Columns

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #5860](https://github.com/TanStack/table/issues/5860)
**Date**: 2025-01-08
**Verified**: Yes
**Impact**: LOW (TypeScript only)
**Already in Skill**: No

**Description**:
When using `columnHelper.accessor()` inside `columnHelper.group()`, TypeScript's `getValue()` method fails to infer the correct return type. It falls back to `unknown` instead of the accessor's actual type.

**Reproduction**:
```typescript
const columns = [
  columnHelper.group({
    id: 'info',
    header: 'Info',
    columns: [
      columnHelper.accessor('firstName', {
        cell: (info) => {
          const value = info.getValue() // Type is 'unknown' instead of 'string'
          return value.toUpperCase() // TypeScript error
        },
      }),
    ],
  }),
]
```

**Solution/Workaround**:
```typescript
// Manually specify type
cell: (info) => {
  const value = info.getValue() as string
  return value.toUpperCase()
}

// OR: Use renderValue() which has better type inference
cell: (info) => {
  const value = info.renderValue() // Correctly typed
  return typeof value === 'string' ? value.toUpperCase() : value
}
```

**Official Status**:
- [ ] Not yet fixed
- [x] Known TypeScript limitation
- [ ] Under investigation

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Infinite Re-Render Pitfall

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [TanStack FAQ](https://tanstack.com/table/latest/docs/faq) | [Blog Post (JP Camara)](https://jpcamara.com/2023/03/07/making-tanstack-table.html)
**Date**: Official docs + 2023 blog (still current)
**Verified**: Official documentation
**Impact**: HIGH
**Already in Skill**: Yes (Known Issue #1)

**Description**:
ALREADY DOCUMENTED in skill as "Issue #1: Infinite Re-Renders". This is a well-known pattern covered in official docs.

**Community Validation**:
- Official FAQ lists this as #1 common mistake
- Multiple blog posts confirm
- Frequently asked on Stack Overflow

**Recommendation**: Already covered. No action needed.

---

### Finding 2.2: Performance Bottleneck with Grouping Feature

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Blog Post (JP Camara)](https://jpcamara.com/2023/03/07/making-tanstack-table.html) | [GitHub Issue #5926](https://github.com/TanStack/table/issues/5926)
**Date**: 2023-03-07 (blog), 2025-02-20 (issue)
**Verified**: Code review + issue report
**Impact**: MEDIUM
**Already in Skill**: Partially (mentions virtualization for large datasets)

**Description**:
The grouping feature causes significant performance degradation on medium-to-large datasets. With grouping enabled, render times can increase from <1 second to 30-40 seconds on 50k rows. The issue is related to `createRow` in table-core using excessive memory for group calculations.

**Reproduction**:
```typescript
const table = useReactTable({
  data: data50000Rows,
  columns,
  getCoreRowModel: getCoreRowModel(),
  getGroupedRowModel: getGroupedRowModel(), // Causes slowdown
  state: { grouping: ['status'] },
})
// Render time: 30-40 seconds vs <1 second without grouping
```

**Solution/Workaround**:
```typescript
// 1. Use server-side grouping for large datasets
// 2. Implement pagination to limit rows per page
// 3. Disable grouping for 10k+ rows
const shouldEnableGrouping = data.length < 10000

// 4. OR: Use React.memo on row components
const MemoizedRow = React.memo(TableRow)
```

**Community Validation**:
- Blog post with performance testing
- GitHub issue confirms memory usage problem
- Multiple users report similar issues

**Recommendation**: Add performance warning to grouping section.

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: getCoreRowModel vs getRowModel Confusion

**Trust Score**: TIER 3 - Community Consensus
**Source**: Multiple discussions + [Medium Article](https://medium.com/@aylo.srd/server-side-pagination-and-sorting-with-tanstack-table-and-react-bd493170125e)
**Date**: 2024-2025 discussions
**Verified**: Cross-referenced with docs
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
A common mistake when implementing server-side features is using `table.getCoreRowModel()` instead of `table.getRowModel()` when rendering rows. This prevents pagination, filtering, and sorting from working because `getCoreRowModel()` returns unprocessed data.

**Solution**:
```typescript
// ❌ WRONG - pagination won't work
<tbody>
  {table.getCoreRowModel().rows.map(row => <TableRow row={row} />)}
</tbody>

// ✅ CORRECT - returns processed rows
<tbody>
  {table.getRowModel().rows.map(row => <TableRow row={row} />)}
</tbody>
```

**Consensus Evidence**:
- Medium article mentions this as common mistake
- Multiple Stack Overflow questions
- No official doc warning about this specific pattern

**Recommendation**: Add to "Common Mistakes" section or as Known Issue #7.

---

### Finding 3.2: Meta Property for Custom Column Styling

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Tutorial (Newbeelearn)](https://newbeelearn.com/blog/using-tanstack-table-in-react/)
**Date**: 2024
**Verified**: Cross-referenced with docs
**Impact**: LOW
**Already in Skill**: No

**Description**:
TanStack Table's `meta` property on column definitions is underutilized but allows custom properties for styling and behavior without polluting the column definition type. This is useful for applying conditional styles to table elements.

**Solution**:
```typescript
const columns = [
  {
    accessorKey: 'status',
    header: 'Status',
    meta: {
      headerClassName: 'text-center',
      cellClassName: (value) => value === 'active' ? 'bg-green-100' : 'bg-gray-100',
    },
  },
]

// In render
<th className={header.column.columnDef.meta?.headerClassName}>
  {header.column.columnDef.header}
</th>
```

**Consensus Evidence**:
- Multiple tutorials mention this pattern
- Official docs briefly mention meta but don't showcase use cases
- Community considers it a "best practice"

**Recommendation**: Add to "Advanced Patterns" section or as a tip.

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

No TIER 4 findings in this research session.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Infinite re-renders | Known Issues #1 | Fully covered with useMemo solution |
| Query + table state mismatch | Known Issues #2 | Covered - include state in query key |
| Server-side manual flags | Known Issues #3 | Covered - manual* flags documented |
| Large dataset performance | Known Issues #6 | Covered - mentions virtualization |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 React Compiler | Known Issues | Add as Issue #7: React 19 Compiler incompatibility |
| 1.2 Server-Side Row Selection | Known Issues | Add as Issue #8: toggleAllRowsSelected server-side bug |
| 1.3 Virtualized Hidden Tabs | Virtualization section | Add warning about hidden containers |
| 1.4 onPaginationChange pageIndex | Known Issues | Add as Issue #9: Client-side pagination state bug |

### Priority 2: Consider Adding (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.5 Column Pinning + Groups | Column/Row Pinning | Add limitation note |
| 1.6 Row Selection Cleanup | Known Issues | Add as Issue #10 with workaround |
| 2.2 Grouping Performance | Row Grouping section | Add performance warning |
| 3.1 getCoreRowModel confusion | Quick Reference or Common Mistakes | Add clarity note |

### Priority 3: Document as Notes (TIER 1, Low Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.7 DevTools Performance | Performance tips | Brief mention |
| 1.8 TypeScript getValue() | TypeScript section | Add type assertion pattern |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "virtualization" in TanStack/table | 2 | 2 |
| "server-side pagination" in TanStack/table | 6 | 4 |
| "re-render" in TanStack/table | 8 | 3 |
| "pinning" in TanStack/table | 7 | 3 |
| "grouping" in TanStack/table | 5 | 2 |
| "filtering" in TanStack/table | 8 | 2 |
| "performance" in TanStack/table | 8 | 3 |
| "typescript" in TanStack/table | 1 | 1 |
| Recent releases (v8.20.0 - v8.21.3) | 15 | 2 |

**Key Issues Examined**:
- #5567 (React Compiler - 29 comments)
- #6117 (React 19.2 - 6 comments)
- #5929 (toggleAllRowsSelected - 0 comments, clear description)
- #6039 (Manual pagination selection - 0 comments, with reproduction)
- #6109 (Virtualized hidden tabs - 0 comments, detailed reproduction)
- #5970 (onPaginationChange bug - 0 comments, with CodeSandbox)
- #5397 (Column pinning groups - 9 comments, multiple confirmations)
- #5850 (Row selection cleanup - 4 comments, maintainer explanation)
- #5988 (DevTools performance - 4 comments)
- #5860 (TypeScript getValue - 2 comments)

### Web Search

| Query | Results | Quality |
|-------|---------|---------|
| "tanstack react-table edge case workaround 2024" | 10 | 3 relevant (FAQ, blog posts) |
| "@tanstack/react-table server pagination issues 2025" | 10 | 4 high-quality (official docs, Medium) |

**High-Quality Sources**:
- [TanStack Table FAQ](https://tanstack.com/table/latest/docs/faq) - Official
- [JP Camara Blog](https://jpcamara.com/2023/03/07/making-tanstack-table.html) - Performance deep dive
- [Medium Article](https://medium.com/@aylo.srd/server-side-pagination-and-sorting-with-tanstack-table-and-react-bd493170125e) - Server-side patterns
- [Newbeelearn Tutorial](https://newbeelearn.com/blog/using-tanstack-table-in-react/) - Styling patterns

### Release Notes

**Versions Reviewed**: v8.21.3 (latest), v8.21.0, v8.20.0

**Findings**:
- v8.21.0: Angular refactor, documentation fixes, no major React changes
- v8.20.0: Vue reactivity support, no breaking changes
- No breaking changes affecting skill content since v8.17.3

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue content
- `gh release view` for release notes
- `WebSearch` for Stack Overflow and community content

**Limitations**:
- Stack Overflow direct site search not working via WebSearch API - used broader queries
- Limited to issues since 2024-01-01 for relevance
- Focused on React adapter (most popular) - Vue/Angular/Svelte issues not deeply explored

**Time Spent**: ~25 minutes

**Version Context**:
- Skill last updated: 2026-01-09 (v8.21.3)
- Research performed: 2026-01-21
- Current version: v8.21.3 (released 2025-04-14)
- No new major releases since skill update

---

## Suggested Follow-up

**For code-example-validator**: Validate code examples in findings 1.1 (React Compiler workaround), 1.2 (row selection fix), and 1.3 (virtualization visibility check) before adding to skill.

**For api-method-checker**: Verify that `getClientRects()` method used in finding 1.3 is available in all target browsers.

**For content-accuracy-auditor**: Cross-reference finding 1.6 (row selection cleanup) with current v8.21.3 behavior to ensure maintainer's explanation is still current.

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

**For React Compiler Issue (Finding 1.1)**:

Add to `## Known Issues & Solutions` section:

```markdown
**Issue #7: React Compiler Incompatibility (React 19+)**
- **Error**: Table doesn't re-render when data changes with React Compiler enabled
- **Cause**: React Compiler's automatic memoization conflicts with table core instance
- **Source**: [GitHub Issue #5567](https://github.com/TanStack/table/issues/5567)
- **Fix**: Add `"use no memo"` directive at top of components using `useReactTable`

```typescript
"use no memo"

function TableComponent() {
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() })
  // Now works correctly with React Compiler
}
```

**Note**: This issue also affects column visibility and row selection. Full fix coming in v9.
```

**For Server-Side Row Selection (Finding 1.2)**:

```markdown
**Issue #8: Server-Side Pagination Row Selection**
- **Error**: `toggleAllRowsSelected(false)` only deselects current page, not all pages
- **Cause**: Selection state persists across pages (intentional for server-side use cases)
- **Source**: [GitHub Issue #5929](https://github.com/TanStack/table/issues/5929)
- **Fix**: Manually clear selection state when toggling off

```typescript
const toggleAllRows = (value: boolean) => {
  if (!value) {
    table.setRowSelection({}) // Clear entire selection object
  } else {
    table.toggleAllRowsSelected(true)
  }
}
```
```

**For Virtualized Hidden Tabs (Finding 1.3)**:

Add to `## Virtualization (1000+ Rows)` section:

```markdown
**⚠️ Important**: When using virtualization inside tabbed content or modals that hide inactive content with `display: none`, add a visibility check:

```typescript
const rowVirtualizer = useVirtualizer({
  count: rows.length,
  getScrollElement: () => containerRef.current,
  estimateSize: () => 50,
  overscan: 10,
  // Disable when container is hidden to prevent infinite re-renders
  enabled: containerRef.current?.getClientRects().length !== 0,
})

// OR: Conditionally render instead of hiding with CSS
{isVisible && <VirtualizedTable />}
```

**Why**: The virtualizer performs layout calculations while hidden, causing infinite loops (large datasets) or incorrect scroll positions (small datasets).

**Source**: [GitHub Issue #6109](https://github.com/TanStack/table/issues/6109)
```

---

**Research Completed**: 2026-01-21 15:45 UTC
**Next Research Due**: After v8.22.0 release OR after v9.0.0 stable (expected Q2 2026)
