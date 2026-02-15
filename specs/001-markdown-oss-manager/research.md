# Research: Markdown OSS 文件管理功能

**Date**: 2026-02-11  
**Feature**: Markdown OSS 文件管理  
**Purpose**: 解决技术选型疑问，确定最佳实现方案

## Research Topics

### 1. 阿里云 OSS 分块上传方案

**Decision**: 使用 OSS 原生分块上传 API (Multipart Upload)

**Rationale**:
- 阿里云 OSS SDK (oss2) 原生支持分块上传，提供完整生命周期管理
- 支持断点续传，自动保存上传进度到本地存储
- 已有 upload_part 和 complete_multipart_upload 接口
- 与现有 OSS 服务架构兼容，无需额外依赖

**Implementation Approach**:
- 前端：将大文件切分为 1MB-5MB 大小的块
- 使用 Web Workers 处理分块计算（避免阻塞 UI）
- 每上传一个块，保存进度到 localStorage
- 网络中断后，从断点继续上传未完成的块

**References**:
- 阿里云 OSS 分块上传文档: https://help.aliyun.com/document_detail/31991.html
- 现有代码: `backend/app/services/oss_service.py` 已使用 oss2 SDK

---

### 2. 离线缓存存储方案

**Decision**: 使用 IndexedDB 存储离线缓存，搭配 localStorage 保存同步状态

**Rationale**:
- IndexedDB 容量大（通常 50MB+），适合存储文件内容
- 支持结构化存储，可以保存文件元数据和内容
- 原生异步 API，不会阻塞主线程
- localStorage 用于保存轻量级的同步状态（队列、时间戳）

**Data Structure**:
```typescript
// IndexedDB Object Stores
interface OfflineCacheDB {
  files: {
    path: string;           // 文件路径 (Primary Key)
    content: string;        // 文件内容
    lastModified: number;   // 本地修改时间
    syncStatus: 'pending' | 'synced' | 'conflict';
  };
  
  syncQueue: {
    id: string;             // 操作 ID (Primary Key)
    path: string;           // 文件路径
    operation: 'create' | 'update' | 'delete';
    timestamp: number;
    retryCount: number;
  };
}
```

**Sync Strategy**:
- 网络恢复时，按时间顺序处理 syncQueue
- 先上传所有 pending 状态的文件
- 检测冲突：比较本地 lastModified 和 OSS last_modified
- 冲突处理策略：保留两者，创建冲突副本

---

### 3. 版本历史存储方案

**Decision**: 使用 OSS 独立前缀存储版本历史（`versions/{user_id}/{file_path}/{timestamp}`）

**Rationale**:
- 利用 OSS 的低成本存储和持久性
- 与主文件分离，不影响主文件列表加载性能
- 版本文件不经常访问，适合低频存储
- 可通过生命周期策略自动清理旧版本（30天后删除）

**Version Naming Convention**:
```
versions/{user_id}/markdown/{user_id}/{original_path}/{timestamp}_{version_id}.md
```

Example:
```
versions/user_123/markdown/user_123/docs/readme.md/20260211143000_v1.md
```

**Version Metadata**:
- 存储在版本文件的前 500 字节作为 Header
- 或者使用 OSS Object Metadata 存储
- 包含：创建时间、内容摘要、文件大小

**Optimization**:
- 使用 OSS ListObjectsV2 按前缀列出版本
- 分页加载，每页 20 个版本
- 缓存版本列表到 sessionStorage

---

### 4. 前端状态管理方案

**Decision**: 扩展现有 Zustand Store，新增 offlineStore 管理离线状态

**Rationale**:
- 项目已使用 Zustand 进行状态管理，保持一致性
- Zustand 轻量、易用、支持持久化中间件
- 可以创建独立的 offlineStore，不污染现有 store

**Store Structure**:
```typescript
// stores/offlineStore.ts
interface OfflineState {
  // 网络状态
  isOnline: boolean;
  isSyncing: boolean;
  
  // 待同步队列
  pendingFiles: PendingFile[];
  
  // 同步进度
  syncProgress: {
    total: number;
    completed: number;
    currentFile: string;
  };
  
  // Actions
  setOnlineStatus: (status: boolean) => void;
  addToSyncQueue: (file: PendingFile) => void;
  removeFromQueue: (path: string) => void;
  syncFiles: () => Promise<void>;
}
```

---

### 5. 文件树视觉区分方案

**Decision**: 使用图标和颜色标签双重标识

**Visual Design**:
- **本地文件**: 灰色文件图标 + "本地" 标签（柔和灰色）
- **OSS 文件**: 蓝色云图标 + "云端" 标签（品牌蓝色）
- **同步中**: 旋转动画图标 + "同步中..." 标签
- **离线修改**: 黄色警告图标 + "待同步" 标签

**Icon Library**: 
- 使用现有项目中的 SVG 图标
- 添加 lucide-react 图标库作为补充（可选）

**Implementation**:
```typescript
interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  storageType: 'local' | 'oss' | 'syncing' | 'offline';
  children?: FileNode[];
}
```

---

## 技术决策总结

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 分块上传 | OSS Multipart Upload | 原生支持、断点续传、架构兼容 |
| 离线缓存 | IndexedDB + localStorage | 容量大、异步 API、状态分离 |
| 版本存储 | OSS 独立前缀 | 低成本、持久性、自动清理 |
| 状态管理 | Zustand (扩展) | 项目一致性、轻量易用 |
| 视觉区分 | 图标 + 颜色标签 | 直观清晰、符合直觉 |

## 风险与缓解

1. **IndexedDB 浏览器兼容性**
   - 风险: 旧版浏览器不支持
   - 缓解: 检测支持情况，不支持时降级到内存缓存 + 提醒用户

2. **分块上传进度丢失**
   - 风险: 浏览器关闭导致进度丢失
   - 缓解: 每完成一个块保存 progress 到 localStorage

3. **版本历史性能问题**
   - 风险: 大量版本时 ListObjects 缓慢
   - 缓解: 分页加载、前端缓存、限制最大版本数（100）

4. **冲突解决复杂性**
   - 风险: 离线期间多设备修改同一文件
   - 缓解: 简单策略 - 保留两者，用户手动合并

## 后续研究（可选）

- Web Workers 实现方案（大文件处理优化）
- Service Workers 离线体验增强
- Conflict-free Replicated Data Types (CRDT) 自动合并
