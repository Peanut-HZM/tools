# CrossShare UI 修复设计方案

## 1. Why

### 问题 1：首页无法滚动，Footer 挡住内容
当前 `Layout.tsx` 使用了 `h-screen overflow-hidden`，这是之前为了解决 CrossShare 工具页面滚动问题而做的全局修改，但导致首页（`/` 路径）也被固定高度无法滚动，底部内容被 Footer 遮挡。

### 问题 2：CrossShare 消息功能缺失
CrossShare 消息面板缺少之前设计并实现的功能：
- 缺少智能内容识别（JSON、代码、Markdown）
- 缺少语法高亮
- 缺少复制功能
- 缺少增强编辑器

## 2. What Changes

### 修复 1：首页布局修复

**修改文件**：`frontend/src/components/Layout/Layout.tsx`

**方案**：条件化布局，仅工具页面使用 `h-screen overflow-hidden`

```tsx
// 修改前
<div className="bg-slate-900 text-slate-100 h-screen flex flex-col overflow-hidden">

// 修改后
<div className={`bg-slate-900 text-slate-100 ${
  isToolPage ? 'h-screen overflow-hidden' : 'min-h-screen'
} flex flex-col`}>
```

### 修复 2：CrossShare 消息功能恢复

**新增文件**：
- `frontend/src/components/Tools/CrossShare/JsonViewer.tsx` - JSON 格式化组件
- `frontend/src/components/Tools/CrossShare/CodeViewer.tsx` - 代码高亮组件
- `frontend/src/components/Tools/CrossShare/utils/contentDetector.ts` - 内容识别工具

**修改文件**：
- `frontend/src/components/Tools/CrossShare/MessagePanel.tsx` - 集成新功能

**新增依赖**：
- `react-syntax-highlighter` - 代码高亮
- `@types/react-syntax-highlighter` - 类型定义

## 3. Architecture

### 内容识别逻辑

```typescript
type ContentType = 'json' | 'code' | 'markdown' | 'text';

function detectContentType(content: string): ContentType {
  // 1. 检测 JSON (优先级 1)
  if (/^\s*[\[{]/.test(content)) {
    try {
      JSON.parse(content);
      return 'json';
    } catch {}
  }
  // 2. 检测代码块 (优先级 2)
  if (/^```[\w]*\n/.test(content)) {
    return 'code';
  }
  // 3. 检测 Markdown (优先级 3)
  if (/[#*\-_`>\[\]]/.test(content)) {
    return 'markdown';
  }
  return 'text';
}
```

### 组件架构

```
MessagePanel
├── MessageList
│   └── MessageItem[]
│       ├── MessageContent
│       │   ├── JsonViewer (智能识别 JSON)
│       │   ├── CodeViewer (智能识别代码)
│       │   └── MarkdownPreview (普通 Markdown)
│       ├── MessageActions
│       │   ├── CopyButton (复制功能)
│       │   ├── EditButton (编辑功能)
│       │   └── DeleteButton (删除功能)
│       └── Timestamp
└── MessageInput
```

### 折叠阈值

| 内容类型 | 阈值 | 折叠时显示 |
|----------|------|------------|
| JSON | >10 行 | 显示前 10 行 + "展开查看详情（共 X 行）" |
| 代码 | >10 行 | 显示前 10 行 + "展开查看详情（共 X 行）" |
| Markdown | >10 行 | 显示前 10 行 + "展开查看详情" |

## 4. Implementation Plan

### Phase 1: 修复首页布局
1. 修改 `Layout.tsx`，条件化应用 `h-screen overflow-hidden`
2. 验证首页可正常滚动
3. 验证工具页面布局正常

### Phase 2: 添加依赖
1. 安装 `react-syntax-highlighter`
2. 验证安装成功

### Phase 3: 工具函数开发
1. 创建 `contentDetector.ts`
2. 实现 `detectContentType` 函数
3. 实现 `countLines` 函数

### Phase 4: 组件开发
1. 创建 `JsonViewer.tsx` - JSON 格式化显示
2. 创建 `CodeViewer.tsx` - 代码高亮显示
3. 集成到 `MessagePanel.tsx`

### Phase 5: 复制功能
1. 添加复制按钮
2. 实现多种复制方式（内容、Markdown 源码、HTML）
3. 集成 Toast 提示

### Phase 6: 测试验证
1. 验证 JSON 识别和格式化
2. 验证代码识别和高亮
3. 验证复制功能
4. 验证首页滚动正常

## 5. Guardrails

### 约束条件
- 保持深色主题样式一致
- 不影响现有消息发送、接收功能
- CrossShare 工具页面的布局样式不变
- 只改动首页和 MessagePanel 相关代码

### 验收标准
- [ ] 首页可正常滚动，Footer 不再遮挡内容
- [ ] JSON 内容能被正确识别并格式化显示
- [ ] 代码块能被正确识别并语法高亮
- [ ] 提供复制功能且正常工作
- [ ] 工具页面布局不受影响
- [ ] 构建通过无错误
