# 数据库工具分页无限循环问题修复设计文档

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复分页条数切换时导致的无限循环请求问题，使用直接在 `onChange` 中调用的方式替代 `useEffect` 方案。

**Architecture:** 移除导致循环的 `useEffect`，改为在分页条数选择器的 `onChange` 事件处理函数中直接调用 `fetchData` 函数。

**Tech Stack:** React 18 + TypeScript

---

## 1. 问题分析

### 1.1 问题现象

用户打开数据库表数据查看页面后，浏览器 Network 面板显示接口被无限次调用，页面持续发送请求。

### 1.2 问题原因

原有实现中存在依赖项循环：

```typescript
// fetchData 依赖 pageSize
const fetchData = useCallback(async (pageNum: number, newPageSize?: number) => {
  // ... 使用 pageSize
}, [configId, tableName, databaseName, whereClause, orderByClause, pageSize, toast]);

// useEffect 依赖 fetchData 和 result
useEffect(() => {
  if (result) {
    setPage(1);
    fetchData(1);
  }
}, [pageSize, fetchData, result]);
```

**循环链路：**
1. `pageSize` 变化
2. → `fetchData` 函数更新（因为它依赖 `pageSize`）
3. → `useEffect` 触发（因为它依赖 `fetchData`）
4. → 调用 `fetchData(1)` → `setResult(data)` 
5. → `result` 从 `null` 变为有值
6. → `useEffect` 再次触发（因为它依赖 `result`）
7. → 回到步骤 4，形成无限循环

---

## 2. 解决方案

### 2.1 方案 C：直接在 onChange 中调用

**修改点 1：** 移除导致循环的 `useEffect`

```typescript
// 删除以下代码
useEffect(() => {
  if (result) {
    setPage(1);
    fetchData(1);
  }
}, [pageSize, fetchData, result]);
```

**修改点 2：** 在 `onChange` 中直接调用 `fetchData`

```typescript
<select 
  value={pageSize}
  onChange={(e) => {
    const newPageSize = Number(e.target.value);
    setPageSize(newPageSize);
    setPage(1);
    fetchData(1, newPageSize); // 直接调用，传入新的 pageSize
  }}
>
```

### 2.2 为什么方案 C 有效

- **无依赖项循环：** 不引入新的 `useEffect`，避免了依赖项问题
- **代码清晰：** 逻辑集中在 `onChange` 处理函数中，易于理解
- **行为可控：** 只在用户实际切换分页条数时触发，不会因其他状态变化而误触发

---

## 3. 实现细节

### 3.1 修改文件

`frontend/src/components/Tools/DatabaseTool/TableDataViewer.tsx`

### 3.2 具体改动

1. **删除第 72-79 行的 `useEffect`**
2. **修改第 183-191 行的 `onChange` 处理函数**

### 3.3 修改后代码

```typescript
// 第 37-59 行：fetchData 函数保持不变
const fetchData = useCallback(async (pageNum: number, newPageSize?: number) => {
  setLoading(true);
  try {
    const data = await api.queryTableData(configId, tableName, {
      database_name: databaseName,
      where: whereClause,
      order_by: orderByClause,
      page: pageNum,
      page_size: newPageSize ?? pageSize
    });
    // ...
  }
  // ...
}, [configId, tableName, databaseName, whereClause, orderByClause, pageSize, toast]);

// 删除第 72-79 行的 useEffect

// 第 181-199 行：修改 onChange 处理函数
<select 
  value={pageSize}
  onChange={(e) => {
    const newPageSize = Number(e.target.value);
    setPageSize(newPageSize);
    setPage(1);
    fetchData(1, newPageSize);
  }}
  className="bg-slate-900 border border-slate-600 rounded px-2 py-1 focus:outline-none"
>
  <option value={10}>10</option>
  <option value={20}>20</option>
  <option value={50}>50</option>
  <option value={100}>100</option>
</select>
```

---

## 4. 测试要点

### 4.1 功能测试

- [ ] 切换分页条数后，数据自动刷新
- [ ] 切换分页条数后，页码重置为 1
- [ ] 不会触发无限循环请求
- [ ] 首次加载表格时，只发送一次请求

### 4.2 浏览器验证

- [ ] Network 面板显示请求次数正常（每次切换只发送 1 次请求）
- [ ] 浏览器 Console 无错误
- [ ] 页面响应正常

---

## 5. 验收标准

1. ✅ 无限循环请求问题已修复
2. ✅ 切换分页条数后，数据自动刷新
3. ✅ 页码自动重置为第 1 页
4. ✅ 浏览器 Console 无错误
5. ✅ Network 面板显示请求次数正常

---

## 6. 后续注意事项

1. **fetchData 依赖项：** `fetchData` 的依赖项中包含 `pageSize`，但在 `onChange` 中我们已经通过参数 `newPageSize` 传递了新值，所以不会有问题
2. **其他状态变化：** 切换 WHERE、ORDER BY 时，仍需手动点击"Run"按钮，这是预期行为
