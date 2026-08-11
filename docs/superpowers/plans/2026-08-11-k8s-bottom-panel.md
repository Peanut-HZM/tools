# K8s 控制台底部多标签页面板实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将右侧 Pod 详情抽屉改为底部多标签页面板，支持同时打开多个 Pod 的详情，每个标签页独立，类似浏览器标签页体验。

**Architecture:** 在 k8sStore 中新增 openedTabs 和 activeTabId 状态管理多标签，新建 BottomPanel 组件渲染底部面板和标签栏，修改 PodList 点击行为从 setSelectedResource 改为 openResourceTab。

**Tech Stack:** React 18, TypeScript, Zustand, Tailwind CSS, @tanstack/react-query v5

## Global Constraints

- 所有对话、文档、注释、日志、提交信息必须使用中文
- 修改前后端代码后，必须使用浏览器进行验证
- 前端端口 5178，后端端口 19092
- 服务重启统一用 `python dev-services.py restart`
- TypeScript 文件修改后需验证编译无错误
- 每个任务需编写测试并验证通过

---

### Task 1: 修改 k8sStore 添加多标签页状态

**Files:**
- Modify: `frontend/src/stores/k8sStore.ts`

**Interfaces:**
- Produces: `openedTabs: ResourceTab[]`, `activeTabId: string | null`, `openResourceTab()`, `closeResourceTab()`, `setActiveTab()`, `clearAllTabs()`

- [ ] **Step 1: 定义 ResourceTab 类型**

```typescript
// 新增在 k8sStore.ts 顶部
interface ResourceTab {
  id: string;  // 唯一标识：{type}-{namespace}-{name}
  type: string;  // 'pod' | 'deployment' | ...
  namespace: string;
  name: string;
}
```

- [ ] **Step 2: 添加新状态到 K8sStore interface**

```typescript
interface K8sStore {
  // ... 现有状态 ...
  
  // 新增：多标签页管理
  openedTabs: ResourceTab[];
  activeTabId: string | null;
}
```

- [ ] **Step 3: 添加初始状态**

```typescript
export const useK8sStore = create<K8sStore>()((set) => ({
  // ... 现有初始状态 ...
  
  // 新增初始状态
  openedTabs: [],
  activeTabId: null,
}));
```

- [ ] **Step 4: 添加 Actions 到 interface**

```typescript
interface K8sStore {
  // ... 现有 actions ...
  
  // 新增：多标签页管理
  openResourceTab: (resource: ResourceTab) => void;
  closeResourceTab: (tabId: string) => void;
  setActiveTab: (tabId: string) => void;
  clearAllTabs: () => void;
}
```

- [ ] **Step 5: 实现 openResourceTab**

```typescript
// 在 create() 的 set 中添加
openResourceTab: (resource) =>
  set((s) => {
    // 如果标签已存在，直接切换
    const exists = s.openedTabs.find(t => t.id === resource.id);
    if (exists) {
      return { activeTabId: resource.id };
    }
    // 否则添加新标签并激活
    return {
      openedTabs: [...s.openedTabs, resource],
      activeTabId: resource.id,
    };
  }),
```

- [ ] **Step 6: 实现 closeResourceTab**

```typescript
closeResourceTab: (tabId) =>
  set((s) => {
    const newTabs = s.openedTabs.filter(t => t.id !== tabId);
    // 如果关闭的是当前激活的标签，激活最后一个
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
```

- [ ] **Step 7: 实现 setActiveTab 和 clearAllTabs**

```typescript
setActiveTab: (tabId) => set({ activeTabId: tabId }),

clearAllTabs: () => set({ openedTabs: [], activeTabId: null }),
```

- [ ] **Step 8: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误（或仅其他模块的既有错误）

- [ ] **Step 9: Commit**

```bash
git add frontend/src/stores/k8sStore.ts
git commit -m "feat(k8s): 添加多标签页状态管理到 k8sStore"
```

---

### Task 2: 新建 BottomPanel 组件

