## ADDED Requirements

### Requirement: 显示 API Key 创建时间
系统 SHALL 在配置详情中显示该 API Key 的创建时间。

#### Scenario: 查看创建时间
- **WHEN** 用户查看配置详情或列表
- **THEN** 显示"创建时间：2024-01-15 10:30:00"

### Requirement: 支持配置备注
系统 SHALL 允许用户为每个 API Key 配置添加备注，方便识别和管理。

#### Scenario: 添加备注
- **WHEN** 用户在编辑配置时填写备注字段
- **THEN** 备注信息保存后显示在配置列表中

#### Scenario: 查看备注
- **WHEN** 用户将鼠标悬停在备注图标上
- **THEN** 显示备注的完整内容

### Requirement: 显示 API Key 识别信息
系统 SHALL 显示 API Key 的后几位，方便用户在多个 Key 中识别。

#### Scenario: 显示后缀
- **WHEN** 用户查看配置列表
- **THEN** API Key 列显示格式为 "...abcd"（最后4位）

### Requirement: 支持切换默认配置
系统 SHALL 允许用户将某个配置设为默认，未指定时使用默认配置。

#### Scenario: 设为默认
- **WHEN** 用户点击"设为默认"按钮
- **THEN** 系统将该配置设为默认，其他配置取消默认状态

#### Scenario: 查看默认标识
- **WHEN** 用户查看配置列表
- **THEN** 默认配置显示"默认"标签
