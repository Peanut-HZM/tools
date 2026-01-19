/**
 * Register Form Component
 */
import { useState, useEffect } from 'react';
import { useAuth } from '../../stores/authStore';
import Toast from '../MarkdownEditor/Toast/Toast';
import { useI18n } from '../../i18n';
import { getSystemSettings, SystemSettings } from '../../api/adminApi';
import { sendVerificationCode } from '../../api/authApi';

interface RegisterFormProps {
  onSuccess?: () => void;
  onSwitchToLogin?: () => void;
}

export default function RegisterForm({ onSuccess, onSwitchToLogin }: RegisterFormProps) {
  const { register, isLoading, error, clearError } = useAuth();
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
  
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState<'success' | 'error'>('error');
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
      setToastMessage(error);
      setToastType('error');
      setShowToast(true);
      clearError();
    }
  }, [error, clearError]);

  const handleSendCode = async (target: string, type: 'email' | 'phone') => {
    if (!target) {
      setToastMessage(type === 'email' ? '请输入邮箱' : '请输入手机号');
      setToastType('error');
      setShowToast(true);
      return;
    }
    
    try {
      await sendVerificationCode(target, type);
      setToastMessage('验证码发送成功');
      setToastType('success');
      setShowToast(true);
      if (type === 'email') setEmailCooldown(60);
      else setPhoneCooldown(60);
    } catch (e) {
      setToastMessage(e instanceof Error ? e.message : '验证码发送失败');
      setToastType('error');
      setShowToast(true);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    if (!username.trim()) {
      setToastMessage(t.auth.inputUsername);
      setToastType('error');
      setShowToast(true);
      return;
    }
    if (username.length < 3) {
      setToastMessage(t.auth.usernameMinLength);
      setToastType('error');
      setShowToast(true);
      return;
    }
    if (!email.trim()) {
      setToastMessage(t.auth.inputEmail);
      setToastType('error');
      setShowToast(true);
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setToastMessage(t.auth.invalidEmail);
      setToastType('error');
      setShowToast(true);
      return;
    }
    
    // Check Email Code
    if (settings?.enable_email_verify && !emailCode) {
      setToastMessage('请输入邮箱验证码');
      setToastType('error');
      setShowToast(true);
      return;
    }

    // Check Phone
    if (settings?.enable_phone_verify) {
      if (!phone.trim()) {
        setToastMessage('请输入手机号');
        setToastType('error');
        setShowToast(true);
        return;
      }
      if (!phoneCode) {
        setToastMessage('请输入手机验证码');
        setToastType('error');
        setShowToast(true);
        return;
      }
    }

    if (!password) {
      setToastMessage(t.auth.inputPassword);
      setToastType('error');
      setShowToast(true);
      return;
    }
    if (password.length < 6) {
      setToastMessage(t.auth.passwordMinLength);
      setToastType('error');
      setShowToast(true);
      return;
    }
    if (password.length > 50) {
      setToastMessage(t.auth.passwordMaxLength);
      setToastType('error');
      setShowToast(true);
      return;
    }
    if (password !== confirmPassword) {
      setToastMessage(t.auth.passwordMismatch);
      setToastType('error');
      setShowToast(true);
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
      <div className="bg-slate-800 rounded-xl p-8 shadow-xl">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">{t.auth.registerTitle}</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-slate-300 mb-1">
              {t.auth.username}
            </label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder={t.auth.inputUsername}
              disabled={isLoading}
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-1">
              {t.auth.email}
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors"
              placeholder={t.auth.inputEmail}
              required
            />
          </div>

          {settings?.enable_email_verify && (
            <div>
              <label htmlFor="emailCode" className="block text-sm font-medium text-slate-300 mb-1">
                邮箱验证码
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  id="emailCode"
                  value={emailCode}
                  onChange={(e) => setEmailCode(e.target.value)}
                  className="flex-1 px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors"
                  placeholder="请输入验证码"
                  required
                />
                <button
                  type="button"
                  onClick={() => handleSendCode(email, 'email')}
                  disabled={emailCooldown > 0}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap min-w-[100px]"
                >
                  {emailCooldown > 0 ? `${emailCooldown}s` : '获取验证码'}
                </button>
              </div>
            </div>
          )}

          {settings?.enable_phone_verify && (
            <>
              <div>
                <label htmlFor="phone" className="block text-sm font-medium text-slate-300 mb-1">
                  手机号
                </label>
                <input
                  type="tel"
                  id="phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors"
                  placeholder="请输入手机号"
                  required
                />
              </div>

              <div>
                <label htmlFor="phoneCode" className="block text-sm font-medium text-slate-300 mb-1">
                  手机验证码
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    id="phoneCode"
                    value={phoneCode}
                    onChange={(e) => setPhoneCode(e.target.value)}
                    className="flex-1 px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors"
                    placeholder="请输入验证码 (测试码: 202601)"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => handleSendCode(phone, 'phone')}
                    disabled={phoneCooldown > 0}
                    className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap min-w-[100px]"
                  >
                    {phoneCooldown > 0 ? `${phoneCooldown}s` : '获取验证码'}
                  </button>
                </div>
              </div>
            </>
          )}

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-1">
              {t.auth.password}
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder={t.auth.inputPassword}
              disabled={isLoading}
              maxLength={50}
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-300 mb-1">
              {t.auth.confirmPassword}
            </label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder={t.auth.confirmPassword}
              disabled={isLoading}
              maxLength={50}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2 px-4 bg-cyan-500 hover:bg-cyan-600 disabled:bg-cyan-500/50 text-white font-medium rounded-lg transition-colors cursor-pointer"
          >
            {isLoading ? t.auth.registerProcessing : t.auth.register}
          </button>
        </form>

        <div className="mt-6 text-center">
          <span className="text-slate-400">{t.auth.hasAccount}</span>
          <button
            onClick={onSwitchToLogin}
            className="ml-2 text-cyan-400 hover:text-cyan-300 cursor-pointer"
          >
            {t.auth.registerToLogin}
          </button>
        </div>
      </div>

      {showToast && (
        <Toast
          message={toastMessage}
          type={toastType}
          onClose={() => setShowToast(false)}
        />
      )}
    </div>
  );
}
