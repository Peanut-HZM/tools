import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface WorkspaceTab {
  id: string;
  toolId: string;
  toolName: string;
  toolIcon: string;
  openedAt: number;
}

interface ToolInfo {
  id: string;
  title: string;
  icon: string;
}

interface WorkspaceState {
  tabs: WorkspaceTab[];
  activeTabId: string | null;

  addTab: (tool: ToolInfo) => void;
  removeTab: (tabId: string) => void;
  setActiveTab: (tabId: string) => void;
}

/** 生成唯一 ID */
function generateTabId(): string {
  return `tab-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      tabs: [],
      activeTabId: null,

      addTab: (tool: ToolInfo) => {
        const { tabs } = get();
        // 检查是否已有该工具的标签
        const existing = tabs.find((t) => t.toolId === tool.id);
        if (existing) {
          set({ activeTabId: existing.id });
          return;
        }
        // 新建标签
        const newTab: WorkspaceTab = {
          id: generateTabId(),
          toolId: tool.id,
          toolName: tool.title,
          toolIcon: tool.icon,
          openedAt: Date.now(),
        };
        set({
          tabs: [...tabs, newTab],
          activeTabId: newTab.id,
        });
      },

      removeTab: (tabId: string) => {
        const { tabs, activeTabId } = get();
        const index = tabs.findIndex((t) => t.id === tabId);
        if (index === -1) return;

        const newTabs = tabs.filter((t) => t.id !== tabId);
        let newActiveTabId = activeTabId;

        if (activeTabId === tabId) {
          // 关闭的是活跃标签，切换到相邻标签
          if (newTabs.length === 0) {
            newActiveTabId = null;
          } else if (index === 0) {
            // 第一个标签被删除，切换到新的第一个
            newActiveTabId = newTabs[0].id;
          } else {
            // 切换到前一个标签
            newActiveTabId = newTabs[index - 1].id;
          }
        }

        set({ tabs: newTabs, activeTabId: newActiveTabId });
      },

      setActiveTab: (tabId: string) => {
        set({ activeTabId: tabId });
      },
    }),
    {
      name: 'workspace-tabs',
      partialize: (state) => ({
        tabs: state.tabs,
        activeTabId: state.activeTabId,
      }),
    }
  )
);
