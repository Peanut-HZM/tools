import { useState, useEffect, useRef } from 'react';
import Taro from '@tarojs/taro';
import { View, Text, ScrollView, Picker } from '@tarojs/components';
import { tokenUsageApi } from '../../../services/tokenUsage';
import type { SummaryResponse, ChartSeriesItem } from '../../../services/tokenUsage';
import { formatApiError } from '../../../utils/mobileTool';
import Loading from '../../../components/Loading';
import Icon from '../../../components/Icon';
import './index.scss';

/**
 * Token 消耗统计页（/summary + /details 新接口版）。
 *
 * - 汇总卡：总 Token / 总成本，副行展示 输入/输出/缓存 拆分（四项分量口径，
 *   与后端一致，zcode 含缓存读的口径已统一）；
 * - 列表：chart_series 日粒度前端聚合（周/月维度），每行附输入/输出/缓存明细；
 * - 新鲜度：展示最后同步时间；is_stale 时后端 /summary 会自动触发后台同步，
 *   本页每 15s 静默重拉（上限 8 次）直至数据刷新；另提供手动"立即同步"。
 */

type Dimension = 'daily' | 'weekly' | 'monthly';

const DIMENSION_LABELS: Record<Dimension, string> = {
  daily: '按日',
  weekly: '按周',
  monthly: '按月',
};

const DAY_OPTIONS = [7, 14, 30, 60, 90];

/** Token 数格式化：亿 / 万 / 整数 */
function fmtTokens(v: number): string {
  if (!Number.isFinite(v)) return '-';
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)}亿`;
  if (v >= 1e4) return `${(v / 1e4).toFixed(1)}万`;
  return String(Math.round(v));
}

/** 成本格式化 */
function fmtCost(v: number): string {
  if (!Number.isFinite(v) || v === 0) return '$0';
  if (v >= 1) return `$${v.toFixed(2)}`;
  return `$${v.toFixed(4)}`;
}

/** ISO 周键（YYYY-Www），聚合 weekly 维度用 */
function isoWeekKey(dateStr: string): string {
  const d = new Date(`${dateStr.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(d.getTime())) return dateStr.slice(0, 7);
  const target = new Date(d.getTime());
  const dayNr = (d.getDay() + 6) % 7; // 周一=0
  target.setDate(target.getDate() - dayNr + 3); // 本周四
  const firstThursday = new Date(target.getFullYear(), 0, 4);
  const diff = target.getTime() - firstThursday.getTime();
  const week = 1 + Math.round(diff / (7 * 24 * 3600 * 1000));
  return `${target.getFullYear()}-W${String(week).padStart(2, '0')}`;
}

/** 按维度聚合 chart_series（daily 原样 / weekly 按ISO周 / monthly 按月） */
function aggregateSeries(items: ChartSeriesItem[], dimension: Dimension): ChartSeriesItem[] {
  if (dimension === 'daily') return items;
  const bucket = new Map<string, ChartSeriesItem>();
  for (const it of items) {
    const key = dimension === 'monthly' ? it.date.slice(0, 7) : isoWeekKey(it.date);
    const b = bucket.get(key) || {
      date: key, total_tokens: 0, total_cost: 0,
      input_tokens: 0, output_tokens: 0, cache_tokens: 0,
    };
    b.total_tokens += it.total_tokens;
    b.total_cost += it.total_cost;
    b.input_tokens += it.input_tokens;
    b.output_tokens += it.output_tokens;
    b.cache_tokens += it.cache_tokens;
    bucket.set(key, b);
  }
  return [...bucket.values()].sort((a, b) => (a.date < b.date ? 1 : -1));
}

