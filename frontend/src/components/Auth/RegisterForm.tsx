/**
 * Register Form Component
 */
import { useState, useEffect } from 'react';
import { useAuth } from '../../stores/authStore';
import { useToast } from '../../hooks/useToast';
import { useI18n } from '../../i18n';
import { getSystemSettings, SystemSettings } from '../../api/adminApi';
import { sendVerificationCode } from '../../api/authApi';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

interface RegisterFormProps {
  onSuccess?: () => void;
  onSwitchToLogin?: () => void;
}

export default function RegisterForm({ onSuccess, onSwitchToLogin }: RegisterFormProps) {
  const { register, isLoading, error, clearError } = useAuth();
  const { error: showError, success: showSuccess } = useToast();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [emailCode, setEmailCode] = useState('');
  const [phoneCode, setPhoneCode] = useState('');

  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [emailCooldown, setEmailCooldown] = useState(0);
  const [phoneCooldown, setPhoneCooldown] = useState(0);
  const { t } = useI18n();

  useEffect(() => {
    // Fetch settings to know which fields to show
    getSystemSettings().then(setSettings).catch(console.error);
  }, []);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    if (emailCooldown > 0) {
      interval = setInterval(() => setEmailCooldown(c => c - 1), 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [emailCooldown]);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    if (phoneCooldown > 0) {
      interval = setInterval(() => setPhoneCooldown(c => c - 1), 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [phoneCooldown]);

  // 当有错误时显示 Toast
  useEffect(() => {
    if (error) {
      showError(error);
      clearError();
    }
  }, [error, clearError, showError]);

  const handleSendCode = async (target: string, type: 'email' | 'phone') => {
    if (!target) {
      showError(type === 'email' ? '请输入邮箱' : '请输入手机号');
      return;
    }

    try {
      await sendVerificationCode(target, type);
      showSuccess('验证码发送成功');
      if (type === 'email') setEmailCooldown(60);
      else setPhoneCooldown(60);
    } catch (e) {
      showError(e instanceof Error ? e.message : '验证码发送失败');

    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    if (!username.trim()) {
      showError(t.auth.inputUsername);
      return;
    }
    if (username.length < 3) {
      showError(t.auth.usernameMinLength);
      return;
    }
    if (!email.trim()) {
      showError(t.auth.inputEmail);
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      showError(t.auth.invalidEmail);
      return;
    }

    // Check Email Code
    if (settings?.enable_email_verify && !emailCode) {
      showError('请输入邮箱验证码');
      return;
    }

    // Check Phone
    if (settings?.enable_phone_verify) {
      if (!phone.trim()) {
        showError('请输入手机号');
        return;
      }
      if (!phoneCode) {
        showError('请输入手机验证码');
        return;
      }
    }

    if (!password) {
      showError(t.auth.inputPassword);
      return;
    }
    if (password.length < 6) {
      showError(t.auth.passwordMinLength);
      return;
    }
    if (password.length > 50) {
      showError(t.auth.passwordMaxLength);
      return;
    }
    if (password !== confirmPassword) {
      showError(t.auth.passwordMismatch);
      return;
    }

    try {
      await register(username, email, password, phone, emailCode, phoneCode);
      onSuccess?.();
    } catch (e) {
      // Error is handled by the auth store and useEffect
    }
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="bg-surface-1 rounded-xl p-8 shadow-md">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">{t.auth.registerTitle}</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-ink-muted mb-1">
              {t.auth.username}
            </label>
            <Input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder={t.auth.inputUsername}
              disabled={isLoading}
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-ink-muted mb-1">
              {t.auth.email}
            </label>
            <Input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={t.auth.inputEmail}
              required
            />
          </div>

          {settings?.enable_email_verify && (
            <div>
              <label htmlFor="emailCode" className="block text-sm font-medium text-ink-muted mb-1">
                邮箱验证码
              </label>
              <div className="flex gap-2">
                <Input
                  type="text"
                  id="emailCode"
                  value={emailCode}
                  onChange={(e) => setEmailCode(e.target.value)}
                  placeholder="请输入验证码"
                  required
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => handleSendCode(email, 'email')}
                  disabled={emailCooldown > 0}
                  className="min-w-[100px]"
                >
                  {emailCooldown > 0 ? `${emailCooldown}s` : '获取验证码'}
                </Button>
              </div>
            </div>
          )}

          {settings?.enable_phone_verify && (
            <>
              <div>
                <label htmlFor="phone" className="block text-sm font-medium text-ink-muted mb-1">
                  手机号
                </label>
                <Input
                  type="tel"
                  id="phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="请输入手机号"
                  required
                />
              </div>

              <div>
                <label htmlFor="phoneCode" className="block text-sm font-medium text-ink-muted mb-1">
                  手机验证码
                </label>
                <div className="flex gap-2">
                  <Input
                    type="text"
                    id="phoneCode"
                    value={phoneCode}
                    onChange={(e) => setPhoneCode(e.target.value)}
                    placeholder="请输入验证码 (测试码: 202601)"
                    required
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => handleSendCode(phone, 'phone')}
                    disabled={phoneCooldown > 0}
                    className="min-w-[100px]"
                  >
                    {phoneCooldown > 0 ? `${phoneCooldown}s` : '获取验证码'}
                  </Button>
                </div>
              </div>
            </>
          )}

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-ink-muted mb-1">
              {t.auth.password}
            </label>
            <Input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t.auth.inputPassword}
              disabled={isLoading}
              maxLength={50}
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-ink-muted mb-1">
              {t.auth.confirmPassword}
            </label>
            <Input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder={t.auth.confirmPassword}
              disabled={isLoading}
              maxLength={50}
            />
          </div>

          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? t.auth.registerProcessing : t.auth.register}
          </Button>
        </form>

        <div className="mt-6 text-center">
          <span className="text-ink-muted">{t.auth.hasAccount}</span>
          <Button
            onClick={onSwitchToLogin}
            variant="link"
            className="ml-2 cursor-pointer"
          >
            {t.auth.registerToLogin}
          </Button>
        </div>
      </div>
    </div>
  );
}
