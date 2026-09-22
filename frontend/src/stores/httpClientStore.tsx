/**
 * HTTP Client 状态管理
 *
 * 每个标签页独立持有自己的响应（response）与发送状态（sending），
 * 切换标签页时互不干扰；发送请求时在指定标签页上下文中执行。
 */

import { create } from 'zustand';
import {
  Collection,
  HttpRequest,
  Environment,
  RequestHistory,
  SendRequestPayload,
  SendRequestResponse,
  fetchCollections,
  fetchRequests,
  fetchEnvironments,
  fetchActiveEnvironment,
  sendHttpRequest,
  fetchHistory,
  clearHistory,
  deleteHistoryItem,
  deleteRequest as apiDeleteRequest,
  activateEnvironment as apiActivateEnvironment,
  duplicateRequest as apiDuplicateRequest,
  updateRequest,
} from '../services/httpClientApi';

interface OpenTab {
  requestId: string;
  request: HttpRequest;
  isModified: boolean;
  /** 该标签页最近一次请求的响应 */
  response: SendRequestResponse | null;
  /** 是否正在发送请求 */
  sending: boolean;
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

  // Actions
  loadCollections: () => Promise<void>;
  loadRequests: (collectionId: string) => Promise<void>;
  loadEnvironments: () => Promise<void>;
  activateEnvironment: (envId: string) => Promise<void>;
  setActiveTab: (tabId: string | null) => void;
  openTab: (request: HttpRequest) => void;
  closeTab: (requestId: string) => void;
  updateTabRequest: (requestId: string, request: Partial<HttpRequest>) => void;
  setTabResponse: (requestId: string, response: SendRequestResponse | null) => void;
  setTabSending: (requestId: string, sending: boolean) => void;
  saveRequest: (requestId: string) => Promise<HttpRequest>;
  renameRequest: (requestId: string, name: string) => Promise<HttpRequest>;
  sendRequest: (requestId: string, payload: SendRequestPayload) => Promise<SendRequestResponse>;
  loadHistory: () => Promise<void>;
  removeHistoryItem: (id: string) => Promise<void>;
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

  // 激活环境（后端互斥激活后更新本地状态）
  activateEnvironment: async (envId: string) => {
    try {
      const activated = await apiActivateEnvironment(envId);
      set(state => ({
        environments: state.environments.map(e =>
          e.id === envId ? { ...e, is_active: true } : { ...e, is_active: false }
        ),
        activeEnvironment: activated,
      }));
    } catch (error) {
      console.error('Failed to activate environment:', error);
      throw error;
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
        openTabs: [...openTabs, {
          requestId: request.id,
          request,
          isModified: false,
          response: null,
          sending: false,
        }],
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

  // 设置标签页响应
  setTabResponse: (requestId: string, response: SendRequestResponse | null) => {
    set(state => ({
      openTabs: state.openTabs.map(tab =>
        tab.requestId === requestId ? { ...tab, response } : tab
      ),
    }));
  },

  // 设置标签页发送状态
  setTabSending: (requestId: string, sending: boolean) => {
    set(state => ({
      openTabs: state.openTabs.map(tab =>
        tab.requestId === requestId ? { ...tab, sending } : tab
      ),
    }));
  },

  // Save request（持久化到后端）
  saveRequest: async (requestId: string) => {
    const { openTabs } = get();
    const tab = openTabs.find(t => t.requestId === requestId);
    if (!tab) {
      throw new Error('标签页不存在');
    }
    try {
      // 序列化 form_data：去除 File 对象（不可 JSON 序列化），仅保留可序列化字段
      const { form_data, ...restRequest } = tab.request;
      const serializedFormData = form_data?.map((entry) => ({
        key: entry.key,
        value: entry.type === 'file' ? (entry.file?.name || entry.value || '') : entry.value,
        type: entry.type,
        enabled: entry.enabled ?? true,
        description: entry.description || '',
      }));
      const updated = await updateRequest(requestId, { ...restRequest, form_data: serializedFormData });
      // 保存期间用户可能继续编辑，重新读取最新状态，避免旧快照覆盖新编辑
      const { openTabs: latestTabs } = get();
      const newTabs = latestTabs.map(t =>
        t.requestId === requestId
          ? { ...t, request: { ...(updated as HttpRequest), ...t.request }, isModified: false }
          : t
      );
      set({ openTabs: newTabs });
      return updated;
    } catch (error) {
      console.error('Failed to save request:', error);
      throw error;
    }
  },

  // Rename request（树内改名：直接持久化，不标记未保存）
  renameRequest: async (requestId: string, name: string) => {
    try {
      const updated = await updateRequest(requestId, { name });
      const { openTabs: latestTabs } = get();
      const newTabs = latestTabs.map(t =>
        t.requestId === requestId
          ? { ...t, request: { ...t.request, name: updated.name } }
          : t
      );
      set({ openTabs: newTabs });
      return updated;
    } catch (error) {
      console.error('Failed to rename request:', error);
      throw error;
    }
  },

  // Send HTTP request（在指定标签页上下文中执行，响应写入该标签页）
  sendRequest: async (requestId: string, payload: SendRequestPayload) => {
    get().setTabResponse(requestId, null);
    get().setTabSending(requestId, true);
    try {
      const response = await sendHttpRequest(payload);
      get().setTabResponse(requestId, response);
      get().setTabSending(requestId, false);
      return response;
    } catch (error: any) {
      get().setTabSending(requestId, false);
      // 将错误信息转为失败响应展示在标签页内
      let errorResponse: SendRequestResponse;
      if (error?.response?.data) {
        const errorData = error.response.data;
        errorResponse = {
          status_code: error.response.status || 0,
          status_text: '',
          headers: error.response.headers || {},
          body: typeof errorData === 'string' ? errorData : JSON.stringify(errorData, null, 2),
          response_time: 0,
          size: 0,
          content_type: 'application/json',
          request_url: payload.url || '',
          request_headers: {},
          extracted_variables: {},
          assertion_results: [],
          error: typeof errorData?.detail === 'string' ? errorData.detail : undefined,
        };
      } else {
        errorResponse = {
          status_code: 0,
          status_text: '',
          headers: {},
          body: '',
          response_time: 0,
          size: 0,
          content_type: 'text/plain',
          request_url: payload.url || '',
          request_headers: {},
          extracted_variables: {},
          assertion_results: [],
          error: `请求失败：${error?.message || '未知错误'}`,
        };
      }
      get().setTabResponse(requestId, errorResponse);
      throw error;
    }
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

  // 删除单条历史
  removeHistoryItem: async (id: string) => {
    try {
      await deleteHistoryItem(id);
      set(state => ({ history: state.history.filter(h => h.id !== id) }));
    } catch (error) {
      console.error('Failed to delete history item:', error);
      throw error;
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
      headers: Array.isArray(reqData.headers) ? reqData.headers : [],
      params: Array.isArray(reqData.params) ? reqData.params : [],
      body_type: reqData.body_type || 'none',
      body: reqData.body || '',
      form_data: [],
      auth_type: reqData.auth_type || 'none',
      auth_config: {},
      extract_variables: [],
      assertions: [],
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
