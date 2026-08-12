# 工作区侧边栏优化设计文档

**日期**: 2026-08-12  
**状态**: 已批准  
**优先级**: 高

---

## 1. 需求背景

用户进入工作区（/workspace）后，存在三个体验问题：

1. **Header 未隐藏** — 首页、搜索工具、后台管理、联系我们等导航组件在工作区中不需要展示，浪费屏幕空间
2. **侧边栏图标不显示** — 工具列表中的图标显示为通用图标，未正确渲染 Font Awesome 图标
3. **缺少搜索功能** — 工具数量较多（23+），没有搜索框难以快速定位目标工具

---

## 2. 设计目标

1. **沉浸式体验** — 工作区模式下完全隐藏 Header，最大化工作空间
2. **正确展示图标** — 侧边栏工具列表显示每个工具对应的 Font Awesome 图标
3. **快速搜索** — 侧边栏顶部提供搜索框，按工具名称实时过滤

---

## 3. 改动范围

### 3.1 Layout.tsx — 隐藏 Header

**文件**: `frontend/src/components/Layout/Layout.tsx`

**当前问题**: `isImmersion` 变量已正确判断了 `/workspace` 和 `/tools/` 路径，但 Header 组件始终渲染，仅通过 CSS 类控制布局。

**修复方案**: 条件渲染 Header，当 `isImmersion` 为 true 时不渲染 Header。

```tsx
{!isImmersion && (
  <Header
    searchValue={searchValue}
    onSearchChange={handleSearchChange}
    onSearch={onSearch}
  />
)}
```

### 3.2 WorkspaceSidebar.tsx — 修复图标 + 添加搜索框

**文件**: `frontend/src/components/Workspace/WorkspaceSidebar.tsx`

#### 3.2.1 图标修复

**当前问题**: API 返回的图标值为 `fa-database`、`fa-server` 等，缺少 Font Awesome 的样式前缀 `fas`。当前代码直接渲染 `tool.icon`，导致图标无法显示。

**修复方案**: 在渲染时添加 `fas` 前缀。

```tsx
// 修改前
<i className={[tool.icon, 'text-xs w-4 text-center flex-shrink-0'].join(' ')}></i>

// 修改后
<i className={['fas', tool.icon, 'text-xs w-4 text-center flex-shrink-0'].join(' ')}></i>
```

#### 3.2.2 搜索框

**位置**: 在"返回首页"按钮下方、工具列表上方

**交互**: 
- 输入关键词实时过滤工具列表
- 仅搜索工具名称（`tool.title`）
- 过滤逻辑：`tool.title.toLowerCase().includes(keyword.toLowerCase())`
- 搜索状态用 `useState` 管理，不持久化

**UI**:
- 搜索框样式与现有设计一致（暗色主题）
- 占位符文本："搜索工具..."（中英文通过 i18n）
- 带搜索图标（`fas fa-search`）

```tsx
const [searchQuery, setSearchQuery] = useState('');

const filteredTools = tools.filter((tool) =>
  tool.title.toLowerCase().includes(searchQuery.toLowerCase())
);
```

### 3.3 i18n 翻译

**文件**: 
- `frontend/src/i18n/locales/zh-CN.ts`
- `frontend/src/i18n/locales/en-US.ts`

**新增 key**:
```typescript
// zh-CN.ts
workspace: {
  // ... 现有 key
  searchPlaceholder: '搜索工具...',
}

// en-US.ts
workspace: {
  // ... 现有 key
  searchPlaceholder: 'Search tools...',
}
```

---

## 4. 组件层级

```
WorkspaceSidebar
├── HomeButton (返回首页)
├── SearchBox (新增) ← 搜索框
├── CollapseToggle (折叠按钮)
└── ToolList
    └── ToolListItem × N (过滤后)
        ├── Icon (fas + tool.icon)
        └── Title
```

---

## 5. 数据流

```
用户输入搜索关键词
  ↓
useState: searchQuery 更新
  ↓
filteredTools = tools.filter(...)
  ↓
ToolList 重新渲染（仅显示匹配的工具）
```

---

## 6. 验收标准

- [ ] 工作区页面（/workspace）Header 完全隐藏
- [ ] 侧边栏工具列表显示正确的 Font Awesome 图标
- [ ] 侧边栏顶部有搜索框
- [ ] 输入关键词实时过滤工具列表
- [ ] 搜索框占位符文本正确（中英文）
- [ ] TypeScript 编译无错误
- [ ] 浏览器 Console 无错误

---

## 7. 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Header 隐藏后其他路由受影响 | 低 | `isImmersion` 仅匹配 `/workspace` 和 `/tools/` |
| 图标前缀修复影响其他组件 | 低 | 仅修改 WorkspaceSidebar，不影响首页工具卡片 |
| 搜索性能（23+ 工具） | 无 | 前端过滤，数据量小，无性能问题 |

---

## 8. 实施计划

### Phase 1：修复 Header 隐藏

1. 修改 Layout.tsx，条件渲染 Header
2. 验证 /workspace 路由 Header 隐藏
3. 验证 /tools/xxx 路由 Header 隐藏
4. 验证首页 Header 正常显示

### Phase 2：修复图标 + 添加搜索框

1. 修改 WorkspaceSidebar.tsx，添加 `fas` 前缀
2. 添加搜索框 UI
3. 实现搜索过滤逻辑
4. 添加 i18n 翻译
5. 验证 TypeScript 编译
6. 浏览器验证

---

**下一步**: 用户 review 本文档后，调用 writing-plans 技能生成详细实现计划。
