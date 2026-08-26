import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Database,
  Download,
  Edit3,
  HardDrive,
  Loader2,
  RefreshCw,
  Settings,
  Trash2,
} from 'lucide-react';
import { useToast } from '../../contexts/ToastContext';
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useAuth } from '../../stores/authStore';
import RequireAuthNotice from '../Common/RequireAuthNotice';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  LabelList,
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
  syncTokenUsage,
  type DbUsageItem,
  type DeviceInfo,
  type FingerprintMatch,
  type ModelSummaryItem,
  type SyncError,
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

function formatDateTime(value?: string | null): string {
  if (!value) return '暂无记录';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未知';
  return date.toLocaleString('zh-CN', { hour12: false });
}

export default function TokenUsage() {
  const { showToast } = useToast();
  const { isAuthenticated, authVersion } = useAuth();
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
  const [backgroundRefreshing, setBackgroundRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [refreshErrors, setRefreshErrors] = useState<SyncError[]>([]);
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
  }, isAuthenticated);

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
  }, isAuthenticated);

  useTokenUsagePolling(async (opts) => {
    await summary.refresh(opts);
  }, 30_000, isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated) return;
    void loadDevices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, authVersion]);

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
    setRefreshErrors([]);
    try {
      const result = await refreshTokenUsage({ days: Math.max(days, 90), background: false, reason: 'manual' });
      if (result.locked) {
        setRefreshError('已有刷新任务进行中，请稍后重试');
        return;
      }
      if (result.fingerprint_match) {
        setFingerprintMatch(result.fingerprint_match);
      }
      // 保存结构化的 errors 数组
      if (result.errors && result.errors.length > 0) {
        setRefreshErrors(result.errors);
      } else {
        setRefreshErrors([]);
      }
      setRefreshError(null);
      await loadDevices();
      await Promise.all([summary.refresh(), details.refresh()]);
      const errorCount = result.errors?.length || 0;
      const errorsMsg = errorCount > 0 ? `，${errorCount} 个来源有告警` : '';
      showToast(`已同步 ${result.total_records} 条记录${errorsMsg}`, 'success', 3000);
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
      setRefreshError(null);
      await loadDevices();
      await Promise.all([summary.refresh(), details.refresh()]);
      showToast(result.message || '数据已清理', 'success', 3000);
    } catch (err: any) {
      setError(err.message || '清理数据失败');
    } finally {
      setClearing(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncError(null);
    try {
      const result = await syncTokenUsage();
      showToast(result.message || '后台同步已启动', 'success', 3000);
      // 不再 await 同步完成，30 秒轮询自动刷新
    } catch (e: any) {
      setSyncError(e.message || '同步启动失败');
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

  const resolveDeviceName = useCallback((item: DbUsageItem): string => {
    const backendName = item.device_name?.trim();
    if (backendName) return backendName;
    if (item.device_id) {
      return deviceNameMap.get(item.device_id) || item.device_id;
    }
    return '-';
  }, [deviceNameMap]);

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
    () =>
      [...summary.data.chart_series]
        .filter(s => s.group_key == null)
        .sort((a, b) => a.date.localeCompare(b.date))
        .map(item => ({
          date: item.date,
          inputTokens: item.input_tokens ?? 0,
          outputTokens: item.output_tokens ?? 0,
          cacheTokens: item.cache_tokens ?? 0,
          totalTokens: item.total_tokens,
          cost: item.total_cost,
        })),
    [summary.data.chart_series]
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
    const headers = ['日期', '分组', '设备', '工具', '模型', '输入 Token', '输出 Token', '缓存创建', '缓存读取', '总 Token', '成本 USD', '更新时间'];
    const rows = details.data.items.map(item => [
      item.date,
      getGroupLabel(item),
      item.device_name || (item.device_id ? deviceNameMap.get(item.device_id) || '-' : '-'),
      getRowToolLabel(item),
      formatModelsUsed(item.models_used),
      item.input_tokens,
      item.output_tokens,
      item.cache_creation_tokens,
      item.cache_read_tokens,
      item.total_tokens,
      item.total_cost,
      item.created_at || '',
    ]);
    const csv = [headers, ...rows]
      .map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(','))
      .join('\n');
    const blob = new Blob([`﻿${csv}`], { type: 'text/csv;charset=utf-8;' });
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

  // 修复：按纯 model 字段二次合并，避免同一模型因 source 不同而被拆分
  // label 直接用纯模型名，不再带工具/source 前缀（用户要求"不需要关注工具"）
  const modelCostSlices: PieSlice[] = useMemo(() => {
    const modelMap = new Map<string, { tokens: number; cost: number }>();
    summary.data.model_summary.forEach(item => {
      const existing = modelMap.get(item.model);
      if (existing) {
        existing.tokens += item.total_tokens;
        existing.cost += item.total_cost;
      } else {
        modelMap.set(item.model, {
          tokens: item.total_tokens,
          cost: item.total_cost,
        });
      }
    });
    return [...modelMap.entries()].map(([model, data]) => ({
      key: model,
      label: model,
      tokens: data.tokens,
      cost: data.cost,
    }));
  }, [summary.data.model_summary]);

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

  // 未登录：不发请求，显示登录提示（登录成功后 authVersion 变化自动重载）
  if (!isAuthenticated) {
    return <RequireAuthNotice />;
  }

  return (
    <div className="min-h-0 overflow-y-auto bg-canvas p-6 text-ink">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal text-ink-inverse">
            Token 消耗统计
            <span className="ml-3 inline-flex items-center gap-1 text-sm font-normal text-ink-muted">
              <Database className="h-3.5 w-3.5" />
              按登录用户、设备和工具维度统计
            </span>
          </h1>
        </div>

        <div className="flex flex-nowrap items-center gap-2">
          <span className="text-xs text-ink-muted">
            {formatDateTime(
              summary.data.sync_meta?.latest_record_at ||
              summary.data.sync_meta?.last_success_at
            )}
          </span>
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefresh}
            disabled={refreshing}
            className="h-8 w-8 flex-shrink-0"
            title="刷新"
          >
            {refreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={exportCSV}
            disabled={!details.data.items.length}
            className="h-8 w-8 flex-shrink-0"
            title="导出"
          >
            <Download className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={handleClearData}
            disabled={clearing}
            className="h-8 w-8 flex-shrink-0"
            title="清理"
          >
            {clearing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSync}
            disabled={syncing}
            className="h-8 flex-shrink-0 text-xs"
            title="ccusage 数据同步"
          >
            {syncing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            {syncing ? '同步中...' : '同步数据'}
          </Button>
          {syncError && (
            <span className="inline-flex items-center text-xs text-danger">{syncError}</span>
          )}
        </div>
      </div>

      <div className="mb-5 grid gap-3 rounded-md border border-border bg-canvas p-4 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        <label className="space-y-1">
          <span className="text-xs text-ink-muted">工具</span>
          <select
            value={selectedTool}
            onChange={event => {
              setSelectedTool(event.target.value);
              setSelectedModel('');
            }}
            className="h-9 w-full rounded-md border border-border bg-canvas px-2 text-sm"
          >
            <option value="">全部工具</option>
            {toolOptions.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-ink-muted">模型</span>
          <select value={selectedModel} onChange={event => setSelectedModel(event.target.value)} className="h-9 w-full rounded-md border border-border bg-canvas px-2 text-sm">
            <option value="">全部模型</option>
            {modelOptions.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-ink-muted">维度</span>
          <select value={reportType} onChange={event => setReportType(event.target.value as TokenUsageReportType)} className="h-9 w-full rounded-md border border-border bg-canvas px-2 text-sm">
            <option value="daily">按天</option>
            <option value="weekly">按周</option>
            <option value="monthly">按月</option>
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-ink-muted">时间范围</span>
          <select value={days} onChange={event => setDays(Number(event.target.value))} className="h-9 w-full rounded-md border border-border bg-canvas px-2 text-sm">
            {timeRangeOptions.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-ink-muted">设备</span>
          <div className="flex gap-1">
            <select value={selectedDevice} onChange={event => setSelectedDevice(event.target.value)} className="h-9 min-w-0 flex-1 rounded-md border border-border bg-canvas px-2 text-sm">
              <option value="">全部设备</option>
              {devices.filter(device => !device.canonical_id).map(device => (
                <option key={device.id} value={device.id}>{device.name}</option>
              ))}
            </select>
            <Button
              variant="outline"
              size="icon"
              onClick={handleRenameDevice}
              disabled={!selectedDevice}
              title="重命名设备"
            >
              <Edit3 className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setDeviceManagerOpen(true)}
              disabled={!devices.length}
              title="管理设备"
            >
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-ink-muted">分组</span>
          <select value={groupBy} onChange={event => setGroupBy(event.target.value as TokenUsageGroupBy)} className="h-9 w-full rounded-md border border-border bg-canvas px-2 text-sm">
            <option value="none">按日期汇总</option>
            <option value="device">按设备对比</option>
            <option value="tool">按工具对比</option>
            <option value="model">按模型分析</option>
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-ink-muted">排序</span>
          <select value={sortBy} onChange={event => setSortBy(event.target.value as TokenUsageSortBy)} className="h-9 w-full rounded-md border border-border bg-canvas px-2 text-sm">
            <option value="created_at">更新时间</option>
            <option value="date">日期</option>
            <option value="created_at">更新时间</option>
            <option value="total_tokens">总 Token</option>
            <option value="total_cost">成本</option>
            <option value="input_tokens">输入</option>
            <option value="output_tokens">输出</option>
            <option value="cache_tokens">缓存</option>
          </select>
        </label>

        <label className="space-y-1">
          <span className="text-xs text-ink-muted">图表</span>
          <select value={chartType} onChange={event => setChartType(event.target.value as 'bar' | 'line')} className="h-9 w-full rounded-md border border-border bg-canvas px-2 text-sm">
            <option value="bar">柱状图</option>
            <option value="line">折线图</option>
          </select>
        </label>
      </div>

      {(error || refreshError || refreshErrors.length > 0 || deviceError || pollError || summary.data.auto_expanded) && (
        <div className="mb-5 space-y-2">
          {error && <div className="rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-red-200">{error}</div>}
          {refreshError && <div className="rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-red-200">{refreshError}</div>}
          {refreshErrors.length > 0 && (
            <div className="space-y-2">
              {refreshErrors.map((err, idx) => (
                <div key={idx} className="rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 flex-shrink-0 text-amber-400" />
                    <div className="flex-1">
                      <div className="font-medium text-amber-200">
                        {err.source}: {err.error}
                      </div>
                      {err.error_code && (
                        <div className="mt-1 text-xs text-amber-300">
                          错误代码: {err.error_code}
                        </div>
                      )}
                      {err.remediation && (
                        <div className="mt-1 text-xs text-amber-200">
                          建议: {err.remediation}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          {deviceError && <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">{deviceError}</div>}
          {pollError && <div className="rounded-md border border-border bg-canvas px-4 py-3 text-sm text-ink-muted">后台轮询失败：{pollError}</div>}
          {summary.data.auto_expanded && <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">当前范围无数据，已自动扩大到最近 {summary.data.actual_days} 天。</div>}
        </div>
      )}

      <Card className="mb-5 grid gap-3 md:grid-cols-5 p-0">
        {[
          { label: '总成本', value: formatCurrency(summary.data.summary.total_cost), icon: Activity },
          { label: '日均成本', value: formatCurrency(summary.data.summary.avg_daily_cost), icon: BarChart3 },
          { label: '总 Token', value: formatToken(summary.data.summary.total_tokens), icon: Database },
          { label: '输入 Token', value: formatToken(summary.data.summary.total_input_tokens), icon: HardDrive },
          { label: '输出 Token', value: formatToken(summary.data.summary.total_output_tokens), icon: HardDrive },
        ].map(card => (
          <div key={card.label} className="rounded-md p-4">
            <div className="mb-2 flex items-center justify-between text-xs text-ink-muted">
              <span>{card.label}</span>
              <card.icon className="h-4 w-4" />
            </div>
            <div className="text-xl font-semibold text-ink-inverse">{card.value}</div>
          </div>
        ))}
      </Card>

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

      <Card className="mb-5 p-4">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-medium text-ink-inverse">{chartTitle}</h2>
          {summary.loading && <Loader2 className="h-4 w-4 animate-spin text-ink-muted" />}
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
                        <Bar yAxisId="left" dataKey="cacheTokens" stackId="tokens" fill="#f59e0b" name="缓存">
                          <LabelList dataKey="totalTokens" formatter={formatToken} position="top" style={{ fill: '#e2e8f0', fontSize: 10, fontWeight: 500 }} />
                        </Bar>
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
            <div className="flex h-full items-center justify-center text-sm text-ink-faint">暂无图表数据</div>
          )}
        </div>
      </Card>

      <Card className="rounded-md">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="text-base font-medium text-ink-inverse">明细数据</h2>
          <span className="text-xs text-ink-muted">共 {details.data.total} 条</span>
        </div>
        <div className="overflow-auto">
          <table className="w-full min-w-[1040px] text-sm">
            <thead className="bg-canvas text-xs text-ink-muted">
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
                <th className="px-4 py-3 text-left">更新时间</th>
              </tr>
            </thead>
            <tbody>
              {!paginatedItems.length && !details.loading ? (
                <tr>
                  <td className="px-4 py-8 text-center text-ink-faint" colSpan={groupBy === 'none' ? 11 : 12}>暂无数据。可以点击"刷新"采集当前用户和设备的数据。</td>
                </tr>
              ) : paginatedItems.map((item, index) => (
                <tr key={`${item.date}-${item.group_key || 'all'}-${index}`} className="border-t border-border hover:bg-surface-1/60">
                  <td className="px-4 py-3 text-ink">{item.date}</td>
                  {groupBy !== 'none' && <td className="max-w-[180px] truncate px-4 py-3 text-ink-muted" title={getGroupLabel(item)}>{getGroupLabel(item)}</td>}
                  <td className="max-w-[160px] truncate px-4 py-3 text-ink-muted" title={resolveDeviceName(item)}>
                    {resolveDeviceName(item)}
                  </td>
                  <td className="max-w-[160px] truncate px-4 py-3 text-ink-muted" title={getRowToolLabel(item)}>
                    {getRowToolLabel(item)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-ink-muted">{formatToken(item.input_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono text-ink-muted">{formatToken(item.output_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono text-ink-muted">{formatToken(item.cache_creation_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono text-ink-muted">{formatToken(item.cache_read_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono font-medium text-ink-inverse">{formatToken(item.total_tokens)}</td>
                  <td className="px-4 py-3 text-right font-mono text-emerald-300">{formatCurrency(item.total_cost)}</td>
                  <td className="max-w-[240px] truncate px-4 py-3 text-ink-muted" title={formatModelsUsed(item.models_used)}>{formatModelsUsed(item.models_used)}</td>
                  <td className="px-4 py-3 text-xs text-ink-faint">{item.created_at ? formatDateTime(item.created_at) : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-border px-4 py-3 text-sm">
            <span className="text-ink-muted">第 {currentPage} / {totalPages} 页</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setCurrentPage(page => Math.max(1, page - 1))} disabled={currentPage === 1}>上一页</Button>
              <Button variant="outline" size="sm" onClick={() => setCurrentPage(page => Math.min(totalPages, page + 1))} disabled={currentPage === totalPages}>下一页</Button>
            </div>
          </div>
        )}
      </Card>

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