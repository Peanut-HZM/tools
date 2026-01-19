# Markdown编辑器OSS上传功能说明

## 功能概述

在Markdown编辑器中新增了直接上传Markdown文档到OSS（阿里云对象存储）的功能，支持上传、预览和编辑，所有文件存储在OSS服务器中。

## 实现的功能

### 后端API端点

1. **上传Markdown文件到OSS**
   - 端点: `POST /api/markdown-editor/oss/upload`
   - 功能: 上传.md、.markdown、.txt文件到OSS
   - 权限: 需要用户认证
   - 文件组织: `markdown/{user_id}/{filename}`

2. **从OSS读取Markdown文件**
   - 端点: `GET /api/markdown-editor/oss/read?file_path={path}`
   - 功能: 读取OSS中的Markdown文件内容
   - 权限: 只能读取自己的文件

3. **保存Markdown文件到OSS**
   - 端点: `POST /api/markdown-editor/oss/save`
   - 功能: 保存编辑后的内容到OSS
   - 权限: 只能保存自己的文件

4. **列出OSS中的Markdown文件**
   - 端点: `GET /api/markdown-editor/oss/list`
   - 功能: 列出当前用户在OSS中的所有Markdown文件

### 前端功能

1. **文件上传组件** (`FileUpload`)
   - 支持拖拽上传
   - 支持点击上传
   - 文件类型验证（.md, .markdown, .txt）
   - 文件大小限制（10MB）
   - 上传进度显示

2. **集成到MarkdownEditor**
   - 当没有打开文件时，显示上传区域
   - 上传后自动加载文件内容到编辑器
   - 支持预览和编辑模式
   - 保存时自动保存到OSS
   - 显示OSS文件标识

## 使用流程

1. **上传文件**
   - 打开Markdown编辑器
   - 如果没有打开文件，会显示上传区域
   - 拖拽或点击上传Markdown文件
   - 文件自动上传到OSS并加载到编辑器

2. **编辑文件**
   - 上传后可以直接在编辑器中编辑
   - 支持实时预览
   - 支持自动保存（如果配置了）

3. **保存文件**
   - 点击保存按钮或使用 Ctrl+S
   - 内容自动保存到OSS
   - 显示保存状态

## 安全特性

1. **用户隔离**: 每个用户的文件存储在独立的OSS路径下
2. **权限控制**: 用户只能访问和修改自己的文件
3. **文件类型验证**: 只允许上传Markdown相关文件
4. **文件大小限制**: 最大10MB

## 配置要求

### 后端配置

需要在 `.env` 文件中配置OSS相关参数：

```env
ALIYUN_OSS_ACCESS_KEY_ID=your_access_key_id
ALIYUN_OSS_ACCESS_KEY_SECRET=your_access_key_secret
ALIYUN_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
ALIYUN_OSS_BUCKET_NAME=your_bucket_name
```

### 数据库要求

OSS服务会自动创建 `oss_files` 表来记录文件信息。

## 文件结构

### 后端文件
- `backend/app/routes/markdown_editor.py` - 添加了OSS相关的API端点
- `backend/app/services/oss_service.py` - OSS服务（已存在）

### 前端文件
- `frontend/src/components/MarkdownEditor/FileUpload/FileUpload.tsx` - 文件上传组件
- `frontend/src/components/MarkdownEditor/FileUpload/FileUpload.css` - 上传组件样式
- `frontend/src/components/MarkdownEditor/MarkdownEditor.tsx` - 集成上传功能
- `frontend/src/api/markdownEditorApi.ts` - 添加了OSS相关的API调用

## 注意事项

1. OSS服务必须正确配置才能使用上传功能
2. 如果OSS未配置，上传功能会显示错误提示
3. OSS文件和本地文件系统文件是分开管理的
4. 上传的文件会立即保存到OSS，编辑后的保存也会更新OSS中的文件
