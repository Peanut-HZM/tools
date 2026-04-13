# 小程序认证守卫与页面跳转优化设计

## 目标

为小程序添加统一的认证守卫机制，确保未登录用户访问受保护页面时被引导到登录页，登录成功后自动返回。同时修复 401 错误后的用户体验问题。

## 方案

使用自定义 Hook `useAuthGuard` 实现认证守卫，在需要登录的页面中调用。

## 架构设计

### 新增文件

- `src/hooks/useAuthGuard.ts` — 统一的认证守卫 Hook
- `src/hooks/index.ts` — Hook 统一导出

### 修改文件

| 文件 | 改动 |
|------|------|
| `src/services/request.ts` | 401 后自动引导到登录页 |
| `src/pages/login/index.tsx` | 支持 `redirect` 参数，登录后返回 |
| `src/pages/change-password/index.tsx` | 修改密码后调用 `logout()` |
| `src/pages/cross-share/message/index.tsx` | 添加认证守卫 |
| `src/pages/cross-share/file/index.tsx` | 添加认证守卫 |

### 不修改的页面

| 页面 | 原因 |
|------|------|
| `/pages/index/index` | TabBar 首页，匿名可访问 |
| `/pages/profile/index` | TabBar 页面，已有 `isAuthenticated` 判断 |
| `/pages/json-formatter/index` | 纯前端工具，不需要登录 |
| `/pages/help/index` | 帮助页面，匿名可访问 |

## 数据流

```
用户访问受保护页面
  → useAuthGuard 检查 isAuthenticated && Storage 中有 token
    → 未登录 → redirectTo /pages/login/index?redirect=/pages/xxx
    → 已登录 → 正常渲染

用户在受保护页面操作
  → API 返回 401
    → request.ts 清除 Storage + showToast
    → 1.5秒后 redirectTo 登录页（带 redirect 参数）

登录成功
  → 检查 redirect 参数
    → 有 → navigateBack 或 redirectTo 返回原页面
    → 无 → 按现有逻辑处理
```

## 需要登录的页面

- `/pages/cross-share/message/index` — 消息
- `/pages/cross-share/file/index` — 文件
- `/pages/change-password/index` — 修改密码

## 不需要登录的页面

- `/pages/index/index` — 工具首页
- `/pages/profile/index` — 我的（已有判断）
- `/pages/json-formatter/index` — JSON 格式化
- `/pages/help/index` — 帮助
- `/pages/ocr/index` — OCR
- `/pages/asr/index` — ASR
- `/pages/http-client/index` — HTTP 客户端
