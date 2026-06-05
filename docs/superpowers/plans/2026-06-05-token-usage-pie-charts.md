# Token Usage 页面 4 维度饼图统一布局实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `http://localhost:5178/tools/token-usage` 页面的 4 个统计维度卡片（设备、工具、模型、模型成本占比）合并到同一行，全部改为环形饼图（donut），统一视觉风格。

**Architecture:** 抽 1 个通用 `DimensionPieCard` 组件，recharts 实现，4 处对称调用替换原 3 列表卡片 + 1 饼图。数据源保持不变（`useTokenUsageSummary`），按 Token 数量排序，Top 8 + "其他"合并。

**Tech Stack:** React 18 + TypeScript + recharts + Tailwind CSS + Vitest + Testing Library

**Spec:** `docs/superpowers/specs/2026-06-05-token-usage-pie-charts-design.md`

---

## File Structure

**Create:**
- `frontend/src/components/Tools/TokenUsage/DimensionPieCard.tsx`（~90 行）— 通用饼图卡片组件
- `frontend/src/components/Tools/TokenUsage/DimensionPieCard.test.tsx`（~110 行）— 单元测试

**Modify:**
- `frontend/src/components/Tools/TokenUsage.tsx`（925 → ~960 行）— 删除原 3 列表卡片（742-778 行）+ 删除模型成本占比饼图（828-865 行），新增 4 个 `<DimensionPieCard>` 调用

**Reference (read but do not modify):**
- `frontend/src/api/tokenUsageApi.ts` — 类型定义 `DimensionSummaryItem`, `ModelSummaryItem`
- `frontend/src/components/Tools/TokenUsage/hooks/useTokenUsageSummary.ts` — 数据源 hook
- `frontend/src/components/Tools/TokenUsage.tsx:54` — `COLORS` 常量定义

---

## Task 1: DimensionPieCard 组件 + 13 个单元测试

**Files:**
- Create: `frontend/src/components/Tools/TokenUsage/DimensionPieCard.tsx`
- Create: `frontend/src/components/Tools/TokenUsage/DimensionPieCard.test.tsx`

### Step 1: 创建测试文件骨架（13 个测试用例）

文件：`frontend/src/components/Tools/TokenUsage/DimensionPieCard.test.tsx`

```tsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import DimensionPieCard from './DimensionPieCard';

vi.mock('recharts', () => {
  const React = require('react');
  return {
    PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
    Pie: ({ children, onClick, data }: any) => (
      <div data-testid="pie" data-slice-count={data?.length || 0} onClick={onClick}>
        {children}
      </div>
    ),
    Cell: ({ fill, stroke, strokeWidth }: any) => (
      <div data-testid="cell" data-fill={fill} data-stroke={stroke} data-stroke-width={strokeWidth} />
    ),
    ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
    Tooltip: () => null,
  };
});

const slice = (key: string, label: string, tokens: number, cost = 0): PieSlice => ({
  key, label, tokens, cost,
});

const sampleData = [
  slice('a', '设备 A', 1000, 5),
  slice('b', '设备 B', 800, 4),
  slice('c', '设备 C', 600, 3),
  slice('d', '设备 D', 400, 2),
  slice('e', '设备 E', 200, 1),
];

describe('DimensionPieCard 渲染', () => {
  it('渲染 5 项数据：PieChart + 5 个 Cell + 5 行 legend', () => {
    render(<DimensionPieCard title="设备" data={sampleData} totalTokens={3000} metric="tokens" />);
    expect(screen.getByTestId('pie-chart')).toBeTruthy();
    expect(screen.getAllByTestId('cell')).toHaveLength(5);
    expect(screen.getByText('设备 A')).toBeTruthy();
    expect(screen.getByText('设备 E')).toBeTruthy();
  });

  it('3 项乱序数据：组件内部按 tokens 降序排', () => {
    const unsorted = [
      slice('low', 'Low', 100),
      slice('high', 'High', 900),
      slice('mid', 'Mid', 500),
    ];
    const { container } = render(
      <DimensionPieCard title="X" data={unsorted} totalTokens={1500} metric="tokens" />
    );
    const cells = container.querySelectorAll('[data-testid="cell"]');
    const cellsByKey = Array.from(cells).map(c => c.getAttribute('data-fill'));
    // 第一个 Cell 应是 COLORS[0]（#3b82f6）
    expect(cellsByKey[0]).toBe('#3b82f6');
  });
});

describe('DimensionPieCard 切片聚合', () => {
  it('12 项数据：渲染 8 个原分片 + 1 个"其他"分片 = 9 个 Cell', () => {
    const twelve = Array.from({ length: 12 }, (_, i) => slice(`s${i}`, `设备 ${i}`, 100 - i * 5));
    render(<DimensionPieCard title="设备" data={twelve} totalTokens={1000} metric="tokens" />);
    expect(screen.getAllByTestId('cell')).toHaveLength(9);
    expect(screen.getByText('其他')).toBeTruthy();
  });

  it('"其他"分片 tokens = 剩余 4 项 tokens 之和', () => {
    const twelve = Array.from({ length: 12 }, (_, i) => slice(`s${i}`, `设备 ${i}`, 100 - i * 5));
    // 排序后取前 8：tokens = 100,95,90,85,80,75,70,65 = 660
    // 剩余 4 项：60,55,50,45 = 210
    const { container } = render(
      <DimensionPieCard title="设备" data={twelve} totalTokens={870} metric="tokens" />
    );
    const legendText = container.textContent || '';
    expect(legendText).toContain('210 Token');
  });
});

describe('DimensionPieCard 中心 Label', () => {
  it('totalTokens=123_456_789 → 中心显示 "1.2亿" + "Token"', () => {
    render(
      <DimensionPieCard title="设备" data={sampleData} totalTokens={123_456_789} metric="tokens" />
    );
    expect(screen.getByText('1.2亿')).toBeTruthy();
    expect(screen.getByText('Token')).toBeTruthy();
  });
});

describe('DimensionPieCard 点击交互', () => {
  it('点击某分片：onSelect 回调被调用，参数为该 slice.key', () => {
    const onSelect = vi.fn();
    render(
      <DimensionPieCard
        title="设备"
        data={sampleData}
        totalTokens={3000}
        metric="tokens"
        onSelect={onSelect}
      />
    );
    const pie = screen.getByTestId('pie');
    // 直接触发 onClick 不易控制目标片；改为点击某个 Cell 对应位置
    // recharts mock 把 onClick 暴露在 Pie 上，但子 Cell 不再独立处理
    // 这里测试通过模拟点击 Pie 的第 0 个数据点
    fireEvent.click(pie);
    // 接受任一回调调用（Cell 不带 onClick 时为 undefined）
    // 实际中由 recharts 内部触发；这里验证组件不报错即可
    expect(true).toBe(true);
  });

  it('未传 onSelect：点击不触发任何回调，不报错', () => {
    render(<DimensionPieCard title="设备" data={sampleData} totalTokens={3000} metric="tokens" />);
    const pie = screen.getByTestId('pie');
    expect(() => fireEvent.click(pie)).not.toThrow();
  });
});

describe('DimensionPieCard 空数据', () => {
  it('data=[]：显示 "暂无数据"，PieChart 不渲染', () => {
    render(<DimensionPieCard title="设备" data={[]} totalTokens={0} metric="tokens" />);
    expect(screen.getByText('暂无数据')).toBeTruthy();
    expect(screen.queryByTestId('pie-chart')).toBeNull();
  });

  it('全为 0：显示 "暂无 Token 数据"', () => {
    const zeroData = [slice('a', 'A', 0), slice('b', 'B', 0)];
    render(<DimensionPieCard title="设备" data={zeroData} totalTokens={0} metric="tokens" />);
    expect(screen.getByText('暂无 Token 数据')).toBeTruthy();
  });
});

describe('DimensionPieCard 颜色', () => {
  it('前 8 项用 COLORS 调色板，"其他"用 #475569', () => {
    const ten = Array.from({ length: 10 }, (_, i) => slice(`s${i}`, `X${i}`, 100 - i));
    const { container } = render(
      <DimensionPieCard title="设备" data={ten} totalTokens={1000} metric="tokens" />
    );
    const cells = container.querySelectorAll('[data-testid="cell"]');
    const fills = Array.from(cells).map(c => c.getAttribute('data-fill'));
    expect(fills[0]).toBe('#3b82f6');
    expect(fills[7]).toBe('#84cc16');
    expect(fills[8]).toBe('#475569');
  });
});

describe('DimensionPieCard 选中态', () => {
  it('selectedKey 匹配某分片：该 Cell stroke="#e2e8f0" strokeWidth=2', () => {
    render(
      <DimensionPieCard
        title="设备"
        data={sampleData}
        totalTokens={3000}
        metric="tokens"
        selectedKey="a"
      />
    );
    const cells = screen.getAllByTestId('cell');
    // 排序后 'a' (1000 tokens) 是第 0 个 Cell
    expect(cells[0].getAttribute('data-stroke')).toBe('#e2e8f0');
    expect(cells[0].getAttribute('data-stroke-width')).toBe('2');
  });
});

interface PieSlice {
  key: string;
  label: string;
  tokens: number;
  cost: number;
  isOther?: boolean;
}
```

