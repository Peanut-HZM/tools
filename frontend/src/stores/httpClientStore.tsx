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
  sendRequest: (payload: SendRequestPayload) => Promise<SendRequestResponse>;
  clearResponse: () => void;
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

  // Send HTTP request
  sendRequest: async (payload: SendRequestPayload) => {
    set({ sendingRequest: true });
    try {
      const response = await sendHttpRequest(payload);
      set({ currentResponse: response, sendingRequest: false });
      return response;
    } catch (error) {
      console.error('Failed to send request:', error);
      set({ sendingRequest: false });
      throw error;
    }
  },

  // Clear response
  clearResponse: () => {
    set({ currentResponse: null });
  },
}));
