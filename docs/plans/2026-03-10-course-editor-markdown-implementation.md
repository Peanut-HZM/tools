# 课程编辑器 Markdown 支持实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复课程编辑器数据加载问题，并实现支持语法高亮、工具栏、实时预览的 Markdown 编辑器组件。

**Architecture:**
1. 修复数据加载：从 Zustand store 获取课程数据，替换 localStorage 模拟
2. 创建可复用的 MarkdownEditor 组件，集成 Monaco Editor 和 react-markdown 预览
3. 在 CourseEditor 中集成 MarkdownEditor 替换原有 textarea

**Tech Stack:** React 18, TypeScript, Monaco Editor, react-markdown, remark-gfm, rehype-highlight, Zustand, Tailwind CSS

---

## Task 1: 修复数据加载 - 添加 getCourse API 函数

**Files:**
- Modify: `frontend/src/services/coursePlatform.ts:188-189`

**Steps:**

**Step 1: 在 coursePlatform.ts 文件末尾添加 getCourse 函数**

在 `publishCourse` 函数后面（第 188 行后）添加：

```typescript
export const getCourse = async (courseId: number): Promise<Course> => {
  const response = await axios.get(`${API_BASE}/admin/courses/${courseId}`);
  return response.data;
};
```

**Step 2: 保存文件并验证语法**

观察 VSCode 是否有类型错误，确保没有红色波浪线。

**Step 3: 提交**

```bash
git add frontend/src/services/coursePlatform.ts
git commit -m "feat: add getCourse API function"
```

---

## Task 2: 修复数据加载 - 在 store 中添加 getCourseById 方法

**Files:**
- Modify: `frontend/src/stores/courseAdminStore.ts:296-297`

**Steps:**

**Step 1: 在 CourseState 接口中添加 getCourseById 方法定义**

在 `clearError: () => void;` 前面（约第 296 行）添加：

```typescript
getCourseById: (courseId: number) => Course | null;
```

**Step 2: 在 useCourseAdminStore 实现中添加 getCourseById 方法**

在 `clearError: () => { set({ error: null }); },` 前面添加：

```typescript
getCourseById: (courseId: number) => {
  return get().courses.find((c) => c.id === courseId) || null;
},
```

**Step 3: 保存文件并验证类型**

确保没有 TypeScript 错误。

**Step 4: 提交**

```bash
git add frontend/src/stores/courseAdminStore.ts
git commit -m "feat: add getCourseById method to course store"
```

---

## Task 3: 创建 MarkdownEditor 组件

**Files:**
- Create: `frontend/src/components/Admin/CourseManagement/MarkdownEditor.tsx`

**Steps:**

**Step 1: 创建 MarkdownEditor.tsx 文件**

创建新文件 `frontend/src/components/Admin/CourseManagement/MarkdownEditor.tsx`，内容如下：