**Files:**
- Create: `frontend/src/components/Tools/K8sTool/BottomPanel/BottomPanel.tsx`
- Create: `frontend/src/components/Tools/K8sTool/BottomPanel/TabBar.tsx`

**Interfaces:**
- Consumes: `useK8sStore` 的 `openedTabs`, `activeTabId`, `closeResourceTab`, `setActiveTab`
- Produces: 底部多标签页面板 UI

- [ ] **Step 1: 创建 BottomPanel.tsx 基础结构**

```typescript
/**
 * K8s 底部多标签页面板
 * 
 * 替代原有的右侧 PodDetail 抽屉
 * 支持同时打开多个资源的详情，每个标签页独立
 */
import React, { useState } from 'react';
import { useK8sStore } from '../../../stores/k8sStore';
import { TabBar } from './TabBar';
import { PodDetail } from '../ResourceDetail/PodDetail';

const DEFAULT_HEIGHT = '50vh';
const MIN_HEIGHT = 300;
const MAX_HEIGHT_PERCENT = 70;

export const BottomPanel: React.FC = () => {
  const { openedTabs, activeTabId } = useK8sStore();
  const [panelHeight, setPanelHeight] = useState(DEFAULT_HEIGHT);
  const [isDragging, setIsDragging] = useState(false);

  // 如果没有打开的标签，不渲染
  if (openedTabs.length === 0) return null;

  return (
    <div
      className="absolute bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-700 z-40 shadow-2xl animate-slide-in-bottom"
      style={{ height: panelHeight }}
    >
      {/* 标签栏 */}
      <TabBar />

      {/* 可拖动分隔条 */}
      <div
        onMouseDown={(e) => {
          setIsDragging(true);
          e.preventDefault();
        }}
        className={`h-1 bg-slate-700 hover:bg-blue-500 cursor-row-resize transition-colors ${
          isDragging ? 'bg-blue-500' : ''
        }`}
      />

      {/* 内容区域 */}
      <div className="flex-1 overflow-hidden">
        {activeTabId && (
          <PodDetail tabId={activeTabId} />
        )}
      </div>
    </div>
  );
};
```

- [ ] **Step 2: 创建 TabBar.tsx**

```typescript
/**
 * 底部面板的标签栏组件
 * 显示所有打开的资源标签，支持切换和关闭
 */
import React from 'react';
import { useK8sStore } from '../../../stores/k8sStore';

export const TabBar: React.FC = () => {
  const { openedTabs, activeTabId, setActiveTab, closeResourceTab } = useK8sStore();

  return (
    <div className="flex items-center gap-1 px-2 py-1 bg-slate-800 border-b border-slate-700 overflow-x-auto">
      {openedTabs.map((tab) => {
        const isActive = tab.id === activeTabId;
        return (
          <div
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded cursor-pointer transition-colors ${
              isActive
                ? 'bg-blue-600/20 text-blue-300 border border-blue-500/40'
                : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700 hover:text-slate-200 border border-transparent'
            }`}
          >
            <i className="fas fa-cube text-xs"></i>
            <span className="text-xs truncate max-w-[150px]">{tab.name}</span>
            <span className="text-[10px] text-slate-500">{tab.namespace}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                closeResourceTab(tab.id);
              }}
              className="ml-1 text-slate-500 hover:text-red-400 transition-colors"
              title="关闭标签"
            >
              <i className="fas fa-times text-xs"></i>
            </button>
          </div>
        );
      })}

      {openedTabs.length === 0 && (
        <div className="text-xs text-slate-500 px-2">
          点击 Pod 行打开详情
        </div>
      )}
    </div>
  );
};
```

- [ ] **Step 3: 添加底部滑出动画样式**

在 `frontend/src/index.css` 或 Tailwind 配置中添加：

```css
@keyframes slide-in-bottom {
  from {
    transform: translateY(100%);
  }
  to {
    transform: translateY(0);
  }
}

