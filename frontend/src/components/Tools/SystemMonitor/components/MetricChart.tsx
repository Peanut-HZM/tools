// frontend/src/components/Tools/SystemMonitor/components/MetricChart.tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

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

/** 通用趋势图：recharts 折线图封装 */
export default function MetricChart({ data, lines, height = 260, yUnit = '' }: MetricChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickFormatter={(v: string) => v.slice(5)} />
        <YAxis stroke="#64748b" fontSize={11} unit={yUnit} width={44} />
        <Tooltip
          contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
          labelStyle={{ color: '#94a3b8' }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {lines.map((line) => (
          <Line key={line.key} type="monotone" dataKey={line.key} name={line.name}
            stroke={line.color} strokeWidth={1.5} dot={false} connectNulls />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
