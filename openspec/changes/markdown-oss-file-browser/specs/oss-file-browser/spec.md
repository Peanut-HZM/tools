## ADDED Requirements

### Requirement: Sidebar支持存储源切换
侧边栏 SHALL 支持在本地文件系统和阿里云OSS之间切换显示。

#### Scenario: 用户切换标签页
- **WHEN** 用户点击"OSS文件"标签
- **THEN** 侧边栏显示阿里云OSS文件列表
- **AND** "OSS文件"标签变为激活状态

#### Scenario: 默认显示本地文件
- **WHEN** 用户打开Markdown编辑器
- **THEN** 默认显示"本地文件"标签页
- **AND** 显示本地文件树

### Requirement: OSS文件列表展示
系统 SHALL 在OSS文件标签页显示当前用户上传到阿里云OSS的所有Markdown文件。

#### Scenario: 显示OSS文件列表
- **GIVEN** 用户已登录且有OSS文件
- **WHEN** 用户切换到OSS文件标签
- **THEN** 系统显示文件列表
- **AND** 每个文件显示文件名、大小和最后修改时间
- **AND** 文件按上传时间倒序排列（最新在前）

#### Scenario: 空状态显示
- **GIVEN** 用户没有OSS文件
- **WHEN** 用户切换到OSS文件标签
- **THEN** 显示空状态提示"暂无云端文件"
- **AND** 提供上传按钮

#### Scenario: 加载状态
- **WHEN** 系统正在获取OSS文件列表
- **THEN** 显示加载动画
- **AND** 禁用文件列表交互

### Requirement: OSS文件列表刷新
用户 SHALL 能够手动刷新OSS文件列表。

#### Scenario: 点击刷新按钮
- **GIVEN** OSS文件列表已加载
- **WHEN** 用户点击刷新按钮
- **THEN** 系统重新获取最新文件列表
- **AND** 更新显示内容

### Requirement: UI主题适配
OSS文件浏览器组件 SHALL 支持现有的暗黑和亮色主题。

#### Scenario: 暗黑主题
- **GIVEN** 当前主题为暗黑模式
- **WHEN** 用户切换到OSS文件标签
- **THEN** 组件使用深色背景（bg-slate-800）
- **AND** 文字使用浅色（text-slate-300）

#### Scenario: 亮色主题
- **GIVEN** 当前主题为亮色模式
- **WHEN** 用户切换到OSS文件标签
- **THEN** 组件使用浅色背景
- **AND** 文字使用深色
