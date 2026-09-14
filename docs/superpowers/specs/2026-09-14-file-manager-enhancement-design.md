# 文件管理器扩展设计文档

**创建日期**: 2026-09-14  
**状态**: 设计完成，待实现  
**相关功能**: 文件编辑器 - 选择文件夹/文件对话框

---

## 需求概述

将现有的"选择文件夹"对话框扩展为完整文件管理器，支持：

1. **访问任意目录** - 用户可以浏览本机任何位置的文件夹和文件
2. **文件详细信息** - 显示文件大小、修改时间等元数据
3. **快速访问** - 提供常用目录（Home、Desktop、Documents 等）的快速导航
4. **完整文件操作** - 支持新建、重命名、删除、复制、移动、上传、下载
5. **路径输入常驻** - 路径输入框始终可见，支持直接输入路径

---

## 第一部分：后端 API 改动

### 1.1 移除路径限制

**现状**：后端 `MarkdownFileService` 验证路径必须在用户根目录内。

**改动**：
- 新增 `allow_any_path` 模式，启用时跳过根目录限制
- 保留路径安全检查（防止 `..` 遍历攻击到敏感系统目录）
- 配置存储在用户配置中（`EditorConfig` 新增字段 `allow_any_path: boolean`）

**敏感路径黑名单**（后端硬编码）：
- `/etc/shadow`, `/etc/passwd`
- `/proc/*`
- `/sys/*`
- 其他操作系统敏感目录

### 1.2 扩展目录浏览 API

> **基础路径**: `/api/markdown-editor`

**现有端点**: `GET /files/directories` - 只返回目录列表

**扩展为**: `GET /files/browse` - 返回文件和文件夹混合列表

**请求参数**:
- `parent_path` (query, required): 要浏览的目录路径
- `offset` (query, optional): 分页偏移量，默认 0
- `limit` (query, optional): 每页数量，默认 100，最大 500

**响应格式**:
```python
class FileItem:
    name: str              # 文件/文件夹名
    path: str              # 完整路径
    type: str              # "file" 或 "directory"
    size: int              # 字节数，目录为 0
    modified_at: str       # ISO 时间字符串
    extension: str         # 文件扩展名（目录为空）
    is_previewable: bool   # 是否可预览

class BrowseResponse:
    current_path: str      # 当前浏览路径
    items: list[FileItem]  # 文件和文件夹列表
    total: int             # 总数量
    offset: int            # 当前偏移量
    limit: int             # 每页数量
    has_more: bool         # 是否还有更多
```

### 1.3 新增文件操作 API

> **基础路径**: 所有端点前缀为 `/api/markdown-editor`

| 端点 | 方法 | 功能 | 请求体/参数 |
|------|------|------|------------|
| `/files/browse` | GET | 浏览目录内容 | `?parent_path=/path&offset=0&limit=100` |
| `/files/copy` | POST | 复制文件/文件夹 | `{ "source_path": str, "target_path": str }` |
| `/files/move` | POST | 移动文件/文件夹 | `{ "source_path": str, "target_path": str }` |
| `/files/rename` | POST | 重命名文件/文件夹 | `{ "path": str, "new_name": str }` |
| `/files/delete` | POST | 删除文件/文件夹 | `{ "path": str }` |
| `/files/create` | POST | 新建文件或文件夹 | `{ "parent_path": str, "name": str, "type": "file" \| "directory" }` |
| `/files/upload` | POST | 上传文件 | `multipart/form-data`，字段: `file`, `parent_path` |
| `/files/download` | GET | 下载文件 | `?path=/path/to/file` |
| `/files/info` | GET | 获取文件/文件夹详细信息 | `?path=/path/to/file` |

---

## 第二部分：前端 UI 设计

### 2.1 对话框布局

```
┌─────────────────────────────────────────────────────────────┐
│  文件管理器                                          [关闭]  │
├─────────────────────────────────────────────────────────────┤
│ ← 返回  │ 🏠 📂 📁  快速访问  │ [路径输入框____________]  │  ← 工具栏（路径输入常驻）
├─────────────────────────────────────────────────────────────┤
│ 名称            │ 类型     │ 大小       │ 修改时间          │  ← 表头
│─────────────────────────────────────────────────────────────│
│  Documents     │ 文件夹   │ -          │ 2024-01-15 14:30  │
│  Projects    │ 文件夹   │ -          │ 2024-01-14 10:20  │
│ 📄 readme.md   │ 文件     │ 2.3 KB     │ 2024-01-13 09:15  │
│ 🖼️ image.png   │ 文件     │ 156 KB     │ 2024-01-12 16:45  │
├─────────────────────────────────────────────────────────────
│ 根目录：/ | 已选择：/Users/... | 取消 │ 选择此文件夹/文件   │  ← 底部操作栏
└─────────────────────────────────────────────────────────────┘
```

### 2.2 快速访问按钮

工具栏快捷按钮（可配置）：
-  Home (`~/`)
-  Desktop (`~/Desktop`)
- 📁 Documents (`~/Documents`)
- 📝 Projects (`~/Projects`)
- 📦 Downloads (`~/Downloads`)
- ️ 更多... (打开设置配置更多快速访问)

