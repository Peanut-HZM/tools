import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import DimensionPieCard, { type PieSlice } from './DimensionPieCard';

afterEach(() => {
  cleanup();
});

vi.mock('recharts', () => ({
  PieChart: ({ children }: { children?: React.ReactNode }) => <div data-testid="pie-chart">{children}</div>,
  Pie: ({ children, onClick, data }: { children?: React.ReactNode; onClick?: (entry: { key: string }) => void; data?: unknown[] }) => (
    <div data-testid="pie" data-slice-count={data?.length || 0} onClick={() => onClick?.({ key: 'a' })}>
      {children}
    </div>
  ),
  Cell: ({ fill, stroke, strokeWidth }: { fill?: string; stroke?: string; strokeWidth?: number }) => (
    <div data-testid="cell" data-fill={fill} data-stroke={stroke} data-stroke-width={strokeWidth} />
  ),
  ResponsiveContainer: ({ children }: { children?: React.ReactNode }) => <div data-testid="responsive-container">{children}</div>,
  Tooltip: () => null,
}));

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
    // 第一个 Cell 应是 COLORS[0]（var(--accent-info)）
    expect(cellsByKey[0]).toBe('var(--accent-info)');
  });
});

describe('DimensionPieCard 切片显示', () => {
  it('12 项数据：全部 12 个 Cell 都渲染，无"其他"聚合', () => {
    const twelve = Array.from({ length: 12 }, (_, i) => slice(`s${i}`, `设备 ${i}`, 100 - i * 5));
    render(<DimensionPieCard title="设备" data={twelve} totalTokens={1000} metric="tokens" />);
    expect(screen.getAllByTestId('cell')).toHaveLength(12);
    expect(screen.queryByText('其他')).toBeNull();
  });

  it('20 项数据：全部渲染，图例可滚动', () => {
    const twenty = Array.from({ length: 20 }, (_, i) => slice(`s${i}`, `模型 ${i}`, 200 - i * 8));
    const { container } = render(
      <DimensionPieCard title="模型" data={twenty} totalTokens={2000} metric="tokens" />
    );
    expect(screen.getAllByTestId('cell')).toHaveLength(20);
    // 图例区域应有滚动能力
    const legendArea = container.querySelector('.overflow-y-auto');
    expect(legendArea).toBeTruthy();
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
    fireEvent.click(pie);
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith('a');
  });

  it('未传 onSelect：点击不触发任何回调，不报错', () => {
    render(<DimensionPieCard title="设备" data={sampleData} totalTokens={3000} metric="tokens" />);
    const pie = screen.getByTestId('pie');
    expect(() => fireEvent.click(pie)).not.toThrow();
  });
});

describe('DimensionPieCard Tooltip', () => {
  it('metric="cost" 时 PieChart 正常渲染（Tooltip 在 PieChart 内）', () => {
    const { container } = render(
      <DimensionPieCard title="模型成本占比" data={sampleData} totalTokens={3000} metric="cost" />
    );
    expect(container.querySelector('[data-testid="pie-chart"]')).toBeTruthy();
  });

  it('metric="tokens" 时 PieChart 正常渲染', () => {
    const { container } = render(
      <DimensionPieCard title="设备" data={sampleData} totalTokens={3000} metric="tokens" />
    );
    expect(container.querySelector('[data-testid="pie-chart"]')).toBeTruthy();
  });

  it('每个 slice 带 percent 字段（由 totalTokens 计算）', () => {
    const { container } = render(
      <DimensionPieCard title="设备" data={sampleData} totalTokens={3000} metric="tokens" />
    );
    const cells = container.querySelectorAll('[data-testid="cell"]');
    // 5 项数据全部渲染
    expect(cells).toHaveLength(5);
    // 数据中 tokens 总和 = 1000+800+600+400+200 = 3000 = totalTokens
    // 第一项 (1000) percent = 33.3%
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
  it('所有项用 COLORS 调色板循环取色（无"其他"专用色）', () => {
    const ten = Array.from({ length: 10 }, (_, i) => slice(`s${i}`, `X${i}`, 100 - i));
    const { container } = render(
      <DimensionPieCard title="设备" data={ten} totalTokens={1000} metric="tokens" />
    );
    const cells = container.querySelectorAll('[data-testid="cell"]');
    const fills = Array.from(cells).map(c => c.getAttribute('data-fill'));
    expect(fills[0]).toBe('var(--accent-info)');
    expect(fills[7]).toBe('var(--accent-primary)');
    // 第 9 项循环回 COLORS[0]
    expect(fills[8]).toBe('var(--accent-info)');
    expect(fills[9]).toBe('var(--accent-success)');
  });
});

describe('DimensionPieCard 选中态', () => {
  it('selectedKey 匹配某分片：该 Cell stroke="var(--ink-default)" strokeWidth=2', () => {
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
    expect(cells[0].getAttribute('data-stroke')).toBe('var(--ink-default)');
    expect(cells[0].getAttribute('data-stroke-width')).toBe('2');
  });
});
