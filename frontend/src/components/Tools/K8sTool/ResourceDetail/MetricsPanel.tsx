/**
 * K8s 资源详情 - 指标面板
 *
 * 展示 Pod 的 CPU / 内存使用量折线图（recharts）
 * 每次轮询获取的快照数据累积在本地 state 中，形成时间序列
 * 数据来源：api.getPodMetrics()
 */
import React, { useEffect, useRef, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Loader2, LineChart as LineChartIcon } from 'lucide-react';
import { useI18n } from '../../../../i18n';
import { useK8sStore } from '../../../../stores/k8sStore';
import { usePodMetrics } from '../../../../hooks/useK8sClient';
import { Card } from '@/components/ui/Card';

interface Props {
  podName: string;
  namespace: string;
}

/** 单个图表数据点 */
interface MetricsDataPoint {
  time: string;     // HH:MM:SS 显示用
  timestamp: number; // Unix 时间戳，用于排序
  cpu: number;       // 累计 CPU（核）
  memory: number;    // 累计内存（Mi）
}

// 最多保留 60 个数据点（15s * 60 = 15 分钟）
const MAX_POINTS = 60;

/** 图表语义色（与 styles/tokens/colors.css 中 --chart-* 六项一一对应） */
interface ChartColors {
  cpu: string;     // CPU 折线
  memory: string;  // 内存折线
  grid: string;    // 网格线 / 分隔线
  axis: string;    // 坐标轴线
  surface: string; // Tooltip 面板底色
  label: string;   // 刻度与图例文字
}

/**
 * 从 CSS token 读取图表颜色的"已解析值"（具体色值，非 var() 引用）
 *
 * 为什么不用 var() 直接传给 recharts：
 * recharts 会把 stroke/fill 以 SVG attribute 形式渲染到 <path>/<line>/<text>，
 * 而 SVG presentation attribute 不做 CSS 变量替换（部分浏览器不解析 var()）；
 * 且折线颜色还会驱动图例图标、Tooltip 色点、悬停圆点等 recharts 内部 SVG 元素，
 * 这些元素不接受外部 style prop，无法通过内联样式覆盖。
 * 因此统一经 getComputedStyle 读取 token 的最终值，attribute 与 style 均可安全使用。
 */
const readChartColors = (): ChartColors => {
  // 防御：非浏览器环境（SSR/测试）下返回空串，交由 recharts 默认值兜底
  const styles =
    typeof window === 'undefined' ? null : getComputedStyle(document.documentElement);
  const read = (name: string): string =>
    styles ? styles.getPropertyValue(name).trim() : '';
  return {
    cpu: read('--chart-cpu'),
    memory: read('--chart-memory'),
    grid: read('--chart-grid'),
    axis: read('--chart-axis'),
    surface: read('--chart-surface'),
    label: read('--chart-label'),
  };
};

/**
 * 将 K8s 资源量字符串转换为数值
 * - CPU: "100m" → 0.1（核）、"2" → 2（核）
 * - 内存: "256Mi" → 256（Mi）、"1Gi" → 1024（Mi）、"1024Ki" → 1（Mi）
 */
const parseCpu = (cpu: string): number => {
  if (!cpu) return 0;
  if (cpu.endsWith('m')) return parseFloat(cpu.slice(0, -1)) / 1000;
  return parseFloat(cpu) || 0;
};

const parseMemoryMi = (mem: string): number => {
  if (!mem) return 0;
  if (mem.endsWith('Gi')) return parseFloat(mem) * 1024;
  if (mem.endsWith('Mi')) return parseFloat(mem);
  if (mem.endsWith('Ki')) return parseFloat(mem) / 1024;
  // 纯字节
  return parseFloat(mem) / (1024 * 1024) || 0;
};

/** 将 Unix 时间戳格式化为 HH:MM:SS */
const formatTime = (ts: number): string => {
  const d = new Date(ts);
  return d.toLocaleTimeString('zh-CN', { hour12: false });
};

