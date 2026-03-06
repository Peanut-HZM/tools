## Why

CrossShare 工具的消息页面存在 API 500 错误，用户输入消息后点击发送没有任何响应。控制台显示 `/api/cross-share/messages` 的 GET 和 POST 请求均返回 500 错误，导致消息无法加载和发送。

## What Changes

- **修复后端消息 API**: 解决 `/api/cross-share/messages` 接口的 500 错误
- **修复消息类型枚举处理**: 确保 `MessageType` 枚举在查询和创建时正确处理
- **添加错误日志和边界处理**: 增强服务层的错误处理和日志记录
- **前端优化错误提示**: 添加 Toast 提示让用户了解错误信息

## Capabilities

### New Capabilities

无新能力，仅修复现有功能的 Bug。

### Modified Capabilities

- `cross-share-message`: 修复消息加载和发送的 API 接口

## Impact

- 受影响文件:
  - `backend/app/routes/cross_share.py`: 修复消息 API 路由
  - `backend/app/services/cross_share_service.py`: 修复服务层逻辑和错误处理
  - `backend/app/schemas/cross_share.py`: 确保 MessageType 枚举序列化正确
  - `frontend/src/components/Tools/CrossShare/MessagePanel.tsx`: 添加错误提示
  - `frontend/src/services/crossShare.ts`: 优化 API 错误处理

- 用户体验影响:
  - 修复后用户可以正常发送和接收消息
  - 错误提示更友好
