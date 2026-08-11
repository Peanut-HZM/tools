# K8s 终端修复与子 Tab 持久化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复终端 Tab 切换后无法输入命令的问题，并将子 Tab 状态（概览/容器/日志/终端/YAML/事件/指标/关联资源）持久化到 store，切换 Pod 时保持子 Tab 选择。

**Architecture:** 将子 Tab 状态从 PodDetail 组件内部 useState 提升到 k8sStore 的 activeSubTabs 字段（按 tabId 维度存储）。终端组件在 isActive 变为 true 时自动调用 terminal.focus()。关闭标签时清理对应的 activeSubTabs 条目。

**Tech Stack:** React 18, TypeScript, Zustand, xterm.js

## Global Constraints

- 所有对话、文档、注释、日志、提交信息必须使用中文
- 修改前后端代码后，必须使用浏览器进行验证
- 前端端口 5178，后端端口 19092
- 服务重启统一用 `python dev-services.py restart`
- TypeScript 文件修改后需验证编译无错误
- 每个任务需编写测试并验证通过

---

### Task 1: k8sStore 新增 activeSubTabs 状态管理

**Files:**
- Modify: `frontend/src/stores/k8sStore.ts`

**Interfaces:**
- Produces: `activeSubTabs: Record<string, string>`, `setActiveSubTab(tabId, subTabKey)`

- [ ] **Step 1: 在 K8sStore interface 中添加新字段和 action**

在 `K8sStore` interface 中添加：
```typescript
/** 每个标签页的活跃子 Tab（key: tabId, value: subTabKey） */
activeSubTabs: Record<string, string>;
setActiveSubTab: (tabId: string, subTabKey: string) => void;
```

- [ ] **Step 2: 添加初始状态**

在 `useK8sStore` 的 create set 中添加：
```typescript
activeSubTabs: {},
```

- [ ] **Step 3: 实现 setActiveSubTab action**

在 create set 中添加：
```typescript
setActiveSubTab: (tabId, subTabKey) =>
  set((s) => ({
    activeSubTabs: { ...s.activeSubTabs, [tabId]: subTabKey },
  })),
```

- [ ] **Step 4: 修改 closeResourceTab 清理逻辑**

修改 `closeResourceTab`，在删除标签时同时清理对应的 activeSubTabs 条目：
```typescript
closeResourceTab: (tabId) =>
  set((s) => {
    const newTabs = s.openedTabs.filter(t => t.id !== tabId);
    const { [tabId]: _, ...remainingSubTabs } = s.activeSubTabs;
    const newActiveId =
      s.activeTabId === tabId
        ? newTabs.length > 0
          ? newTabs[newTabs.length - 1].id
          : null
        : s.activeTabId;
    return {
      openedTabs: newTabs,
      activeTabId: newActiveId,
      activeSubTabs: remainingSubTabs,
    };
  }),
```

- [ ] **Step 5: 修改 clearAllTabs 也清理 activeSubTabs**

```typescript
clearAllTabs: () => set({ openedTabs: [], activeTabId: null, activeSubTabs: {} }),
```

- [ ] **Step 6: 添加测试**

在 `frontend/src/stores/k8sStore.test.ts` 中添加测试：
```typescript
describe('activeSubTabs 子 Tab 持久化', () => {
  beforeEach(() => {
    useK8sStore.getState().clearAllTabs();
  });

  test('setActiveSubTab 存储指定标签的子 Tab', () => {
    const { setActiveSubTab } = useK8sStore.getState();
    setActiveSubTab('tab-1', 'logs');
    expect(useK8sStore.getState().activeSubTabs['tab-1']).toBe('logs');
  });

  test('不同标签的子 Tab 状态独立', () => {
    const { setActiveSubTab } = useK8sStore.getState();
    setActiveSubTab('tab-1', 'logs');
    setActiveSubTab('tab-2', 'terminal');
    expect(useK8sStore.getState().activeSubTabs['tab-1']).toBe('logs');
    expect(useK8sStore.getState().activeSubTabs['tab-2']).toBe('terminal');
  });

  test('closeResourceTab 清理对应的 activeSubTabs 条目', () => {
    const { openResourceTab, setActiveSubTab, closeResourceTab } = useK8sStore.getState();
    openResourceTab({ id: 'tab-1', type: 'pod', namespace: 'default', name: 'a' });
    setActiveSubTab('tab-1', 'logs');
    closeResourceTab('tab-1');
    expect(useK8sStore.getState().activeSubTabs['tab-1']).toBeUndefined();
  });

  test('clearAllTabs 清空所有 activeSubTabs', () => {
    const { setActiveSubTab, clearAllTabs } = useK8sStore.getState();
    setActiveSubTab('tab-1', 'logs');
    setActiveSubTab('tab-2', 'terminal');
    clearAllTabs();
    expect(useK8sStore.getState().activeSubTabs).toEqual({});
  });
});
```

