import { useState, useEffect } from 'react';
import { getSystemSettings, updateSystemSettings, SystemSettings } from '../../api/adminApi';
import { useToast } from '../../hooks/useToast';
import { ToastContainer } from '../MarkdownEditor/Toast/Toast';

export default function SystemSettingsPage() {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const { toasts, removeToast, success, error } = useToast();

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const data = await getSystemSettings();
      setSettings(data);
    } catch (e) {
      error('获取系统设置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleRegistration = async () => {
    if (!settings) return;
    
    const newValue = !settings.allow_registration;
    try {
      await updateSystemSettings({ allow_registration: newValue });
      setSettings({ ...settings, allow_registration: newValue });
      success(`用户注册功能已${newValue ? '开启' : '关闭'}`);
    } catch (e) {
      error('更新设置失败');
    }
  };

  const handleToggleEmailVerify = async () => {
    if (!settings) return;
    
    const newValue = !settings.enable_email_verify;
    try {
      await updateSystemSettings({ enable_email_verify: newValue });
      setSettings({ ...settings, enable_email_verify: newValue });
      success(`邮箱验证已${newValue ? '开启' : '关闭'}`);
    } catch (e) {
      error('更新设置失败');
    }
  };

  const handleTogglePhoneVerify = async () => {
    if (!settings) return;
    
    const newValue = !settings.enable_phone_verify;
    try {
      await updateSystemSettings({ enable_phone_verify: newValue });
      setSettings({ ...settings, enable_phone_verify: newValue });
      success(`手机号验证已${newValue ? '开启' : '关闭'}`);
    } catch (e) {
      error('更新设置失败');
    }
  };

  if (loading) return <div className="text-white">加载中...</div>;

  return (
    <div>
      <h2 className="text-2xl font-bold text-white mb-6">系统设置</h2>
      
      <div className="space-y-6">
        {/* User Registration Toggle */}
        <div className="bg-slate-700 rounded-lg p-6 border border-slate-600">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-medium text-white">用户注册</h3>
              <p className="text-sm text-slate-400 mt-1">
                开启后，游客可以在登录页面自行注册账号。关闭后，仅管理员可添加用户。
              </p>
            </div>
            
            <button
              onClick={handleToggleRegistration}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 focus:ring-offset-slate-900 ${
                settings?.allow_registration ? 'bg-cyan-500' : 'bg-slate-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings?.allow_registration ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Email Verification Toggle */}
        <div className="bg-slate-700 rounded-lg p-6 border border-slate-600">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-medium text-white">邮箱验证注册</h3>
              <p className="text-sm text-slate-400 mt-1">
                开启后，用户注册时必须验证邮箱。
              </p>
            </div>
            
            <button
              onClick={handleToggleEmailVerify}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 focus:ring-offset-slate-900 ${
                settings?.enable_email_verify ? 'bg-cyan-500' : 'bg-slate-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings?.enable_email_verify ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Phone Verification Toggle */}
        <div className="bg-slate-700 rounded-lg p-6 border border-slate-600">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-medium text-white">手机号验证注册</h3>
              <p className="text-sm text-slate-400 mt-1">
                开启后，用户注册时必须输入手机号并验证。
              </p>
            </div>
            
            <button
              onClick={handleTogglePhoneVerify}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2 focus:ring-offset-slate-900 ${
                settings?.enable_phone_verify ? 'bg-cyan-500' : 'bg-slate-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings?.enable_phone_verify ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>
      </div>
      
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}