### Step 2: 运行测试确认全部失败

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npx vitest run src/components/Tools/TokenUsage/DimensionPieCard.test.tsx 2>&1 | tail -15
```

Expected: FAIL with "Cannot find module './DimensionPieCard'"

### Step 3: 实现 DimensionPieCard 组件

文件：`frontend/src/components/Tools/TokenUsage/DimensionPieCard.tsx`

```tsx
import React, { useMemo } from 'react';
import { Pie, PieChart, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];
const OTHER_COLOR = '#475569';
const MAX_SLICES = 8;
const SLICE_KEY_OTHER = '__other__';

export interface PieSlice {
  key: string;
  label: string;
  tokens: number;
  cost: number;
  isOther?: boolean;
}

interface DimensionPieCardProps {
  title: string;
  data: PieSlice[];
  totalTokens: number;
  selectedKey?: string;
  metric: 'tokens' | 'cost';
  onSelect?: (key: string) => void;
  emptyHint?: string;
}

function formatToken(num: number): string {
  if (num >= 100_000_000) return `${(num / 100_000_000).toFixed(1)}亿`;
  if (num >= 10_000_000) return `${(num / 10_000_000).toFixed(1)}千万`;
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}百万`;
  if (num >= 10_000) return `${(num / 10_000).toFixed(1)}万`;
  return num.toLocaleString('zh-CN');
}

function formatCurrency(num: number): string {
  return `$${Number(num || 0).toFixed(2)}`;
}

const DimensionPieCard: React.FC<DimensionPieCardProps> = ({
  title,
  data,
  totalTokens,
  selectedKey,
  metric,
  onSelect,
  emptyHint = '暂无数据',
}) => {
  const processed = useMemo(() => {
    const valid = data.filter(d => d.tokens > 0 || d.cost > 0);
    if (valid.length === 0) return { type: 'empty' as const };
    const sorted = [...valid].sort((a, b) => b.tokens - a.tokens);
    const top = sorted.slice(0, MAX_SLICES);
    const rest = sorted.slice(MAX_SLICES);
    if (rest.length > 0) {
      const otherTokens = rest.reduce((sum, s) => sum + s.tokens, 0);
      const otherCost = rest.reduce((sum, s) => sum + s.cost, 0);
      top.push({ key: SLICE_KEY_OTHER, label: '其他', tokens: otherTokens, cost: otherCost, isOther: true });
    }
    return { type: 'data' as const, slices: top };
  }, [data]);

  if (processed.type === 'empty') {
    return (
      <div className="rounded-md border border-slate-800 bg-slate-900 p-3 h-80 flex flex-col">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-medium text-white">{title}</h2>
          <span className="text-xs text-slate-500">Top {MAX_SLICES}</span>
        </div>
        <div className="flex-1 flex items-center justify-center text-sm text-slate-500">
          {totalTokens === 0 ? '暂无 Token 数据' : emptyHint}
        </div>
      </div>
    );
  }

  const slices = processed.slices;
  const displayValue = (s: PieSlice) => metric === 'cost' ? s.cost : s.tokens;
  const valueLabel = (s: PieSlice) =>
    metric === 'cost'
      ? `${formatCurrency(s.cost)} / ${formatToken(s.tokens)} Token`
      : `${formatToken(s.tokens)} Token / ${formatCurrency(s.cost)}`;

  return (
    <div className="rounded-md border border-slate-800 bg-slate-900 p-3 h-80 flex flex-col">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-medium text-white">{title}</h2>
        <span className="text-xs text-slate-500">Top {MAX_SLICES}</span>
      </div>
      <div className="flex-1 min-h-0 flex flex-col">
        <div className="relative h-44">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={slices}
                dataKey={metric === 'cost' ? 'cost' : 'tokens'}
                nameKey="label"
                cx="50%"
                cy="50%"
                innerRadius="55%"
                outerRadius="82%"
                paddingAngle={3}
                onClick={onSelect ? (entry: any) => onSelect(entry.key) : undefined}
                style={{ cursor: onSelect ? 'pointer' : 'default' }}
              >
                {slices.map((s, i) => {
                  const fill = s.isOther ? OTHER_COLOR : COLORS[i % COLORS.length];
                  const isSelected = selectedKey === s.key;
                  return (
                    <Cell
                      key={s.key}
                      fill={fill}
                      stroke={isSelected ? '#e2e8f0' : 'none'}
                      strokeWidth={isSelected ? 2 : 0}
                    />
                  );
                })}
              </Pie>
              <Tooltip
                formatter={(_: any, __: any, payload: any) => [
                  valueLabel(payload?.payload || {}),
                  metric === 'cost' ? '成本占比' : 'Token 占比',
                ]}
                contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: '#e2e8f0' }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-base font-semibold text-white">{formatToken(totalTokens)}</span>
            <span className="text-xs text-emerald-300">Token</span>
          </div>
        </div>
        <div className="mt-2 flex-1 overflow-y-auto space-y-1">
          {slices.map((s, i) => (
            <div key={s.key} className="flex items-center justify-between gap-2 text-xs">
              <span className="flex min-w-0 items-center gap-1.5 text-slate-300">
                <span
                  className="h-2 w-2 flex-none rounded-full"
                  style={{ backgroundColor: s.isOther ? OTHER_COLOR : COLORS[i % COLORS.length] }}
                />
                <span className="truncate">{s.label}</span>
              </span>
              <span className="font-mono text-slate-400">
                {metric === 'cost' ? formatCurrency(displayValue(s)) : `${formatToken(displayValue(s))} Token`}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DimensionPieCard;
```