export default function TokenUsagePage() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState<SummaryResponse | null>(null);
  const [dimension, setDimension] = useState<Dimension>('daily');
  const [days, setDays] = useState(30);
  const [selectedDevice, setSelectedDevice] = useState('');
  // is_stale 时的自动追新轮询（后端触发同步需要时间，15s 后重拉）
  const stalePollCountRef = useRef(0);

  const fetchData = async (silent = false) => {
    if (!silent) { setLoading(true); setError(''); }
    try {
      const res = await tokenUsageApi.summary({
        type: dimension,
        days,
        device_id: selectedDevice || undefined,
      });
      setData(res);
      // 过期数据被后端自动同步中：开启有限次轮询直至新鲜
      stalePollCountRef.current = res.sync_meta?.is_stale ? 0 : 99;
    } catch (err: any) {
      if (!silent) setError(formatApiError(err));
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [dimension, days, selectedDevice]);

  // is_stale 时每 15s 静默重拉（最多 8 次 ≈ 2 分钟），等待后端自动同步完成
  useEffect(() => {
    const timer = setInterval(() => {
      if (stalePollCountRef.current < 8) {
        stalePollCountRef.current += 1;
        fetchData(true);
      }
    }, 15000);
    return () => clearInterval(timer);
  }, [dimension, days, selectedDevice]);

  /** 手动立即同步（同步式接口，完成后重拉） */
  const handleSync = async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      const res = await tokenUsageApi.refresh(90);
      if (res.locked) {
        Taro.showToast({ title: '已有同步任务进行中', icon: 'none' });
      } else {
        Taro.showToast({
          title: `已同步 ${res.total_records} 条记录`,
          icon: 'success',
        });
      }
      await fetchData(true);
    } catch (err: any) {
      Taro.showToast({ title: formatApiError(err), icon: 'none' });
    } finally {
      setRefreshing(false);
    }
  };

  if (loading && !data) return <Loading text="加载统计..." />;

  const devices = data?.devices || [];
  const summary = data?.summary;
  const series = aggregateSeries(data?.chart_series || [], dimension);
  const syncMeta = data?.sync_meta;
  const lastSync = syncMeta?.last_success_at
    ? syncMeta.last_success_at.slice(5, 16).replace('T', ' ')
    : '';

  return (
    <View className="token-usage-page">
      <View className="filters">
        <View className="filter-row">
          <Text className="filter-label">维度</Text>
          <Picker
            mode="selector"
            range={['daily', 'weekly', 'monthly']}
            value={['daily', 'weekly', 'monthly'].indexOf(dimension)}
            onChange={(e) => setDimension(['daily', 'weekly', 'monthly'][e.detail.value] as Dimension)}
          >
            <View className="picker-value">{DIMENSION_LABELS[dimension]}</View>
          </Picker>
        </View>
        <View className="filter-row">
          <Text className="filter-label">天数</Text>
          <Picker
            mode="selector"
            range={DAY_OPTIONS.map(String)}
            value={DAY_OPTIONS.indexOf(days)}
            onChange={(e) => setDays(DAY_OPTIONS[e.detail.value])}
          >
            <View className="picker-value">{days}天</View>
          </Picker>
        </View>
        {devices.length > 0 && (
          <View className="filter-row">
            <Text className="filter-label">设备</Text>
            <Picker
              mode="selector"
              range={['全部设备', ...devices.map(d => d.name)]}
              value={selectedDevice === '' ? 0 : devices.findIndex(d => d.id === selectedDevice) + 1}
              onChange={(e) => {
                const idx = e.detail.value;
                setSelectedDevice(idx === 0 ? '' : devices[idx - 1].id);
              }}
            >
              <View className="picker-value">
                {selectedDevice === '' ? '全部设备' : devices.find(d => d.id === selectedDevice)?.name}
              </View>
            </Picker>
          </View>
        )}
      </View>

      {error && (
        <View className="error-state">
          <Text>{error}</Text>
          <Text className="retry" onClick={() => fetchData()}>重试</Text>
        </View>
      )}

      {summary && (
        <ScrollView className="stats-content" scrollY>
          <View className="stats-content-inner">

            {/* 同步状态条：最后同步时间 + 手动同步按钮 */}
            <View className="sync-bar">
              <Text className="sync-text">
                {lastSync ? `最后同步 ${lastSync}` : '尚未同步'}
                {syncMeta?.is_stale ? ' · 正在后台更新…' : ''}
              </Text>
              <View
                className={`sync-btn ${refreshing ? 'sync-btn--busy' : ''}`}
                onClick={handleSync}
              >
                <Icon name='download' size={13} color='#8B9BFF' />
                <Text>{refreshing ? '同步中…' : '立即同步'}</Text>
              </View>
            </View>

            <View className="summary-cards">
              <View className="summary-card glass-card">
                <Text className="card-value">{fmtTokens(summary.total_tokens)}</Text>
                <Text className="card-label">总 Token</Text>
                <Text className="card-sub">
                  输入 {fmtTokens(summary.total_input_tokens)} · 输出 {fmtTokens(summary.total_output_tokens)}
                </Text>
                <Text className="card-sub">缓存 {fmtTokens(summary.total_cache_creation_tokens + summary.total_cache_read_tokens)}</Text>
              </View>
              <View className="summary-card glass-card">
                <Text className="card-value">{fmtCost(summary.total_cost)}</Text>
                <Text className="card-label">总成本</Text>
                <Text className="card-sub">日均 {fmtCost(summary.avg_daily_cost)}</Text>
                <Text className="card-sub">{summary.days_count} 个有数据的天</Text>
              </View>
            </View>

            <View className="data-list glass-card">
              <View className="list-header">
                <Text className="header-cell header-cell--wide">时间</Text>
                <Text className="header-cell">Token</Text>
                <Text className="header-cell">成本</Text>
              </View>
              {series.length === 0 ? (
                <View className="list-empty"><Text>暂无数据，点击"立即同步"拉取本机数据</Text></View>
              ) : (
                series.map((item) => (
                  <View key={item.date} className="list-row-wrap">
                    <View className="list-row">
                      <Text className="cell cell--wide">{item.date}</Text>
                      <Text className="cell">{fmtTokens(item.total_tokens)}</Text>
                      <Text className="cell">{fmtCost(item.total_cost)}</Text>
                    </View>
                    <View className="list-subrow">
                      <Text>输入 {fmtTokens(item.input_tokens)}</Text>
                      <Text>输出 {fmtTokens(item.output_tokens)}</Text>
                      <Text>缓存 {fmtTokens(item.cache_tokens)}</Text>
                    </View>
                  </View>
                ))
              )}
            </View>

            {data?.cached && (
              <Text className="cached-hint">数据来自缓存</Text>
            )}
          </View>
        </ScrollView>
      )}
    </View>
  );
}
