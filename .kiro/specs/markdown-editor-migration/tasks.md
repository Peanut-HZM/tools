# Implementation Plan: Markdown Editor Migration

## Overview

本实现计划将 markdown-editor 项目的前后端功能完整迁移到 tool-aggregation-website 的 backend 和 frontend 中。迁移过程包括：1) 后端API迁移和认证系统实现，2) 前端组件从Vue转换为React，3) 用户认证和登录系统集成，4) 工具卡片集成，5) 功能测试和验证。整个实现过程分为后端开发和前端开发两条并行线，最终集成为完整应用。

## Tasks

- [x] 1. 项目准备和环境配置


  - 分析markdown-editor项目结构和依赖
  - 确认backend和frontend的现有架构
  - 规划API路由和组件结构
  - 创建迁移计划文档
  - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

- [x] 2. 后端认证系统实现



  - [x] 2.1 创建认证数据模型

    - 在models/auth_models.py中定义User、LoginRequest、RegisterRequest等Pydantic模型
    - 定义JWT令牌相关模型
    - _Requirements: 4.1, 4.2, 4.3, 4.4_


  - [x] 2.2 实现认证服务

    - 在services/auth_service.py中实现用户注册、登录、登出功能
    - 实现JWT令牌生成和验证
    - 实现密码加密和验证（passlib）
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_


  - [x] 2.3 实现认证API路由

    - 在api/auth.py中实现POST /api/auth/register端点
    - 实现POST /api/auth/login端点
    - 实现POST /api/auth/logout端点
    - 实现GET /api/auth/me端点
    - _Requirements: 4.1, 4.2, 4.3, 4.4_


  - [x] 2.4 实现认证中间件

    - 在middleware/auth_middleware.py中实现JWT认证中间件
    - 实现用户身份提取和验证
    - 实现令牌过期处理
    - _Requirements: 4.5, 4.9_


  - [x] 2.5 集成认证系统到main.py

    - 在main.py中注册认证路由
    - 配置JWT密钥和过期时间
    - 配置CORS支持认证头
    - _Requirements: 4.5, 4.9_

- [x] 3. 后端文件服务迁移



  - [x] 3.1 创建文件数据模型

    - 在models/file_models.py中定义FileNode、FileContent、SaveRequest等模型
    - 迁移markdown-editor的文件模型定义
    - _Requirements: 2.1, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9_


  - [x] 3.2 实现文件服务（支持用户隔离）

    - 在services/file_service.py中实现文件操作服务
    - 实现基于用户ID的文件存储隔离
    - 实现路径遍历防护
    - 实现目录树获取、文件读取、保存、创建、删除、重命名等功能
    - _Requirements: 2.2, 2.6, 2.7, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_


  - [x] 3.3 实现文件API路由

    - 在api/markdown_editor.py中实现文件操作API端点
    - 使用/api/markdown-editor前缀
    - 集成认证中间件验证用户身份
    - 实现GET /api/markdown-editor/files/root端点
    - 实现POST /api/markdown-editor/files/root端点
    - 实现GET /api/markdown-editor/files/tree端点
    - 实现GET /api/markdown-editor/files/read端点
    - 实现POST /api/markdown-editor/files/save端点
    - 实现POST /api/markdown-editor/files/create端点
    - 实现DELETE /api/markdown-editor/files/delete端点
    - 实现POST /api/markdown-editor/files/rename端点
    - 实现POST /api/markdown-editor/files/directory/create端点
    - 实现DELETE /api/markdown-editor/files/directory/delete端点
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9_

- [x] 4. 后端配置服务迁移




  - [x] 4.1 创建配置数据模型

    - 在models/config_models.py中定义EditorConfig模型
    - 迁移markdown-editor的配置模型定义
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9_


  - [x] 4.2 实现配置服务（支持用户隔离）

    - 在services/config_service.py中实现配置管理服务
    - 实现基于用户ID的配置存储隔离
    - 实现配置加载和保存功能
    - _Requirements: 2.2, 2.7, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9_


  - [x] 4.3 实现配置API路由

    - 在api/markdown_editor.py中实现配置API端点
    - 实现GET /api/markdown-editor/config端点
    - 实现POST /api/markdown-editor/config端点
    - 集成认证中间件验证用户身份
    - _Requirements: 2.1, 2.2, 2.4, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9_

