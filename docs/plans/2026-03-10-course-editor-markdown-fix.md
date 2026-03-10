# 课程编辑器 Markdown 支持设计文档

## 概述

修复后台管理课程详情页中"编辑课程"功能的数据加载问题，并为课程描述字段添加完整的 Markdown 编辑和预览功能。

---

## 问题分析

### 问题 1：编辑课程弹窗数据为空

**现象**：在课程详情页点击"编辑课程"按钮后，弹窗内表单字段均为空。

**根本原因**：
- `CourseEditor.tsx` 组件使用 `localStorage.getItem('admin_courses')` 模拟加载课程数据
- 实际课程数据存储在 Zustand store 的 `courses` 数组中
- 没有从 store 正确获取单个课程数据的方法

### 问题 2：课程描述不支持 Markdown

**现象**：课程描述字段使用普通 textarea，无法进行 Markdown 格式编辑和预览。

**需求**：
- 使用 Monaco Editor 提供语法高亮的 Markdown 编辑体验
- 支持工具栏快速插入格式（加粗、斜体、标题、链接、代码块等）
- 支持并排实时预览模式
- 预览使用 react-markdown + remark-gfm + rehype-highlight 渲染

---

## 设计方案

### 方案 1：修复数据加载

**目标**：让 CourseEditor 组件正确加载课程数据。

**实现步骤**：

1. **在 `coursePlatform.ts` 中添加获取单个课程的 API 函数**：
```typescript
export const getCourse = async (courseId: number): Promise<Course> => {
  const response = await axios.get(`${API_BASE}/admin/courses/${courseId}`);
  return response.data;
};
```

2. **在 `courseAdminStore.ts` 中添加获取课程的方法**：
```typescript
getCourseById: (courseId: number) => {
  return get().courses.find((c) => c.id === courseId) || null;
},
```

3. **修改 `CourseEditor.tsx` 的 useEffect**：
```typescript
useEffect(() => {
  if (courseId) {
    // 从 Zustand store 获取课程数据
    const course = useCourseAdminStore.getState().courses.find((c) => c.id === courseId);
    if (course) {
      setFormData(course);
    }
  }
}, [courseId]);
```

---

### 方案 2：Markdown 编辑器组件

**目标**：创建可复用的 MarkdownEditor 组件，支持语法高亮、工具栏、实时预览。

**技术栈**：
- 编辑器：`@monaco-editor/react`（已安装）
- 预览：`react-markdown` + `remark-gfm` + `rehype-highlight`（已安装）
- 主题：Monaco Editor 深色主题（vs-dark）

**组件结构**：

```
MarkdownEditor
├── Toolbar
│   ├── 格式按钮组（B, I, #, [], {}, >, ≡）
│   └── 视图切换按钮（编辑/并排预览）
├── EditorContainer
│   ├── MonacoEditor（编辑模式/并排模式左侧）
│   └── PreviewPanel（并排模式右侧）
└── Footer
    └── 字符计数
```

**工具栏功能**：

| 按钮 | 图标 | 功能 | 插入内容 |
|------|------|------|----------|
| 加粗 | **B** | 插入加粗文本 | `**选中文本**` |
| 斜体 | *I* | 插入斜体文本 | `*选中文本*` |
| 标题 | # | 插入标题 | `## 标题` |
| 链接 | [] | 插入链接 | `[文本](url)` |
| 代码 | {} | 插入代码块 | `\`\`\`\n代码\n\`\`\`` |
| 引用 | > | 插入引用 | `> 引用内容` |
| 列表 | ≡ | 插入无序列表 | `- 列表项` |

**视图模式**：

1. **编辑模式**：只显示 Monaco Editor
2. **并排模式**：左侧 Editor（50%），右侧 Preview（50%）

**预览渲染配置**：

```tsx
<ReactMarkdown
  remarkPlugins={[remarkGfm]}
  rehypePlugins={[rehypeHighlight]}
  components={{
    h1: ({children}) => <h1 className="text-2xl font-bold text-white mb-4">{children}</h1>,
    h2: ({children}) => <h2 className="text-xl font-semibold text-white mb-3">{children}</h2>,
    h3: ({children}) => <h3 className="text-lg font-medium text-white mb-2">{children}</h3>,
    p: ({children}) => <p className="mb-4 text-slate-300 leading-relaxed">{children}</p>,
    strong: ({children}) => <strong className="text-white font-semibold">{children}</strong>,
    em: ({children}) => <em className="text-cyan-300">{children}</em>,
    code: ({children}) => <code className="px-1.5 py-0.5 bg-slate-700/50 rounded text-pink-400 text-xs">{children}</code>,
    pre: ({children}) => <pre className="bg-slate-900/50 rounded-lg p-3 my-2 overflow-x-auto border border-slate-700/30">{children}</pre>,
    ul: ({children}) => <ul className="list-disc list-inside space-y-2 my-3 text-slate-300">{children}</ul>,
    ol: ({children}) => <ol className="list-decimal list-inside space-y-2 my-3 text-slate-300">{children}</ol>,
    li: ({children}) => <li className="text-slate-300">{children}</li>,
    blockquote: ({children}) => <blockquote className="border-l-4 border-cyan-500/50 pl-4 my-3 text-slate-400 italic">{children}</blockquote>,
    a: ({children, href}) => <a href={href} className="text-cyan-400 hover:text-cyan-300 underline">{children}</a>,
  }}
>
  {markdownContent}
</ReactMarkdown>
```