export const MetricsPanel: React.FC<Props> = ({ podName, namespace }) => {
  const { t } = useI18n();
  const mt = t.tools['k8s-tool'].resourceDetail.metrics;
  const { activeConnectionId } = useK8sStore();

  const { data: metricsData, isError, isLoading } = usePodMetrics(
    activeConnectionId,
    podName,
    namespace,
  );

  // 图表颜色：初始从 CSS token 读取，主题切换（<html data-theme> 变更）时自动重读
  const [chartColors, setChartColors] = useState<ChartColors>(readChartColors);
  useEffect(() => {
    // ThemeProvider 挂载后才写入初始 data-theme，渲染期读取时序不可靠，
    // 改用 MutationObserver 监听属性变更，保证任意主题切换路径都能联动
    const observer = new MutationObserver(() => setChartColors(readChartColors()));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });
    return () => observer.disconnect();
  }, []);

  // 累积数据点
  const [dataPoints, setDataPoints] = useState<MetricsDataPoint[]>([]);
  // 记录最新时间戳，避免重复添加同一点
  const lastTsRef = useRef<number>(0);

  // 每次 metricsData 更新时，累积一个新数据点
  useEffect(() => {
    if (!metricsData) return;

    const ts = new Date(metricsData.timestamp).getTime() || Date.now();
    // 避免重复添加
    if (ts <= lastTsRef.current) return;
    lastTsRef.current = ts;

    // 聚合所有容器的 CPU / 内存
    const totalCpu = metricsData.containers.reduce(
      (sum, c) => sum + parseCpu(c.cpu_usage),
      0,
    );
    const totalMemory = metricsData.containers.reduce(
      (sum, c) => sum + parseMemoryMi(c.memory_usage),
      0,
    );

    const newPoint: MetricsDataPoint = {
      time: formatTime(ts),
      timestamp: ts,
      cpu: Math.round(totalCpu * 1000) / 1000,
      memory: Math.round(totalMemory),
    };

    setDataPoints((prev) => {
      const next = [...prev, newPoint];
      // 保留最近 MAX_POINTS 个
      return next.length > MAX_POINTS ? next.slice(next.length - MAX_POINTS) : next;
    });
  }, [metricsData]);

  // 当 Pod 切换时清空数据
  useEffect(() => {
    setDataPoints([]);
    lastTsRef.current = 0;
  }, [podName, namespace]);

  // 加载中
  if (isLoading && dataPoints.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-ink-faint">
        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
        {t.common.loading}
      </div>
    );
  }

  // 错误（Metrics Server 未安装）
  if (isError && dataPoints.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-ink-faint gap-2">
        <LineChartIcon className="w-8 h-8 text-ink-faint" />
        <div>{mt.unavailable}</div>
        <div className="text-xs text-ink-faint">{t.tools['k8s-tool'].errors.METRICS_UNAVAILABLE}</div>
      </div>
    );
  }

  // 无数据
  if (dataPoints.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-ink-faint gap-2">
        <LineChartIcon className="w-8 h-8 text-ink-faint" />
        <div>{mt.noData}</div>
      </div>
    );
  }

  return (
    <div className="p-4 h-full overflow-y-auto space-y-4">
      {/* 当前值概览卡片 */}
      <div className="grid grid-cols-2 gap-3">
        <Card className="bg-surface-1/50 border-border/50 p-3 shadow-none">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full" style={{ background: chartColors.cpu }}></div>
            <span className="text-xs text-ink-muted">CPU</span>
          </div>
          <div className="text-xl font-mono text-ink">
            {dataPoints[dataPoints.length - 1].cpu}
            <span className="text-xs text-ink-faint ml-1">cores</span>
          </div>
        </Card>

        <Card className="bg-surface-1/50 border-border/50 p-3 shadow-none">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full" style={{ background: chartColors.memory }}></div>
            <span className="text-xs text-ink-muted">Memory</span>
          </div>
          <div className="text-xl font-mono text-ink">
            {dataPoints[dataPoints.length - 1].memory}
            <span className="text-xs text-ink-faint ml-1">Mi</span>
          </div>
        </Card>
      </div>

      {/* CPU 折线图 */}
      <div>
        <h4 className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-2">
          {mt.cpuUsage}
        </h4>
        <div className="bg-surface-1/30 border border-border/50 rounded-lg p-2" style={{ height: 180 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={dataPoints}>
              <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
              <XAxis
                dataKey="time"
                tick={{ fill: chartColors.label, fontSize: 10 }}
                stroke={chartColors.axis}
              />
              <YAxis
                tick={{ fill: chartColors.label, fontSize: 10 }}
                stroke={chartColors.axis}
                width={50}
                tickFormatter={(v) => `${v}`}
              />
              <Tooltip
                contentStyle={{
                  background: chartColors.surface,
                  border: `1px solid ${chartColors.grid}`,
                  borderRadius: 4,
                  fontSize: 12,
                }}
                labelStyle={{ color: chartColors.label }}
              />
              <Line
                type="monotone"
                dataKey="cpu"
                stroke={chartColors.cpu}
                strokeWidth={2}
                dot={false}
                name="CPU (cores)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Memory 折线图 */}
      <div>
        <h4 className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-2">
          {mt.memoryUsage}
        </h4>
        <div className="bg-surface-1/30 border border-border/50 rounded-lg p-2" style={{ height: 180 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={dataPoints}>
              <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
              <XAxis
                dataKey="time"
                tick={{ fill: chartColors.label, fontSize: 10 }}
                stroke={chartColors.axis}
              />
              <YAxis
                tick={{ fill: chartColors.label, fontSize: 10 }}
                stroke={chartColors.axis}
                width={50}
                tickFormatter={(v) => `${v}`}
              />
              <Tooltip
                contentStyle={{
                  background: chartColors.surface,
                  border: `1px solid ${chartColors.grid}`,
                  borderRadius: 4,
                  fontSize: 12,
                }}
                labelStyle={{ color: chartColors.label }}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, color: chartColors.label }}
              />
              <Line
                type="monotone"
                dataKey="memory"
                stroke={chartColors.memory}
                strokeWidth={2}
                dot={false}
                name="Memory (Mi)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
