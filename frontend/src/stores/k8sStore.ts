/**
 * K8s 控制台工具 - Zustand 状态管理
 *
 * 管理连接列表、活跃连接、命名空间选择、资源类型等全局 UI 状态
 */
import { create } from 'zustand';
import type { K8sConnection } from '../components/Tools/K8sTool/types';

/** 支持的资源类型 */
type ResourceType = 'pods' | 'workloads' | 'nodes' | 'events';

/** 选中资源的标识 */
interface SelectedResource {
  type: string;
  namespace: string;
  name: string;
}

/** 资源标签页标识 */
export interface ResourceTab {
  /** 唯一标识：{type}-{namespace}-{name} */
  id: string;
  /** 资源类型：'pod' | 'deployment' | ... */
  type: string;
  namespace: string;
  name: string;
}

interface K8sStore {
  // 状态
  connections: K8sConnection[];
  activeConnectionId: string | null;
  namespaces: string[];
  selectedNamespaces: string[];
  resourceType: ResourceType;
  selectedResource: SelectedResource | null;

  // 多标签页管理
  openedTabs: ResourceTab[];
  activeTabId: string | null;

  // 操作
  setConnections: (c: K8sConnection[]) => void;
  setActiveConnection: (id: string | null) => void;
  setNamespaces: (ns: string[]) => void;
  setSelectedNamespaces: (ns: string[]) => void;
  setResourceType: (t: ResourceType) => void;
  setSelectedResource: (r: SelectedResource | null) => void;
  /** 切换连接时重置命名空间和资源选择 */
  resetOnConnectionChange: () => void;

  // 多标签页操作
  openResourceTab: (resource: ResourceTab) => void;
  closeResourceTab: (tabId: string) => void;
  setActiveTab: (tabId: string) => void;
  clearAllTabs: () => void;
}

export const useK8sStore = create<K8sStore>()((set) => ({
  // 初始状态
  connections: [],
  activeConnectionId: null,
  namespaces: [],
  selectedNamespaces: ['default'],
  resourceType: 'pods',
  selectedResource: null,
  openedTabs: [],
  activeTabId: null,

  // 操作实现
  setConnections: (c) => set({ connections: c }),

  setActiveConnection: (id) =>
    set((s) => {
      // 点击同一个连接不重复触发重置
      if (s.activeConnectionId === id) return {};
      return {
        activeConnectionId: id,
        selectedNamespaces: ['default'],
        selectedResource: null,
      };
    }),

  setNamespaces: (ns) => set({ namespaces: ns }),

  setSelectedNamespaces: (ns) => set({ selectedNamespaces: ns }),

  setResourceType: (t) =>
    set({ resourceType: t, selectedResource: null }),

  setSelectedResource: (r) => set({ selectedResource: r }),

  resetOnConnectionChange: () =>
    set({
      namespaces: [],
      selectedNamespaces: ['default'],
      resourceType: 'pods',
      selectedResource: null,
    }),

  // 多标签页操作实现
  openResourceTab: (resource) =>
    set((s) => {
      // 已存在的标签直接激活，不占额外名额
      const exists = s.openedTabs.find((t) => t.id === resource.id);
      if (exists) {
        return { activeTabId: resource.id };
      }
      // 限制最多 10 个标签，达到上限后阻止新增
      if (s.openedTabs.length >= 10) {
        console.warn('标签页数量已达上限（10 个），请先关闭部分标签');
        return {};
      }
      return {
        openedTabs: [...s.openedTabs, resource],
        activeTabId: resource.id,
      };
    }),

  closeResourceTab: (tabId) =>
    set((s) => {
      const newTabs = s.openedTabs.filter((t) => t.id !== tabId);
      const newActiveId =
        s.activeTabId === tabId
          ? newTabs.length > 0
            ? newTabs[newTabs.length - 1].id
            : null
          : s.activeTabId;
      return {
        openedTabs: newTabs,
        activeTabId: newActiveId,
      };
    }),

  setActiveTab: (tabId) => set({ activeTabId: tabId }),

  clearAllTabs: () => set({ openedTabs: [], activeTabId: null }),
}));
