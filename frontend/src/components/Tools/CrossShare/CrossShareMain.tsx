/**
 * CrossShare 跨设备共享主页面
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { deviceApi, messageApi, fileApi, configApi, StorageStats } from '../../services/crossShare';
import Sidebar from './CrossShare/Sidebar';
import MessagePanel from './CrossShare/MessagePanel';
import FilePanel from './CrossShare/FilePanel';
import DevicePanel from './CrossShare/DevicePanel';
import SettingsPanel from './CrossShare/SettingsPanel';

type PanelType = 'messages' | 'files' | 'devices' | 'settings';

const CrossShareMain: React.FC = () => {
  const navigate = useNavigate();
  const [activePanel, setActivePanel] = useState<PanelType>('messages');
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null);
  const [loading, setLoading] = useState(true);

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
      <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-yellow-400 mx-auto mb-4"></div>
          <div className="text-white text-xl">正在加载 CrossShare...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="bg-black/30 backdrop-blur-sm border-b border-white/10">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/')}
                className="text-white/80 hover:text-white transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                <h1 className="text-2xl font-bold text-white">📡 CrossShare 设备传传</h1>
                <p className="text-sm text-white/60">跨设备消息和文件共享</p>
              </div>
            </div>

            {/* Storage Stats */}
            {storageStats && (
              <div className="text-right">
                <div className="text-sm text-white/60 mb-1">
                  存储空间：{Math.round(storageStats.used_quota / 1024 / 1024)}MB / {Math.round(storageStats.storage_quota / 1024 / 1024)}MB
                </div>
                <div className="w-48 h-2 bg-white/20 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-green-400 to-emerald-500 transition-all duration-300"
                    style={{ width: `${Math.min(storageStats.usage_percentage, 100)}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex h-[calc(100vh-88px)]">
        {/* Sidebar */}
        <Sidebar activePanel={activePanel} onSelectPanel={setActivePanel} />

        {/* Main Panel */}
        <main className="flex-1 overflow-y-auto">
          <div className="container mx-auto px-6 py-6">
            {renderPanel()}
          </div>
        </main>
      </div>
    </div>
  );
};

export default CrossShareMain;
