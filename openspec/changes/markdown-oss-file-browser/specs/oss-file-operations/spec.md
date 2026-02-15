## ADDED Requirements

### Requirement: 从OSS打开文件
用户 SHALL 能够点击OSS文件在编辑器中打开。

#### Scenario: 打开OSS文件
- **GIVEN** OSS文件列表已显示
- **WHEN** 用户点击某个文件
- **THEN** 系统从OSS读取文件内容
- **AND** 在编辑器中加载内容
- **AND** 状态栏显示"OSS: 文件名"
- **AND** 编辑器显示OSS文件指示器

#### Scenario: 打开文件时编辑器有未保存内容
- **GIVEN** 当前编辑器有未保存的修改
- **WHEN** 用户尝试打开另一个OSS文件
- **THEN** 系统提示用户是否保存当前文件
- **AND** 如果用户选择保存，先保存再打开新文件

#### Scenario: 文件读取失败
- **GIVEN** 用户点击OSS文件
- **WHEN** 文件读取请求失败
- **THEN** 显示错误提示"无法读取文件"
- **AND** 保持编辑器当前内容不变

### Requirement: 上传文件到OSS
用户 SHALL 能够将本地Markdown文件上传到阿里云OSS。

#### Scenario: 通过按钮上传
- **GIVEN** 用户在OSS文件标签页
- **WHEN** 用户点击"上传文件"按钮
- **AND** 选择本地Markdown文件
- **THEN** 系统上传文件到OSS
- **AND** 成功后刷新文件列表
- **AND** 自动打开上传的文件
- **AND** 显示成功提示"文件上传成功"

#### Scenario: 拖拽上传
- **GIVEN** 用户在OSS文件标签页或编辑器区域
- **WHEN** 用户拖拽Markdown文件到上传区域
- **THEN** 系统上传文件到OSS
- **AND** 成功后刷新文件列表
- **AND** 自动打开上传的文件

#### Scenario: 上传非Markdown文件
- **WHEN** 用户尝试上传非.md/.markdown文件
- **THEN** 显示错误提示"仅支持Markdown文件"
- **AND** 取消上传操作

#### Scenario: 上传失败
- **GIVEN** 用户选择文件上传
- **WHEN** 上传请求失败
- **THEN** 显示错误提示"上传失败: [错误信息]"
- **AND** 文件列表不更新

### Requirement: 保存OSS文件
用户 SHALL 能够编辑并保存OSS文件。

#### Scenario: 保存修改到OSS
- **GIVEN** 当前打开的是OSS文件
- **AND** 用户做了修改
- **WHEN** 用户按下Ctrl+S或点击保存按钮
- **THEN** 系统将修改保存到OSS
- **AND** 显示保存成功状态

#### Scenario: OSS文件自动保存
- **GIVEN** 当前打开的是OSS文件
- **AND** 自动保存功能已启用
- **WHEN** 用户在配置的时间间隔内无操作
- **THEN** 系统自动将修改保存到OSS
