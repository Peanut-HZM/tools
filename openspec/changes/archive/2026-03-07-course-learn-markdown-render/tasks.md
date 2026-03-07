## 1. 安装依赖

- [x] 1.1 安装 react-markdown 核心库
- [x] 1.2 安装 remark-gfm（支持 GFM Markdown 语法）
- [x] 1.3 安装 rehype-highlight（代码语法高亮）
- [x] 1.4 安装 rehype-sanitize（XSS 安全防护）

## 2. 修改 CourseLearnPage 组件

- [x] 2.1 导入 react-markdown 及相关插件
- [x] 2.2 修改章节内容渲染逻辑，使用 Markdown 组件替代 dangerouslySetInnerHTML
- [x] 2.3 配置代码高亮和 XSS 过滤

## 3. 添加样式支持

- [x] 3.1 安装 @tailwindcss/typography 插件（如未安装）
- [x] 3.2 配置 tailwind.config.js 添加 typography 插件
- [x] 3.3 在 CourseLearnPage 中添加 prose-invert 样式类

## 4. 测试验证

- [x] 4.1 验证标题、列表、代码块渲染
- [x] 4.2 验证表格、引用、链接渲染
- [x] 4.3 验证 XSS 过滤功能
- [x] 4.4 验证深色主题样式一致性
