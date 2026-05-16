import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock,
  Database,
  Download,
  Edit3,
  HardDrive,
  Loader2,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  checkTokenUsageHealth,
  clearTokenUsageData,
  getDbTokenUsage,
  getUserDevices,
  refreshTokenUsage,
  renameDevice,
  type DbUsageItem,
  type DeviceInfo,
  type ModelSummaryItem,
  type SyncMeta,
  type TokenUsageGroupBy,
  type TokenUsageReportType,
  type TokenUsageSource,
  type UsageHealthCheck,
  type UsageSummary,
} from '../../api/tokenUsageApi';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];
const PAGE_SIZE = 20;

const emptySummary: UsageSummary = {
  total_input_tokens: 0,
  total_output_tokens: 0,
  total_tokens: 0,
  total_cost: 0,
  days_count: 0,
  avg_daily_cost: 0,
};

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

function sourceLabel(source: TokenUsageSource): string {
  if (source === 'claude') return 'Claude Code';
  if (source === 'opencode') return 'OpenCode';
  return '全部工具';
}

function healthLabel(ok: boolean): string {
  return ok ? '可用' : '不可用';
}

function formatRelativeTime(value?: string | null): string {
  if (!value) return '尚未同步';
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) return '时间未知';
  const diffSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  if (diffSeconds < 60) return '刚刚更新';
  if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} 分钟前`;
  if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)} 小时前`;
  return `${Math.floor(diffSeconds / 86400)} 天前`;
}

function formatDateTime(value?: string | null): string {
  if (!value) return '暂无记录';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未知';
  return date.toLocaleString('zh-CN', { hour12: false });
}

function DataFreshnessBadge({
  syncMeta,
  cached,
  refreshing,
  refreshError,
  onRefresh,
}: {
  syncMeta: SyncMeta | null;
  cached: boolean;
  refreshing: boolean;
  refreshError: string | null;
  onRefresh: () => void;
}) {
  const stale = Boolean(syncMeta?.is_stale);
  const locked = Boolean(syncMeta?.refresh_lock?.locked);
  const ttl = syncMeta?.cache_ttl_seconds ?? 0;

  const buildTooltip = () => {
    const lines: string[] = [];
    lines.push(`状态：${refreshing ? '后台更新中' : refreshError ? '刷新失败' : locked ? '其他窗口正在更新' : stale ? '数据已过期' : cached ? '缓存有效' : '数据库聚合'}`);
    lines.push(`最后同步：${formatDateTime(syncMeta?.last_success_at)}`);
    if (ttl > 0) lines.push(`缓存有效期：剩余 ${Math.ceil(ttl / 60)} 分钟`);
    else lines.push('缓存有效期：未命中缓存');
    if (syncMeta?.stale_reason) lines.push(syncMeta.stale_reason);
    if (refreshError) lines.push(refreshError);
    return lines.join('\n');
  };

  const textClass = refreshing || locked
    ? 'text-sky-300'
    : refreshError || stale
      ? 'text-amber-300'
      : 'text-emerald-300';

  return (
    <span className="inline-flex min-w-0 flex-1 items-center gap-1.5 text-xs" title={buildTooltip()}>
      {refreshing ? (
        <Loader2 className={`h-3.5 w-3.5 flex-shrink-0 animate-spin ${textClass}`} />
      ) : refreshError || stale ? (
        <AlertTriangle className={`h-3.5 w-3.5 flex-shrink-0 ${textClass}`} />
      ) : (
        <Clock className={`h-3.5 w-3.5 flex-shrink-0 ${textClass}`} />
      )}
      <span className={`truncate ${textClass}`}>
        {refreshing ? '后台更新中' : refreshError ? '刷新失败' : `最后同步 ${formatRelativeTime(syncMeta?.last_success_at)}`}
      </span>
    </span>
  );
}