---

## 视觉设计

### 整体布局

```
┌─────────────────────────────────────────────────────────────────┐
│  课程描述 *                                  [编辑] [并排预览] │
├─────────────────────────────────────────────────────────────────┤
│ [B] [I] [#] [[]] [{}] [>] [≡]                  │               │
├──────────────────────────────────────────────┬─┤               │
│                                              │ │   预览区域    │
│  Monaco Editor                               │ │               │
│  (深色主题 vs-dark)                          │ │   Markdown    │
│                                              │ │   渲染结果    │
│  ## 课程简介                                 │ │               │
│                                              │ │  ## 课程简介  │
│  这是一个 **Markdown** 编辑器...              │ │               │
│                                              │ │  实际渲染效果  │
│                                              │ │               │
│                                              │ │               │
├──────────────────────────────────────────────┴─┤               │
│  字符数：128                                   │               │
└────────────────────────────────────────────────┴───────────────┘
```

### 颜色方案（匹配现有 UI）

| 元素 | Tailwind 类 | 颜色值 |
|------|-------------|--------|
| 工具栏背景 | `bg-slate-700/50` | #334155/50 |
| 工具栏边框 | `border-slate-600` | #475569 |
| 按钮背景 | `bg-slate-600` | #475569 |
| 按钮 Hover | `hover:bg-cyan-500/20` | #06b6d4/20 |
| 按钮文字 | `text-slate-300` | #cbd5e1 |
| 按钮 Hover 文字 | `hover:text-cyan-400` | #22d3ee |
| 预览背景 | `bg-slate-900/50` | #0f172a/50 |
| 预览边框 | `border-slate-700/30` | #334155/30 |

### 响应式设计

- **桌面端（≥1024px）**：支持并排模式
- **平板端（768px-1023px）**：默认并排模式，可切换
- **移动端（<768px）**：仅编辑模式，预览使用独立面板

---

## 修改文件清单

| 文件路径 | 修改类型 | 说明 |
|----------|----------|------|
| `frontend/src/services/coursePlatform.ts` | 修改 | 添加 `getCourse` 函数 |
| `frontend/src/stores/courseAdminStore.ts` | 修改 | 添加 `getCourseById` 方法 |
| `frontend/src/components/Admin/CourseManagement/CourseEditor.tsx` | 修改 | 修复数据加载，集成 MarkdownEditor |
| `frontend/src/components/Admin/CourseManagement/MarkdownEditor.tsx` | 新建 | Markdown 编辑器组件 |

---

## 依赖检查

已安装依赖（无需额外安装）：
- ✅ `@monaco-editor/react` ^4.7.0
- ✅ `react-markdown` ^10.1.0
- ✅ `remark-gfm` ^4.0.1
- ✅ `rehype-highlight` ^7.0.2
- ✅ `monaco-editor` ^0.55.1

---

## 实现优先级

1. **P0 - 修复数据加载**：确保 CourseEditor 能正确加载课程数据
2. **P0 - 创建 MarkdownEditor 组件**：基础编辑和预览功能
3. **P1 - 工具栏功能**：快速插入格式按钮
4. **P1 - 视图切换**：编辑模式/并排预览模式
5. **P2 - 字符计数**：Footer 区域显示字数统计

---

## 测试验证

### 功能测试清单

- [ ] 点击"编辑课程"能正确加载课程数据
- [ ] 所有表单字段填充正确（标题、slug、描述、封面图、分类、发布状态）
- [ ] Monaco Editor 正常渲染，深色主题生效
- [ ] 工具栏按钮能正确插入 Markdown 语法
- [ ] 预览区域正确渲染 Markdown 内容
- [ ] 并排模式切换正常
- [ ] 保存课程时 Markdown 内容正确提交
- [ ] 移动端响应式布局正常

### 视觉验证

- [ ] 编辑器主题与整体 UI 风格一致
- [ ] 工具栏按钮有明显的 Hover 反馈
- [ ] 预览区域文字清晰可读
- [ ] 边框、圆角、阴影与设计稿一致

---

## 后续优化建议

1. **图片上传**：支持拖拽上传图片到阿里云 OSS
2. **模板插入**：快速插入课程描述模板
3. **历史版本**：保存描述编辑历史
4. **协同编辑**：多人同时编辑时的冲突处理

---

## 更新日志

### 2026-03-10
- ✅ 完成设计方案
- ⏳ 待实现：数据加载修复
- ⏳ 待实现：MarkdownEditor 组件
