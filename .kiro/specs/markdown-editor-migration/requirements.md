# Requirements Document

## Introduction

本文档定义了将 markdown-editor 项目的前后端功能完整迁移到 tool-aggregation-website 的 backend 和 frontend 中的需求。迁移后的 markdown-editor 将作为一个工具集成到工具聚合网站中，用户可以通过首页的工具卡片进入使用。迁移过程需要确保所有功能完整保留，包括登录认证逻辑，同时不能影响现有功能的正常使用。

## Glossary

- **System**: 整个工具聚合网站应用程序
- **Frontend**: React前端应用
- **Backend**: Python后端服务（FastAPI）
- **Markdown Editor Tool**: 迁移后的Markdown编辑器工具
- **Tool Card**: 工具卡片组件，展示单个工具的信息
- **Authentication**: 用户认证和登录系统
- **File Tree**: 文件树形结构展示组件
- **Monaco Editor**: 代码编辑器组件
- **Preview**: Markdown实时预览组件

## Requirements

### Requirement 1: 工具集成

**User Story:** 作为用户，我希望能够从工具聚合网站的首页通过工具卡片进入Markdown编辑器工具。

#### Acceptance Criteria

1. THE System SHALL 在首页工具列表中显示Markdown编辑器工具卡片
2. THE Tool Card SHALL 包含Markdown编辑器的图标、标题、描述和评分信息
3. WHEN 用户点击Markdown编辑器工具卡片 THEN THE System SHALL 导航到Markdown编辑器页面
4. THE Markdown Editor Tool SHALL 作为独立的路由页面存在，不影响其他工具的正常使用
5. THE System SHALL 保持现有工具的功能和路由不受影响

### Requirement 2: 后端API迁移

**User Story:** 作为开发者，我希望将markdown-editor的所有后端API功能迁移到backend中，并确保API路径和功能完整。

#### Acceptance Criteria

1. THE Backend SHALL 实现文件操作API（获取目录树、读取文件、保存文件、创建文件、删除文件、重命名文件、创建目录、删除目录）
2. THE Backend SHALL 实现配置管理API（获取配置、保存配置）
3. THE Backend SHALL 实现搜索功能API（文件搜索、内容搜索）
4. THE Backend SHALL 使用 `/api/markdown-editor` 作为API前缀，避免与现有API冲突
5. THE Backend SHALL 保持与markdown-editor原有API接口的兼容性
6. THE Backend SHALL 实现路径遍历防护和安全验证
7. THE Backend SHALL 支持用户隔离的文件存储（基于用户ID）

### Requirement 3: 前端组件迁移

**User Story:** 作为开发者，我希望将markdown-editor的所有前端组件和功能迁移到frontend中，并适配React技术栈。

#### Acceptance Criteria

1. THE Frontend SHALL 实现文件树组件（FileTree），支持树形结构展示Markdown文件
2. THE Frontend SHALL 集成Monaco编辑器组件，支持Markdown语法高亮和编辑
3. THE Frontend SHALL 实现实时预览组件（Preview），支持Markdown渲染和代码高亮
4. THE Frontend SHALL 实现搜索对话框组件（SearchDialog），支持文件搜索和内容搜索
5. THE Frontend SHALL 实现设置对话框组件（SettingsDialog），支持编辑器配置管理
6. THE Frontend SHALL 实现自动保存功能（AutoSave），支持可配置的自动保存间隔
7. THE Frontend SHALL 适配React技术栈，将Vue组件转换为React组件
8. THE Frontend SHALL 使用React Router实现路由导航
9. THE Frontend SHALL 保持与现有前端架构的一致性

### Requirement 4: 用户认证和登录系统

**User Story:** 作为用户，我希望在使用Markdown编辑器前进行登录认证，以确保文件数据的安全性和用户隔离。

#### Acceptance Criteria

