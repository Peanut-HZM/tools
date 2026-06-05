# Token Usage 页面 4 维度饼图统一布局设计

**日期**: 2026-06-05
**作者**: Sisyphus
**范围**: 前端 Token Usage 页面 4 个维度卡片
**状态**: 待审查

## 1. 背景与目标

### 1.1 现状

`http://localhost:5178/tools/token-usage` 页面有 4 个统计维度卡片，分布在 **两个独立 grid 行**：

| 卡片 | 当前实现 | 位置 |
|---|---|---|
| 设备 (Top 5) | 列表行式布局 | 第 742-778 行 |
| 工具 (Top 5) | 列表行式布局 | 第 742-778 行 |
| 模型 (Top 5) | 列表行式布局 | 第 742-778 行 |
| 模型成本占比 | recharts 环形饼图（donut） | 第 828-865 行 |

**问题**：
- 4 个卡片视觉风格不统一（3 个列表 + 1 个饼图）
- 占两行垂直空间，浏览需滚动
- 模型成本占比独立于其他 3 个维度

### 1.2 目标

将 4 个卡片合并到 **同一行**，全部改为 **环形饼图（donut）**，统一视觉风格。

### 1.3 非目标

- 不修改明细数据表格（第 868+ 行）
- 不修改顶部筛选器（下拉框、日期范围等）
- 不修改图表库选型（保持 recharts）
- 不修改数据源（保持现有 API）

## 2. 设计决策（已确认）

| 决策项 | 选择 | 理由 |
|---|---|---|
| 数据维度 | 3 个按 Token 数量 + 1 个按成本 USD | 与"消耗统计"主题一致；模型成本占比保留成本维度形成对照 |
| 切片聚合 | Top 8 + "其他"合并 | 与已有模型成本占比 slice(0, 8) 对齐；颜色调色板 8 色 |
| 布局 | 等宽 4 列 | 4 个饼图功能对等；响应式友好（xl→lg→1 列） |
| 点击交互 | 保留点击筛选 | 与现有列表卡片行为一致；不增加学习成本 |
| 中心数值 | 显示总 Token 数量 | 4 张饼图中心统一格式；快速概览总消耗 |
| 实施方式 | 抽 DimensionPieCard 组件 | 4 处对称使用，组件抽象必要；降低 TokenUsage.tsx 复杂度 |

## 3. 架构

### 3.1 文件结构

**新增**：
- `frontend/src/components/Tools/TokenUsage/DimensionPieCard.tsx`（~90 行）— 通用饼图卡片组件
- `frontend/src/components/Tools/TokenUsage/DimensionPieCard.test.tsx`（~110 行）— 单元测试

**修改**：
- `frontend/src/components/Tools/TokenUsage.tsx`（925 → ~960 行）— 替换原 3 个列表卡片 + 1 个模型成本占比饼图

**保留不变**：
- `frontend/src/components/Tools/TokenUsage/hooks/*`（4 个 hooks）
- `frontend/src/api/tokenUsageApi.ts`（数据源）
- 明细表格、筛选器、健康卡片、Token 趋势图

### 3.2 组件契约

```tsx
interface PieSlice {
  key: string;          // 唯一 ID（设备 ID / 工具 ID / 模型名 / '__other__'）
  label: string;        // 显示文本
  tokens: number;       // Token 数量
  cost: number;         // 成本 USD
  isOther?: boolean;    // 是否为"其他"合并分片（灰色 #475569）
}

interface DimensionPieCardProps {
  title: string;                     // '设备' / '工具' / '模型' / '模型成本占比'
  data: PieSlice[];                  // 必填，至少 0 项
  totalTokens: number;               // 中心显示的总 Token 数
  selectedKey?: string;              // 当前选中项（可选）
  metric: 'tokens' | 'cost';         // 决定 Tooltip 主指标
  onSelect?: (key: string) => void;  // 点击某片回调
  emptyHint?: string;                // 空数据提示，默认 '暂无数据'
}
```

### 3.3 组件行为

