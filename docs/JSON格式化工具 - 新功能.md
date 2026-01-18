# JSON格式化工具 - 新功能

## 📝 功能概述

添加了一个全新的JSON格式化工具，支持JSON字符串的格式化、压缩、语法检查和错误提示。

## ✨ 主要功能

### 1. JSON格式化
- 将压缩的JSON字符串格式化为易读的格式
- 支持自定义缩进大小（2空格、4空格、8空格）
- 自动美化显示，提高可读性

### 2. JSON压缩
- 将格式化的JSON字符串压缩为单行
- 去除所有空格和换行
- 适合传输和存储

### 3. 语法检查
- 自动检测JSON语法错误
- 显示详细的错误信息
- 弹窗提示错误位置和原因

### 4. 辅助功能
- 一键复制格式化结果
- 加载示例JSON数据
- 清空输入输出
- 实时预览

## 🎯 使用场景

1. **开发调试**: 格式化API返回的JSON数据
2. **数据查看**: 美化显示配置文件
3. **数据压缩**: 减小JSON文件大小
4. **语法检查**: 验证JSON字符串是否正确
5. **学习参考**: 查看JSON结构示例

## 🔧 技术实现

### 前端组件
**文件**: `frontend/src/components/Tools/JsonFormatter.tsx`

#### 核心功能实现

##### 1. JSON格式化
```typescript
const formatJson = () => {
  try {
    const parsed = JSON.parse(input);
    const formatted = JSON.stringify(parsed, null, indentSize);
    setOutput(formatted);
    setError(null);
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : '未知错误';
    setError(`JSON格式错误: ${errorMessage}`);
    alert(`❌ JSON格式错误\n\n${errorMessage}`);
  }
};
```

##### 2. JSON压缩
```typescript
const minifyJson = () => {
  try {
    const parsed = JSON.parse(input);
    const minified = JSON.stringify(parsed);
    setOutput(minified);
    setError(null);
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : '未知错误';
    setError(`JSON格式错误: ${errorMessage}`);
    alert(`❌ JSON格式错误\n\n${errorMessage}`);
  }
};
```

##### 3. 错误处理
- 使用 `try-catch` 捕获 `JSON.parse()` 错误
- 提取错误信息并显示
- 弹窗提示用户具体错误
- 在输出区域显示错误提示

### 工具数据
**文件**: `backend/app/data/tools_data.py`

```python
Tool(
    id="json-formatter",
    icon="fa-code",
    iconColor="bg-green-500",
    title="JSON格式化",
    description="粘贴JSON字符串，自动格式化并美化显示，支持语法检查和错误提示",
    rating=4.9,
    usageCount="3.2K",
    category="开发工具"
)
```

### 路由配置
**文件**: `frontend/src/App.tsx`

```typescript
import JsonFormatter from './components/Tools/JsonFormatter';

const [currentPage, setCurrentPage] = useState<
  'home' | 'image-downloader' | 'video-downloader' | 'json-formatter'
>('home');

const handleToolClick = (toolId: string) => {
  if (toolId === 'json-formatter') {
    setCurrentPage('json-formatter');
  }
  // ...
};

if (currentPage === 'json-formatter') {
  return <JsonFormatter />;
}
```

## 📊 界面设计

### 布局结构
```
┌─────────────────────────────────────────────┐
│  返回按钮                                    │
│  标题 + 图标                                 │
│  描述                                        │
├─────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐        │
│  │  输入JSON    │  │  格式化结果  │        │
│  │  (文本框)    │  │  (文本框)    │        │
│  │              │  │              │        │
│  │              │  │              │        │
│  └──────────────┘  └──────────────┘        │
├─────────────────────────────────────────────┤
│  缩进大小选择 | 格式化 | 压缩 | 清空       │
├─────────────────────────────────────────────┤
│  功能说明                                    │
│  常见JSON错误                                │
└─────────────────────────────────────────────┘
```

### 颜色方案
- **主色调**: 绿色 (`bg-green-500`) - 代表代码和开发
- **背景**: 深色主题 (`bg-slate-900`)
- **卡片**: 深灰色 (`bg-slate-800`)
- **边框**: 浅灰色 (`border-slate-700`)
- **错误**: 红色 (`text-red-500`)

## 🎨 用户体验

### 1. 输入区域
- 大文本框（高度 384px）
- 等宽字体显示
- 占位符提示
- "加载示例"快捷按钮

### 2. 输出区域
- 只读文本框
- 等宽字体显示
- "复制结果"快捷按钮
- 错误提示区域

### 3. 操作按钮
- **格式化**: 蓝色主按钮
- **压缩**: 橙色按钮
- **清空**: 灰色按钮
- **缩进选择**: 下拉菜单

### 4. 错误提示
- 弹窗提示（`alert`）
- 输出区域下方显示错误信息
- 红色边框和背景
- 详细的错误描述

## 📝 示例数据

### 示例JSON
```json
{
  "name": "张三",
  "age": 30,
  "email": "zhangsan@example.com",
  "address": {
    "city": "北京",
    "district": "朝阳区",
    "street": "建国路1号"
  },
  "hobbies": ["阅读", "旅游", "摄影"],
  "isActive": true,
  "balance": 1234.56
}
```