```tsx
/**
 * Markdown 编辑器组件
 * 支持 Monaco Editor 语法高亮和实时预览
 */
import React, { useState, useMemo } from 'react';
import Editor from '@monaco-editor/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/atom-one-dark.css';

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  height?: string;
  showPreview?: boolean;
}

export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  value,
  onChange,
  placeholder = '使用 Markdown 格式编写内容...',
  height = '300px',
  showPreview = false,
}) => {
  const [viewMode, setViewMode] = useState<'edit' | 'split'>('edit');

  // 工具栏按钮配置
  const toolbarButtons = [
    { icon: 'B', title: '加粗', prefix: '**', suffix: '**' },
    { icon: 'I', title: '斜体', prefix: '*', suffix: '*' },
    { icon: '#', title: '标题', prefix: '## ', suffix: '' },
    { icon: '[]', title: '链接', prefix: '[', suffix: '](url)' },
    { icon: '{}', title: '代码块', prefix: '```\n', suffix: '\n```' },
    { icon: '>', title: '引用', prefix: '> ', suffix: '' },
    { icon: '≡', title: '列表', prefix: '- ', suffix: '' },
  ];

  // 处理工具栏按钮点击
  const handleToolbarClick = (prefix: string, suffix: string) => {
    const textarea = document.querySelector('textarea[aria-label="Editor content"]') as HTMLTextAreaElement;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = value.substring(start, end);
    const newText = value.substring(0, start) + prefix + selectedText + suffix + value.substring(end);
    onChange(newText);

    // 恢复光标位置
    setTimeout(() => {
      textarea.setSelectionRange(start + prefix.length, end + prefix.length);
      textarea.focus();
    }, 0);
  };

  // 字符计数
  const charCount = useMemo(() => value.length, [value]);

  // 预览组件
  const Preview = () => (
    <div className="h-full overflow-y-auto p-4 bg-slate-900/50 rounded-r-xl">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          h1: ({ children }) => <h1 className="text-2xl font-bold text-white mb-4">{children}</h1>,
          h2: ({ children }) => <h2 className="text-xl font-semibold text-white mb-3">{children}</h2>,
          h3: ({ children }) => <h3 className="text-lg font-medium text-white mb-2">{children}</h3>,
          p: ({ children }) => <p className="mb-4 text-slate-300 leading-relaxed">{children}</p>,
          strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
          em: ({ children }) => <em className="text-cyan-300">{children}</em>,
          code: ({ children }) => (
            <code className="px-1.5 py-0.5 bg-slate-700/50 rounded text-pink-400 text-xs">
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="bg-slate-900/50 rounded-lg p-3 my-2 overflow-x-auto border border-slate-700/30">
              {children}
            </pre>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-inside space-y-2 my-3 text-slate-300">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside space-y-2 my-3 text-slate-300">{children}</ol>
          ),
          li: ({ children }) => <li className="text-slate-300">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-cyan-500/50 pl-4 my-3 text-slate-400 italic">
              {children}
            </blockquote>
          ),
          a: ({ children, href }) => (
            <a
              href={href}
              className="text-cyan-400 hover:text-cyan-300 underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              {children}
            </a>
          ),
        }}
      >
        {value || '*暂无内容*'}
      </ReactMarkdown>
    </div>
  );

  return (
    <div className="border border-slate-600 rounded-xl overflow-hidden bg-slate-800/50">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-700/50 border-b border-slate-600">
        <div className="flex items-center gap-1">
          {toolbarButtons.map((btn, index) => (
            <button
              key={index}
              type="button"
              onClick={() => handleToolbarClick(btn.prefix, btn.suffix)}
              className="px-2.5 py-1.5 text-sm bg-slate-600 hover:bg-cyan-500/20 text-slate-300 hover:text-cyan-400 rounded transition-all font-mono"
              title={btn.title}
            >
              {btn.icon}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setViewMode('edit')}
            className={`px-3 py-1.5 text-xs rounded transition-all font-medium ${
              viewMode === 'edit'
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                : 'bg-slate-600 text-slate-300 hover:bg-slate-500'
            }`}
          >
            <i className="fas fa-edit mr-1.5"></i>
            编辑
          </button>
          <button
            type="button"
            onClick={() => setViewMode('split')}
            className={`px-3 py-1.5 text-xs rounded transition-all font-medium ${
              viewMode === 'split'
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                : 'bg-slate-600 text-slate-300 hover:bg-slate-500'
            }`}
          >
            <i className="fas fa-columns mr-1.5"></i>
            并排预览
          </button>
        </div>
      </div>

      {/* 编辑器和预览 */}
      <div className={`flex ${viewMode === 'split' ? 'flex-row' : 'flex-col'}`}>
        {/* Monaco Editor */}
        <div className={viewMode === 'split' ? 'w-1/2' : 'w-full'}>
          <Editor
            height={height}
            language="markdown"
            theme="vs-dark"
            value={value}
            onChange={(val) => onChange(val || '')}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              wordWrap: 'on',
              scrollBeyondLastLine: false,
              automaticLayout: true,
              padding: { top: 12 },
            }}
          />
        </div>

        {/* 预览面板 */}
        {viewMode === 'split' && (
          <div className="w-1/2 border-l border-slate-700/50">
            <Preview />
          </div>
        )}
      </div>

      {/* Footer - 字符计数 */}
      <div className="px-4 py-2 bg-slate-700/30 border-t border-slate-600 flex items-center justify-between">
        <p className="text-xs text-slate-400">
          <i className="fas fa-info-circle mr-1"></i>
          支持 Markdown 格式
        </p>
        <p className="text-xs text-slate-400">
          {charCount} 字
        </p>
      </div>
    </div>
  );
};

export default MarkdownEditor;
```

**Step 2: 保存文件并验证**

确保没有 TypeScript 错误，检查 import 路径是否正确。

**Step 3: 提交**

```bash
git add frontend/src/components/Admin/CourseManagement/MarkdownEditor.tsx
git commit -m "feat: create MarkdownEditor component with Monaco Editor and preview"
```

---

## Task 4: 在 CourseEditor 中集成 MarkdownEditor

**Files:**
- Modify: `frontend/src/components/Admin/CourseManagement/CourseEditor.tsx:1-322`

**Steps:**

**Step 1: 修改 import 语句**

在文件顶部添加 MarkdownEditor 的 import：

```typescript
import { MarkdownEditor } from './MarkdownEditor';
```

**Step 2: 修改 useEffect 加载课程数据**

替换原有的 useEffect（第 27-40 行）：

```typescript
// 加载课程数据（编辑模式）
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

**Step 3: 替换课程描述的 textarea**

找到课程描述部分（约第 198-218 行），替换为：

```tsx
{/* 课程描述 - Markdown 编辑器 */}
<div>
  <label className="block text-sm font-medium text-slate-300 mb-2">
    <i className="fas fa-align-left mr-2 text-cyan-400"></i>
    课程描述 *
  </label>
  <MarkdownEditor
    value={formData.description || ''}
    onChange={(val) => setFormData((prev) => ({ ...prev, description: val }))}
    placeholder="## 课程简介\n\n在此编写课程描述，支持 **Markdown** 格式...\n\n### 内容大纲\n- 第一点\n- 第二点"
    height="300px"
  />
  <p className="text-xs text-slate-500 mt-2">
    <i className="fas fa-markdown mr-1"></i>
    支持 Markdown 格式，点击"并排预览"查看实时效果
  </p>
