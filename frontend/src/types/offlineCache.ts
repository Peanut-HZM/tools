/**
 * TypeScript type definitions for offline caching system
 * 
 * These types support the IndexedDB offline cache and sync functionality
 * for the Markdown OSS file management feature.
 */

/** Sync status of a cached file */
export type SyncStatus = 'synced' | 'pending' | 'conflict';

/** Type of sync operation */
export type SyncOperationType = 'create' | 'update' | 'delete';

/** Offline file data stored in IndexedDB */
export interface OfflineFile {
  /** Full file path (unique identifier) */
  path: string;
  /** File content */
  content: string;
  /** Local modification timestamp (Unix ms) */
  localModified: number;
  /** OSS last modification timestamp (Unix ms) */
  ossModified: number;
  /** Current sync status */
  syncStatus: SyncStatus;
  /** Content checksum for validation */
  checksum: string;
}

/** Sync queue item for pending operations */
export interface SyncQueueItem {
  /** Unique operation ID */
  id: string;
  /** Target file path */
  path: string;
  /** Operation type */
  operation: SyncOperationType;
  /** Operation timestamp */
  timestamp: number;
  /** Number of retry attempts */
  retryCount: number;
  /** Last error message (if any) */
  lastError?: string;
}

/** Metadata entry for IndexedDB */
export interface MetadataEntry<T = unknown> {
  /** Metadata key */
  key: string;
  /** Metadata value */
  value: T;
}

/** Network status information */
export interface NetworkStatus {
  /** Whether the browser is online */
  isOnline: boolean;
  /** Whether currently syncing with OSS */
  isSyncing: boolean;
  /** Type of network connection */
  connectionType?: 'wifi' | '4g' | '3g' | '2g' | 'slow-2g' | 'unknown';
  /** Estimated effective round-trip time (ms) */
  rtt?: number;
}

/** Sync progress information */
export interface SyncProgress {
  /** Total number of files to sync */
  total: number;
  /** Number of files successfully synced */
  completed: number;
  /** Number of files failed to sync */
  failed: number;
  /** Current file being synced */
  currentFile?: string;
  /** Progress percentage (0-100) */
  percentage: number;
}

/** Conflict information when sync detects changes */
export interface SyncConflict {
  /** File path with conflict */
  path: string;
  /** Local file version */
  localVersion: OfflineFile;
  /** OSS file version */
  ossVersion: {
    path: string;
    content: string;
    lastModified: number;
  };
  /** Timestamp when conflict was detected */
  detectedAt: number;
}

/** Options for file upload */
export interface UploadOptions {
  /** Target directory path */
  targetPath?: string;
  /** Whether to overwrite existing file */
  overwrite?: boolean;
  /** Callback for upload progress */
  onProgress?: (progress: number) => void;
  /** Chunk size for multipart upload (bytes) */
  chunkSize?: number;
}

/** Result of a sync operation */
export interface SyncResult {
  /** Whether sync was successful */
  success: boolean;
  /** Number of files synced */
  syncedCount: number;
  /** Number of files failed */
  failedCount: number;
  /** Conflicts detected during sync */
  conflicts: SyncConflict[];
  /** Error message (if failed) */
  error?: string;
}

/** OSS file information from API */
export interface OssFileInfo {
  /** Full file path in OSS */
  file_path: string;
  /** File name */
  filename: string;
  /** File size in bytes */
  size: number;
  /** Last modification time (ISO string) */
  last_modified: string;
  /** Storage type identifier */
  storage_type: 'oss';
}

/** File tree node for unified local and OSS files */
export interface FileTreeNode {
  /** Node name */
  name: string;
  /** Full node path */
  path: string;
  /** Node type */
  type: 'file' | 'directory';
  /** Storage type for visual distinction */
  storageType: 'local' | 'oss' | 'syncing' | 'offline';
  /** Child nodes (for directories) */
  children?: FileTreeNode[];
  /** Whether directory is expanded (UI state) */
  isExpanded?: boolean;
  /** Additional metadata */
  metadata?: {
    size?: number;
    lastModified?: string;
    syncStatus?: SyncStatus;
  };
}

/** Offline store state */
export interface OfflineState {
  /** Current network status */
  networkStatus: NetworkStatus;
  /** Current sync progress */
  syncProgress: SyncProgress | null;
  /** Pending files count */
  pendingCount: number;
  /** Conflicts requiring resolution */
  conflicts: SyncConflict[];
  /** Last sync timestamp */
  lastSyncAt?: number;
  /** Error message (if any) */
  error?: string;
}

/** Actions available in offline store */
export interface OfflineActions {
  /** Set online/offline status */
  setOnlineStatus: (isOnline: boolean) => void;
  /** Start sync process */
  startSync: () => Promise<void>;
  /** Cancel ongoing sync */
  cancelSync: () => void;
  /** Mark conflict as resolved */
  resolveConflict: (path: string, resolution: 'local' | 'oss' | 'both') => void;
  /** Clear all errors */
  clearError: () => void;
  /** Clear offline cache */
  clearCache: () => Promise<void>;
}

/** Complete offline store type */
export type OfflineStore = OfflineState & OfflineActions;