- [x] 5. 后端搜索服务迁移



  - [x] 5.1 创建搜索数据模型

    - 在models/search_models.py中定义FileSearchResult、ContentSearchResult等模型
    - 迁移markdown-editor的搜索模型定义
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [x] 5.2 实现搜索服务（支持用户隔离）


    - 在services/search_service.py中实现搜索功能
    - 实现基于用户ID的文件搜索范围限制
    - 实现文件名搜索和内容搜索
    - 实现正则表达式搜索和大小写敏感搜索
    - _Requirements: 2.2, 2.7, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_



  - [x] 5.3 实现搜索API路由
    - 在api/markdown_editor.py中实现搜索API端点
    - 实现GET /api/markdown-editor/search/files端点
    - 实现GET /api/markdown-editor/search/content端点
    - 集成认证中间件验证用户身份
    - _Requirements: 2.1, 2.2, 2.4, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

- [x] 6. 后端工具和路径验证


  - [x] 6.1 实现路径工具函数


    - 在utils/path_utils.py中实现路径验证和规范化函数
    - 实现路径遍历攻击防护
    - 实现用户目录路径构建函数
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_


  - [x] 6.2 编写后端单元测试


    - 测试认证API端点
    - 测试文件操作API端点
    - 测试配置API端点
    - 测试搜索API端点
    - 测试路径验证和用户隔离
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 6.1, 6.2_

- [x] 7. 前端认证系统实现



  - [x] 7.1 创建认证API客户端

    - 在api/authApi.ts中实现认证API调用函数
    - 实现登录、注册、登出、获取用户信息等API调用
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 7.2 创建认证状态管理Store


    - 在stores/authStore.ts中使用Zustand实现认证状态管理
    - 管理用户信息、登录状态、JWT令牌
    - 实现登录、注册、登出方法
    - 实现令牌持久化（localStorage）
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6, 4.7, 4.8_


  - [x] 7.3 创建认证组件

    - 在components/Auth/LoginForm.tsx中实现登录表单组件
    - 在components/Auth/RegisterForm.tsx中实现注册表单组件
    - 在components/Auth/AuthGuard.tsx中实现路由守卫组件
    - _Requirements: 4.1, 4.2, 4.3, 4.6, 4.7_


  - [x] 7.4 集成认证到Header组件

    - 修改components/Header/Header.tsx，集成登录状态显示
    - 修改components/Header/LoginButton.tsx，实现登录/登出功能
    - 显示用户信息和登出按钮
    - _Requirements: 4.7, 4.8_


  - [x] 7.5 实现认证路由保护


    - 在routes中实现Markdown编辑器路由保护
    - 使用AuthGuard组件保护需要登录的路由
    - 实现未登录时跳转到登录页面
    - _Requirements: 4.6, 4.7_


- [x] 8. 前端Markdown编辑器API客户端



  - [x] 8.1 创建Markdown编辑器API客户端

    - 在api/markdownEditorApi.ts中实现所有Markdown编辑器API调用
    - 实现文件操作API调用（获取目录树、读取文件、保存文件等）
    - 实现配置API调用（获取配置、保存配置）
    - 实现搜索API调用（文件搜索、内容搜索）
    - 在API请求中自动添加JWT令牌
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3_


  - [x] 8.2 创建TypeScript类型定义

    - 在types/markdownEditor.ts中定义所有Markdown编辑器相关的TypeScript类型
    - 定义文件模型、配置模型、搜索模型等类型
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3_

- [x] 9. 前端状态管理Store迁移



  - [x] 9.1 创建文件状态管理Store

    - 在stores/fileStore.ts中使用Zustand实现文件状态管理
    - 管理根路径、当前文件、目录树等状态
    - 实现文件操作方法（打开、保存、创建、删除等）
    - 迁移markdown-editor的fileStore功能
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11_


  - [x] 9.2 创建编辑器状态管理Store

    - 在stores/editorStore.ts中使用Zustand实现编辑器状态管理
    - 管理编辑器内容、光标位置、保存状态等
    - 迁移markdown-editor的editorStore功能
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 5.10, 5.11_

  - [x] 9.3 创建配置状态管理Store


    - 在stores/configStore.ts中使用Zustand实现配置状态管理
    - 管理编辑器配置、预览配置等
    - 实现配置加载和保存方法
    - 迁移markdown-editor的configStore功能
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10_