export default function TokenUsage() {
  const [items, setItems] = useState<DbUsageItem[]>([]);
  const [summary, setSummary] = useState<UsageSummary>(emptySummary);
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [health, setHealth] = useState<UsageHealthCheck | null>(null);
  const [source, setSource] = useState<TokenUsageSource>('all');
  const [reportType, setReportType] = useState<TokenUsageReportType>('daily');
  const [days, setDays] = useState(30);
  const [groupBy, setGroupBy] = useState<TokenUsageGroupBy>('none');
  const [selectedDevice, setSelectedDevice] = useState('');
  const [chartType, setChartType] = useState<'bar' | 'line'>('bar');
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cached, setCached] = useState(false);
  const [lastSyncMessage, setLastSyncMessage] = useState<string | null>(null);
  const [autoExpanded, setAutoExpanded] = useState(false);
  const [actualDays, setActualDays] = useState<number | null>(null);
  const [modelSummary, setModelSummary] = useState<ModelSummaryItem[]>([]);
  const [syncMeta, setSyncMeta] = useState<SyncMeta | null>(null);
  const [backgroundRefreshing, setBackgroundRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const lastAutoRefreshRef = useRef<Record<string, number>>({});

  const timeRangeOptions = useMemo(() => {
    if (reportType === 'daily') {
      return [
        { label: '最近 7 天', value: 7 },
        { label: '最近 14 天', value: 14 },
        { label: '最近 30 天', value: 30 },
        { label: '最近 90 天', value: 90 },
      ];
    }
    if (reportType === 'weekly') {
      return [
        { label: '最近 4 周', value: 28 },
        { label: '最近 8 周', value: 56 },
        { label: '最近 12 周', value: 84 },
        { label: '最近 24 周', value: 168 },
      ];
    }
    return [
      { label: '最近 3 个月', value: 90 },
      { label: '最近 6 个月', value: 180 },
      { label: '最近 12 个月', value: 365 },
    ];
  }, [reportType]);

  const deviceNameMap = useMemo(() => {
    return new Map(devices.map(device => [device.id, device.name]));
  }, [devices]);

  useEffect(() => {
    setDays(reportType === 'daily' ? 30 : reportType === 'weekly' ? 56 : 180);
    setCurrentPage(1);
  }, [reportType]);

  const loadDevices = useCallback(async () => {
    const result = await getUserDevices();
    setDevices(result.devices);
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getDbTokenUsage({
        source,
        type: reportType,
        days,
        group_by: groupBy,
        device_id: selectedDevice || undefined,
      });
      setItems(result.items || []);
      setSummary(result.summary || emptySummary);
      setCached(Boolean(result.cached));
      setAutoExpanded(Boolean(result.auto_expanded));
      setActualDays(result.actual_days || null);
      setModelSummary(result.model_summary || []);
      setSyncMeta(result.sync_meta || null);
      setCurrentPage(1);
      if (result.devices?.length) {
        setDevices(result.devices);
      }
    } catch (err: any) {
      setError(err.message || '加载 Token 使用数据失败');
    } finally {
      setLoading(false);
    }
  }, [days, groupBy, reportType, selectedDevice, source]);

  useEffect(() => {
    checkTokenUsageHealth().then(setHealth).catch(() => setHealth(null));
    loadDevices().catch(() => undefined);
  }, [loadDevices]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const queryKey = `${source}:${reportType}:${days}:${groupBy}:${selectedDevice || 'all'}`;

  useEffect(() => {
    if (!syncMeta?.is_stale || backgroundRefreshing || refreshing) return;
    const lastAt = lastAutoRefreshRef.current[queryKey] || 0;
    if (Date.now() - lastAt < 60_000) return;

    let cancelled = false;
    lastAutoRefreshRef.current[queryKey] = Date.now();

    async function refreshStaleData() {
      setBackgroundRefreshing(true);
      setRefreshError(null);
      try {
        const result = await refreshTokenUsage({ days: Math.max(days, 90), background: true, reason: 'stale' });
        if (result.locked) {
          if (!cancelled) setRefreshError('其他窗口正在更新数据');
          return;
        }
        if (!cancelled) {
          await loadDevices();
          await fetchData();
        }
      } catch (err: any) {
        if (!cancelled) {
          setRefreshError(err.message || '后台刷新失败，已保留当前数据');
        }
      } finally {
        if (!cancelled) setBackgroundRefreshing(false);
      }
    }

    refreshStaleData();
    return () => {
      cancelled = true;
    };
  }, [backgroundRefreshing, days, fetchData, loadDevices, queryKey, refreshing, syncMeta?.is_stale]);

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    setLastSyncMessage(null);
    try {
      const result = await refreshTokenUsage({ days: Math.max(days, 90), background: false, reason: 'manual' });
      if (result.locked) {
        setRefreshError('已有刷新任务进行中，请稍后重试');
        return;
      }
      const errors = result.errors?.length ? `，${result.errors.length} 个来源有告警` : '';
      setLastSyncMessage(`已同步 ${result.total_records} 条记录${errors}`);
      setRefreshError(null);
      await loadDevices();
      await fetchData();
    } catch (err: any) {
      setError(err.message || '手动同步失败');
    } finally {
      setRefreshing(false);
    }
  };

  const handleClearData = async () => {
    const confirmed = window.confirm('确认清理当前登录用户的 Token 使用数据吗？\n\n这会删除数据库记录、同步日志和 Redis 缓存。');
    if (!confirmed) return;

    setClearing(true);
    setError(null);
    try {
      const result = await clearTokenUsageData();
      setLastSyncMessage(result.message);
      setItems([]);
      setSummary(emptySummary);
      setModelSummary([]);
      setSyncMeta(null);
      setRefreshError(null);
      await loadDevices();
      await fetchData();
    } catch (err: any) {
      setError(err.message || '清理数据失败');
    } finally {
      setClearing(false);
    }
  };

  const handleRenameDevice = async () => {
    if (!selectedDevice) return;
    const currentName = devices.find(device => device.id === selectedDevice)?.name || selectedDevice;
    const nextName = window.prompt('请输入设备名称。留空会恢复默认名称。', currentName);
    if (nextName === null) return;

    setLoading(true);
    setError(null);
    try {
      await renameDevice(selectedDevice, nextName);
      await loadDevices();
      await fetchData();
    } catch (err: any) {
      setError(err.message || '重命名设备失败');
    } finally {
      setLoading(false);
    }
  };

  const sortedItems = useMemo(
    () => [...items].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()),
    [items]
  );

  const chartData = useMemo(
    () => [...items].sort((a, b) => a.date.localeCompare(b.date)).map(item => ({
      date: item.date,
      inputTokens: item.input_tokens,
      outputTokens: item.output_tokens,
      cacheTokens: item.cache_creation_tokens + item.cache_read_tokens,
      totalTokens: item.total_tokens,
      cost: item.total_cost,
    })),
    [items]
  );

  const groupedData = useMemo(() => {
    if (groupBy === 'none') return [];
    const grouped: Record<string, Record<string, number>> = {};
    const dates = new Set<string>();

    items.forEach(item => {
      const key = groupBy === 'device' && item.group_key
        ? deviceNameMap.get(item.group_key) || item.group_key
        : item.group_key || '未识别';
      dates.add(item.date);
      grouped[key] = grouped[key] || {};
      grouped[key][item.date] = (grouped[key][item.date] || 0) + item.total_tokens;
    });

    return [...dates].sort().map(date => {
      const row: Record<string, string | number> = { date };
      Object.entries(grouped).forEach(([key, values]) => {
        row[key] = values[date] || 0;
      });
      return row;
    });
  }, [deviceNameMap, groupBy, items]);

  const modelData = useMemo(() => {
    const sourceName = (sourceValue: string) => {
      if (sourceValue === 'claude') return 'Claude';
      if (sourceValue === 'opencode') return 'OpenCode';
      return sourceValue;
    };

    return modelSummary
      .map(item => ({
        name: `${sourceName(item.source)} · ${item.display_model || item.model || '未知模型'}`,
        value: item.total_cost,
        tokens: item.total_tokens,
      }))
      .filter(item => item.value > 0 || item.tokens > 0)
      .sort((a, b) => b.value - a.value || b.tokens - a.tokens)
      .slice(0, 8);
  }, [modelSummary]);

  const totalPages = Math.max(1, Math.ceil(sortedItems.length / PAGE_SIZE));
  const paginatedItems = sortedItems.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const getGroupLabel = (item: DbUsageItem) => {
    if (groupBy === 'device' && item.group_key) {
      return deviceNameMap.get(item.group_key) || item.group_key;
    }
    return item.group_key || '-';
  };

  const exportCSV = () => {
    if (!items.length) return;
    const headers = ['日期', '分组', '输入 Token', '输出 Token', '缓存创建', '缓存读取', '总 Token', '成本 USD', '模型'];
    const rows = sortedItems.map(item => [
      item.date,
      item.group_key || '',
      item.input_tokens,
      item.output_tokens,
      item.cache_creation_tokens,
      item.cache_read_tokens,
      item.total_tokens,
      item.total_cost,
      item.models_used.join('; '),
    ]);
    const csv = [headers, ...rows]
      .map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(','))
      .join('\n');
    const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `token-usage-${source}-${reportType}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-0 overflow-y-auto bg-slate-950 p-6 text-slate-100">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal text-white">
            Token 消耗统计
            <span className="ml-3 inline-flex items-center gap-1 text-sm font-normal text-slate-400">
              <Database className="h-3.5 w-3.5" />
              按登录用户、设备和工具维度统计
            </span>
          </h1>
        </div>

        <div className="flex flex-nowrap items-center gap-2">
          <DataFreshnessBadge
            syncMeta={syncMeta}
            cached={cached}
            refreshing={refreshing || backgroundRefreshing}
            refreshError={refreshError}
            onRefresh={handleRefresh}
          />
          <button
            onClick={handleRefresh}
            disabled={loading || refreshing}
            className="inline-flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            title="刷新"
          >
            {refreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </button>
          <button
            onClick={exportCSV}
            disabled={!items.length || loading}
            className="inline-flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            title="导出"
          >
            <Download className="h-4 w-4" />
          </button>
          <button
            onClick={handleClearData}
            disabled={loading || clearing}
            className="inline-flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            title="清理"
          >
            {clearing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {health && (
        <div className="mb-4 grid gap-3 md:grid-cols-4">
          {[
            { name: 'ccusage', ok: health.ccusage_installed, detail: 'Claude Code' },
            { name: 'opencode-usage', ok: health.opencode_usage_installed, detail: 'OpenCode' },
            { name: 'ccusage-opencode', ok: health.ccusage_opencode_installed, detail: 'OpenCode 历史数据' },
            { name: 'Codex/OpenClaw', ok: null, detail: '待接入真实 usage 数据' },
          ].map(({ name, ok, detail }) => (
            <div key={name} className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-900 px-3 py-2">
              <span className="text-sm text-slate-300" title={detail}>{name}</span>
              <span className={`inline-flex items-center gap-1 text-xs ${ok === true ? 'text-emerald-300' : ok === false ? 'text-red-300' : 'text-slate-500'}`}>
                <CheckCircle2 className="h-3.5 w-3.5" />
                {ok === null ? '待接入' : healthLabel(Boolean(ok))}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="mb-5 grid gap-3 rounded-md border border-slate-800 bg-slate-900 p-4 lg:grid-cols-6">
        <label className="space-y-1">
          <span className="text-xs text-slate-400">工具</span>
          <select value={source} onChange={event => setSource(event.target.value as TokenUsageSource)} className="h-9 w-full rounded-md border border-slate-700 bg-slate-950 px-2 text-sm">
            <option value="all">全部工具</option>
            <option value="claude">Claude Code</option>
            <option value="opencode">OpenCode</option>
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-slate-400">维度</span>
          <select value={reportType} onChange={event => setReportType(event.target.value as TokenUsageReportType)} className="h-9 w-full rounded-md border border-slate-700 bg-slate-950 px-2 text-sm">
            <option value="daily">按天</option>
            <option value="weekly">按周</option>
            <option value="monthly">按月</option>
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-slate-400">时间范围</span>
          <select value={days} onChange={event => setDays(Number(event.target.value))} className="h-9 w-full rounded-md border border-slate-700 bg-slate-950 px-2 text-sm">
            {timeRangeOptions.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-slate-400">设备</span>
          <div className="flex gap-1">
            <select value={selectedDevice} onChange={event => setSelectedDevice(event.target.value)} className="h-9 min-w-0 flex-1 rounded-md border border-slate-700 bg-slate-950 px-2 text-sm">
              <option value="">全部设备</option>
              {devices.map(device => (
                <option key={device.id} value={device.id}>{device.name}</option>
              ))}
            </select>
            <button
              onClick={handleRenameDevice}
              disabled={!selectedDevice}
              title="重命名设备"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Edit3 className="h-4 w-4" />
            </button>
          </div>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-slate-400">分组</span>
          <select value={groupBy} onChange={event => setGroupBy(event.target.value as TokenUsageGroupBy)} className="h-9 w-full rounded-md border border-slate-700 bg-slate-950 px-2 text-sm">
            <option value="none">按日期汇总</option>
            <option value="device">按设备对比</option>
            <option value="model">按模型分析</option>
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-slate-400">图表</span>
          <select value={chartType} onChange={event => setChartType(event.target.value as 'bar' | 'line')} className="h-9 w-full rounded-md border border-slate-700 bg-slate-950 px-2 text-sm">
            <option value="bar">柱状图</option>
            <option value="line">折线图</option>
          </select>
        </label>
      </div>

      {(error || lastSyncMessage || autoExpanded) && (
        <div className="mb-5 space-y-2">
          {error && <div className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>}
          {lastSyncMessage && <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">{lastSyncMessage}</div>}
          {autoExpanded && <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">当前范围无数据，已自动扩大到最近 {actualDays} 天。</div>}
        </div>
      )}

      <div className="mb-5 grid gap-3 md:grid-cols-5">
        {[
          { label: '总成本', value: formatCurrency(summary.total_cost), icon: Activity },
          { label: '日均成本', value: formatCurrency(summary.avg_daily_cost), icon: BarChart3 },
          { label: '总 Token', value: formatToken(summary.total_tokens), icon: Database },
          { label: '输入 Token', value: formatToken(summary.total_input_tokens), icon: HardDrive },
          { label: '输出 Token', value: formatToken(summary.total_output_tokens), icon: HardDrive },
        ].map(card => (
          <div key={card.label} className="rounded-md border border-slate-800 bg-slate-900 p-4">
            <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
              <span>{card.label}</span>
              <card.icon className="h-4 w-4" />
            </div>
            <div className="text-xl font-semibold text-white">{card.value}</div>
          </div>
        ))}
      </div>

      <div className="mb-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="rounded-md border border-slate-800 bg-slate-900 p-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-medium text-white">{groupBy === 'none' ? `${sourceLabel(source)} 趋势` : groupBy === 'device' ? '设备消耗对比' : '模型消耗分析'}</h2>
            {loading && <Loader2 className="h-4 w-4 animate-spin text-slate-400" />}
          </div>
          <div className="h-80">
            {(groupBy === 'none' ? chartData : groupedData).length ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={groupBy === 'none' ? chartData : groupedData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                  <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={formatToken} />
                  {groupBy === 'none' && <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={value => `$${value}`} />}
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: '#e2e8f0' }} />
                  <Legend />
                  {groupBy === 'none' ? (
                    <>
                      {chartType === 'bar' ? (
                        <>
                          <Bar yAxisId="left" dataKey="inputTokens" stackId="tokens" fill="#3b82f6" name="输入" />
                          <Bar yAxisId="left" dataKey="outputTokens" stackId="tokens" fill="#10b981" name="输出" />
                          <Bar yAxisId="left" dataKey="cacheTokens" stackId="tokens" fill="#f59e0b" name="缓存" />
                        </>
                      ) : (
                        <>
                          <Line yAxisId="left" type="monotone" dataKey="inputTokens" stroke="#3b82f6" strokeWidth={2} name="输入" dot={{ r: 3 }} />
                          <Line yAxisId="left" type="monotone" dataKey="outputTokens" stroke="#10b981" strokeWidth={2} name="输出" dot={{ r: 3 }} />
                          <Line yAxisId="left" type="monotone" dataKey="cacheTokens" stroke="#f59e0b" strokeWidth={2} name="缓存" dot={{ r: 3 }} />
                        </>
                      )}
                      <Line yAxisId="right" type="monotone" dataKey="cost" stroke="#ef4444" strokeWidth={2} name="成本" dot={{ r: 3 }} />
                    </>
                  ) : (
                    Object.keys(groupedData[0] || {}).filter(key => key !== 'date').map((key, index) => (
                      chartType === 'bar'
                        ? <Bar key={key} yAxisId="left" dataKey={key} fill={COLORS[index % COLORS.length]} name={key} />
                        : <Line key={key} yAxisId="left" type="monotone" dataKey={key} stroke={COLORS[index % COLORS.length]} strokeWidth={2} name={key} dot={{ r: 3 }} />
                    ))
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">暂无图表数据</div>
            )}
          </div>
        </div>

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
                  <Tooltip formatter={(value: number) => [formatCurrency(value), '成本']} contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: '#e2e8f0' }} />
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
                <span className="font-mono text-slate-400">{formatCurrency(model.value)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-md border border-slate-800 bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <h2 className="text-base font-medium text-white">明细数据</h2>
          <span className="text-xs text-slate-400">共 {items.length} 条</span>
        </div>
        <div className="overflow-auto">
          <table className="w-full min-w-[920px] text-sm">
            <thead className="bg-slate-950 text-xs text-slate-400">
              <tr>
                <th className="px-4 py-3 text-left">日期</th>
                {groupBy !== 'none' && <th className="px-4 py-3 text-left">分组</th>}
                <th className="px-4 py-3 text-right">输入</th>
                <th className="px-4 py-3 text-right">输出</th>
                <th className="px-4 py-3 text-right">缓存创建</th>
                <th className="px-4 py-3 text-right">缓存读取</th>
                <th className="px-4 py-3 text-right">总计</th>
                <th className="px-4 py-3 text-right">成本</th>
                <th className="px-4 py-3 text-left">模型</th>
              </tr>
            </thead>
            <tbody>
              {!paginatedItems.length && !loading ? (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-500" colSpan={groupBy === 'none' ? 8 : 9}>暂无数据。可以点击“刷新”采集当前用户和设备的数据。</td>
                </tr>
              ) : paginatedItems.map((item, index) => (
                <tr key={`${item.date}-${item.group_key || 'all'}-${index}`} className="border-t border-slate-800 hover:bg-slate-800/60">
                  <td className="px-4 py-3 text-slate-200">{item.date}</td>
                  {groupBy !== 'none' && <td className="max-w-[180px] truncate px-4 py-3 text-slate-300" title={getGroupLabel(item)}>{getGroupLabel(item)}</td>}
                  <td className="px-4 py-3 text-right font-mono text-slate-300">{formatToken(item.input_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-300">{formatToken(item.output_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-400">{formatToken(item.cache_creation_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-400">{formatToken(item.cache_read_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono font-medium text-white">{formatToken(item.total_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono text-emerald-300">{formatCurrency(item.total_cost)}</td>
                  <td className="max-w-[240px] truncate px-4 py-3 text-slate-400" title={item.models_used.join(', ')}>{item.models_used.join(', ') || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3 text-sm">
            <span className="text-slate-400">第 {currentPage} / {totalPages} 页</span>
            <div className="flex gap-2">
              <button onClick={() => setCurrentPage(page => Math.max(1, page - 1))} disabled={currentPage === 1} className="rounded-md border border-slate-700 px-3 py-1.5 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40">上一页</button>
              <button onClick={() => setCurrentPage(page => Math.min(totalPages, page + 1))} disabled={currentPage === totalPages} className="rounded-md border border-slate-700 px-3 py-1.5 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40">下一页</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
