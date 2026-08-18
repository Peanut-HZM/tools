# 工具页多标签工作区实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将工具页从单页路由导航改造为多标签工作区，支持同时打开多个工具并保持状态。

**Architecture:** 新建 `/workspace` 路由，使用 Zustand Store 管理标签状态。工作区页面包含左侧工具列表 + 右侧标签栏 + 标签面板。所有标签组件保持挂载（`display: none` 切换），实现状态完全保留。

**Tech Stack:** React 18, React Router v7, Zustand 5, Tailwind CSS v3, TypeScript 5

## Global Constraints

- 所有 UI 文本必须通过 i18n（`t.xxx`），同时更新 zh-CN 和 en-US
- 使用 Zustand `create` 模式（不用 React Context），使用 `persist` 中间件
- 暗色主题：`bg-slate-900` 基底、`bg-slate-800` 卡片、`border-slate-700` 边框
- 工具列表从后端 API 获取（`/api/tools?platform=pc`），不硬编码
- 前端端口 5178，后端端口 19092
- TypeScript 严格模式，所有组件 props 定义 interface

---

### Task 1: 创建工作区 Zustand Store

**Files:**
- Create: `frontend/src/stores/workspaceStore.ts`
- Test: `frontend/src/stores/workspaceStore.test.ts`

**Interfaces:**
- Consumes: `Tool` type from `frontend/src/types/index.ts`
- Produces: `useWorkspaceStore` hook with `tabs`, `activeTabId`, `addTab`, `removeTab`, `setActiveTab`

- [ ] **Step 1: Write failing tests for workspace store**

Create `frontend/src/stores/workspaceStore.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { useWorkspaceStore } from './workspaceStore';

describe('workspaceStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useWorkspaceStore.setState({
      tabs: [],
      activeTabId: null,
    });
  });

  it('should start with empty tabs', () => {
    const state = useWorkspaceStore.getState();
    expect(state.tabs).toEqual([]);
    expect(state.activeTabId).toBeNull();
  });

  it('should add a tab', () => {
    const tool = {
      id: 'k8s-tool',
      title: 'K8s 控制台',
      icon: 'fas fa-server',
    };
    useWorkspaceStore.getState().addTab(tool);
    
    const state = useWorkspaceStore.getState();
    expect(state.tabs).toHaveLength(1);
    expect(state.tabs[0].toolId).toBe('k8s-tool');
    expect(state.tabs[0].toolName).toBe('K8s 控制台');
    expect(state.activeTabId).toBe(state.tabs[0].id);
  });

  it('should reuse existing tab when adding same tool', () => {
    const tool = {
      id: 'k8s-tool',
      title: 'K8s 控制台',
      icon: 'fas fa-server',
    };
    useWorkspaceStore.getState().addTab(tool);
    const firstTabId = useWorkspaceStore.getState().tabs[0].id;
    
    useWorkspaceStore.getState().addTab(tool);
    
    const state = useWorkspaceStore.getState();
    expect(state.tabs).toHaveLength(1);
    expect(state.activeTabId).toBe(firstTabId);
  });

  it('should remove a tab', () => {
    const tool = {
      id: 'k8s-tool',
      title: 'K8s 控制台',
      icon: 'fas fa-server',
    };
    useWorkspaceStore.getState().addTab(tool);
    const tabId = useWorkspaceStore.getState().tabs[0].id;
    
    useWorkspaceStore.getState().removeTab(tabId);
    
    const state = useWorkspaceStore.getState();
    expect(state.tabs).toHaveLength(0);
    expect(state.activeTabId).toBeNull();
  });

  it('should switch to adjacent tab when removing active tab', () => {
    const tool1 = { id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' };
    const tool2 = { id: 'ssh-tool', title: 'SSH', icon: 'fas fa-key' };
    const tool3 = { id: 'db-tool', title: 'DB', icon: 'fas fa-database' };
    
    useWorkspaceStore.getState().addTab(tool1);
    useWorkspaceStore.getState().addTab(tool2);
    useWorkspaceStore.getState().addTab(tool3);
    
    const tabs = useWorkspaceStore.getState().tabs;
    // Active is tool3 (last added)
    expect(useWorkspaceStore.getState().activeTabId).toBe(tabs[2].id);
    
    // Remove active tab (tool3)
    useWorkspaceStore.getState().removeTab(tabs[2].id);
    
    // Should switch to tool2 (previous)
    expect(useWorkspaceStore.getState().activeTabId).toBe(tabs[1].id);
  });

  it('should set active tab', () => {
    const tool1 = { id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' };
    const tool2 = { id: 'ssh-tool', title: 'SSH', icon: 'fas fa-key' };
    
    useWorkspaceStore.getState().addTab(tool1);
    useWorkspaceStore.getState().addTab(tool2);
    
    const tabs = useWorkspaceStore.getState().tabs;
    useWorkspaceStore.getState().setActiveTab(tabs[0].id);
    
    expect(useWorkspaceStore.getState().activeTabId).toBe(tabs[0].id);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/stores/workspaceStore.test.ts`
