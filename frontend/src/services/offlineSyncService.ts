/**
 * Offline Sync Service
 * 
 * Manages synchronization between IndexedDB offline cache and OSS.
 * Handles conflict detection and resolution.
 */
import {
  getAllPendingFiles,
  updateFileSyncStatus,
  getSyncQueue,
  removeFromSyncQueue,
  incrementRetryCount,
  type OfflineFile,
  type SyncQueueItem,
} from '../utils/indexedDb';
import * as api from '../api/markdownEditorApi';
import type { SyncResult, SyncConflict } from '../types/offlineCache';

const MAX_RETRIES = 5;
const RETRY_DELAY_BASE = 1000;

export class OfflineSyncService {
  private isSyncing = false;
  private abortController: AbortController | null = null;

  /**
   * Check if there's a conflict between local and OSS versions
   */
  async checkConflict(file: OfflineFile): Promise<SyncConflict | null> {
    try {
      const response = await api.readMarkdownFromOss(file.path);
      if (!response.success) {
        return null;
      }

        if (file.localModified > file.ossModified + 5000) {
        return {
          path: file.path,
          localVersion: file,
          ossVersion: {
            path: file.path,
            content: response.content,
            lastModified: Date.now(),
          },
          detectedAt: Date.now(),
        };
      }

      return null;
    } catch {
      return null;
    }
  }

  /**
   * Sync a single file to OSS
   */
  async syncFile(file: OfflineFile): Promise<boolean> {
    try {
      const response = await api.saveMarkdownToOss(file.path, file.content);
      
      if (response.success) {
        await updateFileSyncStatus(file.path, 'synced');
        return true;
      } else {
        await updateFileSyncStatus(file.path, 'conflict');
        return false;
      }
    } catch (error) {
      console.error(`Failed to sync file ${file.path}:`, error);
      return false;
    }
  }

  /**
   * Perform full sync of all pending files
   */
  async performSync(
    onProgress?: (completed: number, total: number) => void
  ): Promise<SyncResult> {
    if (this.isSyncing) {
      return {
        success: false,
        syncedCount: 0,
        failedCount: 0,
        conflicts: [],
        error: 'Sync already in progress',
      };
    }

    this.isSyncing = true;
    this.abortController = new AbortController();

    try {
      const pendingFiles = await getAllPendingFiles();
      const syncQueue = await getSyncQueue();
      
      const allItems: (OfflineFile | SyncQueueItem)[] = [...pendingFiles, ...syncQueue];
      const total = allItems.length;
      
      if (total === 0) {
        return {
          success: true,
          syncedCount: 0,
          failedCount: 0,
          conflicts: [],
        };
      }

      let syncedCount = 0;
      let failedCount = 0;
      const conflicts: SyncConflict[] = [];

      for (let i = 0; i < allItems.length; i++) {
        if (this.abortController.signal.aborted) {
          break;
        }

        const item = allItems[i];

        if ('syncStatus' in item) {
          const conflict = await this.checkConflict(item);
          if (conflict) {
            conflicts.push(conflict);
            await updateFileSyncStatus(item.path, 'conflict');
            failedCount++;
          } else {
            const success = await this.syncFile(item);
            if (success) {
              syncedCount++;
            } else {
              failedCount++;
            }
          }
        } else {
          const success = await this.processQueueItem(item);
          if (success) {
            syncedCount++;
            await removeFromSyncQueue(item.id);
          } else {
            failedCount++;
            if (item.retryCount < MAX_RETRIES) {
              await incrementRetryCount(item.id);
              await this.delay(RETRY_DELAY_BASE * Math.pow(2, item.retryCount));
            } else {
              await removeFromSyncQueue(item.id);
            }
          }
        }

        onProgress?.(i + 1, total);
      }

      return {
        success: conflicts.length === 0 && failedCount === 0,
        syncedCount,
        failedCount,
        conflicts,
      };
    } catch (error) {
      return {
        success: false,
        syncedCount: 0,
        failedCount: 0,
        conflicts: [],
        error: error instanceof Error ? error.message : 'Sync failed',
      };
    } finally {
      this.isSyncing = false;
      this.abortController = null;
    }
  }

  /**
   * Process a single sync queue item
   */
  private async processQueueItem(item: SyncQueueItem): Promise<boolean> {
    try {
      switch (item.operation) {
        case 'create':
        case 'update': {
          const file = await getAllPendingFiles().then(files => 
            files.find(f => f.path === item.path)
          );
          if (file) {
            return await this.syncFile(file);
          }
          return false;
        }
        
        case 'delete': {
          return true;
        }
        
        default:
          return false;
      }
    } catch {
      return false;
    }
  }

  /**
   * Cancel ongoing sync
   */
  cancelSync(): void {
    if (this.abortController) {
      this.abortController.abort();
    }
  }

  /**
   * Check if sync is in progress
   */
  isSyncInProgress(): boolean {
    return this.isSyncing;
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Singleton instance
export const offlineSyncService = new OfflineSyncService();
export default offlineSyncService;
