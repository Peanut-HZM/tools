## Context

用户已登录状态下，设备传传（CrossShare）页面的所有 API 请求返回 401 未授权错误。

**现状分析：**
1. 主系统认证：token 存储在 `localStorage.getItem('auth_token')`
2. 主系统服务（如 `llmConfigApi.ts`, `prdApi.ts`）都有统一的 `getHeaders()` 方法添加 Bearer token
3. `crossShare.ts` 服务直接使用 axios 调用，**没有添加 Authorization 头**
4. 后端 `cross_share.py` 的 `get_current_user_id()` 依赖明确要求 `Authorization: Bearer <token>` 头

**约束：**
- 必须与主系统认证逻辑保持一致
- 不能破坏现有功能
- 修复应该简单、可维护

## Goals / Non-Goals

**Goals:**
- 为 CrossShare 所有 API 请求自动添加 JWT token
- 使用主系统统一的 token 存储和获取方式
- 修复 401 错误，使已登录用户能正常使用 CrossShare

**Non-Goals:**
- 不改变后端认证逻辑
- 不引入新的认证流程
- 不修改 token 存储机制

## Decisions

### Decision 1: 使用 axios interceptors 统一添加 token

**选择：** 使用 axios 请求拦截器（interceptors）为所有 CrossShare API 请求自动添加 `Authorization: BBearer <token>` 头

**理由：**
1. **代码复用**：拦截器只需定义一次，所有 API 自动受益
2. **统一维护**：认证逻辑集中管理，易于修改和调试
3. **与主系统一致**：主系统其他服务也采用类似模式

** alternatives considered：**
- 方案 A：每个 API 方法手动添加 headers - ❌ 代码重复，易遗漏
- 方案 B：创建封装函数 - ❌ 增加调用复杂度
- 方案 C：axios interceptor - ✅ 最优选择

### Decision 2: Token 来源使用主系统的 `auth_token`

**选择：** 从 `localStorage.getItem('auth_token')` 获取 token

**理由：**
1. 与主系统登录流程统一
2. 用户只需登录一次，所有功能共享认证状态
3. 无需修改现有登录逻辑

## Risks / Trade-offs

**[Risk]** 如果 `auth_token` 不存在或过期，所有请求失败
→ **Mitigation:** 拦截器中检测 401 响应，重定向到登录页

**[Risk]** 拦截器可能影响性能
→ **Mitigation:** 拦截器逻辑简单，仅读取 localStorage，性能影响可忽略

**[Trade-off]** 使用拦截器 vs 封装函数
→ 选择拦截器因为更透明、易维护，但调试时可能不如显式调用清晰

## Migration Plan

1. 修改 `frontend/src/services/crossShare.ts`
   - 添加 `getHeaders()` 函数
   - 为所有 API 方法添加 `headers` 参数
2. 测试登录后的 CrossShare 功能
3. 验证 401 错误消失

无需后端修改，无回滚需求（修复是纯前端且可立即验证）

## Open Questions

无