.animate-slide-in-bottom {
  animation: slide-in-bottom 0.3s ease-out;
}
```

- [ ] **Step 4: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Tools/K8sTool/BottomPanel/
git commit -m "feat(k8s): 新建底部多标签页面板组件"
```

---

### Task 3: 修改 PodDetail 支持 tabId prop

**Files:**
- Modify: `frontend/src/components/Tools/K8sTool/ResourceDetail/PodDetail.tsx`

**Interfaces:**
- Consumes: `tabId` prop
- Produces: 根据 tabId 从 store 读取对应资源信息

- [ ] **Step 1: 修改 PodDetail Props**

```typescript
interface PodDetailProps {
  tabId?: string;  // 新增：从 BottomPanel 传入的标签 ID
}

export const PodDetail: React.FC<PodDetailProps> = ({ tabId }) => {
  // ...
};
```

- [ ] **Step 2: 修改资源读取逻辑**

```typescript
export const PodDetail: React.FC<PodDetailProps> = ({ tabId }) => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const { activeConnectionId, openedTabs, activeTabId } = useK8sStore();
  
  // 如果没有传 tabId，使用 store 中的 activeTabId
  const currentTabId = tabId || activeTabId;
  
  // 从 openedTabs 中查找当前标签
  const currentTab = openedTabs.find(t => t.id === currentTabId);
  
  const [activeTab, setActiveTab] = useState<string>('overview');

  // 如果没有找到标签，不渲染
  if (!currentTab) return null;

  // 获取 Pod 详情（使用 currentTab 的 namespace 和 name）
  const {
    data: pod,
    isLoading,
    isError,
  } = useQuery({
    queryKey: [
      'k8s',
      activeConnectionId,
      'pod',
      currentTab.name,
      currentTab.namespace,
    ],
    queryFn: () =>
      api.getPodDetail(
        activeConnectionId!,
        currentTab.name,
        currentTab.namespace,
      ),
    enabled:
      !!activeConnectionId &&
      currentTab.type === 'pod',
  });

  // ... 其余逻辑保持不变 ...
};
```

- [ ] **Step 3: 移除原有的 selectedResource 依赖**

```typescript
// 删除或注释掉这些代码
// const { selectedResource, setSelectedResource } = useK8sStore();
// if (!selectedResource) return null;
```

- [ ] **Step 4: 修改关闭逻辑**

```typescript
/** 关闭标签（由 BottomPanel 的 TabBar 处理） */
// 移除原有的 handleClose 函数
// const handleClose = () => setSelectedResource(null);
```

- [ ] **Step 5: 修改头部显示**

```typescript
{/* 头部：标题 + 状态 */}
<div className="flex items-center justify-between px-4 py-3 border-b border-slate-700 bg-slate-800/50 shrink-0">
  <div className="flex items-center gap-2">
    <i className="fas fa-cube text-blue-400"></i>
    <h3 className="text-sm font-semibold text-slate-100 truncate max-w-[300px]">
      {currentTab?.name}
    </h3>
    <span className="text-xs text-slate-500 font-mono">
      {currentTab?.namespace}
    </span>
    {pod?.phase && (
      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
        pod.phase === 'Running'
          ? 'bg-green-500/20 text-green-400 border border-green-500/30'
          : pod.phase === 'Failed'
          ? 'bg-red-500/20 text-red-400 border border-red-500/30'
          : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
      }`}>
        {pod.phase}
      </span>
    )}
  </div>

  {/* 移除关闭按钮，由 TabBar 处理 */}
</div>
```

- [ ] **Step 6: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/Tools/K8sTool/ResourceDetail/PodDetail.tsx
git commit -m "feat(k8s): 修改 PodDetail 支持 tabId prop"
```

---

### Task 4: 修改 PodList 点击行为

**Files:**
- Modify: `frontend/src/components/Tools/K8sTool/ResourceTabs/PodList.tsx`

**Interfaces:**
- Consumes: `useK8sStore.openResourceTab`
- Produces: 点击行时打开标签页

- [ ] **Step 1: 修改 handleRowClick**

