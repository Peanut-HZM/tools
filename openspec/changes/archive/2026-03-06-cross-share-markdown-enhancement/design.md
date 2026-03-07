## Context

**当前状态：**
1. CrossShare 消息页面已使用 ReactMarkdown 进行基础 Markdown 渲染
2. 有编辑、删除功能，但编辑功能较简单（仅 textarea）
3. 没有智能识别 JSON/代码的能力
4. 没有提供复制功能

**约束：**
- 保持深色主题样式一致
- 不影响现有消息发送、接收功能
- 使用现有依赖或添加最小化新依赖

## Decisions

### Decision 1: 智能内容识别

**方案：** 使用正则表达式检测内容类型

**检测逻辑：**
```typescript
function detectContentType(content: string): ContentType {
  // 1. 检测 JSON
  if (/^\s*[\[{]/.test(content)) {
    try {
      JSON.parse(content);
      return 'json';
    } catch {}
  }
  // 2. 检测代码块
  if (/^```[\w]*\n/.test(content)) {
    return 'code';
  }
  // 3. 检测 Markdown 语法
  if (/[#*\-_`>\[\]]/.test(content)) {
    return 'markdown';
  }
  return 'text';
}
```

### Decision 2: 混合模式展示

**方案：**
- ≤10 行：直接展开显示
- >10 行：折叠显示摘要 + "展开查看详情"按钮
- JSON 使用 `react-syntax-highlighter` 高亮
- 代码块根据语言自动选择高亮主题

### Decision 3: 多种复制方式

**方案：** 下拉菜单提供 4 个选项
- 复制内容（纯文本）
- 复制 Markdown 源码
- 复制渲染 HTML
- 复制到剪贴板后显示 Toast

### Decision 4: 增强编辑体验

**方案：**
- 编辑时显示左右分栏预览
- 提供 Markdown 工具栏（粗体、斜体、链接、代码、列表等）
- 使用 `react-markdown-editor-lite` 或自定义组件

## Architecture

```
MessagePanel
├── MessageList
│   └── MessageItem
│       ├── MessageContent
│       │   ├── JsonViewer (智能识别 JSON)
│       │   ├── CodeViewer (智能识别代码)
│       │   └── MarkdownPreview (普通 Markdown)
│       ├── MessageActions
│       │   ├── CopyDropdown (多种复制方式)
│       │   ├── EditButton (增强编辑器)
│       │   └── DeleteButton
│       └── Timestamp
└── MessageInput
```

## Dependencies

需添加：
- `react-syntax-highlighter` - 代码高亮
- `@types/react-syntax-highlighter` - 类型定义

## Migration Plan

1. 添加新依赖
2. 创建智能内容识别工具函数
3. 创建 JsonViewer、CodeViewer 组件
4. 修改 MessageItem 支持折叠/展开
5. 添加复制下拉菜单
6. 增强编辑组件
7. 测试验证
