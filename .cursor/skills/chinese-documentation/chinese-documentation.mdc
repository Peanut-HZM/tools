---
name: chinese-documentation
description: 确保新建的 Markdown 文档名称和内容尽量使用中文，只有在必须使用英文的地方才使用英文
type: "always_apply"
---

# 中文文档编写规范

> **目标**：确保所有新建的 Markdown 文档优先使用中文，提高中文用户的可读性和理解性。  
> **原则**：尽量使用中文，必须使用英文的地方才使用英文。

## 📋 文档命名规范

### ✅ 推荐使用中文或拼音

- **中文命名**：`用户指南.md`、`安装说明.md`、`API接口文档.md`
- **拼音命名**：`yonghu-zhinan.md`、`anzhuang-shuoming.md`、`api-jiekou-wendang.md`
- **混合命名**：`README.md`（README 是约定俗成的，保持英文）

### ❌ 避免纯英文命名（除非必要）

- ❌ `user-guide.md`（除非是国际化项目）
- ❌ `installation.md`（除非是国际化项目）
- ✅ `用户指南.md` 或 `yonghu-zhinan.md`

### 特殊情况（必须使用英文）

以下情况必须使用英文：
- **README.md** - 约定俗成的文件名
- **LICENSE** - 许可证文件名
- **CHANGELOG.md** - 变更日志（可考虑 `更新日志.md`）
- **技术术语**：`API.md`、`CLI.md`、`SDK.md` 等

## 📝 文档内容规范

### ✅ 优先使用中文

#### 标题和章节
```markdown
# 用户指南
## 安装步骤
### 前置要求
```

#### 正文内容
```markdown
本文档说明如何安装和使用本系统。

## 快速开始

按照以下步骤进行操作：
1. 下载安装包
2. 解压文件
3. 运行安装脚本
```

#### 列表和说明
```markdown
- **功能特性**：支持多种数据格式
- **性能优化**：提升处理速度
- **安全加固**：增强数据保护
```

### ⚠️ 必须使用英文的地方

#### 1. 代码示例
```markdown
```bash
# 安装依赖
npm install
```

```python
def hello_world():
    print("Hello, World!")
```
```

**说明**：代码本身必须保持英文，但代码注释可以使用中文。

#### 2. 命令行和路径
```markdown
运行以下命令：
```bash
cd /path/to/project
npm run build
```
```

**说明**：命令、路径、文件名保持英文，但说明文字使用中文。

#### 3. 技术术语（首次出现时）
```markdown
使用 **API**（应用程序编程接口）进行数据交互。

**RESTful API** 是一种架构风格。
```

**说明**：技术术语保持英文，但可以加中文解释。

#### 4. 配置文件和 JSON/YAML
```markdown
在 `package.json` 中添加依赖：
```json
{
  "dependencies": {
    "express": "^4.18.0"
  }
}
```
```

**说明**：配置文件内容保持英文，但说明文字使用中文。

#### 5. 环境变量和键名
```markdown
设置环境变量：
```bash
export API_KEY=your-api-key
export DATABASE_URL=postgresql://localhost/db
```
```

**说明**：环境变量名保持英文，但说明文字使用中文。

## 🎯 编写示例

### ✅ 好的示例

```markdown
# 项目使用指南

## 快速开始

### 1. 安装依赖

运行以下命令安装项目依赖：

```bash
npm install
```

### 2. 配置环境变量

创建 `.env` 文件并设置以下变量：

```bash
API_KEY=your-api-key
DATABASE_URL=postgresql://localhost/mydb
```

### 3. 启动服务

使用以下命令启动开发服务器：

```bash
npm run dev
```

## API 接口说明

### 获取用户信息

**接口地址**：`GET /api/users/:id`

**请求参数**：
- `id`（必填）：用户 ID

**返回示例**：
```json
{
  "id": 1,
  "name": "张三",
  "email": "zhangsan@example.com"
}
```
```

### ❌ 不好的示例

```markdown
# User Guide

## Quick Start

### 1. Install Dependencies

Run the following command:

```bash
npm install
```

### 2. Configure Environment Variables

Create `.env` file:

```bash
API_KEY=your-api-key
DATABASE_URL=postgresql://localhost/mydb
```
```

**问题**：全部使用英文，对中文用户不友好。

## 📌 检查清单

创建新文档时，检查以下项目：

- [ ] 文档名称是否使用中文或拼音（除非是 README.md 等约定俗成的文件名）
- [ ] 标题和章节是否使用中文
- [ ] 正文内容是否使用中文
- [ ] 代码示例是否保持英文（代码本身）
- [ ] 代码注释是否可以使用中文
- [ ] 命令和路径是否保持英文
- [ ] 技术术语是否保持英文（但加中文解释）
- [ ] 配置文件内容是否保持英文
- [ ] 说明文字是否使用中文

## 🔍 特殊情况处理

### 国际化项目

如果项目需要支持多语言，可以：
- 使用英文作为主文档
- 提供中文翻译版本：`README.zh.md`、`README.en.md`

### 技术文档

技术文档中：
- **API 文档**：接口名称、参数名保持英文，说明使用中文
- **架构文档**：技术术语保持英文，解释使用中文
- **代码文档**：代码保持英文，注释和说明使用中文

### 开源项目

开源项目可以：
- **README.md** 使用英文（国际化标准）
- 提供 `README.zh.md` 中文版本
- 其他文档优先使用中文

## 💡 最佳实践

1. **标题使用中文**：`# 用户指南` 而不是 `# User Guide`
2. **说明使用中文**：`运行以下命令` 而不是 `Run the following command`
3. **代码保持英文**：代码本身必须保持英文
4. **术语加解释**：首次出现的技术术语加中文解释
5. **注释用中文**：代码注释可以使用中文，提高可读性

## 🎯 应用场景

本规范适用于：
- ✅ 新建的 Markdown 文档
- ✅ 项目文档（README、指南、说明）
- ✅ 技术文档（API 文档、架构文档）
- ✅ 代码注释和说明
- ✅ 用户手册和教程

不适用于：
- ❌ 代码本身（代码必须使用编程语言的语法）
- ❌ 配置文件内容（必须符合配置格式要求）
- ❌ 国际化项目的英文版本

---

**记住**：尽量使用中文，必须使用英文的地方才使用英文！
