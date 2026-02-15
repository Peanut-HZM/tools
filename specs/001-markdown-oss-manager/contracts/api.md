# API Contracts: Markdown OSS 文件管理

**Base URL**: `/api/markdown-editor`  
**Authentication**: Bearer Token (JWT)  
**Content-Type**: `application/json`

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/oss/list` | 列出用户的 OSS 文件 |
| POST | `/oss/upload` | 上传文件到 OSS |
| GET | `/oss/read` | 读取 OSS 文件内容 |
| POST | `/oss/save` | 保存文件到 OSS |
| DELETE | `/oss/delete` | 删除 OSS 文件 |
| POST | `/oss/rename` | 重命名 OSS 文件 |
| POST | `/oss/directory/create` | 创建文件夹 |
| DELETE | `/oss/directory/delete` | 删除文件夹 |
| GET | `/oss/versions` | 列出文件版本历史 |
| GET | `/oss/versions/read` | 读取特定版本内容 |
| POST | `/oss/versions/rollback` | 回滚到特定版本 |
| DELETE | `/oss/versions/delete` | 删除特定版本 |

---

## File Operations

### 1. List OSS Files

**Endpoint**: `GET /oss/list`

**Description**: 获取当前用户存储在 OSS 中的所有 Markdown 文件列表。

**Request**:
```http
GET /api/markdown-editor/oss/list
Authorization: Bearer {jwt_token}
```

**Response** (200 OK):
```json
{
  "success": true,
  "files": [
    {
      "file_path": "markdown/user_123/docs/readme.md",
      "filename": "readme.md",
      "size": 1024,
      "last_modified": "2026-02-11T10:00:00Z",
      "storage_type": "oss"
    },
    {
      "file_path": "markdown/user_123/notes/meeting.md",
      "filename": "meeting.md",
      "size": 2048,
      "last_modified": "2026-02-11T12:30:00Z",
      "storage_type": "oss"
    }
  ],
  "total": 2
}
```

**Error Responses**:
- `401 Unauthorized`: 未提供认证令牌或令牌无效
- `503 Service Unavailable`: OSS 服务未配置

---

### 2. Upload File to OSS

**Endpoint**: `POST /oss/upload`

**Description**: 上传 Markdown 文件到 OSS。支持分块上传大文件。

**Request**:
```http
POST /api/markdown-editor/oss/upload
Authorization: Bearer {jwt_token}
Content-Type: multipart/form-data

Body:
- file: (binary) 文件内容
- path: (string, optional) 目标路径，默认为根目录
```

**Response** (200 OK):
```json
{
  "success": true,
  "file_path": "markdown/user_123/docs/uploaded.md",
  "filename": "uploaded.md",
  "url": "https://oss-cn-beijing.aliyuncs.com/...",
  "size": 1024,
  "message": "File uploaded successfully"
}
```

**Response** (202 Accepted - 分块上传):
```json
{
  "success": true,
  "upload_id": "upload_abc123",
  "file_path": "markdown/user_123/docs/large.md",
  "chunk_size": 1048576,
  "total_chunks": 15,
  "message": "Multipart upload initiated"
}
```

**Error Responses**:
- `400 Bad Request`: 文件类型不支持或文件过大
- `401 Unauthorized`: 未认证
- `409 Conflict`: 文件已存在（可选：覆盖确认）

---

### 3. Upload Chunk (分块上传)

**Endpoint**: `POST /oss/upload/chunk`

**Description**: 上传单个文件块（用于大文件分块上传）。

**Request**:
```http
POST /api/markdown-editor/oss/upload/chunk
Authorization: Bearer {jwt_token}
Content-Type: multipart/form-data

