## Why

用户已登录状态下，设备传传（CrossShare）页面的所有 API 请求返回 401 未授权错误。原因是 `crossShare.ts` 服务没有将 JWT token 添加到请求头，与主系统认证逻辑不统一。

## What Changes

- 修改 `frontend/src/services/crossShare.ts`，为所有 API 请求添加 JWT token 请求头
- 使用主系统统一的 `getAuthToken()` 方法获取 token
- 添加 axios 请求拦截器或统一的 headers 配置，确保所有请求自动携带 token

## Capabilities

### New Capabilities

无 - 此变更是修复现有功能，不引入新能力

### Modified Capabilities

无 - 仅修复实现细节，不改变接口规范或行为要求

## Impact

- **前端**: `frontend/src/services/crossShare.ts` 需要修改
- **认证**: 使用主系统统一的 `localStorage.getItem('auth_token')` 存储
- **后端**: 无需修改，后端认证逻辑正确
