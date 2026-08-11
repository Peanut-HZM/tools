# K8s 控制台底部多标签页面板设计文档

**日期**: 2026-08-11  
**状态**: 待实现  
**优先级**: 高  

---

## 问题描述

当前点击 Pod 后，右侧弹出 60% 宽度的抽屉面板。这种方式存在以下问题：
1. 只能同时查看一个 Pod 的详情
2. 右侧抽屉占用大量横向空间，影响左侧列表浏览
3. 切换 Pod 时需要关闭再重新打开，效率低

## 解决方案

将右侧抽屉改为**底部多标签页面板**，类似浏览器的标签页体验：

- **底部面板**：从底部滑出，占据屏幕高度的 50-70%（可拖动调整）
- **多标签页**：可以同时打开多个 Pod 的详情，每个标签页独立
- **标签栏**：在面板顶部显示所有打开的标签，支持点击切换、关闭
- **保持功能完整**：每个标签页内保留所有 8 个子 Tab（概览/容器/日志/终端/YAML/事件/指标/关联资源）

---

## 架构设计

### 1. Store 状态设计（k8sStore.ts）

```typescript
// 新增：管理多个打开的资源标签
interface ResourceTab {
  id: string;  // 唯一标识：{type}-{namespace}-{name}
  type: string;  // 'pod' | 'deployment' | ...
  namespace: string;
  name: string;
}

// 状态新增
interface K8sState {
  // ... 现有字段 ...
  
  // 新增：多标签页管理
  openedTabs: ResourceTab[];  // 所有打开的标签
  activeTabId: string | null;  // 当前激活的标签 ID
}

// 新增 Actions
interface K8sActions {
  // ... 现有 actions ...
  
  openResourceTab: (resource: ResourceTab) => void;  // 打开或切换到标签
  closeResourceTab: (tabId: string) => void;  // 关闭标签
  setActiveTab: (tabId: string) => void;  // 切换激活标签
  clearAllTabs: () => void;  // 关闭所有标签
}
```

### 2. 组件结构

```
K8sTool.tsx
├── ConnectionList (左侧面板)
├── 可拖动分隔条
── 右侧主区域
│   ├── TopBar
│   └── ResourceTabs (Pod/Workload/Node/Events 列表)
└── BottomPanel (新增 - 替代 PodDetail)
    ├── TabBar (标签栏)
    │   ── Tab[] (多个标签，支持切换、关闭)
    ├── 可拖动分隔条 (调整面板高度)
    └── TabContent (当前激活标签的内容)
        └── PodDetail (现有组件，保持所有功能)
            ├── OverviewPanel
            ├── ContainersPanel
            ├── LogsViewer
            ├── K8sTerminalPanel
            ├── YamlPanel
            ├── EventsPanel
            ├── MetricsPanel
            └── RelatedPanel
```

### 3. 新建组件：BottomPanel.tsx

**职责**：
- 管理底部面板的显示/隐藏
- 渲染标签栏（所有打开的标签）
- 渲染当前激活标签的内容
- 提供可拖动分隔条调整高度

**Props**：
```typescript
interface BottomPanelProps {
  // 无 props，所有状态从 store 读取
}
```

**关键特性**：
- 从底部滑出动画（`animate-slide-in-bottom`）
- 高度范围：300px - 70vh（默认 50vh）
- 可拖动分隔条调整高度
- 标签栏支持水平滚动（标签过多时）

### 4. 修改组件：PodList.tsx

**改动**：
```typescript
// 修改前：点击行设置 selectedResource（单选）
const handleRowClick = (pod: typeof pods[0]) => {
  setSelectedResource({
    type: 'pod',
    namespace: pod.namespace,
    name: pod.name,
  });
};

// 修改后：点击行打开标签页（多选）
const handleRowClick = (pod: typeof pods[0]) => {
  openResourceTab({
    id: `pod-${pod.namespace}-${pod.name}`,
    type: 'pod',
    namespace: pod.namespace,
    name: pod.name,
  });
};
```

### 5. 修改组件：K8sTool.tsx

**改动**：
```typescript
// 修改前
{selectedResource && <PodDetail />}

// 修改后
<BottomPanel />
```

---

## 样式设计

### 动画

