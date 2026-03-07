## Why

当前课程学习页面的章节内容以纯文本方式展示，导致 Markdown 格式的内容（如标题、代码块、列表、表格等）无法正确渲染，影响学习体验。需要将纯文本展示改为 Markdown 预览格式展示。

## What Changes

- 学习页面的章节内容从纯文本展示改为 Markdown 渲染展示
- 支持 Markdown 语法：标题、列表、代码块、表格、引用、粗体、斜体等
- 保持深色主题样式，确保代码高亮与整体设计风格一致

## Capabilities

### New Capabilities
- `markdown-render`: 课程学习页面 Markdown 渲染能力，支持将章节内容中的 Markdown 语法渲染为格式化的 HTML

### Modified Capabilities
<!-- 无修改的现有能力 -->

## Impact

- 前端组件：`frontend/src/pages/CourseLearnPage.tsx` 需要引入 Markdown 渲染组件
- 样式：需要添加 Markdown 渲染后的样式支持
- 依赖：需要安装 markdown 渲染相关的依赖包（如 react-markdown）