Expected: FAIL — `workspaceStore` module not found

- [ ] **Step 3: Implement workspace store**

Create `frontend/src/stores/workspaceStore.ts`:

```typescript
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/stores/workspaceStore.test.ts`
Expected: PASS — 6/6 tests passing

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/workspaceStore.ts frontend/src/stores/workspaceStore.test.ts
git commit -m "feat(workspace): 创建工作区 Zustand Store，管理标签状态"
```

---

### Task 2: 创建 TabBar 组件

**Files:**
- Create: `frontend/src/components/Workspace/TabBar.tsx`
- Test: `frontend/src/components/Workspace/TabBar.test.tsx`

**Interfaces:**
- Consumes: `useWorkspaceStore` (tabs, activeTabId, setActiveTab, removeTab)
- Produces: `<TabBar />` 组件，渲染标签栏

- [ ] **Step 1: Write failing tests for TabBar**

Create `frontend/src/components/Workspace/TabBar.test.tsx`:

```tsx
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TabBar } from './TabBar';
import { useWorkspaceStore } from '../../stores/workspaceStore';

describe('TabBar', () => {
  beforeEach(() => {
    useWorkspaceStore.setState({ tabs: [], activeTabId: null });
  });

  it('should render nothing when no tabs', () => {
    const { container } = render(<TabBar />);
    expect(container.firstChild).toBeNull();
  });

  it('should render tabs', () => {
    useWorkspaceStore.getState().addTab({ id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' });
    useWorkspaceStore.getState().addTab({ id: 'ssh-tool', title: 'SSH', icon: 'fas fa-key' });

    render(<TabBar />);
    expect(screen.getByText('K8s')).toBeTruthy();
    expect(screen.getByText('SSH')).toBeTruthy();
  });

  it('should highlight active tab', () => {
    useWorkspaceStore.getState().addTab({ id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' });
    useWorkspaceStore.getState().addTab({ id: 'ssh-tool', title: 'SSH', icon: 'fas fa-key' });

    render(<TabBar />);
    const k8sTab = screen.getByText('K8s').closest('[data-tab-id]');
    expect(k8sTab?.getAttribute('data-active')).toBe('true');
  });

  it('should switch tab on click', () => {
    useWorkspaceStore.getState().addTab({ id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' });
    useWorkspaceStore.getState().addTab({ id: 'ssh-tool', title: 'SSH', icon: 'fas fa-key' });

    render(<TabBar />);
    const k8sTab = screen.getByText('K8s').closest('[data-tab-id]');
    fireEvent.click(k8sTab!);

    expect(useWorkspaceStore.getState().activeTabId).toBe(
      useWorkspaceStore.getState().tabs[0].id
    );
  });

  it('should remove tab on close click', () => {
    useWorkspaceStore.getState().addTab({ id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' });

    render(<TabBar />);
    const closeBtn = screen.getByText('×');
    fireEvent.click(closeBtn);

    expect(useWorkspaceStore.getState().tabs).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/Workspace/TabBar.test.tsx`
Expected: FAIL — `TabBar` module not found

- [ ] **Step 3: Implement TabBar component**

Create `frontend/src/components/Workspace/TabBar.tsx`:

```tsx
import React from 'react';
import { useWorkspaceStore } from '../../stores/workspaceStore';

export const TabBar: React.FC = () => {
  const { tabs, activeTabId, setActiveTab, removeTab } = useWorkspaceStore();

  if (tabs.length === 0) return null;

  return (
    <div className="flex items-end bg-slate-800 border-b border-slate-700 h-10 px-2 gap-0.5 overflow-x-auto">
      {tabs.map((tab) => {
        const isActive = tab.id === activeTabId;
        return (
          <div
            key={tab.id}
            data-tab-id={tab.id}
            data-active={isActive}
            className={[
              'flex items-center gap-2 px-3 py-1.5 rounded-t-md text-sm cursor-pointer transition-colors min-w-0 max-w-[180px] group',
              isActive
                ? 'bg-slate-900 text-slate-100 border-t border-l border-r border-slate-700'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-700',
            ].join(' ')}
            onClick={() => setActiveTab(tab.id)}
          >
            <i className={[tab.toolIcon, 'text-xs flex-shrink-0'].join(' ')}></i>
            <span className="truncate">{tab.toolName}</span>
            <button
              className="ml-1 text-slate-500 hover:text-slate-200 hover:bg-slate-600 rounded px-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={(e) => {
                e.stopPropagation();
                removeTab(tab.id);
              }}
              title="关闭标签"
            >
              ×
            </button>
          </div>
        );
      })}
    </div>
  );
};
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/Workspace/TabBar.test.tsx`
Expected: PASS — 5/5 tests passing

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Workspace/TabBar.tsx frontend/src/components/Workspace/TabBar.test.tsx
git commit -m "feat(workspace): 创建 TabBar 浏览器风格标签栏组件"
```

---

### Task 3: 创建 TabPanels 组件（状态保持核心）

**Files:**
- Create: `frontend/src/components/Workspace/TabPanels.tsx`

**Interfaces:**
- Consumes: `useWorkspaceStore` (tabs, activeTabId), tool component mapping
- Produces: `<TabPanels />` 组件，所有标签保持挂载

- [ ] **Step 1: 创建工具组件映射**

Create `frontend/src/components/Workspace/toolComponents.tsx`:

```tsx
import React from 'react';
import K8sTool from '../Tools/K8sTool/K8sTool';
import SSHTool from '../Tools/SSHTool/SSHTool';
import DatabaseTool from '../Tools/DatabaseTool/DatabaseTool';
import RedisTool from '../Tools/RedisTool/RedisTool';
import MarkdownEditorTool from '../Tools/MarkdownEditorTool';
import OCRTool from '../Tools/OCR/OCRTool';
import ASRTool from '../Tools/ASR/ASRTool';
import JsonFormatter from '../Tools/JsonFormatter';
import Calendar from '../Tools/Calendar';
import AIAssistant from '../Tools/AIAssistant';
import KeyGenerator from '../Tools/KeyGenerator';
import MarkItDownConverter from '../Tools/MarkItDownConverter';
import ProductManagerAgent from '../Tools/ProductManagerAgent';
import LearningSharePlatform from '../Tools/LearningSharePlatform';
import CrossShareMain from '../Tools/CrossShare/CrossShareMain';
import CursorHistory from '../Tools/CursorHistory/CursorHistory';
import HttpApiClient from '../Tools/HttpApiClient/HttpApiClient';
import SystemMonitor from '../Tools/SystemMonitor';
import TokenUsage from '../Tools/TokenUsage';
import OpenClawChat from '../Tools/OpenClawChat/OpenClawChat';
import ImageDownloader from '../Tools/ImageDownloader';
import VideoDownloader from '../Tools/VideoDownloader';

/**
 * 工具 ID → 组件映射
 * 工作区通过此映射渲染标签面板
 */
export const toolComponentMap: Record<string, React.ComponentType> = {
  'k8s-tool': K8sTool,
  'ssh-tool': SSHTool,
  'database-tool': DatabaseTool,
  'redis-tool': RedisTool,
  'markdown-editor': MarkdownEditorTool,
  'ocr': OCRTool,
  'asr': ASRTool,
  'json-formatter': JsonFormatter,
  'calendar': Calendar,
  'ai-assistant': AIAssistant,
  'key-generator': KeyGenerator,
  'markitdown-converter': MarkItDownConverter,
  'product-manager': ProductManagerAgent,
  'learning-share': LearningSharePlatform,
  'cross-share': CrossShareMain,
  'cursor-history': CursorHistory,
  'http-api-client': HttpApiClient,
  'system-monitor': SystemMonitor,
  'token-usage': TokenUsage,
  'openclaw': OpenClawChat,
  'image-downloader': ImageDownloader,
  'video-downloader': VideoDownloader,
};
```

- [ ] **Step 2: 实现 TabPanels**

Create `frontend/src/components/Workspace/TabPanels.tsx`:

```tsx
import React from 'react';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { toolComponentMap } from './toolComponents';

/**
 * 标签面板容器
 * 所有标签保持挂载，通过 display: none/block 切换
 * 这是状态保持的核心实现
 */
export const TabPanels: React.FC = () => {
  const { tabs, activeTabId } = useWorkspaceStore();

  if (tabs.length === 0) return null;

  return (
    <div className="flex-1 min-h-0 overflow-hidden">
      {tabs.map((tab) => {
        const ToolComponent = toolComponentMap[tab.toolId];
        if (!ToolComponent) {
          // 未知的工具 ID，显示占位
          return (
            <div
              key={tab.id}
              style={{ display: tab.id === activeTabId ? 'flex' : 'none' }}
              className="h-full items-center justify-center text-slate-500"
            >
              <div className="text-center">
                <i className="fas fa-exclamation-triangle text-4xl mb-4"></i>
                <p>未知工具: {tab.toolId}</p>
              </div>
            </div>
          );
        }

        return (
          <div
            key={tab.id}
            style={{ display: tab.id === activeTabId ? 'flex' : 'none' }}
            className="h-full flex-col"
          >
            <ToolComponent />
          </div>
        );
      })}
    </div>
  );
};
```

- [ ] **Step 3: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit src/components/Workspace/TabPanels.tsx`
Expected: 无错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Workspace/toolComponents.tsx frontend/src/components/Workspace/TabPanels.tsx
git commit -m "feat(workspace): 创建 TabPanels 组件，display:none 保持标签状态"
```

---

### Task 4: 创建 WorkspaceSidebar 组件

**Files:**
- Create: `frontend/src/components/Workspace/WorkspaceSidebar.tsx`
- Test: `frontend/src/components/Workspace/WorkspaceSidebar.test.tsx`

**Interfaces:**
- Consumes: `useWorkspaceStore` (tabs, activeTabId, addTab), Tool list from API
- Produces: `<WorkspaceSidebar />` 左侧边栏组件

- [ ] **Step 1: Write failing tests for WorkspaceSidebar**

Create `frontend/src/components/Workspace/WorkspaceSidebar.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { WorkspaceSidebar } from './WorkspaceSidebar';
import { useWorkspaceStore } from '../../stores/workspaceStore';

// Mock useNavigate
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));

describe('WorkspaceSidebar', () => {
  const mockTools = [
    { id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server', description: '', rating: 0, usageCount: '0', category: 'dev', iconColor: '' },
    { id: 'ssh-tool', title: 'SSH', icon: 'fas fa-key', description: '', rating: 0, usageCount: '0', category: 'dev', iconColor: '' },
  ];

  beforeEach(() => {
    useWorkspaceStore.setState({ tabs: [], activeTabId: null });
  });

  it('should render home button', () => {
    render(<WorkspaceSidebar tools={mockTools} />);
    expect(screen.getByText('返回首页')).toBeTruthy();
  });

  it('should render tool list', () => {
    render(<WorkspaceSidebar tools={mockTools} />);
    expect(screen.getByText('K8s')).toBeTruthy();
    expect(screen.getByText('SSH')).toBeTruthy();
  });

  it('should highlight opened tools', () => {
    useWorkspaceStore.getState().addTab({ id: 'k8s-tool', title: 'K8s', icon: 'fas fa-server' });
    render(<WorkspaceSidebar tools={mockTools} />);
    
    const k8sItem = screen.getByText('K8s').closest('[data-tool-id]');
    expect(k8sItem?.getAttribute('data-active')).toBe('true');
  });

  it('should add tab when clicking tool', () => {
    render(<WorkspaceSidebar tools={mockTools} />);
    fireEvent.click(screen.getByText('K8s'));
    
    expect(useWorkspaceStore.getState().tabs).toHaveLength(1);
    expect(useWorkspaceStore.getState().tabs[0].toolId).toBe('k8s-tool');
  });

  it('should be collapsible', () => {
    render(<WorkspaceSidebar tools={mockTools} />);
    const toggle = screen.getByTitle('折叠侧边栏');
    fireEvent.click(toggle);
    // After collapse, tool names should be hidden
    expect(screen.queryByText('K8s')).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/Workspace/WorkspaceSidebar.test.tsx`
Expected: FAIL — `WorkspaceSidebar` module not found

- [ ] **Step 3: Implement WorkspaceSidebar**

Create `frontend/src/components/Workspace/WorkspaceSidebar.tsx`:

```tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import type { Tool } from '../../types';

interface Props {
  tools: Tool[];
}

const SIDEBAR_COLLAPSED_KEY = 'workspace-sidebar-collapsed';

export const WorkspaceSidebar: React.FC<Props> = ({ tools }) => {
  const navigate = useNavigate();
  const { tabs, addTab } = useWorkspaceStore();
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true';
  });

  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(collapsed));
  }, [collapsed]);

  const openedToolIds = new Set(tabs.map((t) => t.toolId));

  const handleToolClick = (tool: Tool) => {
    addTab({ id: tool.id, title: tool.title, icon: tool.icon });
  };

  const handleGoHome = () => {
    navigate('/');
  };

  if (collapsed) {
    return (
      <div className="w-12 bg-slate-800 border-r border-slate-700 flex flex-col items-center py-2">
        <button
          onClick={() => setCollapsed(false)}
          className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-700 rounded transition-colors"
          title="展开侧边栏"
        >
          <i className="fas fa-chevron-right text-xs"></i>
        </button>
      </div>
    );
  }

  return (
    <div className="w-52 bg-slate-800 border-r border-slate-700 flex flex-col h-full">
      {/* 首页按钮 */}
      <div className="p-3 border-b border-slate-700">
        <button
          onClick={handleGoHome}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-sm font-medium transition-colors"
        >
          <i className="fas fa-home"></i>
          <span>返回首页</span>
        </button>
      </div>

      {/* 折叠按钮 */}
      <div className="flex justify-end px-2 pt-2">
        <button
          onClick={() => setCollapsed(true)}
          className="p-1 text-slate-500 hover:text-slate-300 hover:bg-slate-700 rounded transition-colors"
          title="折叠侧边栏"
        >
          <i className="fas fa-chevron-left text-xs"></i>
        </button>
      </div>

      {/* 工具列表 */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        <div className="text-[10px] text-slate-500 uppercase font-semibold tracking-wider px-2 mb-2">
          工具列表
        </div>
        <div className="space-y-0.5">
          {tools.map((tool) => {
            const isOpened = openedToolIds.has(tool.id);
            return (
              <div
                key={tool.id}
                data-tool-id={tool.id}
                data-active={isOpened}
                className={[
                  'flex items-center gap-2 px-3 py-2 rounded-md text-sm cursor-pointer transition-colors',
                  isOpened
                    ? 'bg-blue-600/20 text-blue-300'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white',
                ].join(' ')}
                onClick={() => handleToolClick(tool)}
              >
                <i className={[tool.icon, 'text-xs w-4 text-center flex-shrink-0'].join(' ')}></i>
                <span className="truncate">{tool.title}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/Workspace/WorkspaceSidebar.test.tsx`
Expected: PASS — 5/5 tests passing

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Workspace/WorkspaceSidebar.tsx frontend/src/components/Workspace/WorkspaceSidebar.test.tsx
git commit -m "feat(workspace): 创建 WorkspaceSidebar 左侧工具列表组件，支持折叠"
```

---

### Task 5: 创建 EmptyWorkspace 欢迎页

**Files:**
- Create: `frontend/src/components/Workspace/EmptyWorkspace.tsx`

**Interfaces:**
- Consumes: `Tool[]` (常用工具列表)
- Produces: `<EmptyWorkspace />` 欢迎页组件

- [ ] **Step 1: 实现 EmptyWorkspace**

Create `frontend/src/components/Workspace/EmptyWorkspace.tsx`:

```tsx
import React from 'react';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import type { Tool } from '../../types';

interface Props {
  tools: Tool[];
}

/** 常用工具 ID 列表（快捷入口） */
const FEATURED_TOOL_IDS = [
  'k8s-tool',
  'ssh-tool',
  'database-tool',
  'redis-tool',
  'markdown-editor',
  'json-formatter',
];

export const EmptyWorkspace: React.FC<Props> = ({ tools }) => {
  const { addTab } = useWorkspaceStore();

  const featuredTools = FEATURED_TOOL_IDS
    .map((id) => tools.find((t) => t.id === id))
    .filter((t): t is Tool => t !== undefined);

  const handleOpenTool = (tool: Tool) => {
    addTab({ id: tool.id, title: tool.title, icon: tool.icon });
  };

  return (
    <div className="flex-1 flex items-center justify-center bg-slate-900">
      <div className="text-center max-w-md">
        <i className="fas fa-tools text-6xl text-slate-600 mb-6"></i>
        <h2 className="text-2xl font-bold text-slate-200 mb-2">开始使用</h2>
        <p className="text-slate-400 mb-8">
          从左侧工具列表选择一个工具，或点击下方快捷入口
        </p>
        {featuredTools.length > 0 && (
          <div className="grid grid-cols-3 gap-3">
            {featuredTools.map((tool) => (
              <button
                key={tool.id}
                onClick={() => handleOpenTool(tool)}
                className="flex flex-col items-center gap-2 p-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-slate-600 rounded-lg transition-colors"
              >
                <i className={[tool.icon, 'text-xl text-blue-400'].join(' ')}></i>
                <span className="text-xs text-slate-300">{tool.title}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit src/components/Workspace/EmptyWorkspace.tsx`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Workspace/EmptyWorkspace.tsx
git commit -m "feat(workspace): 创建空工作区欢迎页组件"
```

---

### Task 6: 创建 WorkspacePage 容器

**Files:**
- Create: `frontend/src/components/Workspace/WorkspacePage.tsx`

**Interfaces:**
- Consumes: `WorkspaceSidebar`, `TabBar`, `TabPanels`, `EmptyWorkspace`, tools from API
- Produces: `<WorkspacePage />` 工作区主容器

- [ ] **Step 1: 实现 WorkspacePage**

Create `frontend/src/components/Workspace/WorkspacePage.tsx`:

```tsx
import React, { useEffect, useState } from 'react';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { WorkspaceSidebar } from './WorkspaceSidebar';
import { TabBar } from './TabBar';
import { TabPanels } from './TabPanels';
import { EmptyWorkspace } from './EmptyWorkspace';
import type { Tool } from '../../types';
import { fetchTools } from '../../services/api';

export const WorkspacePage: React.FC = () => {
  const { tabs } = useWorkspaceStore();
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTools('pc')
      .then((data) => setTools(data))
      .catch((err) => console.error('Failed to fetch tools:', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-slate-400">加载中...</div>
      </div>
    );
  }

  const hasTabs = tabs.length > 0;

  return (
    <div className="h-screen bg-slate-900 flex flex-col overflow-hidden">
      <div className="flex flex-1 min-h-0">
        {/* 左侧边栏 */}
        <WorkspaceSidebar tools={tools} />

        {/* 右侧内容区 */}
        <div className="flex-1 flex flex-col min-w-0">
          {hasTabs ? (
            <>
              {/* 标签栏 */}
              <TabBar />
              {/* 标签面板 */}
              <TabPanels />
            </>
          ) : (
            /* 空工作区欢迎页 */
            <EmptyWorkspace tools={tools} />
          )}
        </div>
      </div>
    </div>
  );
};
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit src/components/Workspace/WorkspacePage.tsx`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Workspace/WorkspacePage.tsx
git commit -m "feat(workspace): 创建 WorkspacePage 容器，组装侧边栏、标签栏、面板"
```

---

### Task 7: 路由集成 + 首页跳转

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Hero/Hero.tsx` (or `ToolGrid.tsx`)

**Interfaces:**
- Consumes: `WorkspacePage`, `useWorkspaceStore.addTab`, `Tool`
- Produces: `/workspace` 路由，首页点击跳转工作区

- [ ] **Step 1: 在 App.tsx 中添加 /workspace 路由**

在 `frontend/src/App.tsx` 中：

1. 添加 import（在文件顶部其他 import 附近）：

```tsx
import WorkspacePage from './components/Workspace/WorkspacePage';
```

2. 在 `<Routes>` 中添加路由（在 `<Route path="/" element={<HomePage />} />` 之后）：

```tsx
<Route path="/workspace" element={<WorkspacePage />} />
```

- [ ] **Step 2: 修改首页工具点击行为**

在 `frontend/src/App.tsx` 中，找到 `HomePage` 组件内的 `handleToolClick` 函数，修改为跳转到工作区：

找到这段代码（约第 240-266 行）：

```tsx
const handleToolClick = (toolId: string) => {
  const toolRoutes: Record<string, string> = {
    // ... 现有路由映射
  };
  const route = toolRoutes[toolId];
  if (route) {
    navigate(route);
  } else {
    alert(interpolate(t.errors.toolNotImplemented, { toolId }));
  }
};
```

替换为：

```tsx
const handleToolClick = (toolId: string) => {
  // 从已加载的工具列表中找到工具信息
  const tool = tools.find((t) => t.id === toolId);
  if (tool) {
    // 跳转到工作区，由工作区 Store 管理标签
    // addTab 在 WorkspacePage 中会通过 useWorkspaceStore 调用
    navigate('/workspace', { state: { openToolId: toolId } });
  } else {
    alert(interpolate(t.errors.toolNotImplemented, { toolId }));
  }
};
```

**注意**：这里使用 `navigate state` 传递要打开的工具 ID。WorkspacePage 需要处理这个 state。

- [ ] **Step 3: WorkspacePage 处理导航 state**

修改 `frontend/src/components/Workspace/WorkspacePage.tsx`，在 `useEffect` 中处理导航 state：

添加 import：

```tsx
import { useLocation } from 'react-router-dom';
```

在组件中添加：

```tsx
const location = useLocation();
const { addTab } = useWorkspaceStore();

// 处理从首页跳转过来时传递的工具 ID
useEffect(() => {
  const state = location.state as { openToolId?: string } | null;
  if (state?.openToolId && tools.length > 0) {
    const tool = tools.find((t) => t.id === state.openToolId);
    if (tool) {
      addTab({ id: tool.id, title: tool.title, icon: tool.icon });
    }
    // 清除 state，避免刷新后重复触发
    window.history.replaceState({}, '');
  }
}, [location.state, tools, addTab]);
```

- [ ] **Step 4: 验证编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Workspace/WorkspacePage.tsx
git commit -m "feat(workspace): 添加 /workspace 路由，首页点击工具跳转到工作区"
```

---

### Task 8: i18n 翻译

**Files:**
- Modify: `frontend/src/i18n/locales/zh-CN.ts`
- Modify: `frontend/src/i18n/locales/en-US.ts`

- [ ] **Step 1: 添加中文翻译**

在 `frontend/src/i18n/locales/zh-CN.ts` 中，在 `common` 对象内添加：

```typescript
// 在 common 对象中添加
workspace: {
  home: '返回首页',
  toolList: '工具列表',
  closeTab: '关闭标签',
  collapseSidebar: '折叠侧边栏',
  expandSidebar: '展开侧边栏',
  welcome: '开始使用',
  welcomeHint: '从左侧工具列表选择一个工具，或点击下方快捷入口',
  unknownTool: '未知工具',
},
```

- [ ] **Step 2: 添加英文翻译**

在 `frontend/src/i18n/locales/en-US.ts` 中，在 `common` 对象内添加：

```typescript
workspace: {
  home: 'Go Home',
  toolList: 'Tool List',
  closeTab: 'Close Tab',
  collapseSidebar: 'Collapse Sidebar',
  expandSidebar: 'Expand Sidebar',
  welcome: 'Get Started',
  welcomeHint: 'Select a tool from the sidebar or use quick access below',
  unknownTool: 'Unknown Tool',
},
```

- [ ] **Step 3: 替换硬编码文本为 i18n**

更新各 Workspace 组件中的硬编码中文：

- `WorkspaceSidebar.tsx`: `返回首页` → `t.workspace.home`
- `WorkspaceSidebar.tsx`: `工具列表` → `t.workspace.toolList`
- `EmptyWorkspace.tsx`: `开始使用` → `t.workspace.welcome`
- `EmptyWorkspace.tsx`: `从左侧工具列表...` → `t.workspace.welcomeHint`
- `TabBar.tsx`: `关闭标签` → `t.workspace.closeTab`

每个组件需要添加 `const { t } = useI18n();` import。

- [ ] **Step 4: 验证编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/i18n/locales/zh-CN.ts frontend/src/i18n/locales/en-US.ts frontend/src/components/Workspace/
git commit -m "feat(workspace): 添加工作区 i18n 翻译（中英文）"
```

---

### Task 9: 浏览器验证

- [ ] **Step 1: 启动服务**

```bash
python dev-services.py restart frontend
```

- [ ] **Step 2: 验证清单**

在浏览器中访问 `http://localhost:5178`，逐项验证：

1. ✅ 首页正常显示工具卡片网格
2. ✅ 点击工具卡片 → 跳转到 `/workspace`
3. ✅ 工作区左侧显示工具列表，Header 不显示
4. ✅ 工作区顶部标签栏显示打开的工具
5. ✅ 点击左侧另一个工具 → 新增标签
6. ✅ 切换标签 → 内容切换，状态保持
7. ✅ 点击标签 × → 关闭标签
8. ✅ 关闭最后一个标签 → 显示欢迎页
9. ✅ 点击"返回首页" → 跳回 `/`
10. ✅ 刷新页面 → 标签列表恢复
11. ✅ 侧边栏折叠/展开正常
12. ✅ 浏览器 Console 无错误

- [ ] **Step 3: 如有问题，修复后重新验证**

---

## 总结

本计划共 9 个任务：

1. **Task 1**: 工作区 Zustand Store（标签状态管理）
2. **Task 2**: TabBar 浏览器风格标签栏
3. **Task 3**: TabPanels 状态保持核心（display:none）
4. **Task 4**: WorkspaceSidebar 左侧工具列表
5. **Task 5**: EmptyWorkspace 欢迎页
6. **Task 6**: WorkspacePage 容器
7. **Task 7**: 路由集成 + 首页跳转
8. **Task 8**: i18n 翻译
9. **Task 9**: 浏览器验证

**关键设计决策**：
- 所有标签保持挂载（`display: none`），状态完全保留
- Zustand `persist` 中间件持久化标签列表到 localStorage
- 工具组件映射（`toolComponentMap`）集中管理
- 首页 → 工作区通过 `navigate state` 传递工具 ID
