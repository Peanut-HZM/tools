## Context

当前课程学习页面（CourseLearnPage.tsx）使用 `dangerouslySetInnerHTML` 直接渲染章节内容，但内容中的 Markdown 语法没有被解析，导致用户看到的是原始 Markdown 文本而非格式化后的内容。

项目已有 Markdown 编辑器工具（MarkItDownConverter），可以参考其 Markdown 渲染方式。

## Goals / Non-Goals

**Goals:**
- 在学习页面正确渲染 Markdown 格式的学习内容
- 支持常用 Markdown 语法：标题、段落、列表、代码块、表格、引用、链接、图片等
- 保持与现有设计一致的深色主题样式
- 代码块支持语法高亮

**Non-Goals:**
- 不需要编辑功能，仅预览
- 不需要支持自定义 Markdown 扩展语法
- 不需要服务端渲染

## Decisions

### 1. Markdown 渲染库选择

**决策**: 使用 `react-markdown` 库进行 Markdown 渲染

**理由:**
- React 组件化，与现有项目技术栈一致
- 轻量级，按需加载 Markdown 语法支持
- 支持自定义组件渲染器，便于样式定制
- 社区活跃，维护良好

**替代方案:**
- `marked` + `DOMPurify`: 需要额外处理 XSS 安全，不如 react-markdown 安全
- `remark-react`: 已合并到 react-markdown，不再独立维护

### 2. 代码高亮支持

**决策**: 使用 `rehype-highlight` 或 `prismjs` 进行代码语法高亮

**理由:**
- 与 react-markdown 集成简单
- 支持多种编程语言
- 支持深色主题配色

### 3. 样式处理

**决策**: 使用 Tailwind CSS 的 `prose` 插件（`@tailwindcss/typography`）配合自定义样式

**理由:**
- 项目已使用 Tailwind CSS
- `prose` 插件提供开箱即用的 Markdown 样式
- 支持深色主题（`prose-invert`）

## Risks / Trade-offs

**风险 1**: 新增依赖包增加打包体积
→ **缓解**: 按需加载，使用代码分割

**风险 2**: Markdown 内容可能包含 XSS 攻击脚本
→ **缓解**: react-markdown 默认转义 HTML，使用 `rehype-sanitize` 进行内容过滤

**风险 3**: 代码块样式与现有主题不一致
→ **缓解**: 自定义代码块主题，匹配深色设计

## Migration Plan

1. 安装依赖：`react-markdown`, `remark-gfm`, `rehype-highlight`, `rehype-sanitize`
2. 修改 CourseLearnPage.tsx，使用 Markdown 组件渲染内容
3. 添加 Markdown 样式支持
4. 测试各种 Markdown 语法渲染效果
5. 验证安全性（XSS 过滤）

## Open Questions

无