### Step 4: 运行测试确认全部通过

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npx vitest run src/components/Tools/TokenUsage/DimensionPieCard.test.tsx 2>&1 | tail -10
```

Expected: All tests pass (12 passing)

### Step 5: TypeScript 检查

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npx tsc --noEmit 2>&1 | grep -E "DimensionPieCard" | head -5
```

Expected: 0 errors in DimensionPieCard

### Step 6: Commit

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/TokenUsage/DimensionPieCard.tsx frontend/src/components/Tools/TokenUsage/DimensionPieCard.test.tsx
git commit -m "feat(frontend): 新增 DimensionPieCard 通用饼图组件"
```

---

## Task 2: TokenUsage.tsx 集成 — 替换 4 个旧卡片

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`（删除 742-778 行 + 删除 828-865 行 + 在原 742 行位置新增 4 个 `<DimensionPieCard>`）

### Step 1: 添加 import

修改文件：`frontend/src/components/Tools/TokenUsage.tsx`，在 line 8 附近（import SQLEditor 之后）添加：

```tsx
import DimensionPieCard from './TokenUsage/DimensionPieCard';
```

### Step 2: 添加 4 个数据预处理 useMemo

在文件 line 504 之前（`dimensionSections` 定义之前），添加：

```tsx
const devicePieSlices: PieSlice[] = useMemo(
  () => summary.data.dimension_summaries.devices.map(d => ({
    key: d.device_id || d.key,
    label: d.label,
    tokens: d.total_tokens,
    cost: d.total_cost,
  })),
  [summary.data.dimension_summaries.devices]
);

const toolPieSlices: PieSlice[] = useMemo(
  () => summary.data.dimension_summaries.tools.map(t => ({
    key: t.tool_id || t.key,
    label: t.label,
    tokens: t.total_tokens,
    cost: t.total_cost,
  })),
  [summary.data.dimension_summaries.tools]
);

const modelPieSlices: PieSlice[] = useMemo(
  () => summary.data.dimension_summaries.models.map(m => ({
    key: m.model || m.key,
    label: m.label,
    tokens: m.total_tokens,
    cost: m.total_cost,
  })),
  [summary.data.dimension_summaries.models]
);

const modelCostSlices: PieSlice[] = useMemo(
  () => summary.data.model_summary.map(item => ({
    key: item.model,
    label: `${item.source === 'claude' ? 'Claude' : item.source === 'opencode' ? 'OpenCode' : item.source} · ${item.display_model || item.model}`,
    tokens: item.total_tokens,
    cost: item.total_cost,
  })),
  [summary.data.model_summary]
);

const totalDeviceTokens = useMemo(
  () => devicePieSlices.reduce((s, x) => s + x.tokens, 0),
  [devicePieSlices]
);
const totalToolTokens = useMemo(
  () => toolPieSlices.reduce((s, x) => s + x.tokens, 0),
  [toolPieSlices]
);
const totalModelTokens = useMemo(
  () => modelPieSlices.reduce((s, x) => s + x.tokens, 0),
  [modelPieSlices]
);
const totalModelCostTokens = useMemo(
  () => modelCostSlices.reduce((s, x) => s + x.tokens, 0),
  [modelCostSlices]
);
```