### 2.3 右键菜单

右键点击文件/文件夹显示上下文菜单：

**文件菜单**:
- 打开
- 重命名
- 复制
- 移动
- 删除
- 下载

**文件夹菜单**:
- 进入
- 新建文件夹
- 新建文件
- 重命名
- 复制
- 移动
- 删除

---

## 第三部分：前端组件架构

### 3.1 组件拆分

```
FolderBrowserDialog/
├── FolderBrowserDialog.tsx       # 主对话框（保持现有入口）
├── FileManager.tsx                # 新增：文件管理器核心组件
├── FileList.tsx                   # 新增：文件列表组件
├── FileItemRow.tsx                # 新增：单行文件/文件夹
├── FileContextMenu.tsx            # 新增：右键菜单
├── QuickAccessBar.tsx             # 新增：快速访问工具栏
├── PathInput.tsx                  # 新增：路径输入框
└── fileOperations.ts              # 新增：文件操作 API 调用封装
```

### 3.2 状态管理

```typescript
interface FileManagerState {
  currentPath: string;           // 当前浏览路径
  items: FileItem[];             // 文件和文件夹列表
  selectedItems: string[];       // 选中的项目
  loading: boolean;              // 加载状态
  error: string | null;          // 错误信息
  quickAccess: string[];         // 用户自定义快速访问列表
  sortField: 'name' | 'size' | 'modified';  // 排序字段
  sortOrder: 'asc' | 'desc';     // 排序方向
}
```

### 3.3 与现有组件集成

- 保持 `FolderBrowserDialog` 作为入口，内部使用新的 `FileManager` 组件
- 现有"本地文件"树形视图保留不变（`Tree.tsx`）
- 新增"文件管理器"模式，通过对话框顶部 Tab 切换：`[本地文件 | 文件管理器 | OSS 文件]`

---

## 第四部分：错误处理与安全性

### 4.1 错误处理

| 场景 | 前端处理 | 后端返回 |
|------|----------|----------|
| 路径不存在 | 显示错误提示 + 返回上层 | 404 |
| 权限不足 | 显示"无权限访问" + 灰色显示 | 403 |
| 路径为空目录 | 显示"空目录"提示 | 空列表 |
| 大目录加载慢 | 显示加载进度 + 支持取消 | 分页返回 |
| 文件操作失败 | Toast 提示 + 重试按钮 | 具体错误信息 |
| 敏感路径访问 | 显示"禁止访问" | 403 |

### 4.2 安全检查

- **JWT 认证**: 只有登录用户才能访问文件管理 API
- **敏感路径黑名单**: 后端硬编码禁止访问的系统敏感目录
- **路径遍历防护**: 防止 `../../../` 等攻击
- **文件大小限制**: 下载时防止传输超大文件（默认 100MB）

### 4.3 性能优化

- **分页加载**: 目录列表每页 100 项，支持滚动加载更多
- **懒加载**: 文件夹大小不递归计算，显示为 0
- **图标缓存**: 文件图标缓存避免重复读取
- **虚拟滚动**: 大目录使用虚拟滚动优化渲染性能

---

## 成功标准

- [ ] **A**: 可以浏览任意目录 - 输入 `/` 或任何路径都能看到内容
- [ ] **B**: 可以执行文件操作 - 新建、重命名、删除、复制、移动、上传、下载都能正常工作
- [ ] **C**: 性能可接受 - 大目录（1000+ 文件）加载不超过 2 秒
- [ ] **D**: 错误处理完善 - 权限不足、路径不存在等情况有清晰的错误提示
- [ ] **E**: UI 体验流畅 - 操作反馈及时，有加载状态、成功/失败提示

---

## 开发周期估算

- **后端 API 改动**: 1 天
- **前端 UI 开发**: 1.5 天
- **集成测试与验收**: 0.5 天
- **总计**: 3 天

---

## 附录：API 示例

### 浏览目录

```bash
GET /api/markdown-editor/files/browse?parent_path=/Users/huazhongmin/Projects
Authorization: Bearer <token>
```

**响应**:
```json
{
  "success": true,
  "data": {
    "current_path": "/Users/huazhongmin/Projects",
    "items": [
      {
        "name": "tools",
        "path": "/Users/huazhongmin/Projects/tools",
        "type": "directory",
        "size": 0,
        "modified_at": "2024-01-15T14:30:00Z",
        "extension": "",
        "is_previewable": false
      },
      {
        "name": "readme.md",
        "path": "/Users/huazhongmin/Projects/readme.md",
        "type": "file",
        "size": 2355,
        "modified_at": "2024-01-13T09:15:00Z",
        "extension": ".md",
        "is_previewable": true
      }
    ],
    "total": 2,
    "has_more": false
  }
}
```

### 复制文件

```bash
POST /api/markdown-editor/files/copy
Authorization: Bearer <token>
Content-Type: application/json

{
  "source_path": "/Users/huazhongmin/Projects/readme.md",
  "target_path": "/Users/huazhongmin/Projects/readme_copy.md"
}
```

**响应**:
```json
{
  "success": true,
  "message": "文件复制成功"
}
```
