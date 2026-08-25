/**
 * Login Form Component
 */
import { useState, useEffect } from 'react';
import { useAuth } from '../../stores/authStore';
import { useToast } from '../../hooks/useToast';
import { useI18n } from '../../i18n';

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
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 bg-surface-2 border border-border rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder={t.auth.inputUsername}
              disabled={isLoading}
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-ink-muted mb-1">
              {t.auth.password}
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-surface-2 border border-border rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder={t.auth.inputPassword}
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2 px-4 bg-accent hover:bg-accent-hover disabled:bg-cyan-500/50 text-white font-medium rounded-lg transition-colors cursor-pointer"
          >
            {isLoading ? t.auth.loginProcessing : t.auth.login}
          </button>
        </form>

        <div className="mt-6 text-center">
          <span className="text-ink-muted">{t.auth.noAccount}</span>
          <button
            onClick={onSwitchToRegister}
            className="ml-2 text-accent hover:text-cyan-300 cursor-pointer"
          >
            {t.auth.loginToRegister}
          </button>
        </div>
      </div>
    </div>
  );
}
