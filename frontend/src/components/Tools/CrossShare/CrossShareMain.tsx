/**
 * CrossShare 跨设备共享主页面
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { deviceApi, messageApi, fileApi, configApi, StorageStats, generateDeviceToken } from '../../../services/crossShare';
import { useToast } from '../../../hooks/useToast';
import Toast, { ToastContainer } from '../../MarkdownEditor/Toast/Toast';
import { useAuth } from '../../../stores/authStore';
import Sidebar from './Sidebar';
import MessagePanel from './MessagePanel';
import FilePanel from './FilePanel';
import DevicePanel from './DevicePanel';
import SettingsPanel from './SettingsPanel';

type PanelType = 'messages' | 'files' | 'devices' | 'settings';

const CrossShareMain: React.FC = () => {
  const navigate = useNavigate();
  const { toast, showToast } = useToast();
  const { user, logout } = useAuth();
  const [activePanel, setActivePanel] = useState<PanelType>('messages');
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentDeviceId, setCurrentDeviceId] = useState<string | null>(null);

  const handleLogout = () => {
    logout();
    navigate('/');
    showToast('已退出登录', 'info');
  };

  // 注册当前设备
  useEffect(() => {
    registerCurrentDevice();
  }, []);

  const registerCurrentDevice = async () => {
    try {
      // 生成设备 token
      const deviceToken = generateDeviceToken();
      
      // 获取设备信息
      const ua = navigator.userAgent;
      let deviceType: 'desktop' | 'mobile' | 'tablet' = 'desktop';
      if (/mobile/i.test(ua)) {
        deviceType = 'mobile';
      } else if (/tablet/i.test(ua)) {
        deviceType = 'tablet';
      }

      // 生成设备名称
      let deviceName = 'Unknown Device';
      if (ua.includes('Mac')) {
        deviceName = 'Mac';
      } else if (ua.includes('Win')) {
        deviceName = 'Windows';
      } else if (ua.includes('Linux')) {
        deviceName = 'Linux';
      } else if (ua.includes('iPhone')) {
        deviceName = 'iPhone';
      } else if (ua.includes('iPad')) {
        deviceName = 'iPad';
      } else if (ua.includes('Android')) {
        deviceName = 'Android';
      }

      // 添加浏览器信息
      const browser = ua.includes('Chrome') ? 'Chrome' : ua.includes('Firefox') ? 'Firefox' : 'Safari';
      deviceName += ` (${browser})`;

      // 注册设备
      const device = await deviceApi.registerDevice(deviceName, deviceToken, deviceType);
      setCurrentDeviceId(device.id);
      
      // 存储设备 ID 到 localStorage
      localStorage.setItem('crossshare_device_id', device.id);
      localStorage.setItem('crossshare_device_token', deviceToken);
    } catch (error) {
      console.error('Failed to register device:', error);
    }
  };

  // Load initial data
  useEffect(() => {
    loadStorageStats();
  }, []);

  const loadStorageStats = async () => {
    try {
      const stats = await fileApi.getStorageStats();
      setStorageStats(stats);
    } catch (error) {
      console.error('Failed to load storage stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderPanel = () => {
    switch (activePanel) {
      case 'messages':
        return <MessagePanel />;
      case 'files':
        return <FilePanel onStatsUpdate={loadStorageStats} />;
      case 'devices':
        return <DevicePanel />;
      case 'settings':
        return <SettingsPanel />;
      default:
        return <MessagePanel />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <div className="text-slate-400 text-xl">正在加载 CrossShare...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Toast */}
      {toast && <Toast {...toast} />}

      {/* Main Content - 自适应布局 */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <Sidebar activePanel={activePanel} onSelectPanel={setActivePanel} />

        {/* Main Panel - 使用 flex 布局，内容区域自适应高度 */}
        <main className="flex-1 overflow-hidden">
          <div className="w-full h-full px-6 py-6">
            {renderPanel()}
          </div>
        </main>
      </div>
    </div>
  );
};

export default CrossShareMain;