```typescript
// 修改前
const handleRowClick = (pod: typeof pods[0]) => {
  setSelectedResource({
    type: 'pod',
    namespace: pod.namespace,
    name: pod.name,
  });
};

// 修改后
const handleRowClick = (pod: typeof pods[0]) => {
  openResourceTab({
    id: `pod-${pod.namespace}-${pod.name}`,
    type: 'pod',
    namespace: pod.namespace,
    name: pod.name,
  });
};
```

- [ ] **Step 2: 更新 store 引用**

```typescript
// 修改 store 解构
const { activeConnectionId, selectedNamespaces, openResourceTab } = useK8sStore();

// 删除 setSelectedResource（如果不再使用）
```

- [ ] **Step 3: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Tools/K8sTool/ResourceTabs/PodList.tsx
git commit -m "feat(k8s): 修改 PodList 点击行为为打开标签页"
```

---

### Task 5: 修改 K8sTool 使用 BottomPanel

**Files:**
- Modify: `frontend/src/components/Tools/K8sTool/K8sTool.tsx`

**Interfaces:**
- Consumes: `BottomPanel` 组件
- Produces: 主布局集成底部面板

- [ ] **Step 1: 导入 BottomPanel**

```typescript
// 删除
import { PodDetail } from './ResourceDetail/PodDetail';

// 新增
import { BottomPanel } from './BottomPanel/BottomPanel';
```

- [ ] **Step 2: 移除 selectedResource 引用**

```typescript
// 修改前
const { connections, activeConnectionId, setActiveConnection, setConnections, selectedResource } = useK8sStore();

// 修改后
const { connections, activeConnectionId, setActiveConnection, setConnections } = useK8sStore();
```

- [ ] **Step 3: 替换 PodDetail 为 BottomPanel**

```typescript
// 修改前
{selectedResource && <PodDetail />}

// 修改后
<BottomPanel />
```

- [ ] **Step 4: 移除 selectedResource 相关逻辑**

删除所有 `selectedResource` 的使用（如果有）。

- [ ] **Step 5: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Tools/K8sTool/K8sTool.tsx
git commit -m "feat(k8s): 集成 BottomPanel 替代 PodDetail 抽屉"
```

---

### Task 6: 添加可拖动高度调整功能

**Files:**
- Modify: `frontend/src/components/Tools/K8sTool/BottomPanel/BottomPanel.tsx`

**Interfaces:**
- Produces: 可拖动调整面板高度（300px - 70vh）

- [ ] **Step 1: 添加拖动状态和 Refs**

```typescript
const [panelHeight, setPanelHeight] = useState(DEFAULT_HEIGHT);
const [isDragging, setIsDragging] = useState(false);
const dragStartYRef = useRef(0);
const dragStartHeightRef = useRef(0);
```

- [ ] **Step 2: 实现拖动开始**

```typescript
const handleDragStart = (e: React.MouseEvent) => {
  setIsDragging(true);
  dragStartYRef.current = e.clientY;
  // 解析当前高度（px 或 vh）
  const currentHeight = panelHeight;
  if (currentHeight.endsWith('vh')) {
    dragStartHeightRef.current = (parseFloat(currentHeight) / 100) * window.innerHeight;
  } else {
    dragStartHeightRef.current = parseFloat(currentHeight);
  }
  e.preventDefault();
};
```

- [ ] **Step 3: 实现拖动中（useEffect）**

```typescript
useEffect(() => {
  if (!isDragging) return;

  const handleMouseMove = (e: MouseEvent) => {
    const deltaY = dragStartYRef.current - e.clientY;  // 向上拖动增加高度
    const newHeight = Math.max(
      MIN_HEIGHT,
      Math.min(
        (MAX_HEIGHT_PERCENT / 100) * window.innerHeight,
        dragStartHeightRef.current + deltaY
      )
    );
    setPanelHeight(`${newHeight}px`);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);

  return () => {
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };
}, [isDragging]);
```

- [ ] **Step 4: 绑定拖动事件到分隔条**

