import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { checkTokenUsageHealth, refreshTokenUsage, getDbTokenUsage, renameDevice, getUserDevices, UsageItem, UsageSummary } from '../../api/tokenUsageApi';
import type { DbUsageItem, DeviceInfo } from '../../api/tokenUsageApi';
import { useI18n } from '../../i18n';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

// Token number formatting: 亿 / 千万 / 百万 / 万
const formatToken = (num: number): string => {
  if (num >= 100_000_000) return `${(num / 100_000_000).toFixed(1)}亿`;
  if (num >= 10_000_000) return `${(num / 10_000_000).toFixed(1)}千万`;
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}百万`;
  if (num >= 10_000) return `${(num / 10_000).toFixed(1)}万`;
  return num.toLocaleString();
};

export default function TokenUsage() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<UsageItem[]>([]);
  const [summary, setSummary] = useState<UsageSummary | null>(null);

  const [source, setSource] = useState<'claude' | 'opencode' | 'all'>('claude');
  const [reportType, setReportType] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [days, setDays] = useState(30);
  const [chartType, setChartType] = useState<'bar' | 'line'>('bar');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;
  const [cacheTime, setCacheTime] = useState<string | null>(null);
  const [isCached, setIsCached] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const [groupBy, setGroupBy] = useState<'none' | 'device' | 'model'>('none');
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [syncing, setSyncing] = useState(false);
  const [availableDevices, setAvailableDevices] = useState<DeviceInfo[]>([]);

  useEffect(() => {
    getUserDevices().then(res => setAvailableDevices(res.devices)).catch(console.error);
  }, []);

  const [health, setHealth] = useState<{ ccusage_installed: boolean; opencode_usage_installed: boolean; ccusage_opencode_installed: boolean } | null>(null);

  // Dynamically generate time range options based on dimension
  const timeRangeOptions = useMemo(() => {
    switch (reportType) {
      case 'daily':
        return [
          { label: '最近 7 天', value: 7 },
          { label: '最近 14 天', value: 14 },
          { label: '最近 30 天', value: 30 },
          { label: '最近 90 天', value: 90 },
        ];
      case 'weekly':
        return [
          { label: '最近 4 周', value: 28 },
          { label: '最近 8 周', value: 56 },
          { label: '最近 12 周', value: 84 },
          { label: '最近 24 周', value: 168 },
        ];
      case 'monthly':
        return [
          { label: '最近 3 个月', value: 90 },
          { label: '最近 6 个月', value: 180 },
          { label: '最近 12 个月', value: 365 },
        ];
      default:
        return [];
    }
  }, [reportType]);

  // Reset days and page number when dimension changes
  useEffect(() => {
    if (reportType === 'daily') setDays(30);
    else if (reportType === 'weekly') setDays(56);
    else if (reportType === 'monthly') setDays(180);
    setCurrentPage(1);
  }, [reportType]);

  useEffect(() => {
    checkTokenUsageHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getDbTokenUsage({
        type: reportType,
        days,
        group_by: groupBy,
        source,
        device_id: selectedDevice || undefined,
      });
      setItems(result.items as UsageItem[]);
      setSummary(result.summary);
      setIsCached(result.cached || false);
      setCacheTime(null);
      setCurrentPage(1);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [source, reportType, days, groupBy, selectedDevice]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshTokenUsage();
      await fetchData();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setRefreshing(false);
    }
  };

  const handleRenameDevice = useCallback(async (deviceId: string) => {
    const currentDevice = availableDevices.find((d: DeviceInfo) => d.id === deviceId);
    const currentName = currentDevice?.name || deviceId;
    const newName = prompt('请输入设备名称（留空恢复默认）:', currentName);
    if (newName === null) return; // User cancelled

    try {
      setLoading(true);
      await renameDevice(deviceId, newName || '');
      await fetchData();
      await setUserDisplayName();
    } catch (e: any) {
      alert(e.message || '重命名失败');
    } finally {
      setLoading(false);
    }
  }, [availableDevices, fetchData]);

  const setUserDisplayName = useCallback(async () => {
    const newDevices = await getUserDevices();
    setAvailableDevices(newDevices.devices);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Grouped data construction (by device/model)
  const groupedData = useMemo(() => {
    if (groupBy === 'none') return [];
    const grouped: Record<string, Record<string, number>> = {};
    const allDates = new Set<string>();

    (items as DbUsageItem[]).forEach(item => {
      const key = (item as DbUsageItem).group_key || 'unknown';
      allDates.add(item.date);
      if (!grouped[key]) grouped[key] = {};
      grouped[key][item.date] = (grouped[key][item.date] || 0) + item.total_tokens;
    });

    const sortedDates = [...allDates].sort();
    return sortedDates.map(date => {
      const row: Record<string, string | number> = { date };
      Object.entries(grouped).forEach(([key, dates]) => {
        row[key] = dates[date] || 0;
      });
      return row;
    });
  }, [groupBy, items]);

  const sortedItems = [...items].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

  const chartData = sortedItems.map(item => ({
    date: item.date,
    inputTokens: item.input_tokens,
    outputTokens: item.output_tokens,
    cacheTokens: item.cache_creation_tokens + item.cache_read_tokens,
    totalTokens: item.total_tokens,
    cost: item.total_cost,
  }));

  const modelData: { name: string; value: number }[] = [];
  sortedItems.forEach(item => {
    if (item.model_breakdowns?.length > 0) {
      item.model_breakdowns.forEach((m: any) => {
        const name = m.modelName || m.model || 'unknown';
        const cost = m.cost ?? m.costUSD ?? 0;
        const fallbackValue = (m.totalTokens ?? 0) || ((m.inputTokens ?? 0) + (m.outputTokens ?? 0));
        const value = cost !== 0 ? cost : fallbackValue;
        if (value > 0) {
          const existing = modelData.find(d => d.name === name);
          if (existing) {
            existing.value += value;
          } else {
            modelData.push({ name, value });
          }
        }
      });
    } else if (item.models_used?.length > 0) {
      item.models_used.forEach(model => {