- [x] 10. 前端组件迁移（Vue到React）



  - [x] 10.1 创建FileTree组件

    - 在components/MarkdownEditor/FileTree/FileTree.tsx中实现文件树组件
    - 将Vue的FileTree.vue转换为React组件
    - 实现树形结构展示、文件选择等功能
    - _Requirements: 3.1, 5.1, 5.2, 5.3_


  - [x] 10.2 创建Editor组件

    - 在components/MarkdownEditor/Editor/Editor.tsx中实现Monaco编辑器组件
    - 将Vue的Editor.vue转换为React组件
    - 集成Monaco Editor，实现语法高亮、快捷键等功能
    - 实现编辑器配置更新监听
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10_

  - [x] 10.3 创建Preview组件


    - 在components/MarkdownEditor/Preview/Preview.tsx中实现Markdown预览组件
    - 将Vue的Preview.vue转换为React组件
    - 集成markdown-it、highlight.js、KaTeX、Mermaid等库
    - 实现TOC生成和导航
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10_


  - [x] 10.4 创建SearchDialog组件

    - 在components/MarkdownEditor/SearchDialog/SearchDialog.tsx中实现搜索对话框组件
    - 将Vue的SearchDialog.vue转换为React组件
    - 实现文件搜索和内容搜索功能
    - 实现搜索结果展示和文件跳转
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [x] 10.5 创建SettingsDialog组件


    - 在components/MarkdownEditor/SettingsDialog/SettingsDialog.tsx中实现设置对话框组件
    - 将Vue的SettingsDialog.vue转换为React组件
    - 实现编辑器配置和预览配置的UI
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10_


  - [x] 10.6 创建StatusBar组件

    - 在components/MarkdownEditor/StatusBar/StatusBar.tsx中实现状态栏组件
    - 显示文件路径、光标位置、保存状态等信息
    - _Requirements: 5.10, 6.9_


  - [x] 10.7 创建MarkdownEditor主组件

    - 在components/MarkdownEditor/MarkdownEditor.tsx中实现主容器组件
    - 整合FileTree、Editor、Preview等子组件
    - 实现布局管理（侧边栏、编辑器、预览区域）
    - 实现编辑模式和查看模式切换
    - 实现响应式布局和可调整面板
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

- [x] 11. 前端Hooks实现



  - [x] 11.1 实现useAutoSave Hook

    - 在hooks/useAutoSave.ts中实现自动保存功能
    - 实现防抖处理和可配置的保存间隔
    - 迁移markdown-editor的useAutoSave功能
    - _Requirements: 5.11, 14.2_



  - [x] 11.2 实现useFileTree Hook
    - 在hooks/useFileTree.ts中实现文件树相关逻辑
    - 管理文件树状态和操作
    - _Requirements: 5.1, 5.2, 5.3_



  - [x] 11.3 实现useMarkdownPreview Hook
    - 在hooks/useMarkdownPreview.ts中实现Markdown预览相关逻辑
    - 处理Markdown渲染和TOC生成
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9_

- [x] 12. 前端路由和工具卡片集成



  - [x] 12.1 创建Markdown编辑器路由

    - 在routes/MarkdownEditorRoute.tsx中创建路由组件
    - 使用AuthGuard保护路由
    - 集成MarkdownEditor主组件
    - _Requirements: 1.3, 1.4, 4.6, 4.7_


  - [x] 12.2 添加工具卡片到首页

    - 在backend/app/data/tools_data.py中添加Markdown编辑器工具数据
    - 确保工具卡片显示在首页工具列表中

    - _Requirements: 1.1, 1.2_


  - [x] 12.3 实现工具卡片点击跳转
    - 在frontend中实现工具卡片点击事件处理
    - 导航到Markdown编辑器路由
    - _Requirements: 1.3, 1.4_


  - [x] 12.4 验证现有工具不受影响


    - 测试所有现有工具的功能
    - 确保路由和API不受影响
    - _Requirements: 1.5, 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