1. THE System SHALL 实现用户注册功能
2. THE System SHALL 实现用户登录功能
3. THE System SHALL 实现用户登出功能
4. THE System SHALL 实现会话管理（Session Management）
5. THE System SHALL 实现JWT令牌认证机制
6. THE System SHALL 在未登录状态下阻止访问Markdown编辑器工具
7. THE System SHALL 在Header中显示用户登录状态和用户信息
8. THE System SHALL 实现登录状态的持久化（localStorage/sessionStorage）
9. THE Backend SHALL 验证所有Markdown编辑器API请求的认证令牌
10. THE Backend SHALL 基于用户ID隔离文件存储空间

### Requirement 5: 文件管理功能

**User Story:** 作为用户，我希望能够管理我的Markdown文件，包括浏览、创建、编辑、删除和重命名操作。

#### Acceptance Criteria

1. THE System SHALL 支持选择根目录（Root Path Selection）
2. THE System SHALL 显示文件树形结构，仅显示Markdown文件和相关目录
3. THE System SHALL 支持打开文件进行编辑或查看
4. THE System SHALL 支持创建新文件
5. THE System SHALL 支持保存文件内容
6. THE System SHALL 支持删除文件
7. THE System SHALL 支持重命名文件
8. THE System SHALL 支持创建目录
9. THE System SHALL 支持删除目录（空目录或递归删除）
10. THE System SHALL 显示文件保存状态（已保存、未保存、保存中、错误）
11. THE System SHALL 实现文件内容的自动保存功能

### Requirement 6: 编辑器功能

**User Story:** 作为用户，我希望使用功能强大的编辑器来编辑Markdown文件，包括语法高亮、自动补全和快捷键支持。

#### Acceptance Criteria

1. THE System SHALL 集成Monaco编辑器
2. THE System SHALL 支持Markdown语法高亮
3. THE System SHALL 支持代码自动补全
4. THE System SHALL 支持快捷键操作（Ctrl+S保存、Ctrl+B加粗、Ctrl+I斜体等）
5. THE System SHALL 支持显示/隐藏行号
6. THE System SHALL 支持可配置的字体大小
7. THE System SHALL 支持可配置的Tab大小和空格/制表符切换
8. THE System SHALL 支持主题切换（亮色/暗色）
9. THE System SHALL 支持光标位置显示
10. THE System SHALL 支持编辑器内容的实时更新

### Requirement 7: 实时预览功能

**User Story:** 作为用户，我希望能够实时预览Markdown渲染效果，包括代码高亮、数学公式和目录生成。

#### Acceptance Criteria

1. THE System SHALL 实现Markdown到HTML的实时渲染
2. THE System SHALL 支持代码块语法高亮（highlight.js）
3. THE System SHALL 支持数学公式渲染（KaTeX）
4. THE System SHALL 支持流程图和图表渲染（Mermaid）
5. THE System SHALL 自动生成文档目录（TOC）
6. THE System SHALL 支持目录导航（点击目录项跳转到对应章节）
7. THE System SHALL 支持XSS防护和内容清理（DOMPurify）
8. THE System SHALL 支持可配置的预览主题
9. THE System SHALL 实现编辑模式和预览模式的切换
10. THE System SHALL 在编辑模式下支持分屏显示（编辑器+预览）

### Requirement 8: 搜索功能

**User Story:** 作为用户，我希望能够快速搜索文件名称和文件内容，以便快速定位所需信息。

#### Acceptance Criteria

1. THE System SHALL 支持按文件名搜索
2. THE System SHALL 支持按文件内容搜索
3. THE System SHALL 支持正则表达式搜索
4. THE System SHALL 支持大小写敏感/不敏感搜索
5. THE System SHALL 显示搜索结果的文件路径和匹配行信息
6. THE System SHALL 支持点击搜索结果跳转到对应文件位置
7. THE System SHALL 实现搜索对话框UI组件

### Requirement 9: 配置管理功能

**User Story:** 作为用户，我希望能够自定义编辑器和预览的配置，以符合个人使用习惯。

#### Acceptance Criteria

