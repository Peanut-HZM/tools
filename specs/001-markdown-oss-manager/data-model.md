# Data Model: Markdown OSS 文件管理

**Date**: 2026-02-11  
**Feature**: Markdown OSS 文件管理  
**Purpose**: 定义功能涉及的核心数据实体及其关系

## Entity Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        User                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ user_id (PK)                                         │  │
│  │ auth_token                                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│         ┌─────────────────┼─────────────────┐               │
│         ▼                 ▼                 ▼               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  OssFile     │  │ FileVersion  │  │ OfflineCache │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Entities

### 1. OssFile (OSS 文件实体)

表示存储在阿里云 OSS 中的 Markdown 文件。

**Attributes**:

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `file_path` | string (PK) | 文件在 OSS 中的完整路径 | Pattern: `markdown/{user_id}/{relative_path}` |
| `filename` | string | 文件名（不含路径） | Max 255 chars, no special chars |
| `user_id` | string (FK) | 文件所有者 ID | Extracted from file_path prefix |
| `size` | integer | 文件大小（字节） | >= 0 |
| `content` | string | 文件内容（读取时） | Max 10MB |
| `last_modified` | ISO datetime | 最后修改时间 | OSS 返回的时间戳 |
| `storage_type` | enum | 存储类型标识 | Value: 'oss' |
| `sync_status` | enum | 同步状态 | 'synced' \| 'syncing' \| 'offline' |

**Relationships**:
- One-to-Many with `FileVersion`: 一个文件有多个历史版本
- Many-to-One with `User`: 文件属于一个用户

**Validation Rules**:
- file_path 必须包含有效的 user_id 前缀
- filename 不能包含特殊字符: `/ \ : * ? " < > |`
- size 不能超过 10MB（软限制）

---

### 2. FileVersion (文件版本实体)

表示文件的版本历史，存储在 OSS 的独立前缀下。

**Attributes**:

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `version_id` | string (PK) | 版本唯一标识 | Format: `{timestamp}_{random}` |
| `file_path` | string (FK) | 原文件路径 | References OssFile.file_path |
| `version_path` | string | 版本在 OSS 中的存储路径 | Pattern: `versions/{user_id}/{file_path}/{version_id}.md` |
| `user_id` | string | 文件所有者 ID | Denormalized for query efficiency |
| `created_at` | ISO datetime | 版本创建时间 | Auto-generated |
| `size` | integer | 版本大小（字节） | >= 0 |
| `content_preview` | string | 内容摘要 | First 200 chars of content |
| `version_number` | integer | 版本序号 | Auto-increment per file |

**Relationships**:
- Many-to-One with `OssFile`: 版本属于一个文件

**Lifecycle**:
1. 文件保存时自动创建新版本
2. 版本保留 30 天（通过 OSS Lifecycle Rule 自动清理）
3. 用户可手动删除特定版本
4. 回滚操作创建新版本（不删除旧版本）

**Validation Rules**:
- version_path 必须包含有效的 file_path 和 version_id
- 最多保留 100 个版本（超过时自动删除最旧版本）

---

### 3. OfflineCache (离线缓存实体)

存储在浏览器 IndexedDB 中的离线文件缓存。

**Attributes**:

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `path` | string (PK) | 文件路径 | Same as OssFile.file_path |
| `content` | string | 文件内容缓存 | Max 10MB |
| `local_modified` | integer | 本地修改时间戳 | Unix timestamp (ms) |
| `oss_modified` | integer | OSS 最后修改时间戳 | Unix timestamp (ms) |
| `sync_status` | enum | 同步状态 | 'synced' \| 'pending' \| 'conflict' |
| `checksum` | string | 内容校验和 | MD5 hash of content |

**Relationships**:
- One-to-One with `OssFile`: 缓存对应一个 OSS 文件

**State Transitions**:

```
[synced] --(离线编辑)--> [pending] --(网络恢复)--> [syncing] --(成功)--> [synced]
                                               └--(冲突)--> [conflict] --(用户解决)--> [synced]
```

**Conflict Detection**:
```typescript
if (local_modified > oss_modified) {
  // 本地有更新，需要上传
  sync_status = 'pending';
} else if (local_modified < oss_modified) {
  // OSS 有更新，需要下载或提示用户
  sync_status = 'conflict';
}
```

---

### 4. SyncQueue (同步队列实体)

记录待同步的操作队列。

**Attributes**:

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | string (PK) | 操作唯一标识 | UUID v4 |
| `path` | string | 文件路径 | References OssFile.file_path |
| `operation` | enum | 操作类型 | 'create' \| 'update' \| 'delete' |
| `timestamp` | integer | 操作时间戳 | Unix timestamp (ms) |
| `retry_count` | integer | 重试次数 | 0-5, max 5 retries |
| `last_error` | string | 上次错误信息 | Nullable |

**Processing Order**:
1. 按 timestamp 升序处理（先发生的先同步）
2. 同一文件的多条操作合并为最后一条
3. 重试间隔：1s, 2s, 4s, 8s, 16s（指数退避）

