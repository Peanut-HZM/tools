# Markdown Editor

基于Web的Markdown文档管理工具，支持文档浏览、编辑、实时预览和文件管理功能。

## 技术栈

### 后端
- Python 3.10+
- FastAPI
- Pydantic
- aiofiles

### 前端
- Vue.js 3 + TypeScript
- Vite
- Element Plus
- Monaco Editor
- markdown-it + highlight.js

## 快速开始

### 后端

```bash
cd markdown-editor/backend

# 安装依赖
pip install -r requirements.txt

# 设置根目录（可选，默认为当前目录）
export MARKDOWN_EDITOR_ROOT=/path/to/your/docs

# 启动服务
uvicorn app.main:app --reload --port 8001
```

### 前端

```bash
cd markdown-editor/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:5174 即可使用。

## 功能特性

- 📁 目录树展示 - 树形结构浏览Markdown文件
- ✏️ Monaco编辑器 - 语法高亮、自动补全、快捷键支持
- 👁️ 实时预览 - Markdown渲染、代码高亮、TOC生成
- 💾 自动保存 - 可配置的自动保存间隔
- 🔍 全文搜索 - 支持正则表达式和大小写敏感
- ⚙️ 个性化设置 - 主题、字体大小、Tab设置等
- 🔒 安全防护 - 路径遍历防护、XSS清理

## 运行测试

```bash
cd markdown-editor/backend
pytest tests/ -v
```

## API文档

启动后端后访问 http://localhost:8001/docs 查看Swagger API文档。
