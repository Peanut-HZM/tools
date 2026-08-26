import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { useTheme } from '@/lib/theme';
import SettingCard from '../SettingCard';
import { Settings, Globe, Moon, Bell } from 'lucide-react';

interface UserPreferences {
  language: 'zh' | 'en';
  emailNotifications: boolean;
  systemNotifications: boolean;
}

const STORAGE_KEY = 'tk-preferences';

const DEFAULT_PREFS: UserPreferences = {
  language: 'zh',
  emailNotifications: true,
  systemNotifications: true,
};

export default function PreferencesSection() {
  const { theme, setTheme } = useTheme();

  const [preferences, setPreferences] = useState<UserPreferences>(() => {
    if (typeof window === 'undefined') return DEFAULT_PREFS;
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        return { ...DEFAULT_PREFS, ...JSON.parse(saved) };
      }
    } catch {
      // 忽略解析错误
    }
    return DEFAULT_PREFS;
  });

  // 持久化偏好设置到 localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
    } catch {
      // 忽略存储错误
    }
  }, [preferences]);

  const updatePreference = <K extends keyof UserPreferences>(
    key: K,
    value: UserPreferences[K]
  ) => {
    setPreferences(prev => ({ ...prev, [key]: value }));
    // TODO: 调用 API 同步到后端
  };

  const handleThemeChange = (nextTheme: 'dark' | 'light' | 'system') => {
    setTheme(nextTheme);
  };

  const handleLanguageChange = (lang: 'zh' | 'en') => {
    updatePreference('language', lang);
    // 同步更新 <html lang> 以便辅助技术正确识别语言
    if (typeof document !== 'undefined') {
      document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
    }
  };

  return (
    <SettingCard title="偏好设置" icon={<Settings className="w-5 h-5 text-accent" />}>
      <div className="space-y-6">
        {/* 语言设置 */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Globe className="w-4 h-4 text-ink-muted" />
            <h4 className="text-ink font-medium">语言设置</h4>
          </div>
          <div className="flex gap-2">
            <Button
              key="zh"
              onClick={() => handleLanguageChange('zh')}
              variant={preferences.language === 'zh' ? 'default' : 'secondary'}
              type="button"
            >
              中文
            </Button>
            <Button
              key="en"
              onClick={() => handleLanguageChange('en')}
              variant={preferences.language === 'en' ? 'default' : 'secondary'}
              type="button"
            >
              English
            </Button>
          </div>
        </div>

        {/* 主题设置 */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Moon className="w-4 h-4 text-ink-muted" />
            <h4 className="text-ink font-medium">主题设置</h4>
          </div>
          <div className="flex gap-2">
            {(['dark', 'light', 'system'] as const).map((themeOption) => (
              <Button
                key={themeOption}
                onClick={() => handleThemeChange(themeOption)}
                variant={theme === themeOption ? 'default' : 'secondary'}
                type="button"
              >
                {themeOption === 'dark' && '深色'}
                {themeOption === 'light' && '浅色'}
                {themeOption === 'system' && '跟随系统'}
              </Button>
            ))}
          </div>
        </div>

        {/* 通知设置 */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Bell className="w-4 h-4 text-ink-muted" />
            <h4 className="text-ink font-medium">通知设置</h4>
          </div>
          <div className="space-y-3">
            <label className="flex items-center justify-between p-3 bg-canvas/50 rounded-lg cursor-pointer">
              <div>
                <span className="text-ink text-sm">邮件通知</span>
                <p className="text-ink-faint text-xs mt-0.5">接收账户相关的邮件通知</p>
              </div>
              <input
                type="checkbox"
                checked={preferences.emailNotifications}
                onChange={(e) => updatePreference('emailNotifications', e.target.checked)}
                className="w-4 h-4 rounded border-border bg-surface-1 text-accent focus:ring-accent/20"
              />
            </label>
            <label className="flex items-center justify-between p-3 bg-canvas/50 rounded-lg cursor-pointer">
              <div>
                <span className="text-ink text-sm">系统通知</span>
                <p className="text-ink-faint text-xs mt-0.5">在页面右上角显示通知</p>
              </div>
              <input
                type="checkbox"
                checked={preferences.systemNotifications}
                onChange={(e) => updatePreference('systemNotifications', e.target.checked)}
                className="w-4 h-4 rounded border-border bg-surface-1 text-accent focus:ring-accent/20"
              />
            </label>
          </div>
        </div>
      </div>
    </SettingCard>
  );
}