# 数据库工具分页自动刷新设计文档

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 当用户在数据库工具页面切换分页条数（page size）时，自动刷新表格数据，无需手动点击"Run"按钮。

**Architecture:** 使用 React useEffect 监听 pageSize 状态变化，当 pageSize 变化时自动重置页码到第 1 页并触发数据加载。

**Tech Stack:** React 18 + TypeScript, useState, useEffect

---

## 1. 问题描述

### 1.1 现状

当前 `TableDataViewer.tsx` 组件中，分页条数选择器的 `onChange` 事件只更新了 `pageSize` 状态：

```typescript
<select 
  value={pageSize}
  onChange={(e) => {
    setPageSize(Number(e.target.value));
    // 注释：这里没有触发数据刷新，用户需要手动点击 Run 按钮
  }}
>
```

### 1.2 问题

用户切换分页条数后（如从 20 条/页 → 50 条/页），表格不会自动更新，需要手动点击"Run"按钮才能看到新数据。

### 1.3 期望行为

用户切换分页条数后，表格自动重新加载数据（重置到第 1 页）。

---

## 2. 解决方案

### 2.1 方案概述

使用 `useEffect` 监听 `pageSize` 状态变化，当 `pageSize` 变化时：
1. 重置页码到第 1 页
2. 调用 `fetchData(1)` 刷新数据

### 2.2 代码改动

**文件：** `frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx`

**添加 useEffect：**

```typescript
// 监听 pageSize 变化，自动刷新数据
useEffect(() => {
  setPage(1);
  fetchData(1);
}, [pageSize]);
```

### 2.3 注意事项

1. **初始加载问题：** 组件首次挂载时 `pageSize` 从 `undefined` 变为 `20`（默认值），不应触发刷新。解决方案：
   - 方案 A：在 `useEffect` 中检查 `result !== null`（已有数据后才监听）
   - 方案 B：使用 `useRef` 记录是否首次渲染
   - 方案 C：依赖项中加入 `result`，只有当 `result` 不为空时才处理

2. **依赖项问题：** `fetchData` 函数在 `useEffect` 依赖项中会导致循环依赖，需要使用 `useCallback` 包裹或简化逻辑。

---

## 3. 实现细节

### 3.1 修改后的代码结构

```typescript
const TableDataViewer: React.FC<TableDataViewerProps> = ({ configId, databaseName, tableName }) => {
  // ... 其他状态 ...
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  
  // ... fetchSchema 和 fetchData 函数 ...

  // 新增：监听 pageSize 变化
  useEffect(() => {
    // 只在已有数据后监听（避免初始加载时重复请求）
    if (result) {
      setPage(1);
      fetchData(1);
    }
  }, [pageSize]);

  // ... 其他代码 ...
};
```

### 3.2 边界情况处理

| 场景 | 行为 |
|------|------|
| 首次加载表格 | 不触发自动刷新（`result` 为 `null`） |
| 切换分页条数 | 重置到第 1 页，自动刷新数据 |
| 切换 WHERE/ORDER BY | 现有逻辑不变（重置到第 1 页，需点击 Run） |
| 切换表 | 现有逻辑不变（重置所有状态） |

---

## 4. 测试要点

### 4.1 功能测试

- [ ] 切换分页条数（10 → 20 → 50 → 100）后，表格自动刷新
- [ ] 切换分页条数后，页码重置为 1
- [ ] 首次打开表格时，不因 useEffect 触发额外请求
- [ ] 分页、WHERE 条件、ORDER BY 功能正常

### 4.2 性能测试

- [ ] 快速切换分页条数时，不会产生过多重复请求
- [ ] 大数据量（100+ 行）加载时，UI 响应正常

### 4.3 浏览器验证

- [ ] 页面加载无报错
- [ ] 浏览器 Console 无错误
- [ ] 切换分页条数后，数据正确显示

---

## 5. 验收标准

1. ✅ 切换分页条数后，表格自动刷新数据
2. ✅ 页码自动重置为第 1 页
3. ✅ 首次加载时不触发额外请求
4. ✅ 浏览器 Console 无错误
5. ✅ 不影响现有分页、WHERE、ORDER BY 功能

---

## 6. 后续优化建议（可选）

1. **后端返回总记录数：** 当前分页逻辑通过返回行数判断是否有下一页，建议后端返回 `total_count` 字段
2. **防抖处理：** 如果用户频繁切换分页条数，可添加防抖（300ms）减少请求次数
3. **加载状态优化：** 切换分页条数时显示局部 loading 状态
