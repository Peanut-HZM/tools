## ADDED Requirements

### Requirement: API Key 默认脱敏显示
系统 SHALL 在配置列表中默认以脱敏形式显示 API Key，方便用户识别但不泄露完整 Key。

#### Scenario: 查看脱敏显示
- **WHEN** 用户查看配置列表
- **THEN** API Key 列显示格式为 "sk-xxx...abcd"（保留前3位和最后4位）

### Requirement: 用户可以切换显示完整 API Key
系统 SHALL 提供眼睛图标按钮，用户点击后可以切换显示/隐藏完整 API Key。

#### Scenario: 点击显示
- **WHEN** 用户点击 API Key 行的眼睛图标（睁开状态）
- **THEN** API Key 以明文形式显示，眼睛图标变为闭眼状态

#### Scenario: 点击隐藏
- **WHEN** 用户点击已显示的 API Key 的眼睛图标（闭眼状态）
- **THEN** API Key 恢复脱敏显示，眼睛图标变为睁开状态

### Requirement: 用户可以一键复制 API Key
系统 SHALL 提供复制按钮，用户点击后可以直接将 API Key 复制到剪贴板。

#### Scenario: 复制成功
- **WHEN** 用户点击复制按钮
- **THEN** 系统将完整 API Key 复制到剪贴板，显示成功提示"已复制到剪贴板"

#### Scenario: 复制失败
- **WHEN** 复制操作被浏览器阻止（如无权限）
- **THEN** 显示错误提示"复制失败，请手动复制"

### Requirement: 复制后显示安全提示
系统 SHALL 在用户复制 API Key 后显示安全提示。

#### Scenario: 显示安全提示
- **WHEN** 用户成功复制 API Key
- **THEN** 显示 Toast 提示"Key 已复制，请妥善保管，切勿泄露给他人"
