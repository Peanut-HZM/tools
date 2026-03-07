# 用户认证 API 规格

## 概述

实现完整的 JWT 用户认证系统，支持注册、登录、token 管理。

## API 端点

### POST /api/auth/register

**请求体:**
```json
{
  "username": "string (3-50 字符)",
  "email": "string (有效邮箱格式)",
  "password": "string (8-128 字符)"
}
```

**成功响应 (201):**
```json
{
  "user": {
    "id": "string",
    "username": "string",
    "email": "string",
    "created_at": "datetime"
  },
  "token": "string",
  "expires_at": "datetime"
}
```

**错误响应:**
- 400: 无效输入
- 409: 用户名或邮箱已存在

### POST /api/auth/login

**请求体:**
```json
{
  "username": "string",
  "password": "string"
}
```

**成功响应 (200):**
```json
{
  "user": {
    "id": "string",
    "username": "string",
    "email": "string"
  },
  "token": "string",
  "expires_at": "datetime"
}
```

**错误响应:**
- 401: 用户名或密码错误

### GET /api/auth/me

**请求头:** `Authorization: Bearer <token>`

**成功响应 (200):**
```json
{
  "id": "string",
  "username": "string",
  "email": "string",
  "is_active": true
}
```

**错误响应:**
- 401: token 无效或过期

### POST /api/auth/refresh

**请求头:** `Authorization: Bearer <token>`

**成功响应 (200):**
```json
{
  "token": "string",
  "expires_at": "datetime"
}
```

## JWT Token 格式

- 算法：HS256
- 有效期：7 天 (10080 分钟)
- Payload:
  - `sub`: 用户 ID
  - `exp`: 过期时间
  - `iat`: 签发时间
