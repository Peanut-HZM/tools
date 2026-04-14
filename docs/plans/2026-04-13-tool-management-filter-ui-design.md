# 工具管理页面筛选栏 UI 优化设计

**目标**: 将工具管理页面的筛选栏从杂乱的网格布局改造为横向工具栏风格，增强视觉层次和操作效率

**架构**: 纯前端改造，只修改 `SystemMonitor.tsx` 的筛选栏部分

**设计原则**: 横向工具栏 + 图标 + 激活状态高亮 + 响应式换行

---

## 当前问题

1. 7 个筛选字段分两行排列（4列 + 3列），没有视觉层次
2. 所有控件样式完全相同，没有标签、图标或分组
3. "每页 X 条" 分页控件混在筛选字段中
4. PC/移动端展示筛选文字过长
5. 没有显示当前激活的筛选条件提示
6. 没有一键重置筛选的功能

---

## 设计方案

### 1. 布局结构

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🔍 搜索...     📊 状态     📁 分类     🔄 排序     💻 PC  📱 移动   │
│ [重置筛选 ←]                                                        │
├─────────────────────────────────────────────────────────────────────┤
│ 表格...                                                             │
└─────────────────────────────────────────────────────────────────────┘
```

- **第一行**: 7 个筛选控件横向排列，用 `flex flex-wrap gap-2` 布局
- **第二行**: 仅在已激活筛选时显示"重置筛选"按钮 + 当前激活筛选标签
- **分页区域**: "每页条数" 移到表格底部的分页控件中

### 2. 控件样式

每个筛选控件使用统一结构：

```tsx
<div className="flex items-center bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 gap-2 min-w-[140px]">
  <i className="fas fa-search text-slate-500 text-xs"></i>
  <input className="bg-transparent text-white text-sm outline-none w-full placeholder-slate-500" />
</div>
```

- 激活状态：边框变为 `border-blue-500`，背景变为 `bg-slate-750`
- 所有控件有 `cursor-pointer` 和 `hover:border-slate-600` 交互反馈
- 过渡动画：`transition-colors duration-200`

### 3. 图标映射

| 控件 | 图标 | 说明 |
|------|------|------|
| 搜索 | `fa-search` | 放大镜 |
| 状态 | `fa-circle-dot` | 状态点 |
| 分类 | `fa-folder` | 文件夹 |
| 排序 | `fa-arrow-down-a-z` | 排序箭头 |
| PC展示 | `fa-desktop` | 桌面显示器 |
| 移动展示 | `fa-mobile` | 手机 |
| 每页条数 | `fa-list-ol` | 列表数字 |

### 4. 激活筛选提示行

当有任何筛选条件激活时（搜索不为空、状态/分类/排序有值、PC/移动不是"全部"）：

```tsx
<div className="flex items-center gap-2 mb-3">
  <span className="text-xs text-slate-500">已筛选:</span>
  {toolSearch && <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 text-xs rounded">搜索: {toolSearch}</span>}
  {toolStatusFilter && <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 text-xs rounded">状态: {toolStatusFilter === 'online' ? '在线' : '离线'}</span>}
  {/* ... 其他激活的筛选 */}
  <button onClick={handleResetFilters} className="text-xs text-red-400 hover:text-red-300 ml-2">
    <i className="fas fa-times-circle mr-1"></i>重置
  </button>
</div>
```

### 5. 分页区域改造

将"每页条数"选择器移到分页区域：

```tsx
<div className="flex items-center justify-between mt-4 text-sm text-slate-400">
  <div className="flex items-center gap-2">
    <span>共 {toolTotal} 条记录，第 {toolPage}/{toolTotalPages} 页</span>
    <select value={toolPageSize} onChange={...} className="...">
      <option value={10}>10条/页</option>
      <option value={20}>20条/页</option>
      <option value={50}>50条/页</option>
    </select>
  </div>
  {/* 分页按钮 */}
</div>
```

### 6. 响应式行为

- **桌面 (≥1024px)**: 所有控件在一行内排列，不换行
- **平板 (768px-1023px)**: 自动换行到 2 行
- **手机 (<768px)**: 每个控件占一行，搜索框始终全宽

### 7. PC/移动筛选简化

将冗长的选项文字简化为 Toggle 开关样式：

```tsx
<div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2">
  <i className="fas fa-desktop text-slate-500 text-xs"></i>
  <span className="text-xs text-slate-400">PC</span>
  <ToggleSwitch value={showPcFilter} onChange={setShowPcFilter} />
</div>
```

ToggleSwitch 组件：
- 三态：全部（灰色）| 仅展示（绿色）| 仅隐藏（红色）
- 点击切换状态

---

## 文件修改清单

- **Modify**: `frontend/src/components/Admin/ToolManagement.tsx:243-319` — 筛选栏 HTML 结构完全替换
- **Modify**: `frontend/src/components/Admin/ToolManagement.tsx:381-430` — 分页区域加入每页条数选择器
- **Add**: 新增 `handleResetFilters` 函数
- **Add**: 新增 `ToggleSwitch` 小组件（内联定义）

---

## 验证步骤

1. `cd frontend && npx tsc --noEmit` — 无 TypeScript 错误
2. 浏览器访问 http://localhost:5178/admin — 筛选栏显示正确
3. 测试各个筛选控件交互
4. 测试激活筛选提示行显示
5. 测试重置筛选功能
6. 测试响应式布局（手机/平板/桌面）
7. 浏览器 Console 无错误
