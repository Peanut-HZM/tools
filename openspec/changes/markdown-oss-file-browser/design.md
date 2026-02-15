## Context

当前Markdown编辑器使用本地文件系统存储用户的Markdown文档。系统已经集成了阿里云OSS API用于文件上传和读取，但缺乏一个直观的界面来管理云端文件。

**当前架构:**
- FileStore管理本地文件状态（directoryTree, currentFile, currentFilePath等）
- 左侧FileTree组件展示本地目录结构
- 已存在OSS API函数: listOssMarkdownFiles, uploadMarkdownToOss, readMarkdownFromOss
- MarkdownEditor主组件已有ossFilePath状态用于标记当前编辑的是OSS文件

**约束条件:**
- 使用React Context进行状态管理
- 保持与现有FileStore的兼容性
- 支持暗黑/亮色主题切换
- 保持编辑器组件的可复用性

## Goals / Non-Goals

**Goals:**
- 在左侧sidebar实现本地文件和OSS文件的标签切换
- 展示OSS文件列表（文件名、大小、最后修改时间）
- 支持点击OSS文件在编辑器中打开
- 支持拖拽和按钮上传文件到OSS
- 保持现有的编辑体验不变

**Non-Goals:**
- 不支持OSS文件夹结构（扁平化展示）
- 不支持OSS文件重命名/删除（后端API未提供）
- 不修改后端API
- 不引入新的状态管理方案

## Decisions

### Decision 1: Sidebar标签页设计

**选择:** 在左侧sidebar顶部添加标签页切换（本地文件 / OSS文件）

**理由:**
- 保持用户熟悉的文件树位置
- 清晰区分本地和云端存储
- 便于未来扩展更多存储源

**替代方案:**
- 并排显示两个文件树（ rejected: 屏幕空间不足 ）
- 在FileTree内混排本地和OSS文件（ rejected: 概念不清晰 ）

### Decision 2: OSS文件状态管理

**选择:** 扩展现有FileStore，添加ossFileList状态和相关操作

**理由:**
- 复用现有的loading/error处理模式
- 保持状态管理的一致性
- 便于与编辑器组件集成

**数据结构:**
```typescript
interface OssFileState {
  ossFiles: OssFileInfo[];
  isLoadingOssFiles: boolean;
  ossError: string | null;
}
```

### Decision 3: 新组件结构

**选择:** 创建独立的OssFileList组件

**组件层次:**
```
MarkdownEditor
├── Sidebar (带标签页)
│   ├── Tab: 本地文件
│   │   └── FileTree (existing)
│   └── Tab: OSS文件
│       └── OssFileList (new)
│           ├── OssFileItem
│           └── UploadButton/DropZone
```

**理由:**
- 关注点分离，FileTree保持纯粹
- 便于独立测试和维护
- 不同的交互模式（OSS无文件夹操作）

### Decision 4: 文件打开流程

**选择:** 点击OSS文件时，调用readMarkdownFromOss获取内容，通过setContent加载到编辑器

**流程:**
1. 用户点击OSS文件
2. 调用fileStore.openOssFile(filePath)
3. API获取文件内容
4. 调用editorStore.setContent(content, true)
5. 设置ossFilePath标记当前文件来源

**理由:**
- 复用现有的编辑器打开逻辑
- 保持currentFilePath语义不变（仍为本地文件）
- 使用ossFilePath区分文件来源

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| OSS API调用失败 | 添加错误边界和重试机制；显示友好错误提示 |
| 大文件加载慢 | 添加loading状态；考虑文件大小限制提示 |
| 本地和OSS文件同名 | OSS文件显示时添加"云端"标识；路径区分 |
| 用户混淆文件位置 | Tab标签清晰标识；状态栏显示当前文件来源 |
| 频繁刷新导致API限流 | 手动刷新按钮而非自动刷新；缓存文件列表 |

## Migration Plan

**部署步骤:**
1. 创建OssFileList组件
2. 扩展FileStore添加OSS状态
3. 修改MarkdownEditor sidebar添加标签页
4. 验证与现有本地文件功能的兼容性
5. 添加加载状态和错误处理

**回滚策略:**
- 特性由独立组件实现，回滚只需隐藏OSS标签页
- 不影响现有本地文件功能

## Open Questions

1. OSS文件列表是否需要分页？（当前假设用户文件数量较少）
2. 是否需要OSS文件搜索功能？
3. 上传文件是否自动打开？（建议: 是）
