/**
 * 设置面板组件
 */
import React, { useState, useEffect } from 'react';
import { configApi, UserConfig, formatFileSize } from '../../../services/crossShare';

const SettingsPanel: React.FC = () => {
  const [config, setConfig] = useState<UserConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await configApi.getConfig();
      setConfig(data);
    } catch (error) {
      console.error('Failed to load config:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!config) return;

    setSaving(true);
    try {
      await configApi.updateConfig(config);
      alert('设置已保存');
    } catch (error) {
      console.error('Failed to save config:', error);
      alert('保存失败');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-800 rounded-xl shadow-md border border-slate-700">
        <div className="text-slate-400">加载中...</div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-800 rounded-xl shadow-md border border-slate-700">
        <div className="text-slate-400">加载失败</div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col bg-slate-800 rounded-xl shadow-md border border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 p-6 border-b border-slate-700">
        <h2 className="text-xl font-bold text-slate-100">⚙️ 设置</h2>
        <p className="text-sm text-slate-400 mt-1">配置 CrossShare 功能</p>
      </div>

      {/* Settings Form - 可滚动 */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* 文件大小限制 */}
          <div>
            <label className="block text-slate-100 font-medium mb-2">
              单文件最大大小 (MB)
            </label>
            <input
              type="number"
              value={config.max_file_size / 1024 / 1024}
              onChange={(e) =>
                setConfig({ ...config, max_file_size: Number(e.target.value) * 1024 * 1024 })
              }
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-100 focus:outline-none focus:border-blue-500"
              min="1"
              max="10240"
            />
            <p className="text-sm text-slate-400 mt-1">
              当前限制：{formatFileSize(config.max_file_size)} (1-10240 MB)
            </p>
          </div>

          {/* 存储配额 */}
          <div>
            <label className="block text-slate-100 font-medium mb-2">
              总存储配额 (GB)
            </label>
            <input
              type="number"
              value={config.storage_quota / 1024 / 1024 / 1024}
              onChange={(e) =>
                setConfig({ ...config, storage_quota: Number(e.target.value) * 1024 * 1024 * 1024 })
              }
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-100 focus:outline-none focus:border-blue-500"
              min="1"
              max="1024"
            />
            <p className="text-sm text-slate-400 mt-1">
              当前配额：{formatFileSize(config.storage_quota)} (1-1024 GB)
            </p>
          </div>

          {/* 文件过期天数 */}
          <div>
            <label className="block text-slate-100 font-medium mb-2">
              文件过期天数
            </label>
            <input
              type="number"
              value={config.file_expire_days}
              onChange={(e) =>
                setConfig({ ...config, file_expire_days: Number(e.target.value) })
              }
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-100 focus:outline-none focus:border-blue-500"
              min="1"
              max="365"
            />
            <p className="text-sm text-slate-400 mt-1">
              超过此天数的文件将被自动清理 (1-365 天)
            </p>
          </div>

          {/* 启用加密 */}
          <div className="flex items-center justify-between">
            <div>
              <label className="block text-slate-100 font-medium">
                启用端到端加密
              </label>
              <p className="text-sm text-slate-400">
                消息和文件将使用 AES-256 加密
              </p>
            </div>
            <button
              onClick={() => setConfig({ ...config, enable_encryption: !config.enable_encryption })}
              className={`w-12 h-6 rounded-full transition-colors ${
                config.enable_encryption ? 'bg-blue-500' : 'bg-slate-600'
              }`}
            >
              <div
                className={`w-5 h-5 bg-white rounded-full transform transition-transform ${
                  config.enable_encryption ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* 启用剪贴板同步 */}
          <div className="flex items-center justify-between">
            <div>
              <label className="block text-slate-100 font-medium">
                启用剪贴板同步
              </label>
              <p className="text-sm text-slate-400">
                自动同步剪贴板内容到云端
              </p>
            </div>
            <button
              onClick={() => setConfig({ ...config, enable_clipboard: !config.enable_clipboard })}
              className={`w-12 h-6 rounded-full transition-colors ${
                config.enable_clipboard ? 'bg-blue-500' : 'bg-slate-600'
              }`}
            >
              <div
                className={`w-5 h-5 bg-white rounded-full transform transition-transform ${
                  config.enable_clipboard ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
      </div>

      {/* Save Button - 固定在底部 */}
      <div className="flex-shrink-0 p-6 border-t border-slate-700">
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full px-6 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
        >
          {saving ? '保存中...' : '保存设置'}
        </button>
      </div>
    </div>
  );
};

export default SettingsPanel;
