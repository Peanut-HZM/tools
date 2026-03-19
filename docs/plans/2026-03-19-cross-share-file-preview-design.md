# CrossShare 文件预览功能设计文档

**创建日期**: 2026-03-19
**作者**: Claude Code
**状态**: 已批准

---

## 1. 概述

为 CrossShare 跨设备共享工具的文件管理功能增加文件预览能力，支持常见文件类型的在线预览，无需下载即可查看文件内容。

### 1.1 需求背景

用户上传文件后，希望快速查看文件内容，而不必每次都下载。常见需要预览的场景：
- 查看上传的 Markdown 文档内容
- 预览图片、视频、音频
- 快速浏览 Excel 表格数据
- 查看配置文件（JSON）

### 1.2 支持的文件类型

| 类型 | 扩展名 | 预览器 | 实现方式 |
|------|--------|--------|----------|
| 图片 | JPG, PNG, GIF, WebP, SVG | ImageViewer | `<img>` 标签 |
| 视频 | MP4, WebM, AVI, MOV | VideoViewer | `<video>` / react-player |
| 音频 | MP3, WAV, AAC, OGG | AudioViewer | `<audio>` / react-player |
| Markdown | .md | MarkdownViewer | react-markdown |
| PDF | .pdf | PdfViewer | react-pdf |
| Excel | .xlsx, .xls | ExcelViewer | SheetJS + react-data-grid |
| JSON | .json | JsonViewer | react-json-view |
| 文本 | .txt, .doc, .docx | TextViewer | 纯文本显示 |

---

## 2. 架构设计

### 2.1 组件结构

```
frontend/src/components/Tools/CrossShare/
├── FilePanel.tsx          # 现有组件，添加预览按钮
├── FilePreviewModal.tsx   # 预览模态框（新增）
└── preview/               # 预览器子组件目录（新增）
    ├── index.ts           # 统一导出
    ├── ImageViewer.tsx
    ├── VideoViewer.tsx
    ├── AudioViewer.tsx
    ├── MarkdownViewer.tsx
    ├── PdfViewer.tsx
    ├── ExcelViewer.tsx
    ├── JsonViewer.tsx
    └── TextViewer.tsx
```

### 2.2 预览模态框设计

```
┌─────────────────────────────────────────────────────┐
│  📄 filename.ext                              ✕ 关闭 │
├─────────────────────────────────────────────────────┤
│                                                     │
│                   预览内容区域                       │
│          （根据文件类型渲染不同的预览器）             │
│                                                     │
├─────────────────────────────────────────────────────┤
│  文件大小：1.2 MB  •  上传时间：2026-03-19          │
│                                      [⬇️ 下载]     │
└─────────────────────────────────────────────────────┘
```

### 2.3 文件类型判断逻辑

```typescript
function getViewerComponent(file: CrossFile): ViewerType {
  const ext = file.file_name.toLowerCase().split('.').pop();

  switch (file.file_type) {
    case 'image':
      return 'ImageViewer';
    case 'video':
      return 'VideoViewer';
    case 'audio':
      return 'AudioViewer';
    case 'text':
      if (ext === 'md') return 'MarkdownViewer';
      if (ext === 'json') return 'JsonViewer';
      return 'TextViewer';
    case 'document':
      if (ext === 'pdf') return 'PdfViewer';
      if (ext === 'xlsx' || ext === 'xls') return 'ExcelViewer';
      return 'TextViewer'; // Word 等降级为文本
    default:
      return 'TextViewer';
  }
}
```

---

## 3. 技术方案

### 3.1 依赖包

```json
{
  "dependencies": {
    "react-markdown": "^9.0.0",
    "remark-gfm": "^4.0.0",
    "react-pdf": "^7.0.0",
    "xlsx": "^0.18.0",
    "react-player": "^2.0.0",
    "react-json-view": "^1.21.0"
  }
}
```

### 3.2 纯前端解析方案

**选择理由**：
1. 后端无需改动，实现简单
2. 响应快，无额外服务器开销
3. 文件通过 OSS 签名 URL 直接加载，隐私性好
4. 包体积增加可控（约 1-2MB），可接受

**文件加载流程**：
```
1. 用户点击「预览」按钮
2. 前端调用 /files/{id}/download 获取签名 URL
3. 根据文件类型选择对应预览器组件
4. 预览器通过签名 URL 加载文件内容
5. 在模态框中渲染预览
```

---

## 4. 错误处理

### 4.1 错误场景

| 错误类型 | 处理方式 |
|----------|----------|
| 文件过大（>10MB） | 显示提示，建议下载后查看 |
| 格式不支持 | 显示「暂不支持预览」，提供下载按钮 |
| 加载失败 | 显示错误信息，重试按钮 |
| 签名 URL 过期 | 自动刷新签名 URL |

### 4.2 降级策略

- Word 文档（.doc/.docx）：尝试提取纯文本显示
- 未知格式：显示「无法预览」，提供下载按钮

---

## 5. 测试计划

### 5.1 功能测试

- [ ] 图片预览（多种格式）
- [ ] 视频预览（多种格式）
- [ ] 音频预览（多种格式）
- [ ] Markdown 预览（含代码块、表格）
- [ ] PDF 预览（多页文档）
- [ ] Excel 预览（多工作表）
- [ ] JSON 预览（嵌套结构）
- [ ] 文本预览

### 5.2 边界测试

- [ ] 大文件处理（>10MB）
- [ ] 空文件
- [ ] 损坏文件
- [ ] 签名 URL 过期刷新

---

## 6. 验收标准

1. ✅ 点击预览按钮后，模态框在 500ms 内打开
2. ✅ 各类型文件预览内容正确显示
3. ✅ 模态框可正常关闭
4. ✅ 预览失败时有明确提示
5. ✅ 不支持的格式显示降级提示

---

## 7. 后续优化（可选）

- [ ] 添加缩放功能（图片、PDF）
- [ ] 添加全文搜索（大文档）
- [ ] 支持更多格式（PPT、CAD 等）
- [ ] 打印预览内容
- [ ] 截图/导出功能
