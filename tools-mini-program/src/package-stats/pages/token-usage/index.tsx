import { useState, useEffect } from 'react';
import Taro from '@tarojs/taro';
import { View, Text, ScrollView, Picker } from '@tarojs/components';
import { tokenUsageApi } from '../../../services/tokenUsage';
import type { DbQueryResponse } from '../../../services/tokenUsage';
import { formatApiError } from '../../../utils/mobileTool';
import Loading from '../../../components/Loading';
import './index.scss';

type Dimension = 'daily' | 'weekly' | 'monthly';

const DIMENSION_LABELS: Record<Dimension, string> = {
  daily: '按日',
  weekly: '按周',
  monthly: '按月',
};

export default function TokenUsagePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState<DbQueryResponse | null>(null);
  const [dimension, setDimension] = useState<Dimension>('daily');
  const [days, setDays] = useState(30);
  const [selectedDevice, setSelectedDevice] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await tokenUsageApi.queryUsage({
        type: dimension,
        days,
        device_id: selectedDevice || undefined,
      });
      setData(res);
    } catch (err: any) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [dimension, days, selectedDevice]);

  if (loading && !data) return <Loading text="加载统计..." />;

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
            range={[7, 14, 30, 60, 90]}
            value={[7, 14, 30, 60, 90].indexOf(days)}
            onChange={(e) => setDays([7, 14, 30, 60, 90][e.detail.value])}
          >
            <View className="picker-value">{days}天</View>
          </Picker>
        </View>
        {data?.devices && data.devices.length > 0 && (
          <View className="filter-row">
            <Text className="filter-label">设备</Text>
            <Picker
              mode="selector"
              range={['全部设备', ...data.devices.map(d => d.name)]}
              value={selectedDevice === '' ? 0 : data.devices.findIndex(d => d.id === selectedDevice) + 1}
              onChange={(e) => {
                const idx = e.detail.value;
                setSelectedDevice(idx === 0 ? '' : data.devices[idx - 1].id);
              }}
            >
              <View className="picker-value">
                {selectedDevice === '' ? '全部设备' : data.devices.find(d => d.id === selectedDevice)?.name}
              </View>
            </Picker>
          </View>
        )}
      </View>

      {error && (
        <View className="error-state">
          <Text>{error}</Text>
          <Text className="retry" onClick={fetchData}>重试</Text>
        </View>
      )}

      {data && (
        <ScrollView className="stats-content" scrollY>
          <View className="summary-cards">
            <View className="summary-card">
              <Text className="card-value">{(data.summary.total_tokens / 1000).toFixed(1)}K</Text>
              <Text className="card-label">总 Token</Text>
            </View>
            <View className="summary-card">
              <Text className="card-value">{data.summary.total_count}</Text>
              <Text className="card-label">请求数</Text>
            </View>
          </View>

          <View className="data-list">
            <View className="list-header">
              <Text className="header-cell">时间</Text>
              <Text className="header-cell">Token</Text>
              <Text className="header-cell">请求</Text>
            </View>
            {data.items.map((item, idx) => (
              <View key={idx} className="list-row">
                <Text className="cell">
                  {item.date || item.week || item.month || '-'}
                </Text>
                <Text className="cell">{item.total_tokens.toLocaleString()}</Text>
                <Text className="cell">{item.count}</Text>
              </View>
            ))}
          </View>

          {data.cached && (
            <Text className="cached-hint">数据来自缓存</Text>
          )}
        </ScrollView>
      )}
    </View>
  );
}
