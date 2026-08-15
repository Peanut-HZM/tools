// frontend/src/stores/monitorStore.ts
import { create } from 'zustand';
import type { MonitorServer } from '../api/monitorApi';

export type MonitorTab = 'servers' | 'overview' | 'history' | 'processes' | 'services' | 'alerts';

interface MonitorState {
  servers: MonitorServer[];
  selectedServerId: string | null;
  activeTab: MonitorTab;
  unreadAlerts: number;
  setServers: (servers: MonitorServer[]) => void;
  setSelectedServerId: (id: string | null) => void;
  setActiveTab: (tab: MonitorTab) => void;
  setUnreadAlerts: (count: number) => void;
}

export const useMonitorStore = create<MonitorState>((set) => ({
  servers: [],
  selectedServerId: null,
  activeTab: 'servers',
  unreadAlerts: 0,
  setServers: (servers) => set({ servers }),
  setSelectedServerId: (id) => set({ selectedServerId: id }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setUnreadAlerts: (count) => set({ unreadAlerts: count }),
}));
