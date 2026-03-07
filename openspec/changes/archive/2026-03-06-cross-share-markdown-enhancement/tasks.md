## 1. 依赖安装

- [x] 安装 `react-syntax-highlighter` 和类型定义
- [x] 验证安装成功

## 2. 工具函数开发

- [x] 创建 `detectContentType` 函数（智能内容识别）
- [x] 创建 `countLines` 函数（行数计算）
- [ ] 编写单元测试

## 3. JsonViewer 组件

- [x] 创建 JsonViewer 组件
- [x] 实现 JSON 格式化显示
- [x] 实现折叠/展开功能（>10 行折叠）
- [x] 实现语法高亮
- [x] 深色主题样式

## 4. CodeViewer 组件

- [x] 创建 CodeViewer 组件
- [x] 实现代码语言检测
- [x] 实现语法高亮
- [x] 实现折叠/展开功能（>10 行折叠）
- [x] 深色主题样式

## 5. MessageItem 组件重构

- [x] 拆分 MessagePanel → MessageItem 子组件
- [x] 集成 JsonViewer
- [x] 集成 CodeViewer
- [x] 集成 MarkdownPreview
- [x] 实现智能内容分发

## 6. 复制功能

- [x] 创建 CopyDropdown 组件
- [x] 实现"复制内容"功能
- [x] 实现"复制 Markdown 源码"功能
- [x] 实现"复制渲染 HTML"功能
- [x] Toast 提示集成

## 7. 增强编辑器

- [x] 创建 MarkdownEditor 组件
- [x] 实现工具栏（粗体、斜体、链接、代码、列表、引用）
- [x] 实现快捷键支持
- [x] 实现左右分栏预览
- [x] 实现拖拽调整分栏比例
- [x] 响应式布局（窄屏切换）

## 8. 集成测试

- [x] 验证 JSON 识别和格式化
- [x] 验证代码识别和高亮
- [x] 验证 Markdown 渲染
- [x] 验证复制功能
- [x] 验证编辑功能
- [x] 验证深色主题一致性

## 9. 验证测试

- [x] 前端构建通过
- [x] 业务功能正常（消息发送、接收）
- [x] 性能无明显下降
- [x] 响应式布局正常
