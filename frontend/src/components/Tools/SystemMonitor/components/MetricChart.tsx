// frontend/src/components/Tools/SystemMonitor/components/MetricChart.tsx
/**
 * 通用趋势图（recharts 折线图封装）
 *
 * 主题适配：颜色全部读 CSS 变量（--border-default / --ink-faint / --bg-surface-1 等），
 * 不写死 hex —— 之前硬编码 #334155 / #0f172a 导致浅色主题下网格与 tooltip
 * 仍是深色，看起来像「图表没适配主题」。
 * 线色由调用方传入（语义色），保持可辨识。
 */
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

export interface ChartPoint {
  time: string;
  [key: string]: number | string | null;
}

export interface ChartLine {
  key: string;
  name: string;
  color: string;
}

interface MetricChartProps {
  data: ChartPoint[];
  lines: ChartLine[];
  height?: number;
  yUnit?: string;
}

/** 从 CSS 变量取色（含 alpha），拿不到时给安全的回退值 */
function cssVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback;
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  if (!raw) return fallback;
  // 项目 token 是 "R G B" 三元组，需要包成 rgb()
  return /^\d+\s+\d+\s+\d+$/.test(raw) ? `rgb(${raw})` : raw;
}

/** 通用趋势图：渐变面积 + 折线，跟随主题色 */
export default function MetricChart({ data, lines, height = 280, yUnit = '' }: MetricChartProps) {
  const grid = cssVar('--border-default', '#e2e8f0');
  const axis = cssVar('--ink-faint', '#94a3b8');
  const surface = cssVar('--bg-surface-1', '#ffffff');
  const ink = cssVar('--ink-default', '#0f172a');

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
        <defs>
          {lines.map((line) => (
            <linearGradient key={line.key} id={`grad-${line.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={line.color} stopOpacity={0.28} />
              <stop offset="100%" stopColor={line.color} stopOpacity={0.02} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={grid} vertical={false} />
        <XAxis
          dataKey="time"
          stroke={axis}
          fontSize={11}
          tickLine={false}
          axisLine={false}
          minTickGap={24}
        />
        <YAxis
          stroke={axis}
          fontSize={11}
          unit={yUnit}
          width={46}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{
            background: surface,
            border: `1px solid ${grid}`,
            borderRadius: 8,
            fontSize: 12,
            color: ink,
            boxShadow: '0 4px 16px -4px rgba(0,0,0,0.15)',
          }}
          labelStyle={{ color: axis, fontSize: 11 }}
        />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 4 }} iconType="circle" iconSize={8} />
        {lines.map((line) => (
          <Area
            key={line.key}
            type="monotone"
            dataKey={line.key}
            name={line.name}
            stroke={line.color}
            strokeWidth={1.6}
            fill={`url(#grad-${line.key})`}
            dot={false}
            activeDot={{ r: 3, strokeWidth: 0 }}
            connectNulls
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
