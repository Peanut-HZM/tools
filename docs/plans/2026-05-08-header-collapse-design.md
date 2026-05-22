# Header 折叠功能设计

**日期**: 2026-05-08
**状态**: 已批准
**改动范围**: 仅 `src/components/Header/Header.tsx`

---

## 需求

在任意工具页面，用户可以通过点击折叠按钮收起 Header，节省屏幕空间。折叠状态通过 `localStorage` 持久化。

## 设计决策

- **折叠程度**: 完全隐藏 Header，替换为 32px 高的迷你横条
- **按钮位置**: Header 右侧（语言切换按钮之前）
- **状态持久化**: `localStorage`，key 为 `header-collapsed`
- **改动文件**: 仅 `Header.tsx`，一个文件内完成

---

## 交互流程

### 展开状态（默认）

1. Header 正常显示，包含 Logo、搜索框、管理按钮、联系我们、语言切换、登录按钮
2. 右侧新增一个折叠按钮（⌃ chevron-up 图标），位于语言切换按钮之前
3. 点击折叠按钮：
   - 状态切换为折叠
   - 写入 `localStorage.setItem("header-collapsed", "true")`
   - Header 内容完全隐藏
   - 显示 32px 迷你横条

### 折叠状态（迷你横条）

1. 一条 32px 高度的横条，`sticky top-0 z-40 bg-slate-800`
2. 中央显示一个展开按钮（⌄ chevron-down 图标）
3. 点击展开按钮：
   - 状态切换为展开
   - 写入 `localStorage.setItem("header-collapsed", "false")`
   - 恢复完整 Header

---

## 技术实现

### 状态管理

```tsx
const [isCollapsed, setIsCollapsed] = useState(() => {
  const saved = localStorage.getItem("header-collapsed");
  return saved === "true";
});
```

使用函数式初始化，避免每次渲染都读 localStorage。

### 切换逻辑

```tsx
const toggleCollapse = () => {
  setIsCollapsed((prev) => {
    const next = !prev;
    localStorage.setItem("header-collapsed", String(next));
    return next;
  });
};
```

### 渲染逻辑

```tsx
if (isCollapsed) {
  return (
    <header className="sticky top-0 z-40 bg-slate-800 border-b border-slate-700 h-8 flex items-center justify-center">
      <button onClick={toggleCollapse} title="展开导航">
        {/* chevron-down SVG */}
      </button>
    </header>
  );
}

// 正常 Header（现有代码）+ 折叠按钮
return (
  <header>
    {/* ... 现有内容 ... */}
    <button onClick={toggleCollapse} title="折叠导航">
      {/* chevron-up SVG */}
    </button>
    {/* ... 其余内容 ... */}
  </header>
);
```

### 折叠按钮位置

插入在语言切换按钮之前：

```
[搜索框] [管理后台] [联系我们] [语言切换] [折叠按钮 ⌃] [登录按钮]
```

### 图标

使用内联 SVG，不引入额外依赖：

- 折叠按钮（chevron-up）: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="18 15 12 9 6 15"/></svg>`
- 展开按钮（chevron-down）: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"/></svg>`

### 样式

折叠按钮样式：

```tsx
className="px-2 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm transition-colors cursor-pointer"
```

迷你横条展开按钮样式：

```tsx
className="px-3 py-1 rounded text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
```

---

## 边界情况

| 场景 | 处理 |
|------|------|
| 首次访问（无 localStorage） | 默认展开 |
| 从工具页面切换到首页 | 首页也使用相同的 Header，折叠状态保持一致 |
| localStorage 不可用（隐私模式） | try-catch 包裹读写，失败时降级为内存状态 |
| 工具页面滚动区域 | Header 使用 `sticky top-0`，折叠状态不影响工具页面滚动 |

---

## 验证步骤

1. 打开任意工具页面（如 `/tools/json-formatter`）
2. 确认 Header 正常显示，右侧有折叠按钮
3. 点击折叠按钮，Header 收起，顶部出现 32px 迷你横条
4. 点击迷你横条中的展开按钮，Header 恢复
5. 刷新页面，确认折叠/展开状态保持不变
6. 切换到其他工具页面，确认状态保持一致
7. 打开首页 `/`，确认 Header 也遵循相同的折叠状态
8. 检查浏览器 Console 无报错
