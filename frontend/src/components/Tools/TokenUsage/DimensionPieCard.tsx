import React, { useMemo } from 'react';
import { Pie, PieChart, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { Card } from '@/components/ui/Card';

const COLORS = ['rgb(var(--accent-info))', 'rgb(var(--accent-success))', 'rgb(var(--accent-warning))', 'rgb(var(--accent-danger))', 'rgb(var(--accent-secondary))', 'rgb(var(--accent-warm))', 'rgb(var(--accent-cyan))', 'rgb(var(--accent-primary))'];

export interface PieSlice {
  key: string;
  label: string;
  tokens: number;
  cost: number;
  isOther?: boolean;
  percent?: number;
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
    // 区分 2 种空状态：data 未提供 vs data 全为 0
    if (data.length === 0) return { type: 'empty-no-data' as const };
    const valid = data.filter(d => d.tokens > 0 || d.cost > 0);
    if (valid.length === 0) return { type: 'empty-all-zero' as const };
    // 去掉 Top N 限制，显示全部切片，按 tokens 降序
    const sorted = [...valid].sort((a, b) => b.tokens - a.tokens);
    // 为每个切片计算百分比（基于 totalTokens，用于 Tooltip 展示）
    const totalForPercent = totalTokens > 0 ? totalTokens : sorted.reduce((s, x) => s + x.tokens, 0);
    const withPercent = sorted.map(s => ({
      ...s,
      percent: totalForPercent > 0 ? (s.tokens / totalForPercent * 100) : 0,
    }));
    return { type: 'data' as const, slices: withPercent };
  }, [data, totalTokens]);

  if (processed.type !== 'data') {
    const message = processed.type === 'empty-no-data' ? emptyHint : '暂无 Token 数据';
    return (
      <Card className="p-3 h-80 flex flex-col">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-medium text-ink">{title}</h2>
        </div>
        <div className="flex-1 flex items-center justify-center text-sm text-ink-faint">
          {message}
        </div>
      </Card>
    );
  }

  const slices = processed.slices;
  const displayValue = (s: PieSlice) => metric === 'cost' ? s.cost : s.tokens;
  const valueLabel = (s: PieSlice) =>
    metric === 'cost'
      ? `${formatCurrency(s.cost)} / ${formatToken(s.tokens)} Token`
      : `${formatToken(s.tokens)} Token / ${formatCurrency(s.cost)}`;

  return (
    <Card className="p-3 h-80 flex flex-col">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-medium text-ink">{title}</h2>
        <span className="text-xs text-ink-faint">{slices.length} 项</span>
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
                  const fill = COLORS[i % COLORS.length];
                  const isSelected = selectedKey === s.key;
                  return (
                    <Cell
                      key={s.key}
                      fill={fill}
                      stroke={isSelected ? 'rgb(var(--ink-default))' : 'none'}
                      strokeWidth={isSelected ? 2 : 0}
                    />
                  );
                })}
              </Pie>
              <Tooltip
                wrapperStyle={{
                  // 将浮窗从鼠标位置偏移，避免落在甜甜圈中心空洞内
                  transform: 'translate(20px, -100px)',
                  pointerEvents: 'none',
                }}
                content={({ payload }: { payload?: Array<{ payload?: PieSlice }> }) => {
                  const slice = payload?.[0]?.payload;
                  if (!slice) return null;
                  const pct = `${(slice.percent ?? 0).toFixed(1)}%`;
                  return (
                    <div className="rounded border border-border bg-canvas px-3 py-2 text-xs text-ink shadow-lg">
                      <div className="mb-1 font-medium text-ink">{title}</div>
                      <div className="mb-1 text-ink-muted">{slice.label}</div>
                      {metric === 'cost' ? (
                        <>
                          <div>{formatCurrency(slice.cost)} <span className="text-ink-faint">({pct})</span></div>
                          <div className="text-ink-muted">{formatToken(slice.tokens)} Token</div>
                        </>
                      ) : (
                        <>
                          <div>{formatToken(slice.tokens)} Token <span className="text-ink-faint">({pct})</span></div>
                          <div className="text-ink-muted">{formatCurrency(slice.cost)}</div>
                        </>
                      )}
                    </div>
                  );
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-base font-semibold text-ink">{formatToken(totalTokens)}</span>
            <span className="text-xs text-accent-success">Token</span>
          </div>
        </div>
        <div className="mt-2 flex-1 overflow-y-auto space-y-1">
          {slices.map((s, i) => (
            <div key={s.key} className="flex items-center justify-between gap-2 text-xs">
              <span className="flex min-w-0 items-center gap-1.5 text-ink-muted">
                <span
                  className="h-2 w-2 flex-none rounded-full"
                  style={{ backgroundColor: COLORS[i % COLORS.length] }}
                />
                <span className="truncate">{s.label}</span>
              </span>
              <span className="font-mono text-ink-muted">
                {metric === 'cost' ? formatCurrency(displayValue(s)) : `${formatToken(displayValue(s))} Token`}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
};

export default DimensionPieCard;