Body:
- upload_id: (string) 上传会话 ID
- chunk_index: (integer) 块索引（从 0 开始）
- chunk: (binary) 块内容
```

**Response** (200 OK):
```json
{
  "success": true,
  "upload_id": "upload_abc123",
  "chunk_index": 5,
  "completed_chunks": 6,
  "total_chunks": 15,
  "progress": 40
}
```

---

### 4. Complete Multipart Upload

**Endpoint**: `POST /oss/upload/complete`

**Description**: 完成分块上传，合并所有块。

**Request**:
```http
POST /api/markdown-editor/oss/upload/complete
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "upload_id": "upload_abc123",
  "file_path": "markdown/user_123/docs/large.md"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "file_path": "markdown/user_123/docs/large.md",
  "filename": "large.md",
  "url": "https://oss-cn-beijing.aliyuncs.com/...",
  "size": 15728640,
  "message": "Multipart upload completed"
}
```

---

### 5. Read OSS File

**Endpoint**: `GET /oss/read`

**Description**: 读取 OSS 中 Markdown 文件的内容。

**Request**:
```http
GET /api/markdown-editor/oss/read?file_path=markdown/user_123/docs/readme.md
Authorization: Bearer {jwt_token}
```

**Query Parameters**:
- `file_path` (required): 文件在 OSS 中的完整路径

**Response** (200 OK):
```json
{
  "success": true,
  "content": "# Hello World\n\nThis is markdown content...",
  "filename": "readme.md",
  "file_path": "markdown/user_123/docs/readme.md",
  "size": 1024,
  "last_modified": "2026-02-11T10:00:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: 缺少 file_path 参数
- `403 Forbidden`: 无权访问该文件（非本人文件）
- `404 Not Found`: 文件不存在

---

### 6. Save File to OSS

**Endpoint**: `POST /oss/save`

**Description**: 保存 Markdown 内容到 OSS，自动创建版本历史。

**Request**:
```http
POST /api/markdown-editor/oss/save
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "file_path": "markdown/user_123/docs/readme.md",
  "content": "# Updated Content\n\nNew markdown content...",
  "create_version": true
}
```

**Request Body**:
- `file_path` (required): 文件路径
- `content` (required): 文件内容
- `create_version` (optional, default: true): 是否创建版本历史

**Response** (200 OK):
```json
{
  "success": true,
  "file_path": "markdown/user_123/docs/readme.md",
  "version_id": "20260211143000_abc123",
  "size": 2048,
  "message": "File saved successfully"
}
```

**Error Responses**:
- `400 Bad Request`: 请求参数错误
- `403 Forbidden`: 无权修改该文件
- `409 Conflict`: 文件在离线期间被其他设备修改（返回冲突信息）

---

### 7. Delete OSS File

**Endpoint**: `DELETE /oss/delete`

**Description**: 删除 OSS 中的文件。

**Request**:
```http
DELETE /api/markdown-editor/oss/delete?file_path=markdown/user_123/docs/old.md
Authorization: Bearer {jwt_token}
```

**Response** (200 OK):
```json
{
  "success": true,
  "file_path": "markdown/user_123/docs/old.md",
  "message": "File deleted successfully"
}
```

---

### 8. Rename OSS File

**Endpoint**: `POST /oss/rename`

**Description**: 重命名 OSS 中的文件。

**Request**:
```http
POST /api/markdown-editor/oss/rename
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "old_path": "markdown/user_123/docs/old_name.md",
  "new_path": "markdown/user_123/docs/new_name.md"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "old_path": "markdown/user_123/docs/old_name.md",
  "new_path": "markdown/user_123/docs/new_name.md",
  "message": "File renamed successfully"
}
```

---

## Directory Operations

### 9. Create Directory

**Endpoint**: `POST /oss/directory/create`

**Description**: 在 OSS 中创建文件夹（实际为创建占位对象）。

**Request**:
```http
POST /api/markdown-editor/oss/directory/create
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "dir_path": "markdown/user_123/docs/new_folder"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "dir_path": "markdown/user_123/docs/new_folder",
  "message": "Directory created successfully"
}
```

---

### 10. Delete Directory

**Endpoint**: `DELETE /oss/directory/delete`

**Description**: 删除 OSS 中的文件夹。

**Request**:
```http
DELETE /api/markdown-editor/oss/directory/delete?dir_path=markdown/user_123/docs/old_folder&recursive=false
Authorization: Bearer {jwt_token}
```

**Query Parameters**:
- `dir_path` (required): 文件夹路径
- `recursive` (optional, default: false): 是否递归删除子内容

**Response** (200 OK):
```json
{
  "success": true,
  "dir_path": "markdown/user_123/docs/old_folder",
  "deleted_files": 5,
  "message": "Directory deleted successfully"
}
```

**Error Responses**:
- `400 Bad Request`: 文件夹不为空且 recursive=false

---

## Version History Operations

### 11. List File Versions

**Endpoint**: `GET /oss/versions`

**Description**: 获取指定文件的版本历史列表。

**Request**:
```http
GET /api/markdown-editor/oss/versions?file_path=markdown/user_123/docs/readme.md&limit=20&offset=0
Authorization: Bearer {jwt_token}
```

**Query Parameters**:
- `file_path` (required): 文件路径
- `limit` (optional, default: 20): 返回版本数量
- `offset` (optional, default: 0): 分页偏移

**Response** (200 OK):
```json
{
  "success": true,
  "file_path": "markdown/user_123/docs/readme.md",
  "versions": [
    {
      "version_id": "20260211143000_abc123",
      "version_number": 3,
      "created_at": "2026-02-11T14:30:00Z",
      "size": 2048,
      "content_preview": "# Updated Content\n\nNew markdown content..."
    },
    {
      "version_id": "20260211120000_def456",
      "version_number": 2,
      "created_at": "2026-02-11T12:00:00Z",
      "size": 1024,
      "content_preview": "# Hello World\n\nInitial content..."
    }
  ],
  "total": 3,
  "limit": 20,
  "offset": 0
}
```

---

### 12. Read Version Content

**Endpoint**: `GET /oss/versions/read`

**Description**: 读取特定版本的内容（用于预览）。

**Request**:
```http
GET /api/markdown-editor/oss/versions/read?file_path=markdown/user_123/docs/readme.md&version_id=20260211143000_abc123
Authorization: Bearer {jwt_token}
```

**Response** (200 OK):
```json
{
  "success": true,
  "version_id": "20260211143000_abc123",
  "file_path": "markdown/user_123/docs/readme.md",
  "content": "# Updated Content\n\nNew markdown content...",
  "created_at": "2026-02-11T14:30:00Z",
  "size": 2048
}
```

---

### 13. Rollback to Version

**Endpoint**: `POST /oss/versions/rollback`

**Description**: 回滚文件到指定版本（创建新版本，不删除旧版本）。

**Request**:
```http
POST /api/markdown-editor/oss/versions/rollback
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "file_path": "markdown/user_123/docs/readme.md",
  "version_id": "20260211120000_def456"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "file_path": "markdown/user_123/docs/readme.md",
  "rolled_to_version": "20260211120000_def456",
  "new_version_id": "20260211150000_ghi789",
  "message": "File rolled back successfully"
}
```

---

### 14. Delete Version

**Endpoint**: `DELETE /oss/versions/delete`

**Description**: 删除特定版本（仅软删除标记，实际删除由 Lifecycle Rule 处理）。

**Request**:
```http
DELETE /api/markdown-editor/oss/versions/delete?file_path=markdown/user_123/docs/readme.md&version_id=20260211120000_def456
Authorization: Bearer {jwt_token}
```

**Response** (200 OK):
```json
{
  "success": true,
  "version_id": "20260211120000_def456",
  "message": "Version marked for deletion"
}
```

---

## Data Models

### OssFile
```typescript
interface OssFile {
  file_path: string;
  filename: string;
  size: number;
  last_modified: string; // ISO 8601
  storage_type: 'oss';
}
```

### FileVersion
```typescript
interface FileVersion {
  version_id: string;
  version_number: number;
  created_at: string; // ISO 8601
  size: number;
  content_preview: string; // 前200字符
}
```

### ApiResponse
```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `INVALID_FILE_TYPE` | 文件类型不支持 |
| `FILE_TOO_LARGE` | 文件超过大小限制 |
| `FILE_NOT_FOUND` | 文件不存在 |
| `PERMISSION_DENIED` | 无权访问该文件 |
| `VERSION_NOT_FOUND` | 版本不存在 |
| `DIRECTORY_NOT_EMPTY` | 文件夹不为空 |
| `OSS_SERVICE_ERROR` | OSS 服务内部错误 |
| `CONFLICT_DETECTED` | 检测到同步冲突 |

