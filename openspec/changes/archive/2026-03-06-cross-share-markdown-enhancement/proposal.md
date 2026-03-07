## Why

CrossShare 消息页面需要增强 Markdown 格式化展示能力：

1. **缺少智能识别**：用户发送 JSON、代码时，无法自动格式化和语法高亮
2. **复制功能缺失**：无法快速复制消息内容到剪贴板
3. **编辑体验简陋**：仅简单的 textarea，没有 Markdown 预览和快捷工具
4. **长内容展示问题**：没有折叠机制，长 JSON/代码会占用大量空间

这些问题影响了用户体验，需要增强消息展示和编辑功能。

## What Changes

- **智能内容识别**：自动检测 JSON、代码、Markdown、普通文本
- **混合模式展示**：短内容直接展开，长内容折叠
- **语法高亮**：JSON 和代码使用专业高亮主题
- **多种复制方式**：复制纯文本、Markdown 源码、渲染 HTML
- **增强编辑器**：Markdown 实时预览 + 快捷工具栏

## Capabilities

### New Capabilities

- 自动识别并格式化 JSON 内容
- 自动识别并高亮代码块
- 混合模式展示（折叠/展开）
- 一键复制消息内容（多种方式）
- Markdown 增强编辑（实时预览、快捷工具）

### Modified Capabilities

- MessagePanel 组件增强
- MessageItem 组件重构

## Impact

- **前端组件**:
  - `frontend/src/components/Tools/CrossShare/MessagePanel.tsx` - 增强消息展示和编辑
  - `frontend/src/components/Tools/CrossShare/MessageItem.tsx` - 新增组件（可考虑拆分）
  - `frontend/src/components/Tools/CrossShare/JsonViewer.tsx` - 新增组件
  - `frontend/src/components/Tools/CrossShare/CodeViewer.tsx` - 新增组件
  - `frontend/src/components/Tools/CrossShare/MarkdownEditor.tsx` - 新增组件
- **新增依赖**: `react-syntax-highlighter`
- **无后端影响**: 纯前端 UI 增强
