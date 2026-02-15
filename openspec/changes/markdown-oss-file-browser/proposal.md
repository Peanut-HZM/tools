## Why

当前Markdown编辑器仅支持本地文件系统管理，用户需要一种方式将Markdown文档存储到云端（阿里云OSS）并在不同设备间同步。通过添加OSS文件浏览器功能，用户可以直接在编辑器中管理云端Markdown文件，实现无缝的云端文档管理体验。

## What Changes

- **新增OSS文件侧边栏组件**: 在左侧sidebar添加可切换的"本地文件"和"OSS文件"标签页
- **OSS文件列表展示**: 显示当前用户上传到阿里云OSS的所有Markdown文件（支持排序、刷新）
- **OSS文件打开功能**: 点击文件从OSS读取内容并在编辑器中打开
- **文件上传功能**: 支持拖拽上传和手动上传文件到OSS
- **状态管理扩展**: 扩展FileStore以支持OSS文件操作状态
- **UI主题适配**: 确保新组件支持现有的暗黑/亮色主题

## Capabilities

### New Capabilities
- `oss-file-browser`: 阿里云OSS文件浏览器，展示用户云端Markdown文件列表
- `oss-file-operations`: OSS文件操作（上传、打开、刷新列表）

### Modified Capabilities
- 无

## Impact

### 受影响文件
- `frontend/src/components/MarkdownEditor/MarkdownEditor.tsx`: 集成OSS文件浏览器到主编辑器
- `frontend/src/components/MarkdownEditor/FileTree/`: 可能需要调整以适应标签页切换
- `frontend/src/stores/fileStore.tsx`: 添加OSS相关状态和操作
- `frontend/src/api/markdownEditorApi.ts`: 已有OSS API函数，需要验证

### API依赖
- `GET /api/markdown-editor/oss/list`: 获取OSS文件列表
- `POST /api/markdown-editor/oss/upload`: 上传文件到OSS
- `GET /api/markdown-editor/oss/read`: 从OSS读取文件内容
- `POST /api/markdown-editor/oss/save`: 保存文件到OSS

### 用户体验影响
- 左侧sidebar将变为标签页形式（本地文件 / OSS文件）
- 用户可以在本地和云端文件间无缝切换
- 编辑体验保持不变（相同的编辑器组件）
