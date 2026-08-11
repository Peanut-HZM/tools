# K8s 控制台终端修复设计文档

**日期**: 2026-08-11  
**状态**: 待实现  
**优先级**: 高  

---

## 问题描述

### 问题 1：终端无法输入命令

**现象**：终端显示"[已连接]"，但键盘输入完全无响应（无字符回显，光标不移动）。

**根因**：切换到"终端"子 Tab 时，xterm 终端不会自动获得焦点。`terminal.focus()` 仅在 WebSocket 连接成功时调用一次（`socket.onopen`），之后用户切换 Tab 再切回来，终端处于失焦状态，键盘事件被浏览器拦截，无法传递给 xterm。

**当前代码位置**：
- `frontend/src/components/Tools/K8sTool/TerminalPanel/K8sTerminalPanel.tsx:82` — `terminal.focus()` 仅在 `onopen` 调用
- `frontend/src/components/Tools/K8sTool/TerminalPanel/K8sTerminalPanel.tsx:188-204` — `isActive` useEffect 只做 fit/resize，没有 focus
- `frontend/src/components/Tools/K8sTool/TerminalPanel/K8sTerminalPanel.tsx:270-271` — 点击终端区域手动聚焦

**影响**：用户每次切换到终端 Tab，必须手动点击终端区域才能输入，体验差且不符合直觉。

---

### 问题 2：子 Tab 状态不持久化

**现象**：用户在 Pod A 的"日志"子 Tab 查看日志，切换到 Pod B，再切回 Pod A，子 Tab 被重置为"概览"。

**根因**：`activeTab`（子 Tab 状态）是 `PodDetail` 组件内部的 `useState`。当用户切换标签页时，BottomPanel 的渲染逻辑 `activeTabId && <PodDetail tabId={activeTabId} />` 导致 PodDetail 组件实例被重新创建（因为 `tabId` prop 变化），内部 state 丢失，重置为初始值 `'overview'`。

**当前代码位置**：
- `frontend/src/components/Tools/K8sTool/ResourceDetail/PodDetail.tsx:59` — `const [activeTab, setActiveTab] = useState<string>('overview');`
- `frontend/src/components/Tools/K8sTool/BottomPanel/BottomPanel.tsx:66` — `<PodDetail tabId={activeTabId} />`

**影响**：用户无法在不同 Pod 间保持查看的上下文，需要重新切换到目标子 Tab，效率低。

---

## 解决方案

### 方案 1：终端自动聚焦（问题 1）

**改动文件**：`TerminalPanel/K8sTerminalPanel.tsx`

**方案**：在 `isActive` useEffect 中添加 `terminal.focus()` 调用，确保切换到终端 Tab 时自动聚焦。

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
    // 新增：自动聚焦终端
    terminal.focus();
  }, 0);
  return () => clearTimeout(tid);
}, [isActive]);
```

**优点**：
- 改动小，风险低
- 符合用户预期（切换 Tab 自动聚焦）
- 不影响现有功能

---

### 方案 2：子 Tab 状态持久化（问题 2）

**改动文件**：
- `frontend/src/stores/k8sStore.ts`
- `frontend/src/components/Tools/K8sTool/ResourceDetail/PodDetail.tsx`

**方案**：将 `activeTab` 状态提升到 k8sStore，按 tabId 维度存储每个标签的子 Tab 状态。

#### 2.1 k8sStore 新增状态

```typescript
// 在 K8sStore interface 中添加
interface K8sStore {
  // ... 现有状态
  
  /** 每个标签页的活跃子 Tab（key: tabId, value: subTabKey） */
  activeSubTabs: Record<string, string>;
  setActiveSubTab: (tabId: string, subTabKey: string) => void;
}

// 初始状态
export const useK8sStore = create<K8sStore>()((set) => ({
  // ... 现有初始状态
  activeSubTabs: {},
}));

// action 实现
setActiveSubTab: (tabId, subTabKey) =>
  set((s) => ({
    activeSubTabs: { ...s.activeSubTabs, [tabId]: subTabKey }
  })),
