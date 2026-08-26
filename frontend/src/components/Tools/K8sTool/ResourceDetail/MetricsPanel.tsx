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

// CPU 颜色 / 内存颜色
const CPU_COLOR = '#3b82f6';
const MEMORY_COLOR = '#10b981';

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
            <div className="w-2 h-2 rounded-full" style={{ background: CPU_COLOR }}></div>
            <span className="text-xs text-ink-muted">CPU</span>
          </div>
          <div className="text-xl font-mono text-ink">
            {dataPoints[dataPoints.length - 1].cpu}
            <span className="text-xs text-ink-faint ml-1">cores</span>
          </div>
        </Card>

        <Card className="bg-surface-1/50 border-border/50 p-3 shadow-none">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full" style={{ background: MEMORY_COLOR }}></div>
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
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="time"
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                stroke="#4b5563"
              />
              <YAxis
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                stroke="#4b5563"
                width={50}
                tickFormatter={(v) => `${v}`}
              />
              <Tooltip
                contentStyle={{
                  background: '#1e293b',
                  border: '1px solid #374151',
                  borderRadius: 4,
                  fontSize: 12,
                }}
                labelStyle={{ color: '#9ca3af' }}
              />
              <Line
                type="monotone"
                dataKey="cpu"
                stroke={CPU_COLOR}
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
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="time"
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                stroke="#4b5563"
              />
              <YAxis
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                stroke="#4b5563"
                width={50}
                tickFormatter={(v) => `${v}`}
              />
              <Tooltip
                contentStyle={{
                  background: '#1e293b',
                  border: '1px solid #374151',
                  borderRadius: 4,
                  fontSize: 12,
                }}
                labelStyle={{ color: '#9ca3af' }}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, color: '#9ca3af' }}
              />
              <Line
                type="monotone"
                dataKey="memory"
                stroke={MEMORY_COLOR}
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