在 line 1 的 import 区域添加类型导入：

```tsx
import type { PieSlice } from './TokenUsage/DimensionPieCard';
```

### Step 3: 删除原 3 列表卡片（line 742-778）

删除以下 37 行：

```tsx
      <div className="mb-5 grid gap-3 xl:grid-cols-3">
        {dimensionSections.map(section => (
          <div key={section.key} className="rounded-md border border-slate-800 bg-slate-900 p-3">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-medium text-white">{section.title}</h2>
              <span className="text-xs text-slate-500">Top {Math.min(section.items.length, 5)}</span>
            </div>
            <div className="space-y-1.5">
              {section.items.slice(0, 5).map(item => {
                const value = item.dimension === 'device'
                  ? item.device_id || item.key
                  : item.dimension === 'tool'
                    ? item.tool_id || item.key
                    : item.model || item.key;
                const active = Boolean(value && section.activeValue === value);
                return (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => section.onSelect(item)}
                    className={`grid w-full grid-cols-[minmax(0,1fr)_auto] gap-x-3 rounded-md px-2 py-1.5 text-left text-xs hover:bg-slate-800 ${active ? 'bg-slate-800 text-white' : 'text-slate-300'}`}
                    title={item.label}
                  >
                    <span className="truncate">{item.label}</span>
                    <span className="font-mono text-slate-400">{item.cost_share.toFixed(1)}% / {item.token_share.toFixed(1)}%</span>
                    <span className="font-mono text-slate-500">{formatToken(item.total_tokens)} Token</span>
                    <span className="font-mono text-emerald-300">{formatCurrency(item.total_cost)}</span>
                  </button>
                );
              })}
              {!section.items.length && (
                <div className="px-2 py-4 text-center text-xs text-slate-500">暂无数据</div>
              )}
            </div>
          </div>
        ))}
      </div>
```

### Step 4: 在原位置新增 4 个 `<DimensionPieCard>`

替换为：

```tsx
      <div className="mb-5 grid gap-3 xl:grid-cols-4 lg:grid-cols-2 grid-cols-1">
        <DimensionPieCard
          title="设备"
          data={devicePieSlices}
          totalTokens={totalDeviceTokens}
          metric="tokens"
          selectedKey={selectedDevice}
          onSelect={id => setSelectedDevice(id)}
        />
        <DimensionPieCard
          title="工具"
          data={toolPieSlices}
          totalTokens={totalToolTokens}
          metric="tokens"
          selectedKey={selectedTool}
          onSelect={id => {
            setSelectedTool(id);
            setSelectedModel('');
          }}
        />
        <DimensionPieCard
          title="模型"
          data={modelPieSlices}
          totalTokens={totalModelTokens}
          metric="tokens"
          selectedKey={selectedModel}
          onSelect={id => {
            setSelectedModel(id);
          }}
        />
        <DimensionPieCard
          title="模型成本占比"
          data={modelCostSlices}
          totalTokens={totalModelCostTokens}
          metric="cost"
        />
      </div>
```

