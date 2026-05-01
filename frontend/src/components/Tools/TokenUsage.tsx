import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { checkTokenUsageHealth, refreshTokenUsage, getDbTokenUsage, renameDevice, getUserDevices, UsageItem, UsageSummary } from '../../api/tokenUsageApi';
import type { DbUsageItem, DeviceInfo } from '../../api/tokenUsageApi';
import { useI18n } from '../../i18n';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

// 中文 token 格式化：亿 / 千万 / 百万 / 万
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

  // 根据维度动态生成时间范围选项
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

  // 切换维度时重置天数和页码
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
    if (newName === null) return; // 用户取消

    try {
      setLoading(true);
      await renameDevice(deviceId, newName);
      await fetchData();
    } catch (e: any) {
      alert(e.message || '重命名失败');
    } finally {
      setLoading(false);
    }
  }, [availableDevices, fetchData]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const formatNumber = (num: number) => formatToken(num);

  const formatCurrency = (num: number) => `$${num.toFixed(2)}`;

  const exportCSV = () => {
    if (items.length === 0) return;
    const headers = ['Date', 'Input Tokens', 'Output Tokens', 'Cache Creation', 'Cache Read', 'Total Tokens', 'Cost USD', 'Models'];
    const rows = items.map(item => [
      item.date,
      item.input_tokens,
      item.output_tokens,
      item.cache_creation_tokens,
      item.cache_read_tokens,
      item.total_tokens,
      item.total_cost,
      item.models_used.join('; '),
    ]);
    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `token-usage-${source === 'all' ? 'all' : source}-${reportType}-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const sortedItems = [...items].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

  // 分组数据构建（按设备/模型）
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
        const value = item.total_tokens;
        if (value > 0) {
          const existing = modelData.find(d => d.name === model);
          if (existing) {
            existing.value += value;
          } else {
            modelData.push({ name: model, value });
          }
        }
      });
    }
  });

  // 过滤掉 value 为 0 或 NaN 的数据，防止饼图显示重叠
  const filteredModelData = modelData.filter(d => d.value > 0 && !isNaN(d.value));

  const totalPages = Math.ceil(sortedItems.length / pageSize);
  const paginatedItems = sortedItems.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="min-h-0 bg-slate-900 text-slate-100 p-6 overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-slate-100">Token 消耗统计</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-400">
            数据来源: {source === 'all' ? '工具合计' : source === 'claude' ? 'ccusage' : 'opencode-usage'}
          </span>
          {cacheTime && (
            <span className="text-xs text-slate-500">
              {isCached ? '📦 缓存 ' : '🔄 实时 '}
              {new Date(cacheTime).toLocaleTimeString('zh-CN')}
            </span>
          )}
          <button
            onClick={handleRefresh}
            disabled={loading || refreshing}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded text-sm font-medium transition-colors"
          >
            {refreshing ? '刷新中...' : '刷新'}
          </button>
        </div>
      </div>

      {health && (
        <div className="flex gap-4 mb-4 text-xs">
          <span className={health.ccusage_installed ? 'text-green-400' : 'text-red-400'}>
            ● ccusage: {health.ccusage_installed ? '已安装' : '未安装'}
          </span>
          <span className={health.opencode_usage_installed ? 'text-green-400' : 'text-red-400'}>
            ● opencode-usage: {health.opencode_usage_installed ? '已安装' : '未安装'}
          </span>
          <span className={health.ccusage_opencode_installed ? 'text-green-400' : 'text-red-400'}>
            ● ccusage-opencode: {health.ccusage_opencode_installed ? '已安装' : '未安装'}
          </span>
        </div>
      )}

      <div className="bg-slate-800 rounded-lg p-4 mb-6 flex flex-wrap gap-4 items-center">
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-400">工具:</label>
          <select
            value={source}
            onChange={e => setSource(e.target.value as 'claude' | 'opencode' | 'all')}
            className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-100"
          >
            <option value="claude">Claude Code</option>
            <option value="opencode">OpenCode</option>
            <option value="all">工具合计</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-400">维度:</label>
          <div className="flex gap-1">
            {(['daily', 'weekly', 'monthly'] as const).map(type => (
              <button
                key={type}
                onClick={() => setReportType(type)}
                className={`px-3 py-1.5 rounded text-sm transition-colors ${
                  reportType === type
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {type === 'daily' ? '按天' : type === 'weekly' ? '按周' : '按月'}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-400">时间范围:</label>
          <select
            value={days}
            onChange={e => setDays(Number(e.target.value))}
            className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-100"
          >
            {timeRangeOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-400">设备:</label>
          <select
            value={selectedDevice}
            onChange={e => setSelectedDevice(e.target.value)}
            className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-100"
          >
            <option value="">全部设备</option>
            {availableDevices.map((d: DeviceInfo) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
          {selectedDevice && (
            <button
              onClick={() => handleRenameDevice(selectedDevice)}
              className="p-1.5 text-slate-400 hover:text-slate-200 rounded transition-colors"
              title="重命名设备"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-400">分组:</label>
          <div className="flex gap-1">
            {[
              { value: 'none' as const, label: '按日期汇总' },
              { value: 'device' as const, label: '按设备对比' },
              { value: 'model' as const, label: '按模型分析' },
            ].map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setGroupBy(opt.value)}
                  className={`px-3 py-1.5 rounded text-sm transition-colors ${
                    groupBy === opt.value
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-400">图表类型:</label>
          <div className="flex gap-1">
            {(['bar', 'line'] as const).map(type => (
              <button
                key={type}
                onClick={() => setChartType(type)}
                className={`px-3 py-1.5 rounded text-sm transition-colors ${
                  chartType === type
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {type === 'bar' ? '柱状图' : '折线图'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {loading && !items.length && (
        <div className="animate-pulse space-y-4 mb-6">
          <div className="grid grid-cols-5 gap-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="bg-slate-800 rounded-lg p-4 h-20" />
            ))}
          </div>
          <div className="bg-slate-800 rounded-lg h-72" />
        </div>
      )}

      {summary && !loading && (
        <div className="grid grid-cols-6 gap-3 mb-6">
          {[
            { label: '💵 总成本', value: formatCurrency(summary.total_cost), color: 'from-blue-900/50 to-blue-800/30', border: 'border-blue-500/30', hover: 'hover:shadow-blue-500/20' },
            { label: '📈 日均成本', value: formatCurrency(summary.avg_daily_cost), color: 'from-emerald-900/50 to-emerald-800/30', border: 'border-emerald-500/30', hover: 'hover:shadow-emerald-500/20' },
            { label: '🔢 总 Token', value: formatNumber(summary.total_tokens), color: 'from-violet-900/50 to-violet-800/30', border: 'border-violet-500/30', hover: 'hover:shadow-violet-500/20' },
            { label: '📥 输入 Token', value: formatNumber(summary.total_input_tokens), color: 'from-sky-900/50 to-sky-800/30', border: 'border-sky-500/30', hover: 'hover:shadow-sky-500/20' },
            { label: '📤 输出 Token', value: formatNumber(summary.total_output_tokens), color: 'from-amber-900/50 to-amber-800/30', border: 'border-amber-500/30', hover: 'hover:shadow-amber-500/20' },
            null, // Placeholder for Pie Chart
          ].map((card, i) => (
            card ? (
              <div key={i} className={`bg-gradient-to-br ${card.color} rounded-lg p-3 border ${card.border} ${card.hover} shadow-lg transition-all duration-200 hover:scale-[1.02]`}>
                <div className="text-xs text-slate-400 mb-1.5">{card.label}</div>
                <div className="text-lg font-bold text-slate-100">{card.value}</div>
              </div>
            ) : (
              <div key="pie" className="bg-gradient-to-br from-slate-800/80 to-slate-700/50 rounded-lg p-3 border border-slate-600/30 hover:shadow-slate-500/20 shadow-lg transition-all duration-200 hover:scale-[1.02] flex items-center justify-center">
                <div className="w-full">
                  <div className="text-xs text-slate-400 mb-1 text-center">模型占比</div>
                  {filteredModelData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={100}>
                      <PieChart>
                        <Pie
                          data={filteredModelData}
                          cx="50%"
                          cy="50%"
                          outerRadius={45}
                          innerRadius={30}
                          fill="#8884d8"
                          dataKey="value"
                          nameKey="name"
                          paddingAngle={2}
                        >
                          {filteredModelData.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value: number) => [formatCurrency(value), '成本']} contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#e2e8f0' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-[100px] flex items-center justify-center text-slate-500 text-xs">暂无数据</div>
                  )}
                </div>
              </div>
            )
          ))}
        </div>
      )}

      {!loading && (
        <>
          {/* 分组模式图表 */}
          {groupBy !== 'none' && groupedData.length > 0 && (
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 mb-6">
              <h3 className="text-lg font-medium text-slate-200 mb-4">
                {groupBy === 'device' ? '各设备 Token 消耗对比' : '各模型 Token 消耗分析'}
              </h3>
              <ResponsiveContainer width="100%" height={350}>
                <ComposedChart data={groupedData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={formatNumber} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: "1px solid #334155", color: '#e2e8f0' }}
                  />
                  <Legend />
                  {Object.keys(groupedData[0] || {})
                    .filter(k => k !== 'date')
                    .map((key, idx) => (
                      chartType === 'bar' ? (
                        <Bar key={key} dataKey={key} fill={COLORS[idx % COLORS.length]} name={key} />
                      ) : (
                        <Line key={key} type="monotone" dataKey={key} stroke={COLORS[idx % COLORS.length]} strokeWidth={2} name={key} dot={{ r: 3 }} />
                      )
                    ))}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* 常规模式图表 */}
          {groupBy === 'none' && chartData.length > 0 && (
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700 mb-6">
              <h3 className="text-lg font-medium text-slate-200 mb-4">Token 消耗趋势 & 成本</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                    <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={formatNumber} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={(v) => `$${v}`} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', border: "1px solid #334155", color: '#e2e8f0' }}
                    />
                    <Legend />
                    {chartType === 'bar' ? (
                      <>
                        <Bar yAxisId="left" dataKey="inputTokens" stackId="a" fill="#3b82f6" name="输入" />
                        <Bar yAxisId="left" dataKey="outputTokens" stackId="a" fill="#10b981" name="输出" />
                        <Bar yAxisId="left" dataKey="cacheTokens" stackId="a" fill="#f59e0b" name="缓存" />
                      </>
                    ) : (
                      <>
                        <Line yAxisId="left" type="monotone" dataKey="inputTokens" stroke="#3b82f6" strokeWidth={2} name="输入" dot={{ r: 3 }} />
                        <Line yAxisId="left" type="monotone" dataKey="outputTokens" stroke="#10b981" strokeWidth={2} name="输出" dot={{ r: 3 }} />
                        <Line yAxisId="left" type="monotone" dataKey="cacheTokens" stroke="#f59e0b" strokeWidth={2} name="缓存" dot={{ r: 3 }} />
                      </>
                    )}
                    <Line yAxisId="right" type="monotone" dataKey="cost" stroke="#ef4444" strokeWidth={2} name="成本 ($)" dot={{ r: 3 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
          )}
        </>
      )}

      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <div className="flex justify-between items-center p-4 border-b border-slate-700">
          <h3 className="text-lg font-medium text-slate-200">详细数据</h3>
          <button
            onClick={exportCSV}
            disabled={items.length === 0 || loading}
            className="bg-green-600 hover:bg-green-700 disabled:opacity-50 px-3 py-1.5 rounded text-sm transition-colors"
          >
            📥 导出 CSV
          </button>
        </div>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-900/80 text-slate-400 sticky top-0 backdrop-blur-sm">
              <tr>
                <th className="text-left px-4 py-3">日期</th>
                <th className="text-right px-4 py-3">输入</th>
                <th className="text-right px-4 py-3">输出</th>
                <th className="text-right px-4 py-3">缓存创建</th>
                <th className="text-right px-4 py-3">缓存读取</th>
                <th className="text-right px-4 py-3">总计</th>
                <th className="text-right px-4 py-3">成本 ($)</th>
                <th className="text-left px-4 py-3">模型</th>
              </tr>
            </thead>
            <tbody>
                {paginatedItems.length === 0 && !loading ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-slate-500">暂无数据</td>
                </tr>
              ) : (
                paginatedItems.map((item, i) => (
                  <tr key={i} className={`${i % 2 === 0 ? 'bg-slate-800/80' : 'bg-slate-800/40'} border-t border-slate-700/50 hover:bg-slate-700/50 transition-colors`}>
                    <td className="px-4 py-2.5 text-slate-200">{item.date}</td>
                    <td className="px-4 py-2.5 text-right text-slate-300 font-mono">{formatNumber(item.input_tokens)}</td>
                    <td className="px-4 py-2.5 text-right text-slate-300 font-mono">{formatNumber(item.output_tokens)}</td>
                    <td className="px-4 py-2.5 text-right text-slate-400 font-mono">{formatNumber(item.cache_creation_tokens)}</td>
                    <td className="px-4 py-2.5 text-right text-slate-400 font-mono">{formatNumber(item.cache_read_tokens)}</td>
                    <td className="px-4 py-2.5 text-right font-medium text-slate-100 font-mono">{formatNumber(item.total_tokens)}</td>
                    <td className="px-4 py-2.5 text-right text-green-400 font-mono">{formatCurrency(item.total_cost)}</td>
                    <td className="px-4 py-2.5 text-slate-400 max-w-[200px] truncate" title={item.models_used.join(', ')}>{item.models_used.join(', ')}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700">
            <div className="text-sm text-slate-400">
              共 {items.length} 条，第 {currentPage} / {totalPages} 页
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1.5 rounded text-sm bg-slate-700 text-slate-300 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                上一页
              </button>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1.5 rounded text-sm bg-slate-700 text-slate-300 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
