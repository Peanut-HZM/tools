import React, { useState } from 'react';
import SettingCard from '../SettingCard';
import InfoRow from '../InfoRow';
import PasswordStrengthMeter from '../components/PasswordStrengthMeter';
import ChangePasswordModal from '@/components/Common/ChangePasswordModal';
import { Shield, Key, Clock, Monitor } from 'lucide-react';

interface SecuritySettingsSectionProps {
  onPasswordChangeSuccess: () => void;
}

export default function SecuritySettingsSection({ onPasswordChangeSuccess }: SecuritySettingsSectionProps) {
  const [isChangePasswordModalOpen, setIsChangePasswordModalOpen] = useState(false);
  const [previewPassword, setPreviewPassword] = useState('');

  // 模拟最后登录时间（后续可从 API 获取）
  const lastLoginTime = new Date().toLocaleString('zh-CN');
  const lastLoginDevice = 'Chrome on macOS';

  return (
    <>
      <SettingCard title="安全设置" icon={<Shield className="w-5 h-5 text-cyan-400" />}>
        <div className="space-y-6">
          {/* 修改密码 */}
          <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-700/50">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Key className="w-4 h-4 text-slate-400" />
                  <h4 className="text-white font-medium">修改密码</h4>
                </div>
                <p className="text-slate-400 text-sm mb-3">
                  定期修改密码可以提高账户安全性
                </p>
                <div className="max-w-xs">
                  <input
                    type="password"
                    placeholder="输入新密码查看强度"
                    value={previewPassword}
                    onChange={(e) => setPreviewPassword(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-white text-sm focus:border-cyan-500 outline-none transition-colors"
                  />
                  <PasswordStrengthMeter password={previewPassword} />
                </div>
              </div>
              <button
                onClick={() => setIsChangePasswordModalOpen(true)}
                className="ml-4 px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded text-sm font-medium transition-colors flex-shrink-0"
                type="button"
              >
                修改密码
              </button>
            </div>
          </div>

          {/* 登录信息 */}
          <div className="space-y-1">
            <InfoRow
              label="最后登录时间"
              value={lastLoginTime}
            />
            <InfoRow
              label="登录设备"
              value={lastLoginDevice}
            />
          </div>

          {/* 预留：两步验证、登录设备管理 */}
          <div className="pt-4 border-t border-slate-700/50">
            <p className="text-slate-500 text-xs">
              更多安全功能即将推出，敬请期待
            </p>
          </div>
        </div>
      </SettingCard>

      {/* 修改密码模态框 */}
      {isChangePasswordModalOpen && (
        <ChangePasswordModal
          isOpen={isChangePasswordModalOpen}
          onClose={() => setIsChangePasswordModalOpen(false)}
          onSuccess={() => {
            onPasswordChangeSuccess();
            setIsChangePasswordModalOpen(false);
          }}
        />
      )}
    </>
  );
}
