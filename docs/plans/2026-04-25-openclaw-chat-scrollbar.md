# OpenClaw 聊天页面滚动条美化 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 美化 OpenClawChat 消息区域的滚动条，使其在深色主题下不突兀

**Architecture:** 在消息容器 div 上添加自定义 WebKit 滚动条样式

**Tech Stack:** React + Tailwind CSS + 原生 CSS 伪元素

---

### Task 1: 添加自定义滚动条样式

**Files:**
- Modify: `frontend/src/components/Tools/OpenClawChat/OpenClawChat.tsx`

**Step 1: 给消息容器添加自定义 CSS 类**

在组件的 `<style jsx>` 或内联 style 中定义滚动条样式。由于项目使用 Tailwind，我们用原生 CSS 在 JSX 中处理 ::-webkit-scrollbar。

找到消息区域的 div（约第 243 行）：
```tsx
<div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
```

改为：
```tsx
<div
  className="flex-1 overflow-y-auto px-6 py-4 space-y-4 custom-scrollbar"
  style={{
    scrollbarWidth: 'thin',
    scrollbarColor: 'rgba(100, 116, 139, 0.4) transparent',
  }}
>
```

同时在组件内添加 style 标签（放在 return 语句之前或包裹在 JSX 中）：

```tsx
<style>{`
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background-color: rgba(100, 116, 139, 0.4);
    border-radius: 3px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background-color: rgba(100, 116, 139, 0.6);
  }
`}</style>
```

**Step 2: 验证效果**

打开 http://localhost:5178/tools/openclaw，确认：
- 滚动条变为细窄的深灰色
- hover 时颜色稍亮
- 整体与深色主题融合

**Step 3: Commit**

```bash
git add frontend/src/components/Tools/OpenClawChat/OpenClawChat.tsx
git commit -m "style: OpenClawChat 消息区域滚动条美化"
```
