import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
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
      <SettingCard title="安全设置" icon={<Shield className="w-5 h-5 text-accent" />}>
        <div className="space-y-6">
          {/* 修改密码 */}
          <Card className="p-4 bg-canvas/50">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Key className="w-4 h-4 text-ink-muted" />
                  <h4 className="text-ink font-medium">修改密码</h4>
                </div>
                <p className="text-ink-muted text-sm mb-3">
                  定期修改密码可以提高账户安全性
                </p>
                <div className="max-w-xs">
                  <Input
                    type="password"
                    placeholder="输入新密码查看强度"
                    value={previewPassword}
                    onChange={(e) => setPreviewPassword(e.target.value)}
                  />
                  <PasswordStrengthMeter password={previewPassword} />
                </div>
              </div>
              <Button onClick={() => setIsChangePasswordModalOpen(true)} className="ml-4 flex-shrink-0">
                修改密码
              </Button>
            </div>
          </Card>

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
          <div className="pt-4 border-t border-border/50">
            <p className="text-ink-faint text-xs">
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
