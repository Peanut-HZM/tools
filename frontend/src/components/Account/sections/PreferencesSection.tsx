import React, { useState } from 'react';
import SettingCard from '../SettingCard';
import { Settings, Globe, Moon, Bell } from 'lucide-react';

interface UserPreferences {
  language: 'zh' | 'en';
  theme: 'dark' | 'light' | 'system';
  emailNotifications: boolean;
  systemNotifications: boolean;
}

export default function PreferencesSection() {
  const [preferences, setPreferences] = useState<UserPreferences>({
    language: 'zh',
    theme: 'dark',
    emailNotifications: true,
    systemNotifications: true,
  });

  const updatePreference = <K extends keyof UserPreferences>(
    key: K,
    value: UserPreferences[K]
  ) => {
    setPreferences(prev => ({ ...prev, [key]: value }));
    // TODO: 调用 API 保存偏好设置
    console.log('Preference updated:', key, value);
  };

  return (
    <SettingCard title="偏好设置" icon={<Settings className="w-5 h-5 text-cyan-400" />}>
      <div className="space-y-6">
        {/* 语言设置 */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Globe className="w-4 h-4 text-slate-400" />
            <h4 className="text-white font-medium">语言设置</h4>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => updatePreference('language', 'zh')}
              className={`px-4 py-2 rounded text-sm transition-colors ${
                preferences.language === 'zh'
                  ? 'bg-cyan-500 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
              type="button"
            >
              中文
            </button>
            <button
              onClick={() => updatePreference('language', 'en')}
              className={`px-4 py-2 rounded text-sm transition-colors ${
                preferences.language === 'en'
                  ? 'bg-cyan-500 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
              type="button"
            >
              English
            </button>
          </div>
        </div>

        {/* 主题设置 */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Moon className="w-4 h-4 text-slate-400" />
            <h4 className="text-white font-medium">主题设置</h4>
          </div>
          <div className="flex gap-2">
            {(['dark', 'light', 'system'] as const).map((theme) => (
              <button
                key={theme}
                onClick={() => updatePreference('theme', theme)}
                className={`px-4 py-2 rounded text-sm transition-colors ${
                  preferences.theme === theme
                    ? 'bg-cyan-500 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
                type="button"
              >
                {theme === 'dark' && '深色'}
                {theme === 'light' && '浅色'}
                {theme === 'system' && '跟随系统'}
              </button>
            ))}
          </div>
        </div>

        {/* 通知设置 */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Bell className="w-4 h-4 text-slate-400" />
            <h4 className="text-white font-medium">通知设置</h4>
          </div>
          <div className="space-y-3">
            <label className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg cursor-pointer">
              <div>
                <span className="text-white text-sm">邮件通知</span>
                <p className="text-slate-500 text-xs mt-0.5">接收账户相关的邮件通知</p>
              </div>
              <input
                type="checkbox"
                checked={preferences.emailNotifications}
                onChange={(e) => updatePreference('emailNotifications', e.target.checked)}
                className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500/20"
              />
            </label>
            <label className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg cursor-pointer">
              <div>
                <span className="text-white text-sm">系统通知</span>
                <p className="text-slate-500 text-xs mt-0.5">在页面右上角显示通知</p>
              </div>
              <input
                type="checkbox"
                checked={preferences.systemNotifications}
                onChange={(e) => updatePreference('systemNotifications', e.target.checked)}
                className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500/20"
              />
            </label>
          </div>
        </div>
      </div>
    </SettingCard>
  );
}