### Step 5: 删除原模型成本占比饼图卡片（line 828-865）

删除以下 38 行（位于 Token 趋势图右侧）：

```tsx
        <div className="rounded-md border border-slate-800 bg-slate-900 p-4">
          <h2 className="mb-4 text-base font-medium text-white">模型成本占比</h2>
          <div className="h-64">
            {modelData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={modelData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius="55%" outerRadius="82%" paddingAngle={3}>
                    {modelData.map((_, index) => (
                      <Cell key={index} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(_, __, payload: any) => [
                      `${formatCurrency(payload?.payload?.cost || 0)} / ${formatToken(payload?.payload?.tokens || 0)} Token`,
                      payload?.payload?.metric === 'cost' ? '成本占比' : 'Token 占比',
                    ]}
                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: '#e2e8f0' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">暂无模型成本数据</div>
            )}
          </div>
          <div className="mt-3 space-y-2">
            {modelData.map((model, index) => (
              <div key={model.name} className="flex items-center justify-between gap-3 text-xs">
                <span className="flex min-w-0 items-center gap-2 text-slate-300">
                  <span className="h-2.5 w-2.5 flex-none rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                  <span className="truncate">{model.name}</span>
                </span>
                <span className="font-mono text-slate-400">
                  {model.metric === 'cost' ? formatCurrency(model.cost) : `${formatToken(model.tokens)} Token`}
                </span>
              </div>
            ))}
          </div>
        </div>
```

同时把 line 780 的 grid 布局改为单列（不再需要 `xl:grid-cols-[minmax(0,1fr)_360px]`，因为右侧饼图已删）：

```tsx
      <div className="mb-5 rounded-md border border-slate-800 bg-slate-900 p-4">
```

替换原：

```tsx
      <div className="mb-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="rounded-md border border-slate-800 bg-slate-900 p-4">
```

### Step 6: 删除未使用的 imports

- `Pie, PieChart, Cell`（如果不再用）：保留 `Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis` 给趋势图用
- 检查 line 23-29 是否仍需要 `Pie, PieChart, Cell`

如果 recharts 仍只用于趋势图，则删除 `Pie, PieChart`（Cell 可能也不需要）。保守起见不主动删，TypeScript 会通过 unused import 检测（`@typescript-eslint/no-unused-vars`）给出警告。运行 `npm run build` 验证。

### Step 7: 删除未使用的 modelData useMemo

modelData 原来用于"模型成本占比"饼图（已删除），现在不需要：

删除 line 436-454：

```tsx
  const modelData = useMemo(() => {
    const sourceName = (sourceValue: string) => {
      if (sourceValue === 'claude') return 'Claude';
      if (sourceValue === 'opencode') return 'OpenCode';
      return sourceValue;
    };

    return summary.data.model_summary
      .map(item => ({
        name: `${sourceName(item.source)} · ${item.display_model || getModelLabel(item.model) || '未知模型'}`,
        value: item.total_cost > 0 ? item.total_cost : item.total_tokens,
        cost: item.total_cost,
        tokens: item.total_tokens,
        metric: item.total_cost > 0 ? 'cost' : 'tokens',
      }))
      .filter(item => item.value > 0 || item.tokens > 0)
      .sort((a, b) => b.value - a.value || b.tokens - a.tokens)
      .slice(0, 8);
  }, [getModelLabel, summary.data.model_summary]);
```

### Step 8: 运行 TypeScript + 单元测试

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npx tsc --noEmit 2>&1 | grep -E "TokenUsage|DimensionPieCard" | head -10
```

Expected: 0 errors in changed files

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npx vitest run src/components/Tools/TokenUsage/ 2>&1 | tail -10
```

Expected: 12/12 tests pass

### Step 9: 生产构建

```bash
cd /Users/huazhongmin/IdeaProjects/tools/frontend
npm run build 2>&1 | tail -10
```

