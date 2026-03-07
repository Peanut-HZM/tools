# 消息和文件 CRUD API 规格

## 消息 API

### PUT /api/cross-share/messages/{message_id}

**请求体:**
```json
{
  "content": "string (可选，新的消息内容)",
  "message_type": "text|file|link|clipboard|image (可选)"
}
```

**成功响应 (200):**
```json
{
  "id": "string",
  "content": "string",
  "message_type": "string",
  "updated_at": "datetime"
}
```

**错误响应:**
- 403: 无权修改该消息
- 404: 消息不存在

### DELETE /api/cross-share/messages/{message_id}

**成功响应 (200):**
```json
{
  "message": "消息已删除"
}
```

**错误响应:**
- 403: 无权删除该消息
- 404: 消息不存在

## 文件 API

### PUT /api/cross-share/files/{file_id}

**请求体:**
```json
{
  "file_name": "string (可选，新的文件名)"
}
```

**成功响应 (200):**
```json
{
  "id": "string",
  "file_name": "string",
  "file_type": "string",
  "updated_at": "datetime"
}
```

**错误响应:**
- 403: 无权修改该文件
- 404: 文件不存在

### DELETE /api/cross-share/files/{file_id}

**成功响应 (200):**
```json
{
  "message": "文件已删除"
}
```

**错误响应:**
- 403: 无权删除该文件
- 404: 文件不存在

## 权限验证

所有 CRUD 操作必须验证：
1. 资源存在
2. 资源的 user_id 与当前登录用户匹配
