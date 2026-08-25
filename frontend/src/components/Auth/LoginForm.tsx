/**
 * Login Form Component
 */
import { useState, useEffect } from 'react';
import { useAuth } from '../../stores/authStore';
import { useToast } from '../../hooks/useToast';
import { useI18n } from '../../i18n';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

interface LoginFormProps {
  onSuccess?: () => void;
  onSwitchToRegister?: () => void;
}

export default function LoginForm({ onSuccess, onSwitchToRegister }: LoginFormProps) {
  const { login, isLoading, error, clearError } = useAuth();
  const { error: showError, success: showSuccess } = useToast();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const { t } = useI18n();

  // 当有错误时显示 Toast
  useEffect(() => {
    if (error) {
      showError(error);
      clearError();
    }
  }, [error, clearError, showError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!username.trim()) {
      showError(t.auth.inputUsername);
      return;
    }
    if (!password) {
      showError(t.auth.inputPassword);
      return;
    }

    try {
      await login(username, password);
      showSuccess(t.auth.loginSuccess);
      onSuccess?.();
    } catch (e) {
      // Error is handled by the auth store and useEffect
    }
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="bg-surface-1 rounded-xl p-8 shadow-md">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">{t.auth.loginTitle}</h2>

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
            />
          </div>

          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? t.auth.loginProcessing : t.auth.login}
          </Button>
        </form>

        <div className="mt-6 text-center">
          <span className="text-ink-muted">{t.auth.noAccount}</span>
          <Button
            onClick={onSwitchToRegister}
            variant="link"
            className="ml-2 cursor-pointer"
          >
            {t.auth.loginToRegister}
          </Button>
        </div>
      </div>
    </div>
  );
}