```typescript
{/* 可拖动分隔条 */}
<div
  onMouseDown={handleDragStart}
  className={`h-1 bg-slate-700 hover:bg-blue-500 cursor-row-resize transition-colors ${
    isDragging ? 'bg-blue-500' : ''
  }`}
  style={{ cursor: 'row-resize' }}
/>
```

- [ ] **Step 5: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Tools/K8sTool/BottomPanel/BottomPanel.tsx
git commit -m "feat(k8s): 实现底部面板高度可拖动调整"
```

---

### Task 7: 优化标签栏样式和交互

**Files:**
- Modify: `frontend/src/components/Tools/K8sTool/BottomPanel/TabBar.tsx`

**Interfaces:**
- Produces: 美观的标签栏 UI，支持 hover、激活状态、状态指示

- [ ] **Step 1: 添加状态指示器**

```typescript
// 根据资源类型和状态显示不同图标
const getStatusIcon = (tab: ResourceTab) => {
  // 可以通过 query 获取 pod 状态，这里先用通用图标
  return 'fas fa-cube';
};
```

- [ ] **Step 2: 优化标签样式**

```typescript
<div
  key={tab.id}
  onClick={() => setActiveTab(tab.id)}
  className={`flex items-center gap-2 px-3 py-1.5 rounded cursor-pointer transition-colors min-w-[120px] max-w-[200px] ${
    isActive
      ? 'bg-blue-600/20 text-blue-300 border border-blue-500/40'
      : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700 hover:text-slate-200 border border-transparent'
  }`}
>
  <i className={`${getStatusIcon(tab)} text-xs`}></i>
  <span className="text-xs truncate flex-1">{tab.name}</span>
  <span className="text-[10px] text-slate-500 flex-shrink-0">{tab.namespace}</span>
  <button
    onClick={(e) => {
      e.stopPropagation();
      closeResourceTab(tab.id);
    }}
    className={`ml-1 transition-colors ${
      isActive ? 'text-blue-400 hover:text-red-400' : 'text-slate-500 hover:text-red-400'
    }`}
    title="关闭标签"
  >
    <i className="fas fa-times text-xs"></i>
  </button>
</div>
```

- [ ] **Step 3: 添加标签数量限制（最多 10 个）**

在 `openResourceTab` action 中添加：

```typescript
openResourceTab: (resource) =>
  set((s) => {
    // 限制最多 10 个标签
    if (s.openedTabs.length >= 10) {
      // 可以显示 toast 提示，这里简单返回
      return {};
    }
    // ... 其余逻辑
  }),
```

- [ ] **Step 4: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Tools/K8sTool/BottomPanel/TabBar.tsx
git add frontend/src/stores/k8sStore.ts
git commit -m "feat(k8s): 优化标签栏样式和交互"
```

---

### Task 8: 清理废弃代码和兼容性处理

**Files:**
- Modify: `frontend/src/stores/k8sStore.ts`
- Modify: `frontend/src/components/Tools/K8sTool/ResourceTabs/WorkloadList.tsx`
- Modify: `frontend/src/components/Tools/K8sTool/ResourceTabs/NodeList.tsx`
- Modify: `frontend/src/components/Tools/K8sTool/ResourceTabs/EventsList.tsx`

**Interfaces:**
- Produces: 清理 selectedResource 相关代码，统一使用新的多标签 API

- [ ] **Step 1: 标记 selectedResource 为 deprecated**

```typescript
interface K8sStore {
  // ... 
  /** @deprecated 使用 openedTabs 和 activeTabId 替代 */
  selectedResource: SelectedResource | null;
  /** @deprecated 使用 openResourceTab 替代 */
  setSelectedResource: (r: SelectedResource | null) => void;
}
```

- [ ] **Step 2: 更新其他列表组件（可选，逐步迁移）**

对于 WorkloadList、NodeList、EventsList，暂时保持使用 `setSelectedResource`，后续逐步迁移到 `openResourceTab`。