```

#### 2.2 PodDetail 修改

```typescript
// 修改前
const { activeConnectionId, openedTabs, activeTabId } = useK8sStore();
const [activeTab, setActiveTab] = useState<string>('overview');

// 修改后
const { activeConnectionId, openedTabs, activeTabId, activeSubTabs, setActiveSubTab } = useK8sStore();
const currentTabId = tabId || activeTabId;
const activeTab = activeSubTabs[currentTabId || ''] || 'overview';

// 切换子 Tab 时
const handleTabChange = (key: string) => {
  if (currentTabId) {
    setActiveSubTab(currentTabId, key);
  }
};
```

#### 2.3 清理逻辑

当标签关闭时，清理对应的子 Tab 状态（可选，避免内存泄漏）：

```typescript
// 在 closeResourceTab action 中添加
closeResourceTab: (tabId) =>
  set((s) => {
    const newTabs = s.openedTabs.filter(t => t.id !== tabId);
    const { [tabId]: _, ...remainingSubTabs } = s.activeSubTabs;
    // ... 其余逻辑
    return {
      openedTabs: newTabs,
      activeSubTabs: remainingSubTabs,
      // ...
    };
  }),
```

---

## 数据流

### 问题 1 修复后

```
用户切换 Tab 到"终端"
    ↓
activeTab === 'terminal'
    ↓
K8sTerminalPanel isActive=true
    ↓
useEffect 触发
    ↓
fit.fit() + resize + terminal.focus()
    ↓
终端获得焦点，键盘输入正常
```

### 问题 2 修复后

```
用户在 Pod A 切换到"日志"子 Tab
    ↓
handleTabChange('logs')
    ↓
setActiveSubTab(tabId, 'logs')
    ↓
store.activeSubTabs[tabId] = 'logs'
    ↓
用户切换到 Pod B，再切回 Pod A
    ↓
PodDetail 读取 activeSubTabs[tabId] = 'logs'
    ↓
activeTab = 'logs'（保持之前状态）
    ↓
渲染 LogsViewer
```

---

## 测试计划

### 问题 1 测试

1. 打开 Pod 详情，切换到"终端"子 Tab
2. 验证终端自动获得焦点（光标闪烁，可直接输入）
3. 输入命令，验证回显正常
4. 切换到其他子 Tab（如"概览"），再切回"终端"
5. 验证终端重新自动聚焦，可继续输入

### 问题 2 测试

1. 打开 Pod A，切换到"日志"子 Tab
2. 切换到 Pod B，验证 Pod B 显示"概览"（默认）
3. 切回 Pod A，验证仍显示"日志"子 Tab
4. 在 Pod A 切换到"终端"，再切到 Pod B 的"容器"
5. 来回切换 Pod A 和 Pod B，验证各自保持子 Tab 状态
6. 关闭 Pod A 标签，重新打开 Pod A，验证子 Tab 重置为"概览"（状态已清理）

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 状态提升后组件渲染逻辑变化 | 中 | 保留原有 UI 结构，仅数据源从 useState 改为 store |
| 多个标签同时聚焦终端 | 低 | 每个终端实例独立，focus 互不干扰 |
| activeSubTabs 内存增长 | 低 | 标签关闭时清理对应 key；最多 10 个标签，影响可控 |

---

## 后续扩展

1. **子 Tab 状态持久化到 localStorage**：刷新页面后恢复子 Tab 状态（可选）
2. **终端输入历史**：记录命令历史，支持上下键浏览（可选）
3. **终端字体大小调整**：用户自定义终端字体（可选）

---

## 验收标准

- [ ] 切换到终端 Tab 时自动聚焦，可直接输入命令
- [ ] 终端输入命令有回显，Enter 执行命令有输出
- [ ] 切换 Pod 时，子 Tab 状态保持（不重置为概览）
- [ ] 不同 Pod 的子 Tab 状态独立（互不干扰）
- [ ] 关闭标签后重新打开，子 Tab 重置为概览（状态清理）
- [ ] 浏览器 Console 无错误

---

**下一步**: 用户 review 本文档后，调用 writing-plans skill 生成详细实现计划。
