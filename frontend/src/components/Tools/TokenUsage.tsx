import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Clock,
  Database,
  Download,
  Edit3,
  HardDrive,
  Loader2,
  RefreshCw,
  Settings,
  Trash2,
} from 'lucide-react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  clearTokenUsageData,
  createDeviceAlias,
  deleteDeviceAlias,
  getDbTokenUsage,
  getUserDevices,
  mergeDevices,
  refreshTokenUsage,
  renameDevice,
  type DbUsageItem,
  type DeviceInfo,
  type FingerprintMatch,
  type ModelSummaryItem,
  type SyncMeta,
  type TokenUsageGroupBy,
  type TokenUsageReportType,
  type TokenUsageSortBy,
  type TokenUsageSortOrder,
  type TokenUsageSource,
} from '../../api/tokenUsageApi';
import DeviceManagerModal from './TokenUsage/DeviceManagerModal';
import FingerprintMatchDialog from './TokenUsage/FingerprintMatchDialog';
import { useDebouncedValue } from './hooks/useDebouncedValue';
import { useTokenUsageSummary } from './hooks/useTokenUsageSummary';
import { useTokenUsageDetails } from './hooks/useTokenUsageDetails';
import { useTokenUsagePolling } from './hooks/useTokenUsagePolling';
import DimensionPieCard, { type PieSlice } from './TokenUsage/DimensionPieCard';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];
const PAGE_SIZE = 50;

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
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [reportType, setReportType] = useState<TokenUsageReportType>('daily');
  const [days, setDays] = useState(30);
  const [groupBy, setGroupBy] = useState<TokenUsageGroupBy>('none');
  const [selectedDevice, setSelectedDevice] = useState('');
  const [selectedTool, setSelectedTool] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [sortBy, setSortBy] = useState<TokenUsageSortBy>('date');
  const [chartType, setChartType] = useState<'bar' | 'line'>('bar');
  const [currentPage, setCurrentPage] = useState(1);
  const [refreshing, setRefreshing] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deviceError, setDeviceError] = useState<string | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  const [lastSyncMessage, setLastSyncMessage] = useState<string | null>(null);
  const [backgroundRefreshing, setBackgroundRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [fingerprintMatch, setFingerprintMatch] = useState<FingerprintMatch | null>(null);
  const [deviceManagerOpen, setDeviceManagerOpen] = useState(false);

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
    try {
      const result = await getUserDevices();
      setDevices(result.devices);
      setDeviceError(null);
      return true;
    } catch (err: any) {
      setDeviceError(err.message || '加载设备列表失败');
      return false;
    }
  }, []);

  const debouncedDays = useDebouncedValue(days, 200);
  const debouncedGroupBy = useDebouncedValue(groupBy, 200);
  const debouncedSortBy = useDebouncedValue(sortBy, 200);
  const debouncedDevice = useDebouncedValue(selectedDevice, 300);
  const debouncedTool = useDebouncedValue(selectedTool, 300);
  const debouncedModel = useDebouncedValue(selectedModel, 300);

  const summary = useTokenUsageSummary({
    type: reportType,
    days: debouncedDays,
    group_by: debouncedGroupBy,
    source: 'all',
    device_id: debouncedDevice || undefined,
    tool_id: debouncedTool || undefined,
    model: debouncedModel || undefined,
  });

  const details = useTokenUsageDetails({
    type: reportType,
    days: debouncedDays,
    group_by: debouncedGroupBy,
    source: 'all',
    device_id: debouncedDevice || undefined,
    tool_id: debouncedTool || undefined,
    model: debouncedModel || undefined,
    sort_by: debouncedSortBy,
    sort_order: 'desc',
    limit: PAGE_SIZE,
    offset: (currentPage - 1) * PAGE_SIZE,
  });

  useTokenUsagePolling(async (opts) => {
    await summary.refresh(opts);
  });

  useEffect(() => {
    void loadDevices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toolNameMap = useMemo(() => {
    const map = new Map<string, string>();
    summary.data.filter_options.tools.forEach(tool => map.set(tool.tool_id, tool.tool_name));
    summary.data.dimension_summaries.tools.forEach(tool => {
      if (tool.tool_id) map.set(tool.tool_id, tool.label);
      map.set(tool.key, tool.label);
    });
    return map;
  }, [summary.data.dimension_summaries.tools, summary.data.filter_options.tools]);

  const modelNameMap = useMemo(() => {
    const map = new Map<string, string>();
    summary.data.filter_options.models.forEach(model => map.set(model.model, model.model_display_name));
    summary.data.dimension_summaries.models.forEach(model => {
      if (model.model) map.set(model.model, model.label);
      map.set(model.key, model.label);
    });
    return map;
  }, [summary.data.dimension_summaries.models, summary.data.filter_options.models]);

  const toolOptions = useMemo(() => {
    if (summary.data.filter_options.tools.length) {
      return summary.data.filter_options.tools.map(tool => ({
        value: tool.tool_id,
        label: tool.tool_name,
        count: tool.records_count,
      }));
    }
    return summary.data.dimension_summaries.tools.map(tool => ({
      value: tool.tool_id || tool.key,
      label: tool.label,
      count: tool.records_count,
    }));
  }, [summary.data.dimension_summaries.tools, summary.data.filter_options.tools]);

  const modelOptions = useMemo(() => {
    const options = summary.data.filter_options.models.length
      ? summary.data.filter_options.models
          .filter(model => !selectedTool || model.tool_id === selectedTool)
          .map(model => ({
            value: model.model,
            label: model.model_display_name,
            count: model.records_count,
          }))
      : summary.data.dimension_summaries.models
          .filter(model => !selectedTool || model.tool_id === selectedTool)
          .map(model => ({
            value: model.model || model.key,
            label: model.label,
            count: model.records_count,
          }));

    const unique = new Map<string, { value: string; label: string; count: number }>();
    options.forEach(option => {
      if (!option.value || unique.has(option.value)) return;
      unique.set(option.value, option);
    });
    return [...unique.values()];
  }, [summary.data.dimension_summaries.models, summary.data.filter_options.models, selectedTool]);

  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    setRefreshError(null);
    setLastSyncMessage(null);
    try {
      const result = await refreshTokenUsage({ days: Math.max(days, 90), background: false, reason: 'manual' });
      if (result.locked) {
        setRefreshError('已有刷新任务进行中，请稍后重试');
        return;
      }
      if (result.fingerprint_match) {
        setFingerprintMatch(result.fingerprint_match);
      }
      const errors = result.errors?.length ? `，${result.errors.length} 个来源有告警` : '';
      setLastSyncMessage(`已同步 ${result.total_records} 条记录${errors}`);
      setRefreshError(null);
      await loadDevices();
      await Promise.all([summary.refresh(), details.refresh()]);
    } catch (err: any) {
      setRefreshError(err.message || '手动刷新失败');
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
      setRefreshError(null);
      await loadDevices();
      await Promise.all([summary.refresh(), details.refresh()]);
    } catch (err: any) {
      setError(err.message || '清理数据失败');
    } finally {
      setClearing(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncError(null);
    setLastSyncMessage(null);
    try {
      const token = localStorage.getItem('token') || '';
      const res = await fetch('/api/token-usage/refresh-ccusage', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setLastSyncMessage(`ccusage 同步完成: ${data.synced_records} 条`);
      await Promise.all([summary.refresh(), details.refresh()]);
    } catch (e: any) {
      setSyncError(e.message || '同步失败');
    } finally {
      setSyncing(false);
    }
  };

  const handleRenameDevice = async () => {
    if (!selectedDevice) return;
    const currentName = devices.find(device => device.id === selectedDevice)?.name || selectedDevice;
    const nextName = window.prompt('请输入设备名称。留空会恢复默认名称。', currentName);
    if (nextName === null) return;

    setRefreshing(true);
    setError(null);
    try {
      await renameDevice(selectedDevice, nextName);
      await loadDevices();
      await Promise.all([summary.refresh(), details.refresh()]);
    } catch (err: any) {
      setError(err.message || '重命名设备失败');
    } finally {
      setRefreshing(false);
    }
  };

  const sortedItems = useMemo(() => [...details.data.items], [details.data.items]);

  const getToolLabel = useCallback((value?: string | null) => {
    if (!value) return '-';
    return toolNameMap.get(value) || value;
  }, [toolNameMap]);

  const getModelLabel = useCallback((value?: string | null) => {
    if (!value) return '-';
    return modelNameMap.get(value) || value;
  }, [modelNameMap]);

  const formatModelsUsed = useCallback((models: string[]) => {
    if (!models.length) return '-';
    return models.map(model => getModelLabel(model)).join(', ');
  }, [getModelLabel]);

  const chartData = useMemo(
    () => [...details.data.items].sort((a, b) => a.date.localeCompare(b.date)).map(item => ({
      date: item.date,
      inputTokens: item.input_tokens,
      outputTokens: item.output_tokens,
      cacheTokens: item.cache_creation_tokens + item.cache_read_tokens,
      totalTokens: item.total_tokens,
      cost: item.total_cost,
    })),
    [details.data.items]
  );

  const groupedData = useMemo(() => {
    if (groupBy === 'none') return [];
    const grouped: Record<string, Record<string, number>> = {};
    const dates = new Set<string>();

    details.data.items.forEach(item => {
      const key = item.group_key
        ? groupBy === 'device'
          ? deviceNameMap.get(item.group_key) || item.group_key
          : groupBy === 'tool'
            ? getToolLabel(item.group_key)
            : groupBy === 'model'
              ? getModelLabel(item.group_key)
              : item.group_key
        : '未识别';
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
  }, [deviceNameMap, getModelLabel, getToolLabel, groupBy, details.data.items]);

  const totalPages = Math.max(1, Math.ceil(details.data.total / PAGE_SIZE));
  const paginatedItems = details.data.items;

  const getGroupLabel = (item: DbUsageItem) => {
    if (groupBy === 'device' && item.group_key) {
      return deviceNameMap.get(item.group_key) || item.group_key;
    }
    if (groupBy === 'tool' && item.group_key) {
      return getToolLabel(item.group_key);
    }
    if (groupBy === 'model' && item.group_key) {
      return getModelLabel(item.group_key);
    }
    return item.group_key || '-';
  };

  const getRowToolLabel = (item: DbUsageItem) => {
    if (item.tool_id) return getToolLabel(item.tool_id);
    return '-';
  };

  const exportCSV = () => {
    if (!details.data.items.length) return;
    const headers = ['日期', '分组', '设备', '工具', '模型', '输入 Token', '输出 Token', '缓存创建', '缓存读取', '总 Token', '成本 USD'];
    const rows = details.data.items.map(item => [
      item.date,
      getGroupLabel(item),
      item.device_name || '-',
      getRowToolLabel(item),
      formatModelsUsed(item.models_used),
      item.input_tokens,
      item.output_tokens,
      item.cache_creation_tokens,
      item.cache_read_tokens,
      item.total_tokens,
      item.total_cost,
    ]);
    const csv = [headers, ...rows]
      .map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(','))
      .join('\n');
    const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `token-usage-all-${reportType}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

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

  const chartTitle = groupBy === 'none'
    ? 'Token 消耗趋势'
    : groupBy === 'device'
      ? '设备消耗对比'
      : groupBy === 'tool'
        ? '工具消耗对比'
        : '模型消耗分析';

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
            syncMeta={summary.data.sync_meta}
            cached={Boolean(summary.data.cached)}
            refreshing={refreshing || backgroundRefreshing}
            refreshError={refreshError}
            onRefresh={handleRefresh}
          />
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            title="刷新"
          >
            {refreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </button>
          <button
            onClick={exportCSV}
            disabled={!details.data.items.length}
            className="inline-flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            title="导出"
          >
            <Download className="h-4 w-4" />
          </button>
          <button
            onClick={handleClearData}
            disabled={clearing}
            className="inline-flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            title="清理"
          >
            {clearing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </button>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="inline-flex h-8 flex-shrink-0 items-center justify-center gap-1 rounded-md border border-slate-700 px-2 text-xs text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            title="ccusage 数据同步"
          >
            {syncing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            {syncing ? '同步中...' : '同步数据'}
          </button>
          {syncError && (
            <span className="inline-flex items-center text-xs text-red-400">{syncError}</span>
          )}
        </div>
      </div>

      <div className="mb-5 grid gap-3 rounded-md border border-slate-800 bg-slate-900 p-4 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        <label className="space-y-1">
          <span className="text-xs text-slate-400">工具</span>
          <select
            value={selectedTool}
            onChange={event => {
              setSelectedTool(event.target.value);
              setSelectedModel('');
            }}
            className="h-9 w-full rounded-md border border-slate-700 bg-slate-950 px-2 text-sm"
          >
            <option value="">全部工具</option>
            {toolOptions.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-slate-400">模型</span>
          <select value={selectedModel} onChange={event => setSelectedModel(event.target.value)} className="h-9 w-full rounded-md border border-slate-700 bg-slate-950 px-2 text-sm">
            <option value="">全部模型</option>
            {modelOptions.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
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
              {devices.filter(device => !device.canonical_id).map(device => (
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
            <button
              onClick={() => setDeviceManagerOpen(true)}
              disabled={!devices.length}
              title="管理设备"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Settings className="h-4 w-4" />
            </button>
          </div>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-slate-400">分组</span>
          <select value={groupBy} onChange={event => setGroupBy(event.target.value as TokenUsageGroupBy)} className="h-9 w-full rounded-md border border-slate-700 bg-slate-950 px-2 text-sm">
            <option value="none">按日期汇总</option>
            <option value="device">按设备对比</option>
            <option value="tool">按工具对比</option>
            <option value="model">按模型分析</option>
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-slate-400">排序</span>
          <select value={sortBy} onChange={event => setSortBy(event.target.value as TokenUsageSortBy)} className="h-9 w-full rounded-md border border-slate-700 bg-slate-950 px-2 text-sm">
            <option value="date">日期</option>
            <option value="total_tokens">总 Token</option>
            <option value="total_cost">成本</option>
            <option value="input_tokens">输入</option>
            <option value="output_tokens">输出</option>
            <option value="cache_tokens">缓存</option>
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

      {(error || refreshError || deviceError || pollError || lastSyncMessage || summary.data.auto_expanded) && (
        <div className="mb-5 space-y-2">
          {error && <div className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>}
          {refreshError && <div className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">{refreshError}</div>}
          {deviceError && <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">{deviceError}</div>}
          {pollError && <div className="rounded-md border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-300">后台轮询失败：{pollError}</div>}
          {lastSyncMessage && <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">{lastSyncMessage}</div>}
          {summary.data.auto_expanded && <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">当前范围无数据，已自动扩大到最近 {summary.data.actual_days} 天。</div>}
        </div>
      )}

      <div className="mb-5 grid gap-3 md:grid-cols-5">
        {[
          { label: '总成本', value: formatCurrency(summary.data.summary.total_cost), icon: Activity },
          { label: '日均成本', value: formatCurrency(summary.data.summary.avg_daily_cost), icon: BarChart3 },
          { label: '总 Token', value: formatToken(summary.data.summary.total_tokens), icon: Database },
          { label: '输入 Token', value: formatToken(summary.data.summary.total_input_tokens), icon: HardDrive },
          { label: '输出 Token', value: formatToken(summary.data.summary.total_output_tokens), icon: HardDrive },
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
          onSelect={id => setSelectedModel(id)}
        />
        <DimensionPieCard
          title="模型成本占比"
          data={modelCostSlices}
          totalTokens={totalModelCostTokens}
          metric="cost"
          emptyHint="暂无模型成本数据"
        />
      </div>

      <div className="mb-5 rounded-md border border-slate-800 bg-slate-900 p-4">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-medium text-white">{chartTitle}</h2>
          {summary.loading && <Loader2 className="h-4 w-4 animate-spin text-slate-400" />}
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

      <div className="rounded-md border border-slate-800 bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <h2 className="text-base font-medium text-white">明细数据</h2>
          <span className="text-xs text-slate-400">共 {details.data.total} 条</span>
        </div>
        <div className="overflow-auto">
          <table className="w-full min-w-[1040px] text-sm">
            <thead className="bg-slate-950 text-xs text-slate-400">
              <tr>
                <th className="px-4 py-3 text-left">日期</th>
                {groupBy !== 'none' && <th className="px-4 py-3 text-left">分组</th>}
                <th className="px-4 py-3 text-left">设备</th>
                <th className="px-4 py-3 text-left">工具</th>
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
              {!paginatedItems.length && !details.loading ? (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-500" colSpan={groupBy === 'none' ? 10 : 11}>暂无数据。可以点击"刷新"采集当前用户和设备的数据。</td>
                </tr>
              ) : paginatedItems.map((item, index) => (
                <tr key={`${item.date}-${item.group_key || 'all'}-${index}`} className="border-t border-slate-800 hover:bg-slate-800/60">
                  <td className="px-4 py-3 text-slate-200">{item.date}</td>
                  {groupBy !== 'none' && <td className="max-w-[180px] truncate px-4 py-3 text-slate-300" title={getGroupLabel(item)}>{getGroupLabel(item)}</td>}
                  <td className="max-w-[160px] truncate px-4 py-3 text-slate-300" title={item.device_id ? (deviceNameMap.get(item.device_id) || item.device_name || '-') : (item.device_name || '-')}>
                    {item.device_id ? (deviceNameMap.get(item.device_id) || item.device_name || '-') : (item.device_name || '-')}
                  </td>
                  <td className="max-w-[160px] truncate px-4 py-3 text-slate-400" title={getRowToolLabel(item)}>
                    {getRowToolLabel(item)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-slate-300">{formatToken(item.input_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-300">{formatToken(item.output_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-400">{formatToken(item.cache_creation_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono text-slate-400">{formatToken(item.cache_read_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono font-medium text-white">{formatToken(item.total_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono text-emerald-300">{formatCurrency(item.total_cost)}</td>
                  <td className="max-w-[240px] truncate px-4 py-3 text-slate-400" title={formatModelsUsed(item.models_used)}>{formatModelsUsed(item.models_used)}</td>
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

      {fingerprintMatch && (
        <FingerprintMatchDialog
          match={fingerprintMatch}
          currentDeviceName={devices.find(d => d.is_current)?.name || '当前设备'}
          onReuse={async () => {
            try {
              const currentDevice = devices.find(d => d.is_current);
              if (currentDevice && fingerprintMatch) {
                await createDeviceAlias(currentDevice.id, fingerprintMatch.matched_device_id);
                setFingerprintMatch(null);
                await loadDevices();
                await Promise.all([summary.refresh(), details.refresh()]);
              }
            } catch (e: any) {
              setError(e.message || '复用设备失败');
            }
          }}
          onCreateNew={() => setFingerprintMatch(null)}
          onClose={() => setFingerprintMatch(null)}
        />
      )}

      {deviceManagerOpen && (
        <DeviceManagerModal
          devices={devices}
          open={deviceManagerOpen}
          onClose={() => setDeviceManagerOpen(false)}
          onRename={async (id, name) => {
            await renameDevice(id, name);
            await loadDevices();
            await Promise.all([summary.refresh(), details.refresh()]);
          }}
          onMerge={async (sourceIds, targetId) => {
            await mergeDevices(sourceIds, targetId);
            await loadDevices();
            await Promise.all([summary.refresh(), details.refresh()]);
          }}
          onUnmerge={async (aliasId) => {
            await deleteDeviceAlias(aliasId);
            await loadDevices();
            await Promise.all([summary.refresh(), details.refresh()]);
          }}
        />
      )}
    </div>
  );
}
