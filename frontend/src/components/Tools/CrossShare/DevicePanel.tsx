/**
 * 设备面板组件
 */
import React, { useState, useEffect } from 'react';
import { deviceApi, Device } from '../../../services/crossShare';

const DevicePanel: React.FC = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  useEffect(() => {
    loadDevices();
    // 每 10 秒更新设备状态
    const interval = setInterval(loadDevices, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadDevices = async () => {
    try {
      const data = await deviceApi.getDevices();
      setDevices(data);
    } catch (error) {
      console.error('Failed to load devices:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateName = async (deviceId: string) => {
    try {
      await deviceApi.updateDevice(deviceId, { device_name: editingName });
      setEditingId(null);
      loadDevices();
    } catch (error) {
      console.error('Failed to update device name:', error);
    }
  };

  const handleDeleteDevice = async (deviceId: string, deviceName: string) => {
    if (!confirm(`确定要删除设备 "${deviceName}" 吗？`)) return;

    try {
      await deviceApi.deleteDevice(deviceId);
      loadDevices();
    } catch (error) {
      console.error('Failed to delete device:', error);
    }
  };

  const getDeviceTypeIcon = (type: string) => {
    switch (type) {
      case 'desktop':
        return '🖥️';
      case 'mobile':
        return '📱';
      case 'tablet':
        return '📟';
      default:
        return '📟';
    }
  };

  const isOnline = (device: Device) => {
    if (!device.last_seen_at) return false;
    const lastSeen = new Date(device.last_seen_at).getTime();
    const now = Date.now();
    // 5 分钟内活跃视为在线
    return now - lastSeen < 5 * 60 * 1000;
  };

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-surface-1 rounded-xl shadow-md border border-border">
        <div className="text-ink-muted">加载中...</div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col bg-surface-1 rounded-xl shadow-md border border-border overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 p-6 border-b border-border">
        <h2 className="text-xl font-bold text-ink">📱 设备管理</h2>
        <p className="text-sm text-ink-muted mt-1">管理已登录的设备</p>
      </div>

      {/* Device List - 可滚动 */}
      <div className="flex-1 overflow-y-auto divide-y divide-border">
        {devices.length === 0 ? (
          <div className="text-center text-ink-faint py-16">
            <div className="text-6xl mb-4">📭</div>
            <div className="text-ink-muted">暂无设备</div>
            <div className="text-sm mt-2 text-ink-faint">登录一个设备开始使用</div>
          </div>
        ) : (
          devices.map((device) => {
            const online = isOnline(device);
            return (
              <div
                key={device.id}
                className="flex items-center justify-between p-6 hover:bg-surface-2/30 transition-colors"
              >
                <div className="flex items-center space-x-4">
                  <div className="text-4xl">
                    {getDeviceTypeIcon(device.device_type)}
                  </div>
                  <div>
                    {editingId === device.id ? (
                      <div className="flex items-center space-x-2">
                        <input
                          type="text"
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          className="px-3 py-1 bg-surface-3 border border-border rounded-md text-ink focus:outline-none focus:border-accent-info"
                          autoFocus
                        />
                        <button
                          onClick={() => handleUpdateName(device.id)}
                          className="px-3 py-1 text-sm bg-green-500 text-ink-inverse rounded-md hover:bg-green-600 transition-colors"
                        >
                          保存
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="px-3 py-1 text-sm bg-surface-3 text-ink rounded-md hover:bg-surface-3 transition-colors"
                        >
                          取消
                        </button>
                      </div>
                    ) : (
                      <>
                        <div className="text-ink font-medium flex items-center space-x-2">
                          <span>{device.device_name}</span>
                          {online && (
                            <span className="px-2 py-0.5 bg-green-900/30 text-green-400 text-xs rounded-full">
                              在线
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-ink-muted">
                          {device.device_type} • 最后活跃：{device.last_seen_at ? new Date(device.last_seen_at).toLocaleString('zh-CN') : '从未'}
                        </div>
                      </>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => {
                      setEditingId(device.id);
                      setEditingName(device.device_name);
                    }}
                    className="px-3 py-1.5 text-sm bg-surface-2 hover:bg-surface-3 text-ink rounded-lg transition-colors"
                  >
                    ✏️ 重命名
                  </button>
                  <button
                    onClick={() => handleDeleteDevice(device.id, device.device_name)}
                    className="px-3 py-1.5 text-sm bg-red-900/30 hover:bg-red-900/50 text-danger rounded-lg transition-colors"
                  >
                    🗑️ 删除
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default DevicePanel;
