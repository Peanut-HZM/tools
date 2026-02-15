/**
 * IndexedDB Utility Module for Offline Caching
 * 
 * Provides persistent storage for:
 * - Offline file content
 * - Sync queue for pending operations
 * - File metadata and sync status
 */

const DB_NAME = 'MarkdownOssOfflineDB';
const DB_VERSION = 1;

// Object store names
export const STORE_FILES = 'files';
export const STORE_SYNC_QUEUE = 'syncQueue';
export const STORE_METADATA = 'metadata';

// Database instance cache
let dbInstance: IDBDatabase | null = null;

/**
 * Initialize IndexedDB database
 */
export async function initIndexedDB(): Promise<IDBDatabase> {
  if (dbInstance) {
    return dbInstance;
  }

  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => {
      reject(new Error('Failed to open IndexedDB'));
    };

    request.onsuccess = () => {
      dbInstance = request.result;
      resolve(dbInstance);
    };

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;

      // Files store - caches file content
      if (!db.objectStoreNames.contains(STORE_FILES)) {
        const filesStore = db.createObjectStore(STORE_FILES, { keyPath: 'path' });
        filesStore.createIndex('syncStatus', 'syncStatus', { unique: false });
        filesStore.createIndex('localModified', 'localModified', { unique: false });
      }

      // Sync queue store - tracks pending operations
      if (!db.objectStoreNames.contains(STORE_SYNC_QUEUE)) {
        const syncStore = db.createObjectStore(STORE_SYNC_QUEUE, { keyPath: 'id' });
        syncStore.createIndex('path', 'path', { unique: false });
        syncStore.createIndex('timestamp', 'timestamp', { unique: false });
      }

      // Metadata store - general metadata and sync state
      if (!db.objectStoreNames.contains(STORE_METADATA)) {
        db.createObjectStore(STORE_METADATA, { keyPath: 'key' });
      }
    };
  });
}

/**
 * Close database connection
 */
export function closeIndexedDB(): void {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
  }
}

/**
 * Generic function to perform database operations
 */
async function performTransaction<T>(
  storeName: string,
  mode: IDBTransactionMode,
  operation: (store: IDBObjectStore) => IDBRequest<T>
): Promise<T> {
  const db = await initIndexedDB();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([storeName], mode);
    const store = transaction.objectStore(storeName);
    const request = operation(store);

    request.onsuccess = () => {
      resolve(request.result);
    };

    request.onerror = () => {
      reject(new Error(`IndexedDB operation failed: ${request.error?.message}`));
    };

    transaction.onerror = () => {
      reject(new Error(`Transaction failed: ${transaction.error?.message}`));
    };
  });
}

// ==================== Files Store Operations ====================

/**
 * Save file content to IndexedDB
 */
export async function saveOfflineFile(
  path: string,
  content: string,
  ossModified: number = 0
): Promise<void> {
  const fileData: OfflineFile = {
    path,
    content,
    localModified: Date.now(),
    ossModified,
    syncStatus: 'synced',
    checksum: await computeChecksum(content),
  };

  await performTransaction(STORE_FILES, 'readwrite', (store) =>
    store.put(fileData)
  );
}

/**
 * Get file content from IndexedDB
 */
export async function getOfflineFile(path: string): Promise<OfflineFile | null> {
  try {
    const result = await performTransaction<OfflineFile | undefined>(
      STORE_FILES,
      'readonly',
      (store) => store.get(path)
    );
    return result || null;
  } catch {
    return null;
  }
}

/**
 * Update file sync status
 */
export async function updateFileSyncStatus(
  path: string,
  status: SyncStatus
): Promise<void> {
  const file = await getOfflineFile(path);
  if (file) {
    file.syncStatus = status;
    await performTransaction(STORE_FILES, 'readwrite', (store) =>
      store.put(file)
    );
  }
}

/**
 * Mark file as pending sync (modified offline)
 */
export async function markFilePending(path: string, content: string): Promise<void> {
  const existingFile = await getOfflineFile(path);
  
  const fileData: OfflineFile = {
    path,
    content,
    localModified: Date.now(),
    ossModified: existingFile?.ossModified || 0,
    syncStatus: 'pending',
    checksum: await computeChecksum(content),
  };

  await performTransaction(STORE_FILES, 'readwrite', (store) =>
    store.put(fileData)
  );
}

/**
 * Get all files with specific sync status
 */
export async function getFilesByStatus(status: SyncStatus): Promise<OfflineFile[]> {
  const db = await initIndexedDB();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_FILES], 'readonly');
    const store = transaction.objectStore(STORE_FILES);
    const index = store.index('syncStatus');
    const request = index.getAll(status);

    request.onsuccess = () => {
      resolve(request.result || []);
    };

    request.onerror = () => {
      reject(new Error('Failed to get files by status'));
    };
  });
}

/**
 * Get all pending files that need sync
 */
export async function getAllPendingFiles(): Promise<OfflineFile[]> {
  return getFilesByStatus('pending');
}

/**
 * Delete file from IndexedDB
 */
