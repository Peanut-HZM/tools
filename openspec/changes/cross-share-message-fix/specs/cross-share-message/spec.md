## ADDED Requirements

### Requirement: 消息 API 错误处理
系统 SHALL 正确处理消息加载和发送 API 请求，返回适当的错误信息。

#### Scenario: 加载消息列表成功
- **WHEN** 用户打开消息页面
- **AND** 后端 API 正常工作
- **THEN** 系统显示消息列表
- **AND** 消息按创建时间倒序排列

#### Scenario: 加载消息列表失败
- **WHEN** 后端 API 返回错误
- **THEN** 系统显示错误提示"加载消息失败"
- **AND** 控制台输出详细错误日志

#### Scenario: 发送消息成功
- **WHEN** 用户输入消息内容
- **AND** 点击发送按钮
- **AND** 后端 API 正常工作
- **THEN** 消息被发送到服务器
- **AND** 消息列表自动刷新
- **AND** 输入框清空

#### Scenario: 发送消息失败 - 空内容
- **WHEN** 用户输入空内容或仅空格
- **THEN** 发送按钮禁用
- **AND** 消息不被发送

#### Scenario: 发送消息失败 - API 错误
- **WHEN** 后端 API 返回错误
- **THEN** 系统显示错误提示"发送失败：[错误信息]"
- **AND** 输入框保留原内容
- **AND** 发送按钮恢复可用状态

## MODIFIED Requirements

### Requirement: 消息类型枚举处理
后端 SHALL 正确处理 MessageType 枚举在创建和查询时的转换。

#### Scenario: 创建 text 类型消息
- **WHEN** 用户发送文本消息
- **THEN** 消息类型存储为"text"字符串
- **AND** 查询时正确返回 text 类型

#### Scenario: 创建 clipboard 类型消息
- **WHEN** 用户同步剪贴板
- **THEN** 消息类型存储为"clipboard"字符串
- **AND** 查询时正确返回 clipboard 类型

#### Scenario: 查询带类型的消息
- **WHEN** 请求消息列表时指定 message_type 参数
- **THEN** 系统返回指定类型的消息
- **AND** 枚举值正确匹配数据库存储
