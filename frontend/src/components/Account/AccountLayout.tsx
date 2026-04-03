import React, { useState, useEffect } from 'react';
import { getCurrentUser, UserResponse } from '@/api/authApi';
import { useToast } from '@/hooks/useToast';
import AccountHeader from './AccountHeader';
import AccountSidebar from './AccountSidebar';
import BasicInfoSection from './sections/BasicInfoSection';
import SecuritySettingsSection from './sections/SecuritySettingsSection';
import PreferencesSection from './sections/PreferencesSection';
import { AccountSection } from './types';

export default function AccountLayout() {
  const [activeSection, setActiveSection] = useState<AccountSection>('basic');
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const { success, error } = useToast();

  const loadUser = async () => {
    setLoading(true);
    try {
      const userData = await getCurrentUser();
      setUser(userData);
      success('用户信息加载成功');
    } catch (e) {
      error(e instanceof Error ? e.message : '加载用户信息失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUser();
  }, []);

  const handlePasswordChangeSuccess = () => {
    success('密码修改成功，请重新登录');
    // 可选：跳转到登录页或刷新用户信息
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <AccountHeader />

        <div className="flex flex-col lg:flex-row gap-6">
          {/* 侧边栏导航 */}
          <AccountSidebar
            activeSection={activeSection}
            onSectionChange={setActiveSection}
          />

          {/* 主内容区 */}
          <main className="flex-1 min-w-0">
            <div className="space-y-6">
              {activeSection === 'basic' && (
                <BasicInfoSection
                  user={user}
                  loading={loading}
                  onRefresh={loadUser}
                />
              )}
              {activeSection === 'security' && (
                <SecuritySettingsSection
                  onPasswordChangeSuccess={handlePasswordChangeSuccess}
                />
              )}
              {activeSection === 'preferences' && (
                <PreferencesSection />
              )}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