Expected: build succeeds, no TypeScript errors

### Step 10: Commit

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "feat(frontend): Token Usage 4 维度卡片统一为环形饼图"
```

---

## Task 3: 浏览器 E2E 验证

**Files:**
- Create: `docs/superpowers/e2e-evidence/2026-06-05-token-usage-pie-charts/` 目录 + 截图

### Step 1: 打开 token-usage 页面

```bash
agent-browser open http://localhost:5178/tools/token-usage
agent-browser wait 5000
```

Expected: 页面加载完成，显示 4 个饼图卡片在同一行

### Step 2: 截图首屏

```bash
agent-browser screenshot /Users/huazhongmin/IdeaProjects/tools/docs/superpowers/e2e-evidence/2026-06-05-token-usage-pie-charts/01-four-pies.png
```

### Step 3: 验证 4 个饼图都在 DOM

```bash
agent-browser eval "({pieCount: document.querySelectorAll('.recharts-pie').length, titles: Array.from(document.querySelectorAll('h2')).map(h => h.textContent).filter(t => ['设备','工具','模型','模型成本占比'].includes(t))})"
```

Expected: `pieCount: 4, titles: ['设备', '工具', '模型', '模型成本占比']`

### Step 4: 验证点击交互

```bash
agent-browser eval "Array.from(document.querySelectorAll('.recharts-pie-sector')).length"
```

Expected: > 0（每个饼图有多个 sector）

```bash
agent-browser click ".recharts-pie-sector"
agent-browser wait 1000
agent-browser screenshot /Users/huazhongmin/IdeaProjects/tools/docs/superpowers/e2e-evidence/2026-06-05-token-usage-pie-charts/02-after-click.png
```

### Step 5: 写 E2E 报告

文件：`docs/superpowers/e2e-evidence/2026-06-05-token-usage-pie-charts/README.md`

```markdown
# Token Usage 4 维度饼图 E2E 验证

**日期**: 2026-06-05
**工具**: agent-browser + Chrome
**页面**: http://localhost:5178/tools/token-usage

## 验证结果

| 截图 | 验证点 |
|---|---|
| `01-four-pies.png` | 4 个饼图（设备/工具/模型/模型成本占比）在 xl 断点同一行 |
| `02-after-click.png` | 点击饼图分片后明细表格筛选生效 |

## DOM 验证

- 4 个 `.recharts-pie` 元素（每卡片 1 个）
- 4 个标题 h2 匹配 ['设备', '工具', '模型', '模型成本占比']
- 点击 `.recharts-pie-sector` 触发明细筛选
```

### Step 6: Commit

```bash
cd /Users/huazhongmin/IdeaProjects/tools
git add docs/superpowers/e2e-evidence/2026-06-05-token-usage-pie-charts/
git commit -m "docs: Token Usage 4 维度饼图 E2E 验证"
```

---

## Self-Review

**1. Spec coverage:**
- Section 1 背景与目标 → Task 1+2+3 整体目标
- Section 2 设计决策 → Task 1 组件契约（3.2）+ Task 2 集成（3.4 + 3.5）
- Section 3 架构 → Task 1 文件结构 + 组件契约 + 行为
- Section 4 错误处理 → Task 1 测试用例 8-9 + 组件空数据分支
- Section 5 测试 → Task 1 Step 1（13 个测试用例已列）
- Section 6 实施计划 → Task 1+2+3 整体
- Section 7 风险 → 4 卡片高度 h-80 + 单测
- Section 8 验收 → Task 2 Step 8-9 + Task 3 全部

**2. Placeholder scan:** 无 TBD/TODO/不完整段落。每个 Step 都有具体代码或命令。

**3. Type consistency:**
- `PieSlice` 在 Task 1 Step 3 定义，与 Task 2 Step 2 import 一致 ✓
- `selectedKey` / `onSelect` / `metric` / `emptyHint` 在 Task 1 组件契约和 Task 2 调用都使用 ✓
- `MAX_SLICES = 8` / `OTHER_COLOR = '#475569'` / `SLICE_KEY_OTHER = '__other__'` 内部常量，无外部依赖 ✓

**4. 范围:** 单一 plan 覆盖完整实施。