- [ ] **Step 3: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/stores/k8sStore.ts
git commit -m "refactor(k8s): 标记 selectedResource 为 deprecated"
```

---

### Task 9: 浏览器验证和功能测试

**Files:**
- 无文件修改（纯测试任务）

- [ ] **Step 1: 重启前端服务**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
python dev-services.py restart frontend
```

- [ ] **Step 2: 打开 K8s 控制台**

访问：http://localhost:5178/tools/k8s-tool

- [ ] **Step 3: 验证核心功能**

- [ ] 3.1: 选择一个连接，进入 Pod 列表
- [ ] 3.2: 点击一个 Pod 行，验证底部面板弹出
- [ ] 3.3: 验证标签栏显示该 Pod 的标签
- [ ] 3.4: 点击另一个 Pod 行，验证打开新标签
- [ ] 3.5: 点击标签栏切换不同 Pod
- [ ] 3.6: 点击标签的 × 按钮关闭标签
- [ ] 3.7: 拖动分隔条调整面板高度
- [ ] 3.8: 验证每个标签页内的 8 个子 Tab 功能正常
- [ ] 3.9: 验证日志查看器功能（实时日志、下载、搜索）
- [ ] 3.10: 验证终端功能（WebSocket 连接、命令执行）

- [ ] **Step 4: 验证浏览器 Console 无错误**

打开浏览器 DevTools，检查 Console 标签页无红色错误。

- [ ] **Step 5: 验证页面布局**

- [ ] 5.1: 左侧面板正常显示
- [ ] 5.2: 中间 Pod 列表正常显示
- [ ] 5.3: 底部面板不遮挡 Pod 列表（可滚动）
- [ ] 5.4: 响应式布局正常（调整窗口大小）

---

### Task 10: 性能优化（可选）

**Files:**
- Modify: `frontend/src/components/Tools/K8sTool/BottomPanel/TabBar.tsx`
- Modify: `frontend/src/components/Tools/K8sTool/BottomPanel/BottomPanel.tsx`

**Interfaces:**
- Produces: 优化多标签页性能

- [ ] **Step 1: 使用 React.memo 优化 TabBar**

```typescript
export const TabBar: React.FC = React.memo(() => {
  // ...
});
```

- [ ] **Step 2: 使用 React.memo 优化 BottomPanel**

```typescript
export const BottomPanel: React.FC = React.memo(() => {
  // ...
});
```

- [ ] **Step 3: 清理非激活标签的 query cache**

```typescript
// 在 closeResourceTab 中添加
import { useQueryClient } from '@tanstack/react-query';

closeResourceTab: (tabId) =>
  set((s) => {
    const tab = s.openedTabs.find(t => t.id === tabId);
    if (tab) {
      // 清理该标签的 query cache
      queryClient.removeQueries({
        queryKey: ['k8s', s.activeConnectionId, 'pod', tab.name, tab.namespace],
      });
    }
    // ... 其余逻辑
  }),
```

- [ ] **Step 4: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Tools/K8sTool/BottomPanel/
git add frontend/src/stores/k8sStore.ts
git commit -m "perf(k8s): 优化底部多标签页面板性能"
```

---

## 总结

本实现计划共 10 个任务，按顺序执行：

1. **Task 1**: 修改 k8sStore 添加多标签页状态
2. **Task 2**: 新建 BottomPanel 和 TabBar 组件
3. **Task 3**: 修改 PodDetail 支持 tabId prop
4. **Task 4**: 修改 PodList 点击行为
5. **Task 5**: 修改 K8sTool 集成 BottomPanel
6. **Task 6**: 添加可拖动高度调整
7. **Task 7**: 优化标签栏样式和交互
8. **Task 8**: 清理废弃代码
9. **Task 9**: 浏览器验证和功能测试
10. **Task 10**: 性能优化（可选）

每个任务都是独立的，可以单独测试和验证。建议按顺序执行，确保每一步都稳定后再进行下一步。

**预计总工时**: 4-6 小时（包含测试和调试）
