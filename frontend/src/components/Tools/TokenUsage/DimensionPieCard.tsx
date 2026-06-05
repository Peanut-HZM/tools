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
    // 区分 3 种空状态：data 未提供 vs data 全为 0
    if (data.length === 0) return { type: 'empty-no-data' as const };
    const valid = data.filter(d => d.tokens > 0 || d.cost > 0);
    if (valid.length === 0) return { type: 'empty-all-zero' as const };
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

  if (processed.type !== 'data') {
    const message = processed.type === 'empty-no-data' ? emptyHint : '暂无 Token 数据';
    return (
      <div className="rounded-md border border-slate-800 bg-slate-900 p-3 h-80 flex flex-col">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-medium text-white">{title}</h2>
          <span className="text-xs text-slate-500">Top {MAX_SLICES}</span>
        </div>
        <div className="flex-1 flex items-center justify-center text-sm text-slate-500">
          {message}
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
                onClick={onSelect ? ((entry: unknown) => onSelect((entry as PieSlice).key)) : undefined}
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
                formatter={((_: unknown, __: unknown, payload: { payload?: PieSlice } | undefined) => {
                  const slice = payload?.payload;
                  return [
                    slice ? valueLabel(slice) : '',
                    metric === 'cost' ? '成本占比' : 'Token 占比',
                  ] as [string, string];
                }) as never}
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