export async function deleteOfflineFile(path: string): Promise<void> {
  await performTransaction(STORE_FILES, 'readwrite', (store) =>
    store.delete(path)
  );
}

/**
 * Clear all cached files for a user
 */
export async function clearAllOfflineFiles(): Promise<void> {
  const db = await initIndexedDB();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_FILES], 'readwrite');
    const store = transaction.objectStore(STORE_FILES);
    const request = store.clear();

    request.onsuccess = () => {
      resolve();
    };

    request.onerror = () => {
      reject(new Error('Failed to clear offline files'));
    };
  });
}

// ==================== Sync Queue Operations ====================

/**
 * Add operation to sync queue
 */
export async function addToSyncQueue(
  path: string,
  operation: SyncOperationType
): Promise<string> {
  const id = `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  const queueItem: SyncQueueItem = {
    id,
    path,
    operation,
    timestamp: Date.now(),
    retryCount: 0,
  };

  await performTransaction(STORE_SYNC_QUEUE, 'readwrite', (store) =>
    store.add(queueItem)
  );

  return id;
}

/**
 * Get all items in sync queue
 */
export async function getSyncQueue(): Promise<SyncQueueItem[]> {
  const db = await initIndexedDB();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_SYNC_QUEUE], 'readonly');
    const store = transaction.objectStore(STORE_SYNC_QUEUE);
    const index = store.index('timestamp');
    const request = index.getAll();

    request.onsuccess = () => {
      resolve(request.result || []);
    };

    request.onerror = () => {
      reject(new Error('Failed to get sync queue'));
    };
  });
}

/**
 * Remove item from sync queue
 */
export async function removeFromSyncQueue(id: string): Promise<void> {
  await performTransaction(STORE_SYNC_QUEUE, 'readwrite', (store) =>
    store.delete(id)
  );
}

/**
 * Increment retry count for a queue item
 */
export async function incrementRetryCount(id: string): Promise<void> {
  const db = await initIndexedDB();
  
  return new Promise(async (resolve, reject) => {
    try {
      const transaction = db.transaction([STORE_SYNC_QUEUE], 'readwrite');
      const store = transaction.objectStore(STORE_SYNC_QUEUE);
      const request = store.get(id);

      request.onsuccess = () => {
        const item = request.result as SyncQueueItem;
        if (item) {
          item.retryCount += 1;
          store.put(item);
        }
        resolve();
      };

      request.onerror = () => {
        reject(new Error('Failed to increment retry count'));
      };
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * Clear sync queue
 */
export async function clearSyncQueue(): Promise<void> {
  const db = await initIndexedDB();
  
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_SYNC_QUEUE], 'readwrite');
    const store = transaction.objectStore(STORE_SYNC_QUEUE);
    const request = store.clear();

    request.onsuccess = () => {
      resolve();
    };

    request.onerror = () => {
      reject(new Error('Failed to clear sync queue'));
    };
  });
}

// ==================== Metadata Operations ====================

/**
 * Save metadata
 */
export async function saveMetadata(key: string, value: unknown): Promise<void> {
  await performTransaction(STORE_METADATA, 'readwrite', (store) =>
    store.put({ key, value })
  );
}

/**
 * Get metadata
 */
export async function getMetadata<T>(key: string): Promise<T | null> {
  try {
    const result = await performTransaction<{ value: T } | undefined>(
      STORE_METADATA,
      'readonly',
      (store) => store.get(key)
    );
    return result?.value || null;
  } catch {
    return null;
  }
}

/**
 * Delete metadata
 */
export async function deleteMetadata(key: string): Promise<void> {
  await performTransaction(STORE_METADATA, 'readwrite', (store) =>
    store.delete(key)
  );
}

// ==================== Helper Functions ====================

/**
 * Compute simple checksum for content validation
 */
async function computeChecksum(content: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(content);
  
  if (crypto && crypto.subtle) {
    try {
      const hashBuffer = await crypto.subtle.digest('SHA-256', data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    } catch {
      // Fallback to simple hash
    }
  }
  
  // Simple fallback checksum
  return content.length.toString(36) + content.slice(0, 8);
}

// ==================== Types ====================

export type SyncStatus = 'synced' | 'pending' | 'conflict';
export type SyncOperationType = 'create' | 'update' | 'delete';

export interface OfflineFile {
  path: string;
  content: string;
  localModified: number;
  ossModified: number;
  syncStatus: SyncStatus;
  checksum: string;
}

export interface SyncQueueItem {
  id: string;
  path: string;
  operation: SyncOperationType;
  timestamp: number;
  retryCount: number;
  lastError?: string;
}

export default {
  initIndexedDB,
  closeIndexedDB,
  saveOfflineFile,
  getOfflineFile,
  updateFileSyncStatus,
  markFilePending,
  getFilesByStatus,
  getAllPendingFiles,
  deleteOfflineFile,
  clearAllOfflineFiles,
  addToSyncQueue,
  getSyncQueue,
  removeFromSyncQueue,
  incrementRetryCount,
  clearSyncQueue,
  saveMetadata,
  getMetadata,
  deleteMetadata,
};
