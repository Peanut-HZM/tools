## Context

当前 CrossShare 工具的消息页面出现 500 错误，用户无法发送或加载消息。问题涉及前后端多个层面：

**当前状态:**
- 后端 API `/api/cross-share/messages` 返回 500 错误
- 前端 MessagePanel 组件没有错误提示，用户不知道发生了什么
- 服务层的 `get_messages` 和 `create_message` 方法可能存在枚举处理问题

**约束条件:**
- 使用 SQLite 数据库
- MessageType 枚举在创建消息时需要正确处理
- 前端使用 axios 调用 API，需要更好的错误处理

## Goals / Non-Goals

**Goals:**
- 修复后端消息 API 的 500 错误
- 确保消息类型枚举正确处理
- 前端添加错误提示让用户知晓问题
- 添加服务层日志便于调试

**Non-Goals:**
- 不修改数据库 schema
- 不改变现有的消息存储结构
- 不添加新功能，仅修复现有 Bug

## Decisions

### Decision 1: 修复消息类型枚举处理

**选择:** 在 `create_message` 方法中将枚举转换为字符串

**理由:**
- 数据库存储的是字符串类型
- Pydantic 模型在序列化时需要 `.value` 获取枚举值
- 现有代码已经尝试处理但未完全正确

**替代方案:**
- 修改数据库字段为枚举类型（rejected: 需要迁移，SQLite 不支持）
- 完全移除枚举处理（rejected: 失去类型安全）

### Decision 2: 添加服务层日志

**选择:** 在关键操作前后添加详细日志

**理由:**
- 便于定位问题
- 不影响性能
- Python logging 是标准做法

### Decision 3: 前端优化错误提示

**选择:** 使用现有的 Toast 组件显示错误

**理由:**
- 保持 UI 一致性
- 用户友好
- 现有组件可直接复用

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 枚举值不匹配导致数据库错误 | 在 service 层统一转换为字符串 |
| 前端错误处理不足 | 添加 try-catch 和 Toast 提示 |
| 日志过多影响性能 | 使用 DEBUG 级别，生产环境可配置 |

## Migration Plan

**部署步骤:**
1. 停止后端服务
2. 更新 `cross_share_service.py` 和 `cross_share.py`
3. 更新前端 `MessagePanel.tsx`
4. 重启后端和前端服务

**回滚策略:**
- Git 回滚代码到修复前版本

## Open Questions

无
