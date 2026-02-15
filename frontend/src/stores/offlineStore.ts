import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  NetworkStatus,
  SyncProgress,
  SyncConflict,
  OfflineStore,
} from '../types/offlineCache';
import {
  getAllPendingFiles,
  getSyncQueue,
  clearAllOfflineFiles,
  clearSyncQueue,
} from '../utils/indexedDb';

interface OfflineState {
  networkStatus: NetworkStatus;
  syncProgress: SyncProgress | null;
  pendingCount: number;
  conflicts: SyncConflict[];
  lastSyncAt?: number;
  error?: string;
}

const initialState: OfflineState = {
  networkStatus: {
    isOnline: navigator.onLine,
    isSyncing: false,
  },
  syncProgress: null,
  pendingCount: 0,
  conflicts: [],
};

export const useOfflineStore = create<OfflineStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      setOnlineStatus: (isOnline: boolean) => {
        set((state) => ({
          networkStatus: {
            ...state.networkStatus,
            isOnline,
          },
        }));

        if (isOnline && !get().networkStatus.isSyncing) {
          get().startSync();
        }
      },

      startSync: async () => {
        const state = get();
        if (state.networkStatus.isSyncing || !state.networkStatus.isOnline) {
          return;
        }

        set({
          networkStatus: { ...state.networkStatus, isSyncing: true },
          syncProgress: { total: 0, completed: 0, failed: 0, percentage: 0 },
          error: undefined,
        });

        try {
          const pendingFiles = await getAllPendingFiles();
          const syncQueue = await getSyncQueue();
          const total = pendingFiles.length + syncQueue.length;

          if (total === 0) {
            set({
              networkStatus: { ...get().networkStatus, isSyncing: false },
              syncProgress: null,
            });
            return;
          }

          set({
            syncProgress: {
              total,
              completed: 0,
              failed: 0,
              percentage: 0,
            },
          });

          // TODO: Implement actual sync logic
          // This would call the offlineSyncService

          set({
            networkStatus: { ...get().networkStatus, isSyncing: false },
            syncProgress: null,
            lastSyncAt: Date.now(),
            pendingCount: 0,
          });
        } catch (error) {
          set({
            networkStatus: { ...get().networkStatus, isSyncing: false },
            syncProgress: null,
            error: error instanceof Error ? error.message : 'Sync failed',
          });
        }
      },

      cancelSync: () => {
        const state = get();
        if (state.networkStatus.isSyncing) {
          set({
            networkStatus: { ...state.networkStatus, isSyncing: false },
            syncProgress: null,
          });
        }
      },

      resolveConflict: (path: string, resolution: 'local' | 'oss' | 'both') => {
        set((state) => ({
          conflicts: state.conflicts.filter((c) => c.path !== path),
        }));
      },

      clearError: () => {
        set({ error: undefined });
      },

      clearCache: async () => {
        await clearAllOfflineFiles();
        await clearSyncQueue();
        set({
          pendingCount: 0,
          conflicts: [],
        });
      },

      updatePendingCount: async () => {
        const pendingFiles = await getAllPendingFiles();
        set({ pendingCount: pendingFiles.length });
      },
    }),
    {
      name: 'offline-store',
      partialize: (state) => ({
        lastSyncAt: state.lastSyncAt,
      }),
    }
  )
);

export default useOfflineStore;