- [ ] **Step 7: 运行测试**

Run: `cd frontend && npx vitest run src/stores/k8sStore.test.ts`
Expected: 17 passed (13 existing + 4 new)

- [ ] **Step 8: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增错误

- [ ] **Step 9: Commit**

```bash
git add frontend/src/stores/k8sStore.ts frontend/src/stores/k8sStore.test.ts
git commit -m "feat(k8s): k8sStore 新增 activeSubTabs 子 Tab 持久化状态"
```

---

### Task 2: PodDetail 改用 store 中的 activeSubTabs

**Files:**
- Modify: `frontend/src/components/Tools/K8sTool/ResourceDetail/PodDetail.tsx`

**Interfaces:**
- Consumes: `useK8sStore.activeSubTabs`, `useK8sStore.setActiveSubTab`
- Produces: 子 Tab 状态跨 Pod 切换持久化

- [ ] **Step 1: 修改 store 解构**

将：
```typescript
const { activeConnectionId, openedTabs, activeTabId } = useK8sStore();
```
改为：
```typescript
const { activeConnectionId, openedTabs, activeTabId, activeSubTabs, setActiveSubTab } = useK8sStore();
```

- [ ] **Step 2: 替换 useState 为 store 读取**

删除：
```typescript
const [activeTab, setActiveTab] = useState<string>('overview');
```

新增（在 currentTabId 计算之后）：
```typescript
const activeTab = activeSubTabs[currentTabId || ''] || 'overview';
```

- [ ] **Step 3: 删除重置子 Tab 的 useEffect**

删除（第 77-79 行附近）：
```typescript
// 切换 Pod（currentTabId 变化）时，重置子 Tab 到 overview，
// 避免上一个 Pod 选择的子 Tab（例如 Logs / Terminal）误显示在新 Pod 上
useEffect(() => {
  setActiveTab('overview');
}, [currentTabId]);
```

- [ ] **Step 4: 修改子 Tab 切换逻辑**

找到所有 `setActiveTab(...)` 调用，替换为 `setActiveSubTab(currentTabId!, ...)`。

在子 Tab 按钮的 onClick 中，将：
```typescript
onClick={() => setActiveTab(tab.key)}
```
改为：
```typescript
onClick={() => {
  if (currentTabId) {
    setActiveSubTab(currentTabId, tab.key);
  }
}}
```

- [ ] **Step 5: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增错误

- [ ] **Step 6: 更新 PodDetail 测试**

修改 `frontend/src/components/Tools/K8sTool/ResourceDetail/PodDetail.test.tsx` 中的测试，确保 mock store 包含 `activeSubTabs` 和 `setActiveSubTab`：

在 mockStoreState 中添加：
```typescript
activeSubTabs: {},
setActiveSubTab: vi.fn((tabId, subTabKey) => {
  mockStoreState.activeSubTabs[tabId] = subTabKey;
}),
```

更新相关测试用例，验证子 Tab 切换调用 `setActiveSubTab` 而非 `setActiveTab`。

- [ ] **Step 7: 运行测试**

