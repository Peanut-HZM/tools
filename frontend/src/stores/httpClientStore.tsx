/**
 * HTTP Client 状态管理
 */

import { create } from 'zustand';
import {
  Collection,
  HttpRequest,
  Environment,
  RequestHistory,
  fetchCollections,
  fetchRequests,
  fetchEnvironments,
  fetchActiveEnvironment,
  sendHttpRequest,
  fetchHistory,
  clearHistory,
  duplicateRequest as apiDuplicateRequest,
  deleteRequestById as apiDeleteRequest,
  updateRequest,
  SendRequestPayload,
  SendRequestResponse,
} from '../services/httpClientApi';

interface OpenTab {
  requestId: string;
  request: HttpRequest;
  isModified: boolean;
}

export type { OpenTab };

interface HttpClientState {
  // Collections
  collections: Collection[];
  loadingCollections: boolean;

  // Requests
  requests: HttpRequest[];
  loadingRequests: boolean;

  // Environments
  environments: Environment[];
  activeEnvironment: Environment | null;

  // Tabs
  openTabs: OpenTab[];
  activeTabId: string | null;

  // History
  history: RequestHistory[];

  // Current request response
  currentResponse: SendRequestResponse | null;
  sendingRequest: boolean;

  // Actions
  loadCollections: () => Promise<void>;
  loadRequests: (collectionId: string) => Promise<void>;
  loadEnvironments: () => Promise<void>;
  setActiveTab: (tabId: string | null) => void;
  openTab: (request: HttpRequest) => void;
  closeTab: (requestId: string) => void;
  updateTabRequest: (requestId: string, request: Partial<HttpRequest>) => void;
  saveRequest: (requestId: string) => Promise<HttpRequest>;
  sendRequest: (payload: SendRequestPayload) => Promise<SendRequestResponse>;
  clearResponse: () => void;
  loadHistory: () => Promise<void>;
  clearHistory: () => Promise<void>;
  replayFromHistory: (historyItem: RequestHistory) => void;
  duplicateRequest: (request: HttpRequest, targetCollectionId: string) => Promise<void>;
  deleteRequest: (requestId: string, collectionId: string) => Promise<void>;
}