</div>
```

**Step 4: 移除旧的预览逻辑（可选）**

由于 MarkdownEditor 内置预览，可以考虑移除 CourseEditor 原有的 showPreview 逻辑，或者保留用于整体课程卡片预览。

**Step 5: 保存文件并验证**

确保没有 TypeScript 错误，Monaco Editor 能正常加载。

**Step 6: 提交**

```bash
git add frontend/src/components/Admin/CourseManagement/CourseEditor.tsx
git commit -m "feat: integrate MarkdownEditor into CourseEditor and fix data loading"
```

---

## Task 5: 验证和测试

**Files:**
- Test: 浏览器访问 `http://localhost:5178/admin/course`

**Steps:**

**Step 1: 确保前端开发服务器运行**

```bash
cd frontend
npm run dev
```

**Step 2: 访问课程管理页面**

浏览器打开 `http://localhost:5178/admin/course`

**Step 3: 测试数据加载**

1. 点击任意课程卡片进入详情页
2. 点击右上角"编辑课程"按钮
3. 验证所有表单字段是否正确填充：
   - [ ] 课程标题
   - [ ] 课程 slug
   - [ ] 课程描述（Markdown 内容）
   - [ ] 课程分类
   - [ ] 封面图片 URL
   - [ ] 发布状态复选框

**Step 4: 测试 Markdown 编辑器**

1. [ ] Monaco Editor 正常渲染，深色主题生效
2. [ ] 工具栏按钮能点击
3. [ ] 点击"加粗"按钮能插入 `**text**`
4. [ ] 点击"标题"按钮能插入 `## 标题`
5. [ ] 点击"并排预览"能看到 Markdown 渲染效果
6. [ ] 字符计数正确显示
7. [ ] 编辑内容能正确保存到 formData

**Step 5: 测试保存功能**

1. 修改课程描述的 Markdown 内容
2. 点击"保存"按钮
3. 验证保存成功
4. 重新打开编辑，验证内容已保存

**Step 6: 检查浏览器 Console**

确保没有错误（红色）或警告（黄色）。

---

## Task 6: 代码清理和文档更新

**Files:**
- Modify: `docs/plans/2026-03-10-course-editor-markdown-fix.md`

**Steps:**

**Step 1: 更新设计文档**

在设计文档末尾添加：

```markdown
## 实现状态

### 2026-03-10
- ✅ 完成设计方案
- ✅ 实现数据加载修复
- ✅ 实现 MarkdownEditor 组件
- ✅ 集成到 CourseEditor
- ✅ 通过功能测试
```

**Step 2: 提交最终代码**

```bash
git add docs/plans/2026-03-10-course-editor-markdown-fix.md
git commit -m "docs: update implementation status"
```

**Step 3: 推送（可选）**

```bash
git push origin master
```

---

## 完整实现检查清单

### 代码质量
- [ ] TypeScript 类型正确，无 `any` 滥用
- [ ] 组件命名规范（PascalCase）
- [ ] 文件命名规范（PascalCase.tsx）
- [ ] 代码有适当注释
- [ ] 无 console.log 调试代码

### 功能完整
- [ ] 数据加载正常
- [ ] Monaco Editor 渲染正常
- [ ] 工具栏功能正常
- [ ] 预览功能正常
- [ ] 保存功能正常

### 视觉一致
- [ ] 深色主题匹配现有 UI
- [ ] 按钮 Hover 效果明显
- [ ] 边框、圆角、阴影一致
- [ ] 响应式布局正常

### 提交历史
- [ ] 小步提交，每步一个功能
- [ ] 提交信息清晰（使用中文）
- [ ] 提交顺序合理

---

## 故障排除

### Monaco Editor 无法加载
- 检查 `@monaco-editor/react` 是否正确安装
- 检查网络是否能加载 Monaco 资源
- 尝试使用 `editorDidMount` 回调调试

### 预览不显示
- 检查 `react-markdown` 及相关插件是否正确安装
- 检查 import 路径是否正确
- 验证 Markdown 内容是否为空

### 数据加载失败
- 检查后端 API `/api/admin/courses/:id` 是否正常
- 检查 Zustand store 中是否有课程数据
- 使用浏览器 DevTools 查看 Network 请求

---

## 完成标准

所有测试步骤通过，代码已提交，浏览器 Console 无错误，用户可以：
1. 点击"编辑课程"看到完整的课程数据
2. 使用 Markdown 编辑器编写和预览课程描述
3. 保存后内容正确持久化