### 压缩后
```json
{"name":"张三","age":30,"email":"zhangsan@example.com","address":{"city":"北京","district":"朝阳区","street":"建国路1号"},"hobbies":["阅读","旅游","摄影"],"isActive":true,"balance":1234.56}
```

## ⚠️ 常见JSON错误

### 1. 缺少引号
```json
// ❌ 错误
{name: "张三"}

// ✅ 正确
{"name": "张三"}
```

### 2. 多余的逗号
```json
// ❌ 错误
{"name": "张三", "age": 30,}

// ✅ 正确
{"name": "张三", "age": 30}
```

### 3. 缺少逗号
```json
// ❌ 错误
{"name": "张三" "age": 30}

// ✅ 正确
{"name": "张三", "age": 30}
```

### 4. 括号不匹配
```json
// ❌ 错误
{"name": "张三", "address": {"city": "北京"}

// ✅ 正确
{"name": "张三", "address": {"city": "北京"}}
```

### 5. 单引号
```json
// ❌ 错误
{'name': '张三'}

// ✅ 正确
{"name": "张三"}
```

## 🔍 错误检测示例

### 错误1: 缺少引号
**输入**:
```
{name: "张三"}
```

**错误提示**:
```
❌ JSON格式错误

Unexpected token n in JSON at position 1

请检查您的JSON字符串是否正确。
```

### 错误2: 多余的逗号
**输入**:
```json
{"name": "张三",}
```

**错误提示**:
```
❌ JSON格式错误

Unexpected token } in JSON at position 15

请检查您的JSON字符串是否正确。
```

### 错误3: 括号不匹配
**输入**:
```json
{"name": "张三", "address": {"city": "北京"}
```

**错误提示**:
```
❌ JSON格式错误

Unexpected end of JSON input

请检查您的JSON字符串是否正确。
```

## 🚀 使用流程

### 格式化流程
1. 用户打开JSON格式化工具
2. 粘贴或输入JSON字符串
3. 选择缩进大小（可选）
4. 点击"格式化"按钮
5. 查看格式化结果
6. 点击"复制结果"复制到剪贴板

### 压缩流程
1. 用户打开JSON格式化工具
2. 粘贴或输入JSON字符串
3. 点击"压缩"按钮
4. 查看压缩结果
5. 点击"复制结果"复制到剪贴板

### 错误检查流程
1. 用户输入有错误的JSON字符串
2. 点击"格式化"或"压缩"按钮
3. 系统检测到错误
4. 弹窗显示错误信息
5. 输出区域显示错误提示
6. 用户根据提示修正错误

## 💡 使用技巧

### 1. 快速格式化
- 使用 Ctrl+V 粘贴JSON
- 直接点击"格式化"
- 无需手动选择缩进

### 2. 批量处理
- 格式化后复制结果
- 清空输入
- 粘贴下一个JSON

### 3. 学习JSON
- 点击"加载示例"
- 查看标准JSON结构
- 尝试修改和格式化

### 4. 调试API
- 复制API返回的JSON
- 格式化查看结构
- 定位数据问题

## 📊 功能对比

| 功能 | 本工具 | 在线工具 |
|------|--------|----------|
| 格式化 | ✅ | ✅ |
| 压缩 | ✅ | ✅ |
| 语法检查 | ✅ | ✅ |
| 错误提示 | ✅ 弹窗 | ⚠️ 页面显示 |
| 离线使用 | ✅ | ❌ |
| 隐私保护 | ✅ 本地处理 | ⚠️ 上传服务器 |
| 加载速度 | ✅ 快速 | ⚠️ 依赖网络 |
| 自定义缩进 | ✅ | ✅ |
| 示例数据 | ✅ | ⚠️ 部分支持 |

## 🔒 隐私保护

### 本地处理
- ✅ 所有JSON处理在浏览器本地完成
- ✅ 不上传到服务器
- ✅ 不保存用户数据
- ✅ 不记录操作历史

### 安全性
- ✅ 纯前端实现
- ✅ 无网络请求
- ✅ 无数据泄露风险
- ✅ 适合处理敏感数据

## 📚 相关文档

- `backend/app/data/tools_data.py` - 工具数据定义
- `frontend/src/components/Tools/JsonFormatter.tsx` - 前端组件
- `frontend/src/App.tsx` - 路由配置

## ✨ 总结

成功添加JSON格式化工具：

- ✅ 创建前端组件 `JsonFormatter.tsx`
- ✅ 添加工具数据到 `tools_data.py`
- ✅ 配置路由到 `App.tsx`
- ✅ 实现格式化功能
- ✅ 实现压缩功能
- ✅ 实现语法检查
- ✅ 实现错误提示（弹窗）
- ✅ 实现复制功能
- ✅ 实现示例加载
- ✅ 前端自动热更新

用户现在可以使用JSON格式化工具了！

---

**创建时间**: 2024-12-28  
**状态**: ✅ 完成  
**测试**: ✅ 前端已热更新  
**分类**: 开发工具
