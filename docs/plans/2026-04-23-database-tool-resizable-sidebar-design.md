# Database Tool 左侧列表可拖拽调整宽度 - 设计文档

## 1. 需求概述

**目标**: 优化 `http://localhost:5178/tools/database-tool` 页面，使左侧列表（ConnectionList）可以拖动改变宽度，确保用户能完整看到列表中的数据。

**问题**: 当前左侧列表使用固定宽度 `w-64`（256px），内部大量使用 `truncate` 截断文本，导致数据库名、表名、连接别名等内容经常被截断，无法完整查看。

## 2. 方案对比

### 方案A: 复用现有 `ResizablePanel` 组件（推荐）
- **改动范围**: `DatabaseTool.tsx`、`ConnectionList.tsx`
- **优点**:
  - 零新依赖，项目中已验证可用
  - 改动极小，仅2个文件
  - 支持 localStorage 持久化用户偏好宽度
  - 支持最小/最大宽度限制
- **缺点**: 无

### 方案B: 引入 `react-resizable-panels` 库
- **优点**: 专业库，功能完善
- **缺点**: 需新增 npm 依赖，对本需求 overkill

### 方案C: 手动内联实现拖拽逻辑
- **缺点**: 代码重复，维护成本高

## 3. 最终方案: 方案A

### 3.1 组件复用
直接复用 `/frontend/src/components/Tools/CursorHistory/ResizablePanel.tsx`，该组件已实现：
- 鼠标拖拽调整宽度
- `localStorage` 持久化
- 最小/最大宽度约束
- 悬停高亮效果

### 3.2 文件改动

#### `DatabaseTool.tsx`
```tsx
import ResizablePanel from '../CursorHistory/ResizablePanel';

// 包裹 ConnectionList
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

#### `ConnectionList.tsx`
- 将最外层 `<div className="flex flex-col h-full bg-slate-800 border-r border-slate-700 w-64">` 的 `w-64` 移除
- 宽度由父级 `ResizablePanel` 控制

### 3.3 交互设计
- 左侧面板右侧出现 4px 拖拽条，悬停时高亮为蓝色
- 按住拖拽条左右拖动实时调整面板宽度
- 松开鼠标后自动保存到 `localStorage`
- 下次访问自动恢复上次设置的宽度

### 3.4 视觉影响
- 面板拉宽后，`truncate` 文本显示更多内容
- 超出部分仍用省略号，保持整洁

## 4. 边界情况
- 宽度小于 `minWidth`（200px）时自动约束
- 宽度大于 `maxWidth`（500px）时自动约束
- `localStorage` 被清除时恢复默认宽度 280px

## 5. 测试要点
- [ ] 拖拽条可正常显示和悬停高亮
- [ ] 左右拖动可实时调整宽度
- [ ] 刷新页面后宽度保持
- [ ] 最小/最大宽度限制生效
- [ ] 列表内容在宽度增加时显示更多文本

---
日期: 2026-04-23
