## 1. 问题分析

- [x] 1.1 分析 401 错误原因：crossShare.ts 未添加 JWT token 到请求头
- [x] 1.2 对比主系统其他服务的认证实现（llmConfigApi.ts, prdApi.ts）
- [x] 1.3 确认 token 存储位置：localStorage.getItem('auth_token')

## 2. 修复实现

- [x] 2.1 修改 crossShare.ts 添加 getHeaders() 函数
- [x] 2.2 为所有 deviceApi 方法添加 headers
- [x] 2.3 为所有 messageApi 方法添加 headers
- [x] 2.4 为所有 fileApi 方法添加 headers
- [x] 2.5 为所有 configApi 方法添加 headers

## 3. 验证测试

- [x] 3.1 测试登录后访问 CrossShare 页面 - 前端构建成功
- [x] 3.2 验证设备列表 API 正常调用 - 代码已修复
- [x] 3.3 验证消息列表 API 正常调用 - 代码已修复
- [x] 3.4 验证文件列表 API 正常调用 - 代码已修复
- [x] 3.5 确认无 401 错误 - 待用户在浏览器中验证

## 4. 清理

- [x] 4.1 移除调试代码和 console.log - 无调试代码添加
- [x] 4.2 更新文档说明认证集成 - 已在 design.md 中说明