export const useHttpClientStore = create<HttpClientState>((set, get) => ({
  // Initial state
  collections: [],
  loadingCollections: false,
  requests: [],
  loadingRequests: false,
  environments: [],
  activeEnvironment: null,
  openTabs: [],
  activeTabId: null,
  history: [],
  currentResponse: null,
  sendingRequest: false,

  // Load collections
  loadCollections: async () => {
    set({ loadingCollections: true });
    try {
      const collections = await fetchCollections();
      set({ collections, loadingCollections: false });
    } catch (error) {
      console.error('Failed to load collections:', error);
      set({ loadingCollections: false });
    }
  },

  // Load requests by collection
  loadRequests: async (collectionId: string) => {
    set({ loadingRequests: true });
    try {
      const requests = await fetchRequests(collectionId);
      set({ requests, loadingRequests: false });
    } catch (error) {
      console.error('Failed to load requests:', error);
      set({ loadingRequests: false });
    }
  },

  // Load environments
  loadEnvironments: async () => {
    try {
      const [environments, active] = await Promise.all([
        fetchEnvironments(),
        fetchActiveEnvironment(),
      ]);
      set({ environments, activeEnvironment: active });
    } catch (error) {
      console.error('Failed to load environments:', error);
    }
  },

  // Set active tab
  setActiveTab: (tabId: string | null) => {
    set({ activeTabId: tabId });
  },

  // Open a new tab or focus existing
  openTab: (request: HttpRequest) => {
    const { openTabs } = get();
    const existingTab = openTabs.find(tab => tab.requestId === request.id);

    if (existingTab) {
      set({ activeTabId: request.id });
    } else {
      set({
        openTabs: [...openTabs, { requestId: request.id, request, isModified: false }],
        activeTabId: request.id,
      });
    }
  },

  // Close a tab
  closeTab: (requestId: string) => {
    const { openTabs, activeTabId } = get();
    const newTabs = openTabs.filter(tab => tab.requestId !== requestId);

    set({
      openTabs: newTabs,
      activeTabId: activeTabId === requestId ? (newTabs[0]?.requestId || null) : activeTabId,
    });
  },

  // Update request in tab
  updateTabRequest: (requestId: string, requestUpdate: Partial<HttpRequest>) => {
    const { openTabs } = get();
    const newTabs = openTabs.map(tab =>
      tab.requestId === requestId
        ? { ...tab, request: { ...tab.request, ...requestUpdate }, isModified: true }
        : tab
    );
    set({ openTabs: newTabs });
  },

  // Save request（持久化到后端）
  saveRequest: async (requestId: string) => {
    const { openTabs } = get();
    const tab = openTabs.find(t => t.requestId === requestId);
    if (!tab) {
      throw new Error('标签页不存在');
    }
    try {
      const updated = await updateRequest(requestId, { ...tab.request });
      // 保存期间用户可能继续编辑，重新读取最新状态，避免旧快照覆盖新编辑
      const { openTabs: latestTabs } = get();
      const newTabs = latestTabs.map(t =>
        t.requestId === requestId
          ? { ...t, request: { ...updated, ...t.request }, isModified: false }
          : t
      );
      set({ openTabs: newTabs });
      return updated;
    } catch (error) {
      console.error('Failed to save request:', error);
      throw error;
    }
  },

  // Send HTTP request
  sendRequest: async (payload: SendRequestPayload) => {
    set({ sendingRequest: true });
    try {
      const response = await sendHttpRequest(payload);
      set({ currentResponse: response, sendingRequest: false });
      return response;
    } catch (error: any) {
      set({ sendingRequest: false });
      // 设置错误响应对象，让 UI 可以显示错误信息
      if (error.response?.data) {
        const errorData = error.response.data;
        set({
          currentResponse: {
            status_code: error.response.status,
            headers: error.response.headers || {},
            body: typeof errorData === 'string' ? errorData : JSON.stringify(errorData, null, 2),
            response_time: 0,
            content_type: 'application/json',
          }
        });
      } else if (error.message) {
        // 网络错误等无 response 的情况
        set({
          currentResponse: {
            status_code: 0,
            headers: {},
            body: `请求失败：${error.message}`,
            response_time: 0,
            content_type: 'text/plain',
          }
        });
      }
      throw error;
    }
  },

  // Clear response
  clearResponse: () => {
    set({ currentResponse: null });
  },

  // Load history
  loadHistory: async () => {
    try {
      const history = await fetchHistory(100);
      set({ history });
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  },

  // Clear history
  clearHistory: async () => {
    try {
      await clearHistory();
      set({ history: [] });
    } catch (error) {
      console.error('Failed to clear history:', error);
    }
  },

  // Replay from history
  replayFromHistory: (historyItem: RequestHistory) => {
    const { openTab } = get();
    const reqData = historyItem.request_data || {};
    const request: HttpRequest = {
      id: `history_${Date.now()}`,
      collection_id: '',
      name: `${historyItem.method} ${historyItem.url}`,
      method: historyItem.method,
      url: historyItem.url,
      headers: reqData.headers || {},
      params: reqData.params || {},
      body_type: reqData.body_type || 'none',
      body: reqData.body || '',
      auth_type: 'none',
      auth_config: {},
      sort_order: 0,
      created_at: historyItem.timestamp,
      updated_at: historyItem.timestamp,
    };
    openTab(request);
  },

  // Duplicate request
  duplicateRequest: async (request: HttpRequest, targetCollectionId: string) => {
    try {
      await apiDuplicateRequest(request, targetCollectionId);
    } catch (error) {
      console.error('Failed to duplicate request:', error);
      throw error;
    }
  },

  // Delete request
  deleteRequest: async (requestId: string, collectionId: string) => {
    try {
      await apiDeleteRequest(requestId);
      const { loadRequests } = get();
      loadRequests(collectionId);
    } catch (error) {
      console.error('Failed to delete request:', error);
      throw error;
    }
  },
}));
