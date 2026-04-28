# Database Tool 左侧列表可拖拽调整宽度 - 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 database-tool 页面左侧 ConnectionList 添加可拖拽调整宽度功能，解决当前固定宽度导致文本截断的问题。

**Architecture:** 复用项目中已有的 `ResizablePanel` 组件（来自 CursorHistory 工具），该组件已封装拖拽逻辑、localStorage 持久化、最小/最大宽度约束。通过将其包裹在 `ConnectionList` 外层并移除固定宽度类实现。

**Tech Stack:** React 18 + TypeScript + Tailwind CSS

---

## Task 1: 修改 DatabaseTool.tsx 引入 ResizablePanel

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/DatabaseTool.tsx`

**Step 1: 添加 import**

在现有 import 之后添加：

```tsx
import ResizablePanel from '../CursorHistory/ResizablePanel';
```

**Step 2: 用 ResizablePanel 包裹 ConnectionList**

找到：

```tsx
      <ConnectionList 
        onAddConfig={handleAddConfig} 
        onEditConfig={handleEditConfig} 
        onSelectTable={handleSelectTable}
        onOpenSqlConsole={handleOpenSqlConsole}
      />
```

替换为：

```tsx
      <ResizablePanel 
        defaultWidth={280} 
        minWidth={200} 
        maxWidth={500} 
        storageKey="dbTool.leftPanelWidth"
      >
        <ConnectionList 
          onAddConfig={handleAddConfig} 
          onEditConfig={handleEditConfig} 
          onSelectTable={handleSelectTable}
          onOpenSqlConsole={handleOpenSqlConsole}
        />
      </ResizablePanel>
```

**Step 3: 验证修改**

检查：
- ResizablePanel 已正确 import
- ConnectionList 被包裹在 ResizablePanel 内部
- 无 TypeScript 错误

---

## Task 2: 移除 ConnectionList 的固定宽度

**Files:**
- Modify: `frontend/src/components/Tools/DatabaseTool/components/ConnectionList.tsx`

**Step 1: 修改外层 div 的 className**

找到（第46行）：

```tsx
    <div className="flex flex-col h-full bg-slate-800 border-r border-slate-700 w-64">
```

替换为：

```tsx
    <div className="flex flex-col h-full bg-slate-800 border-r border-slate-700">
```

**Step 2: 验证修改**

检查：
- `w-64` 已移除
- 其他样式类保持不变
- 组件仍能在 `ResizablePanel` 内正确渲染

---

## Task 3: 构建与验证

**Files:**
- 无需修改，验证步骤

**Step 1: 构建前端**

```bash
cd frontend
npm run build
```

Expected: 构建成功，无 TypeScript 错误或 ESLint 错误

**Step 2: 启动开发服务器验证**

```bash
cd frontend
npm run dev
```

打开浏览器访问 `http://localhost:5178/tools/database-tool`

验证项：
- [ ] 页面正常加载，无报错
- [ ] 左侧面板右侧出现细竖线（拖拽条）
- [ ] 鼠标悬停在拖拽条上时，光标变为 `col-resize`，细线变为蓝色
- [ ] 按住拖拽条左右拖动，左侧面板宽度实时变化
- [ ] 面板宽度在 200px ~ 500px 之间约束
- [ ] 刷新页面后，宽度保持上次设置
- [ ] 列表中的数据库名、表名在宽度增加时能显示更多内容

---

## 回滚方案

如出现问题，回滚修改：
1. `DatabaseTool.tsx`: 移除 `ResizablePanel` 包裹，恢复原来的 `<ConnectionList ... />`
2. `ConnectionList.tsx`: 恢复 `w-64` 固定宽度类

---

## 备注

- `ResizablePanel` 组件位于 `frontend/src/components/Tools/CursorHistory/ResizablePanel.tsx`，已实现：
  - 鼠标按下/移动/抬起事件处理
  - `localStorage` 读写（通过 `storageKey` 参数）
  - `minWidth` / `maxWidth` 边界约束
  - 拖拽条悬停高亮效果（蓝色）
- 本改动不涉及后端 API，纯前端 UI 调整
- 默认宽度 280px 略大于原 256px，给列表内容更多空间
