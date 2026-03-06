## 1. 状态管理扩展

- [x] 1.1 在FileStore中添加OSS文件状态（ossFiles, isLoadingOssFiles, ossError）
- [x] 1.2 在FileStore中添加OSS文件操作（loadOssFiles, openOssFile）
- [x] 1.3 验证FileStore类型定义和导出

## 2. OSS文件列表组件

- [x] 2.1 创建OssFileList组件文件（frontend/src/components/MarkdownEditor/OssFileList/OssFileList.tsx）
- [x] 2.2 实现文件列表UI（文件名、大小、修改时间）
- [x] 2.3 实现文件项点击打开功能
- [x] 2.4 实现刷新按钮和加载状态
- [x] 2.5 实现空状态和错误状态显示
- [x] 2.6 添加组件导出（index.ts）

## 3. Sidebar标签页集成

- [x] 3.1 修改MarkdownEditor组件，在Sidebar顶部添加标签页切换
- [x] 3.2 实现"本地文件"和"OSS文件"标签切换逻辑
- [x] 3.3 根据当前标签渲染FileTree或OssFileList
- [x] 3.4 确保标签切换时保持各自的滚动位置

## 4. 文件上传功能

- [x] 4.1 在OssFileList中添加上传按钮
- [x] 4.2 实现文件选择对话框（支持.md和.markdown）
- [x] 4.3 调用uploadMarkdownToOss API上传文件
- [x] 4.4 上传成功后刷新文件列表并自动打开文件
- [x] 4.5 添加上传进度和错误提示

## 5. 编辑器集成

- [x] 5.1 验证打开OSS文件后编辑器正确显示内容
- [x] 5.2 确保ossFilePath状态正确设置
- [x] 5.3 验证保存功能（Ctrl+S和自动保存）
- [x] 5.4 确保状态栏显示OSS文件来源

## 6. UI主题适配

- [x] 6.1 为OssFileList组件添加暗黑主题样式
- [x] 6.2 为OssFileList组件添加亮色主题样式
- [x] 6.3 验证主题切换时组件正确更新

## 7. 测试和验证

- [x] 7.1 测试本地文件和OSS文件切换
- [x] 7.2 测试上传、打开、保存完整流程
- [x] 7.3 测试错误处理（网络失败、文件读取失败）
- [x] 7.4 验证TypeScript类型正确
- [x] 7.5 检查代码风格一致性

## 8. 国际化

- [x] 8.1 添加中文翻译（zh-CN.ts）
- [x] 8.2 添加英文翻译（en-US.ts）
- [x] 8.3 在组件中使用翻译函数
