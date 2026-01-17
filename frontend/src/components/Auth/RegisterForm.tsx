/**
 * Register Form Component
 */
import { useState, useEffect } from 'react';
import { useAuth } from '../../stores/authStore';
import Toast from '../MarkdownEditor/Toast/Toast';

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
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  // 当有错误时显示 Toast
  useEffect(() => {
    if (error) {
      setToastMessage(error);
      setShowToast(true);
      clearError();
    }
  }, [error, clearError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    if (!username.trim()) {
      setToastMessage('请输入用户名');
      setShowToast(true);
      return;
    }
    if (username.length < 3) {
      setToastMessage('用户名至少需要3个字符');
      setShowToast(true);
      return;
    }
    if (!email.trim()) {
      setToastMessage('请输入邮箱');
      setShowToast(true);
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setToastMessage('请输入有效的邮箱地址');
      setShowToast(true);
      return;
    }
    if (!password) {
      setToastMessage('请输入密码');
      setShowToast(true);
      return;
    }
    if (password.length < 6) {
      setToastMessage('密码至少需要6个字符');
      setShowToast(true);
      return;
    }
    if (password.length > 50) {
      setToastMessage('密码不能超过50个字符');
      setShowToast(true);
      return;
    }
    if (password !== confirmPassword) {
      setToastMessage('两次输入的密码不一致');
      setShowToast(true);
      return;
    }

    try {
      await register(username, email, password);
      onSuccess?.();
    } catch (e) {
      // Error is handled by the auth store and useEffect
    }
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="bg-slate-800 rounded-xl p-8 shadow-xl">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">注册</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-slate-300 mb-1">
              用户名
            </label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder="请输入用户名（至少3个字符）"
              disabled={isLoading}
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-1">
              邮箱
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder="请输入邮箱"
              disabled={isLoading}
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-1">
              密码
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder="请输入密码（6-50个字符）"
              disabled={isLoading}
              maxLength={50}
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-300 mb-1">
              确认密码
            </label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder="请再次输入密码"
              disabled={isLoading}
              maxLength={50}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2 px-4 bg-cyan-500 hover:bg-cyan-600 disabled:bg-cyan-500/50 text-white font-medium rounded-lg transition-colors cursor-pointer"
          >
            {isLoading ? '注册中...' : '注册'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <span className="text-slate-400">已有账号？</span>
          <button
            onClick={onSwitchToLogin}
            className="ml-2 text-cyan-400 hover:text-cyan-300 cursor-pointer"
          >
            立即登录
          </button>
        </div>
      </div>

      {showToast && (
        <Toast
          message={toastMessage}
          type="error"
          onClose={() => setShowToast(false)}
        />
      )}
    </div>
  );
}
