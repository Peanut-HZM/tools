import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { recordToolVisit } from '../api/adminApi';

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
  isToolSidebarVisible: boolean;

  addTab: (tool: ToolInfo) => void;
  removeTab: (tabId: string) => void;
  setActiveTab: (tabId: string) => void;
  toggleToolSidebar: () => void;
}

/** 生成唯一 ID */
function generateTabId(): string {
  return `tab-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
}

/**
 * 已下线工具 → 替代入口
 *
 * 「订阅套餐额度」(`subscription-quota`) 的全部能力已并入「Agent 订阅中心」
 * (`agent-hub`)。用户本地 localStorage 里可能还留着旧标签页，
 * 这里统一改写成新入口，避免出现「未知工具」。
 */
const RETIRED_TOOL_ALIASES: Record<string, { id: string; name: string }> = {
  'subscription-quota': { id: 'agent-hub', name: 'Agent 订阅中心' },
};

/** 把持久化恢复出来的旧标签页迁移到当前工具 id */
function migrateRetiredTabs(tabs: WorkspaceTab[]): WorkspaceTab[] {
  const seen = new Set<string>();
  const out: WorkspaceTab[] = [];
  for (const tab of tabs) {
    const alias = RETIRED_TOOL_ALIASES[tab.toolId];
    const next = alias ? { ...tab, toolId: alias.id, toolName: alias.name } : tab;
    // 迁移后可能与已有标签重复（旧+新并存），只保留第一个
    if (seen.has(next.toolId)) {
      continue;
    }
    seen.add(next.toolId);
    out.push(next);
  }
  return out;
}

/** 上报一次工具使用（fire-and-forget，失败静默，不阻塞交互） */
function trackToolUsage(toolId: string, toolName: string): void {
  recordToolVisit(toolId, toolName).catch(() => {});
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      tabs: [],
      activeTabId: null,
      isToolSidebarVisible: true,

      addTab: (tool: ToolInfo) => {
        const { tabs } = get();
        // 检查是否已有该工具的标签
        const existing = tabs.find((t) => t.toolId === tool.id);
        if (existing) {
          // 检查名称和图标是否需要更新（管理后台修改后同步）
          if (existing.toolName !== tool.title || existing.toolIcon !== tool.icon) {
            const updatedTabs = tabs.map(tab =>
              tab.id === existing.id
                ? { ...tab, toolName: tool.title, toolIcon: tool.icon }
                : tab
            );
            set({ tabs: updatedTabs, activeTabId: existing.id });
          } else {
            set({ activeTabId: existing.id });
          }
          // 激活已打开的工具同样算一次使用（左侧列表点击已打开工具的场景）
          trackToolUsage(existing.toolId, tool.title);
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
        // 新开工具计入一次使用
        trackToolUsage(newTab.toolId, newTab.toolName);
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
        // Tab 页签切换进入工具也算一次使用；找不到对应 tab 时跳过（防御分支）
        const tab = get().tabs.find((t) => t.id === tabId);
        if (tab) {
          trackToolUsage(tab.toolId, tab.toolName);
        }
      },

      toggleToolSidebar: () => {
        set({ isToolSidebarVisible: !get().isToolSidebarVisible });
      },
    }),
    {
      name: 'workspace-tabs',
      partialize: (state) => ({
        tabs: state.tabs,
        activeTabId: state.activeTabId,
        isToolSidebarVisible: state.isToolSidebarVisible,
      }),
      // 旧版本持久化的标签页在这里迁移（已下线工具 → 新入口）
      merge: (persisted, current) => {
        const saved = persisted as Partial<WorkspaceState> | undefined;
        if (!saved || !Array.isArray(saved.tabs)) {
          return current;
        }
        const tabs = migrateRetiredTabs(saved.tabs);
        const stillActive = tabs.some((t) => t.id === saved.activeTabId);
        return {
          ...current,
          ...saved,
          tabs,
          activeTabId: stillActive ? (saved.activeTabId as string) : (tabs[0]?.id ?? null),
        };
      },
    }
  )
);
