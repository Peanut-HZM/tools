# Auth Token Integration Spec

## Requirement

所有 CrossShare API 请求必须携带有效的 JWT token，格式为 `Authorization: Bearer <token>`。

## Implementation

### Token Source

Token 从 `localStorage.getItem('auth_token')` 获取，与主系统保持一致。

### Headers Format

所有 API 请求必须包含以下 headers：
```
Authorization: Bearer <token>
Content-Type: application/json
```

### Affected APIs

所有 `crossShare.ts` 中的 API 方法：
- Device APIs: `getDevices`, `registerDevice`, `updateDevice`, `deleteDevice`, `pingDevice`
- Message APIs: `getMessages`, `sendMessage`, `updateMessage`, `deleteMessage`, `markMessageRead`, `getClipboardHistory`, `syncClipboard`
- File APIs: `getFiles`, `getFile`, `getUploadToken`, `deleteFile`, `updateFile`, `getDownloadUrl`, `getStorageStats`, `uploadToOSS`
- Config APIs: `getConfig`, `updateConfig`

## Error Handling

- 如果 token 不存在：请求仍发送，后端返回 401
- 如果 token 过期：后端返回 401，前端拦截器可处理跳转到登录页