1. THE System SHALL 支持主题配置（亮色/暗色）
2. THE System SHALL 支持字体大小配置
3. THE System SHALL 支持自动保存间隔配置
4. THE System SHALL 支持预览主题配置
5. THE System SHALL 支持行号显示/隐藏配置
6. THE System SHALL 支持Tab大小配置
7. THE System SHALL 支持空格/制表符配置
8. THE System SHALL 支持语言配置（中文/英文）
9. THE System SHALL 将配置保存到后端，实现跨设备同步
10. THE System SHALL 提供配置对话框UI组件

### Requirement 10: 国际化支持

**User Story:** 作为用户，我希望能够使用中文或英文界面，以符合我的语言偏好。

#### Acceptance Criteria

1. THE System SHALL 支持中文（zh-CN）界面
2. THE System SHALL 支持英文（en-US）界面
3. THE System SHALL 提供语言切换功能
4. THE System SHALL 将语言偏好保存到用户配置中
5. THE System SHALL 实现完整的国际化文本覆盖

### Requirement 11: 响应式布局

**User Story:** 作为用户，我希望在不同屏幕尺寸下都能获得良好的使用体验。

#### Acceptance Criteria

1. THE System SHALL 支持可调整的侧边栏宽度（文件树）
2. THE System SHALL 支持可调整的预览区域宽度
3. THE System SHALL 在编辑模式下支持编辑器/预览区域的比例调整
4. THE System SHALL 在查看模式下支持目录侧边栏和预览区域的布局
5. THE System SHALL 在小屏幕设备上提供合理的默认布局
6. THE System SHALL 实现响应式设计，适配不同屏幕尺寸

### Requirement 12: 安全性和数据隔离

**User Story:** 作为用户，我希望我的文件数据安全可靠，且与其他用户的数据隔离。

#### Acceptance Criteria

1. THE System SHALL 实现路径遍历攻击防护
2. THE System SHALL 实现XSS攻击防护
3. THE System SHALL 基于用户ID实现文件存储隔离
4. THE System SHALL 验证所有文件操作的用户权限
5. THE System SHALL 防止用户访问其他用户的文件
6. THE System SHALL 实现安全的文件路径验证
7. THE System SHALL 记录文件操作日志（可选）

### Requirement 13: 错误处理

**User Story:** 作为用户，我希望在操作出错时能够获得清晰的错误提示和处理建议。

#### Acceptance Criteria

1. THE System SHALL 处理文件读取错误（文件不存在、权限不足等）
2. THE System SHALL 处理文件保存错误（磁盘空间不足、权限不足等）
3. THE System SHALL 处理网络请求错误（连接失败、超时等）
4. THE System SHALL 处理认证错误（令牌过期、无效令牌等）
5. THE System SHALL 显示用户友好的错误消息
6. THE System SHALL 提供错误恢复机制（重试、取消等）

### Requirement 14: 性能优化

**User Story:** 作为用户，我希望应用响应迅速，操作流畅。

#### Acceptance Criteria

1. THE System SHALL 实现文件内容的懒加载
2. THE System SHALL 实现自动保存的防抖处理
3. THE System SHALL 优化大文件的渲染性能
4. THE System SHALL 实现组件懒加载（React.lazy）
5. THE System SHALL 优化Monaco编辑器的初始化性能
6. THE System SHALL 实现搜索结果的虚拟滚动（如需要）

### Requirement 15: 兼容性和集成

**User Story:** 作为开发者，我希望迁移后的功能能够与现有系统无缝集成，不影响现有功能。

#### Acceptance Criteria

1. THE System SHALL 确保现有工具的功能不受影响
2. THE System SHALL 确保现有API路由不受影响
3. THE System SHALL 确保现有前端路由不受影响
4. THE System SHALL 使用统一的认证系统（如果现有系统已有）
5. THE System SHALL 遵循现有的代码规范和架构模式
6. THE System SHALL 确保依赖包不冲突
7. THE System SHALL 确保构建和部署流程兼容