- [x] 13. 国际化支持

  - [x] 13.1 创建国际化配置文件


    - 创建i18n配置文件，支持中文和英文
    - 迁移markdown-editor的国际化文本
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_


  - [x] 13.2 集成国际化到组件


    - 在所有组件中使用国际化文本
    - 实现语言切换功能
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_


- [x] 14. 错误处理和用户体验优化
  - [x] 14.1 实现错误处理


    - 实现API错误处理（网络错误、认证错误、文件操作错误等）
    - 显示用户友好的错误消息

    - 实现错误恢复机制
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

  - [x] 14.2 实现加载状态


    - 在文件操作、API调用等场景显示加载状态
    - 提升用户体验

    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

  - [x] 14.3 实现用户反馈


    - 使用Toast/Message组件显示操作成功/失败提示

    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

- [x] 15. 性能优化
  - [x] 15.1 实现组件懒加载

    - 使用React.lazy加载Markdown编辑器组件
    - 使用Suspense处理加载状态
    - _Requirements: 14.4_


  - [x] 15.2 优化编辑器性能


    - 优化Monaco编辑器初始化
    - 实现大文件的虚拟滚动（如需要）
    - _Requirements: 14.1, 14.3_


  - [x] 15.3 优化自动保存性能


    - 优化防抖处理
    - 减少不必要的保存操作
    - _Requirements: 14.2_

- [x] 16. 样式和主题适配
  - [x] 16.1 适配Tailwind CSS样式


    - 将markdown-editor的样式转换为Tailwind CSS

    - 保持与现有网站风格一致
    - _Requirements: 3.8_

  - [x] 16.2 实现主题切换


    - 支持亮色/暗色主题切换
    - 与现有网站主题系统集成
    - _Requirements: 6.8, 7.8, 9.1_

- [x] 17. 测试和验证
  - [x] 17.1 编写前端单元测试

    - 测试组件渲染和交互
    - 测试状态管理
    - 测试API调用
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 9.1, 9.2, 9.3, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 11.1, 11.2, 11.3_


  - [x] 17.2 编写集成测试


    - 测试前后端API交互
    - 测试认证流程
    - 测试文件操作流程
    - 测试用户隔离
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 6.1, 6.2, 7.1, 7.2, 7.3, 7.4, 7.5, 12.1, 12.2, 12.3_


  - [x] 17.3 功能完整性验证


    - 验证所有markdown-editor功能都已迁移
    - 验证登录认证功能正常
    - 验证文件操作功能正常
    - 验证编辑器功能正常
    - 验证预览功能正常
    - 验证搜索功能正常
    - 验证配置功能正常

    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10, 10.1, 10.2, 10.3, 10.4, 10.5, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

  - [x] 17.4 兼容性验证


    - 验证现有工具功能不受影响
    - 验证现有API路由不受影响
    - 验证现有前端路由不受影响

    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

- [x] 18. 文档和部署
  - [x] 18.1 更新项目README



    - 添加Markdown编辑器工具说明

    - 添加认证系统说明
    - 添加API文档链接
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 18.2 创建部署文档

    - 添加用户数据存储配置说明
    - 添加JWT密钥配置说明
    - 添加环境变量配置说明
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 4.5, 4.9_

  - [x] 18.3 最终验证

    - 验证所有功能与markdown-editor原项目100%一致
    - 验证认证系统正常工作
    - 验证用户隔离正常工作
    - 验证现有功能不受影响
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10, 10.1, 10.2, 10.3, 10.4, 10.5, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

## Notes

- 任务标记为`*`的是可选任务，可以跳过以加快MVP开发
- 每个任务都引用了具体的需求编号，确保可追溯性
- 迁移过程需要确保功能完整性和代码质量
- Vue到React的转换需要仔细处理组件生命周期和状态管理
- 认证系统的实现需要确保安全性和用户体验
- 用户隔离是核心安全要求，必须严格实现
- 所有任务状态初始为未完成，后续开发完成后再标记
