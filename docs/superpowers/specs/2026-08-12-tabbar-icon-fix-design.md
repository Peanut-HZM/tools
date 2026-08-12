# TabBar 图标修复设计文档

**日期**: 2026-08-12  
**状态**: 已批准  
**优先级**: 高

---

## 1. 需求背景

工作区顶部 tab 页签的图标显示为通用图标，未正确渲染各工具的 Font Awesome 图标。

**根本原因**: API 返回的图标值为 `fa-database`、`fa-server` 等，缺少 Font Awesome 的样式前缀 `fas`。

**影响范围**: TabBar.tsx 第 28 行

---

## 2. 设计目标

Tab 页签显示各工具的真实 Font Awesome 图标（如数据库工具显示数据库图标，K8s 显示服务器图标等）。

---

## 3. 改动范围

### 3.1 TabBar.tsx — 添加 `fas` 前缀

**文件**: `frontend/src/components/Workspace/TabBar.tsx`

**修改**: 第 28 行

```tsx
// 修改前
<i className={[tab.toolIcon, 'text-xs flex-shrink-0'].join(' ')}></i>

// 修改后
<i className={['fas', tab.toolIcon, 'text-xs flex-shrink-0'].join(' ')}></i>
```

---

## 4. 验收标准

- [ ] Tab 页签显示正确的 Font Awesome 图标
- [ ] TypeScript 编译无错误
- [ ] 浏览器 Console 无错误
- [ ] 与侧边栏图标修复方案一致

---

## 5. 实施计划

1. 修改 TabBar.tsx 第 28 行
2. 验证 TypeScript 编译
3. 浏览器验证
4. Commit

---

**下一步**: 用户 review 本文档后，调用 writing-plans 技能生成详细实现计划。