---

### 5. FileTreeNode (文件树节点)

前端展示用的文件树节点结构。

**Attributes**:

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `name` | string | 节点名称 | File or folder name |
| `path` | string | 节点完整路径 | Unique identifier |
| `type` | enum | 节点类型 | 'file' \| 'directory' |
| `storage_type` | enum | 存储类型 | 'local' \| 'oss' \| 'syncing' \| 'offline' |
| `children` | array | 子节点列表 | Only for type='directory' |
| `is_expanded` | boolean | 是否展开 | Frontend state only |
| `metadata` | object | 额外元数据 | size, last_modified, etc. |

**Tree Structure Example**:
```json
{
  "name": "root",
  "path": "",
  "type": "directory",
  "storage_type": "local",
  "children": [
    {
      "name": "docs",
      "path": "docs",
      "type": "directory",
      "storage_type": "local",
      "is_expanded": true,
      "children": [
        {
          "name": "readme.md",
          "path": "docs/readme.md",
          "type": "file",
          "storage_type": "local",
          "metadata": { "size": 1024, "last_modified": "2026-02-11T10:00:00Z" }
        }
      ]
    },
    {
      "name": "cloud",
      "path": "markdown/user_123/cloud",
      "type": "directory",
      "storage_type": "oss",
      "is_expanded": false,
      "children": [
        {
          "name": "notes.md",
          "path": "markdown/user_123/cloud/notes.md",
          "type": "file",
          "storage_type": "oss",
          "metadata": { "size": 2048, "last_modified": "2026-02-11T12:00:00Z" }
        }
      ]
    }
  ]
}
```

---

## Data Flows

### 1. 文件上传流程

```
User selects file
       │
       ▼
┌──────────────┐
│ FileUpload   │
│ Component    │
└──────┬───────┘
       │
       ▼
File size > 10MB?
       │
   ┌───┴───┐
   ▼       ▼
 Yes      No
   │       │
   ▼       ▼
Chunk    Direct
Upload   Upload
   │       │
   └───┬───┘
       │
       ▼
┌──────────────┐
│ OSS Service  │
│ (Backend)    │
└──────┬───────┘
       │
       ▼
Save to OSS
       │
       ▼
Create FileVersion
       │
       ▼
Update FileTree
```

### 2. 离线同步流程

```
Network Offline
       │
       ▼
User edits file
       │
       ▼
Save to IndexedDB
(sync_status: pending)
       │
       ▼
Add to SyncQueue
       │
       ▼
Network Restored
       │
       ▼
┌──────────────┐
│ Sync Service │
└──────┬───────┘
       │
       ▼
Process SyncQueue
       │
   ┌───┴───┐
   ▼       ▼
 Success  Conflict
   │       │
   ▼       ▼
Mark     Create
synced   conflict
         copy
```

### 3. 版本回滚流程

```
User selects version
       │
       ▼
┌──────────────┐
│ Version      │
│ History UI   │
└──────┬───────┘
       │
       ▼
Preview version
       │
       ▼
User confirms rollback
       │
       ▼
┌──────────────┐
│ OSS Service  │
└──────┬───────┘
       │
       ▼
Copy version content
       │
       ▼
Save as new version
       │
       ▼
Update current file
```

---

## Storage Mapping

| Entity | Storage | Location | Key/ID |
|--------|---------|----------|--------|
| OssFile | OSS | `markdown/{user_id}/{path}` | file_path |
| FileVersion | OSS | `versions/{user_id}/{file_path}/{version_id}.md` | version_path |
| OfflineCache | IndexedDB | `offline_cache` store | path |
| SyncQueue | IndexedDB | `sync_queue` store | id |
| FileTreeNode | Memory | Frontend state | path |

---

## Indexes

### IndexedDB Indexes

**offline_cache store**:
- Primary Key: `path`
- Index: `sync_status` (for快速查询待同步文件)
- Index: `local_modified` (for排序和冲突检测)

**sync_queue store**:
- Primary Key: `id`
- Index: `path` (for合并同一文件的操作)
- Index: `timestamp` (for按时间顺序处理)

### OSS Prefixes

```
markdown/                    # 主文件存储
  └── {user_id}/
      └── {file_path}

versions/                    # 版本历史存储
  └── {user_id}/
      └── markdown/{user_id}/
          └── {file_path}/
              └── {version_id}.md
```

---

## Constraints & Business Rules

1. **用户隔离**: file_path 必须包含 user_id 前缀，后端必须验证用户只能访问自己的文件
2. **文件大小**: 单文件最大 10MB，超过需要分块上传
3. **版本限制**: 单个文件最多保留 100 个版本，超过自动删除最旧版本
4. **保留期限**: 版本文件保留 30 天，通过 OSS Lifecycle Rule 自动清理
5. **文件名规范**: 不能包含特殊字符，最大长度 255 字符
6. **同步冲突**: 离线编辑期间文件被修改时，保留两者创建冲突副本
7. **队列限制**: SyncQueue 最多保留 1000 条记录，防止无限增长