**数据预处理**（分两层）：
- **TokenUsage.tsx 层**（4 个 useMemo）：将 `dimension_summaries.{devices,tools,models}` 和 `model_summary` 映射为 `PieSlice[]`，每项含 `key` / `label` / `tokens` / `cost` 4 字段
- **DimensionPieCard 内部 useMemo**（1 个）：
  1. 过滤 `tokens > 0 || cost > 0` 的有效项（避免饼图除零）
  2. 按 `tokens` 降序排序
  3. 取前 8 项保留原 `key` 和 `label`
  4. 剩余项合并为 1 个 `{ key: '__other__', label: '其他', isOther: true }`，`tokens` 和 `cost` 分别求和
  5. 颜色：前 8 项用 `COLORS` 调色板（`#3b82f6` ~ `#84cc16` 8 色），`__other__` 用 `#475569`（slate-600）

**渲染结构**（每个卡片）：
```
┌─────────────────────────────┐
│ 设备                    Top 8 │  ← 标题行
├─────────────────────────────┤
│                             │
│         ╭─────╮             │
│       ╱  1.2亿  ╲           │  ← 中心：formatToken(totalTokens) + "Token"
│      │   Token   │           │
│       ╲         ╱            │  ← recharts PieChart donut
│         ╰─────╯             │
│                             │
├─────────────────────────────┤
│ ● 设备 1    1000 / $0.50    │  ← 紧凑 legend（最多 9 行）
│ ● 设备 2     800 / $0.40    │
│ ...                          │
│ ● 其他       500 / $0.20    │
└─────────────────────────────┘
```

**Tooltip 格式**（hover 饼图某片）：
- `metric='tokens'`：显示 `${formatToken(tokens)} Token / ${formatCurrency(cost)}`
- `metric='cost'`：显示 `${formatCurrency(cost)} / ${formatToken(tokens)} Token`

**点击行为**：
- `onSelect` 未提供 → 不绑定点击事件（纯展示）
- `onSelect` 提供 → 点击某片调用 `onSelect(slice.key)`
- 选中状态：当前 `selectedKey === slice.key` 时，该片外侧加 2px slate-100 描边（通过 recharts `<Cell stroke strokeWidth={2}>` 实现）
- 卡片高度：固定 `h-80`（320px），与下方"Token 趋势图"卡片同高；legend 行超出时该列内部滚动（`overflow-y-auto`）

### 3.4 4 个饼图的具体配置

| 卡片 | data 来源 | metric | onSelect | selectedKey |
|---|---|---|---|---|
| 设备 | `summary.data.dimension_summaries.devices` map | `tokens` | `setSelectedDevice` | `selectedDevice` |
| 工具 | `summary.data.dimension_summaries.tools` map | `tokens` | `setSelectedTool` | `selectedTool` |
| 模型 | `summary.data.dimension_summaries.models` map | `tokens` | `setSelectedModel` | `selectedModel` |
| 模型成本占比 | `summary.data.model_summary` map | `cost` | 不传 | 不传 |

### 3.5 布局替换

**删除**：
- 第 742-778 行的 3 列 grid（设备/工具/模型列表卡片）
- 第 828-865 行的模型成本占比饼图卡片（独立于 Token 趋势图右侧）

**新增**：
- 在原"3 列表卡片"位置插入 1 个 4 列 grid，调用 4 次 `<DimensionPieCard>`

**布局代码**：
```tsx
<div className="mb-5 grid gap-3 xl:grid-cols-4 lg:grid-cols-2 grid-cols-1">
  <DimensionPieCard title="设备" data={deviceSlices} totalTokens={deviceTotal} metric="tokens"
    selectedKey={selectedDevice} onSelect={id => setSelectedDevice(id)} />
  <DimensionPieCard title="工具" data={toolSlices} totalTokens={toolTotal} metric="tokens"
    selectedKey={selectedTool} onSelect={id => { setSelectedTool(id); setSelectedModel(''); }} />
  <DimensionPieCard title="模型" data={modelSlices} totalTokens={modelTotal} metric="tokens"
    selectedKey={selectedModel} onSelect={id => setSelectedModel(id)} />
  <DimensionPieCard title="模型成本占比" data={modelCostSlices} totalTokens={modelCostTotal} metric="cost" />
</div>
```

## 4. 错误处理与边界

