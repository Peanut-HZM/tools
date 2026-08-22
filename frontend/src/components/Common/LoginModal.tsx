/**
 * 登录弹窗组件
 * 当 API 返回 401 时弹出，让用户在当前页面直接登录
 */
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../stores/authStore';
import { useI18n } from '../../i18n';
import LoginForm from '../Auth/LoginForm';
import RegisterForm from '../Auth/RegisterForm';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function LoginModal({ isOpen, onClose }: LoginModalProps) {
  const { isAuthenticated } = useAuth();
  const [showRegister, setShowRegister] = useState(false);
  const { t } = useI18n();

  // 登录后自动关闭（由 LoginForm 内部 showSuccess 提示）
  useEffect(() => {
    if (isOpen && isAuthenticated) {
      onClose();
    }
  }, [isAuthenticated, isOpen, onClose]);

  // 打开弹窗时重置状态
  useEffect(() => {
    if (isOpen) {
      setShowRegister(false);
    }
  }, [isOpen]);

  const handleLoginSuccess = useCallback(() => {
    // 由上面的 useEffect 统一处理
  }, []);

  const handleSwitchToRegister = useCallback(() => {
    setShowRegister(true);
  }, []);

  const handleSwitchToLogin = useCallback(() => {
    setShowRegister(false);
  }, []);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100]">
      <div className="bg-slate-800 rounded-xl p-8 shadow-xl w-full max-w-md mx-4 border border-slate-700">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">
            {t.auth.loginTitle}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors cursor-pointer"
            title="关闭"
          >
            <i className="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>

        {showRegister ? (
          <RegisterForm
            onSuccess={handleLoginSuccess}
            onSwitchToLogin={handleSwitchToLogin}
          />
        ) : (
          <LoginForm
            onSuccess={handleLoginSuccess}
            onSwitchToRegister={handleSwitchToRegister}
          />
        )}
      </div>
    </div>
  );
}