Run: `cd frontend && npx vitest run src/components/Tools/K8sTool/ResourceDetail/PodDetail.test.tsx`
Expected: 全部通过

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/Tools/K8sTool/ResourceDetail/PodDetail.tsx frontend/src/components/Tools/K8sTool/ResourceDetail/PodDetail.test.tsx
git commit -m "feat(k8s): PodDetail 子 Tab 状态持久化到 k8sStore"
```

---

### Task 3: 终端 Tab 切换自动聚焦

**Files:**
- Modify: `frontend/src/components/Tools/K8sTool/TerminalPanel/K8sTerminalPanel.tsx`

**Interfaces:**
- Consumes: `isActive` prop（已有）
- Produces: 切换到终端 Tab 时自动聚焦

- [ ] **Step 1: 在 isActive useEffect 中添加 terminal.focus()**

将当前的 isActive useEffect（约第 188-204 行）：
```typescript
// isActive 切换时执行 fit + resize
useEffect(() => {
  if (!isActive) return;
  const fit = fitAddonRef.current;
  const terminal = terminalInstance.current;
  const socket = socketRef.current;
  if (!fit || !terminal) return;

  const tid = setTimeout(() => {
    fit.fit();
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(
        JSON.stringify({ type: 'resize', cols: terminal.cols, rows: terminal.rows })
      );
    }
  }, 0);
  return () => clearTimeout(tid);
}, [isActive]);
```

改为：
```typescript
// isActive 切换时执行 fit + resize + focus
useEffect(() => {
  if (!isActive) return;
  const fit = fitAddonRef.current;
  const terminal = terminalInstance.current;
  const socket = socketRef.current;
  if (!fit || !terminal) return;

  const tid = setTimeout(() => {
    fit.fit();
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(
        JSON.stringify({ type: 'resize', cols: terminal.cols, rows: terminal.rows })
      );
    }
    // 自动聚焦终端，确保键盘输入可用
    terminal.focus();
  }, 0);
  return () => clearTimeout(tid);
}, [isActive]);
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无新增错误

- [ ] **Step 3: 运行测试**

Run: `cd frontend && npx vitest run`
Expected: 无回归

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Tools/K8sTool/TerminalPanel/K8sTerminalPanel.tsx
git commit -m "fix(k8s): 终端 Tab 切换时自动聚焦，修复无法输入命令"
```

---

### Task 4: 浏览器验证和功能测试

**Files:**
- 无文件修改（纯测试任务）

- [ ] **Step 1: 重启前端服务**

```bash
cd /Users/huazhongmin/IdeaProjects/tools
python dev-services.py restart frontend
```

- [ ] **Step 2: 验证终端自动聚焦**

- [ ] 2.1: 打开一个 Pod 的详情，切换到"终端"子 Tab
- [ ] 2.2: 验证终端自动获得焦点（光标闪烁，可直接输入）
- [ ] 2.3: 输入 `ls` 命令，验证有回显和输出
- [ ] 2.4: 切换到其他子 Tab（如"概览"），再切回"终端"
- [ ] 2.5: 验证终端重新自动聚焦，可继续输入

- [ ] **Step 3: 验证子 Tab 状态持久化**

- [ ] 3.1: 打开 Pod A，切换到"日志"子 Tab
- [ ] 3.2: 切换到 Pod B，验证 Pod B 默认显示"概览"
- [ ] 3.3: 切回 Pod A，验证仍显示"日志"子 Tab
- [ ] 3.4: 在 Pod A 切换到"终端"，验证终端可输入
- [ ] 3.5: 切到 Pod B 的"容器"子 Tab
- [ ] 3.6: 来回切换 Pod A 和 Pod B，验证各自保持子 Tab 状态
- [ ] 3.7: 关闭 Pod A 标签，重新打开 Pod A，验证子 Tab 重置为"概览"

- [ ] **Step 4: 验证浏览器 Console 无错误**

打开浏览器 DevTools，检查 Console 标签页无红色错误。

---

## 总结

本实现计划共 4 个任务，按顺序执行：

1. **Task 1**: k8sStore 新增 activeSubTabs 状态（含测试）
2. **Task 2**: PodDetail 改用 store 中的子 Tab 状态（含测试）
3. **Task 3**: 终端 Tab 切换自动聚焦
4. **Task 4**: 浏览器端到端验证

每个任务都是独立的，可以单独测试和验证。

**预计总工时**: 1-2 小时（包含测试和验证）