| 场景 | 行为 |
|---|---|
| `data.length === 0` | 显示 `emptyHint` 文字（"暂无数据"），不渲染 PieChart |
| `data.every(s => s.tokens === 0)` | 显示 "暂无 Token 数据"，不渲染 PieChart |
| 加载中（`summary.loading === true`） | 保持上一次数据，不显示 spinner |
| 颜色溢出（9+ 项） | "其他"分片固定用 `#475569`（slate-600） |
| Label 过长（>20 字符） | CSS truncate，hover Tooltip 显示完整 label |
| 窄屏（`< lg`） | 4 列 → 2 列 → 1 列响应式 |
| 模型数据无成本 | `metric='cost'` 卡片空数据，显示 "暂无模型成本数据" |

## 5. 测试

`DimensionPieCard.test.tsx` 单元测试覆盖：

| # | 场景 | 断言 |
|---|---|---|
| 1 | 渲染 5 项数据 | 渲染 PieChart + 5 个 legend 项 |
| 2 | 3 项乱序数据 | 内部按 tokens 降序排 |
| 3 | 12 项数据 | 渲染 8 个原分片 + 1 个"其他"分片 = 9 个 Cell |
| 4 | "其他"分片数值 | 剩余 4 项 tokens 之和 == "其他"分片 tokens |
| 5 | 中心 Label | `totalTokens=123_456_789` → 显示 "1.2亿" + "Token" |
| 6 | 点击回调 | onSelect 存在 + 点击某片 → 回调被调用，参数为该 slice.key |
| 7 | 无 onSelect | 点击不触发任何回调（不报错） |
| 8 | 空数据 | `data=[]` → 显示 "暂无数据"，PieChart 不渲染 |
| 9 | 全为 0 | `tokens=0` × N → 显示 "暂无 Token 数据" |
| 10 | 颜色 | 前 8 项各用 1 色（COLORS[0..7]），"其他"用 #475569 |
| 11 | metric='cost' Tooltip | hover 时显示 `${formatCurrency} / ${formatToken} Token` |
| 12 | metric='tokens' Tooltip | hover 时显示 `${formatToken} Token / ${formatCurrency}` |
| 13 | 选中态 | `selectedKey='dev-1'` + 数据中含 'dev-1' → 该片有特殊描边 |

## 6. 实施计划概要

按 TDD 方式分 3 个 Task：

**Task 1：DimensionPieCard 组件 + 测试**
- 写 `DimensionPieCard.test.tsx`（13 个测试用例，先红）
- 写 `DimensionPieCard.tsx`（实现到测试全绿）
- Spec 合规审查 + 代码质量审查

**Task 2：TokenUsage.tsx 集成**
- 替换原 3 列表卡片 + 1 饼图为 4 个 `<DimensionPieCard>`
- 删除 30-50 行旧 JSX
- 新增 4 处数据映射
- 类型检查 + 端到端浏览器验证（用 token-usage 页面已有数据）

**Task 3：E2E 验证 + 文档**
- agent-browser 打开页面截图
- 验证 4 个饼图都在一行
- 验证点击筛选交互

## 7. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| recharts 4 个饼图同时渲染性能 | 首次渲染略慢 | 单个饼图 ≤ 9 个 Cell，recharts 性能可接受；如有问题可加 React.memo |
| legend 行数过多（9 行）撑高卡片 | 4 个饼图高度不一致 | 固定卡片高度（如 h-80 = 320px），超出部分 legend 滚动 |
| 取消点击筛选的回归 | 用户失去快速筛选 | 不传 onSelect 时不绑事件，调用方不传即可 |
| 删掉原列表卡片的 5 项明细 | 用户失去 Top 5 明细视图 | 4 个饼图的 legend 紧凑列表本身展示 Top 8，信息量更大 |
| 颜色调色板与现有其他图表不一致 | 视觉割裂 | 复用现有 `COLORS` 常量，slate-600 灰色仅用于"其他" |

## 8. 验收标准

- [ ] 4 个 `<DimensionPieCard>` 在同一行（xl 断点）
- [ ] 4 个饼图均为环形（donut），中心显示总 Token 数
- [ ] 数据维度：3 个 tokens + 1 个 cost
- [ ] 切片数：≤ 8 个原分片 + 1 个"其他"灰色分片
- [ ] 点击设备/工具/模型饼图 → 下方明细表格筛选
- [ ] 点击模型成本占比 → 不触发任何筛选
- [ ] 13 个单元测试全部通过
- [ ] TypeScript 0 新错误
- [ ] 浏览器 E2E 截图归档
- [ ] TokenUsage.tsx 净增 ≤ 50 行