```css
/* 底部滑出动画 */
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

### 标签栏样式

```
┌─────────────────────────────────────────────────────┐
│ [🟢 Pod A ×] [🟡 Pod B ×] [+ 添加]                  │ ← 标签栏
├─────────────────────────────────────────────────────┤
│ ═══════════════════════════════════════════════════ │ ← 可拖动分隔条
│                                                     │
│                  内容区域                            │
│          (PodDetail 组件)                           │
│                                                     │
─────────────────────────────────────────────────────┘
```

**标签样式**：
- 激活标签：蓝色背景 + 白色文字
- 非激活标签：灰色背景 + 灰色文字
- hover 效果：显示关闭按钮
- 状态指示：Running(绿)、Pending(黄)、Failed(红)

---

## 数据流

```
用户点击 Pod 行
    ↓
PodList.handleRowClick(pod)
    ↓
store.openResourceTab({ id, type, namespace, name })
    ↓
BottomPanel 检测到 openedTabs 变化
    ↓
渲染标签栏 + TabContent
    ↓
TabContent 读取 activeTabId
    ↓
渲染对应的 PodDetail
    ↓
PodDetail 使用 useQuery 获取数据
    ↓
显示 8 个子 Tab 的内容
```

---

## 实现步骤

### Task 1: 修改 k8sStore.ts
- 添加 `openedTabs` 和 `activeTabId` 状态
- 添加 `openResourceTab`、`closeResourceTab`、`setActiveTab`、`clearAllTabs` actions
- 移除或废弃 `selectedResource` 状态（或保持兼容）

### Task 2: 新建 BottomPanel.tsx
- 实现底部面板容器
- 实现标签栏（TabBar）
- 实现可拖动分隔条（调整高度）
- 实现内容区域渲染

### Task 3: 修改 PodList.tsx
- 将 `handleRowClick` 改为调用 `openResourceTab`
- 移除对 `setSelectedResource` 的调用

### Task 4: 修改 K8sTool.tsx
- 将 `<PodDetail />` 替换为 `<BottomPanel />`
- 移除 `selectedResource` 相关逻辑

### Task 5: 样式优化
- 添加底部滑出动画
- 优化标签栏样式（hover、激活状态、关闭按钮）
- 优化可拖动分隔条样式
- 确保响应式布局

### Task 6: 测试验证
- 打开多个标签页
- 切换标签页
- 关闭标签页
- 拖动调整面板高度
- 验证所有子 Tab 功能正常

---

## 兼容性考虑

### 向后兼容
- 保留 `selectedResource` 状态（标记为 deprecated）
- 其他组件（如 WorkloadList、NodeList）暂时保持使用 `setSelectedResource`
- 逐步迁移所有列表组件到新的 `openResourceTab` API

### 性能优化
- 使用 React.memo 优化标签栏渲染
- 使用 useQuery 缓存 Pod 详情数据
- 关闭标签时清理对应的 query cache

---

## 验收标准

- [ ] 点击 Pod 行后，底部弹出面板（非右侧抽屉）
- [ ] 可以同时打开多个 Pod 的详情标签
- [ ] 点击标签栏可以切换不同的 Pod 详情
- [ ] 点击标签的 × 按钮可以关闭该标签
- [ ] 拖动分隔条可以调整面板高度
- [ ] 每个标签页内保留所有 8 个子 Tab 功能
- [ ] 日志查看器功能正常（实时日志、下载、搜索）
- [ ] 终端功能正常（WebSocket 连接、命令执行）
- [ ] 所有子 Tab 的数据加载正常

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 多标签页内存占用 | 中 | 限制最大标签数（如 10 个），关闭时清理 cache |
| WebSocket 连接管理 | 中 | 非激活标签的终端/日志暂停连接 |
| 动画性能 | 低 | 使用 CSS 动画而非 JS 动画 |
| 响应式布局 | 低 | 设置最小高度，移动端优化 |

---

## 后续扩展

1. **标签持久化**：刷新页面后恢复打开的标签
2. **标签分组**：按 namespace 或类型分组标签
3. **标签搜索**：快速搜索并切换到目标标签
4. **快捷键**：Ctrl+Tab 切换标签，Ctrl+W 关闭标签
5. **拖拽排序**：拖动标签调整顺序

---

**下一步**: 用户 review 本文档后，调用 writing-plans skill 生成详细实现计划。
