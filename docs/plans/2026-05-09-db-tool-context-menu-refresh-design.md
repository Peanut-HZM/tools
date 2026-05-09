# 数据库工具：右键菜单刷新功能 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在左侧连接列表的右键菜单中添加刷新功能：连接节点添加"刷新连接"，表节点添加"刷新表结构"。

**Architecture:** 在现有右键菜单数组中插入新菜单项，复用已有的 `fetchDatabases()`、`onRefreshConfigs()`、`onRefresh()` 函数。

**Tech Stack:** React 18, TypeScript, Tailwind CSS

---

### Task 1: 连接节点右键菜单添加"刷新连接"

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx` (ConnectionNode.handleContextMenu)
- Modify: `frontend/src/i18n/locales/zh-CN.ts`
- Modify: `frontend/src/i18n/locales/en-US.ts`

**Step 1: 添加 i18n 键**

`zh-CN.ts` contextMenu 中新增：
```typescript
refreshConnection: '刷新连接',
```

`en-US.ts` contextMenu 中新增：
```typescript
refreshConnection: 'Refresh Connection',
```

**Step 2: 在 ConnectionNode 的 handleContextMenu 中添加"刷新连接"菜单项**

在"测试连接"菜单项后面、分隔符前面插入：

```typescript
{
  label: t.database.contextMenu.refreshConnection,
  icon: 'fa-sync',
  action: async () => {
    await fetchDatabases();
    await onRefreshConfigs();
  }
},
```

**Step 3: 验证**

- TypeScript 编译通过
- 浏览器中右键点击连接节点，菜单中出现"刷新连接"
- 点击"刷新连接"后，数据库列表更新

---

### Task 2: 表节点右键菜单添加"刷新表结构"

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx` (FolderNode.handleItemContextMenu)
- Modify: `frontend/src/i18n/locales/zh-CN.ts`
- Modify: `frontend/src/i18n/locales/en-US.ts`

**Step 1: 添加 i18n 键**

`zh-CN.ts` contextMenu 中新增：
```typescript
refreshTableStructure: '刷新表结构',
```

`en-US.ts` contextMenu 中新增：
```typescript
refreshTableStructure: 'Refresh Table Structure',
```

**Step 2: 在 FolderNode 的 handleItemContextMenu 中添加"刷新表结构"菜单项**

在表节点右键菜单末尾（"删除表"之后）追加：

```typescript
{
  separator: true,
  label: '',
  action: () => {}
},
{
  label: t.database.contextMenu.refreshTableStructure,
  icon: 'fa-sync',
  action: async () => {
    await onRefresh();
  }
},
```

**Step 3: 验证**

- TypeScript 编译通过
- 浏览器中右键点击表节点，菜单中出现"刷新表结构"
- 点击后表列表刷新
