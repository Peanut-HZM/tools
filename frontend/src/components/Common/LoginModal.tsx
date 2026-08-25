/**
 * 登录弹窗组件
 * 当 API 返回 401 或未登录访问受保护页面时弹出，让用户在当前页面直接登录
 * 打开状态由 loginModalStore 全局管理
 */
import { useEffect, useState } from 'react';
import { useAuth } from '../../stores/authStore';
import { useLoginModalStore } from '../../stores/loginModalStore';
import { useI18n } from '../../i18n';
import LoginForm from '../Auth/LoginForm';
import RegisterForm from '../Auth/RegisterForm';

export default function LoginModal() {
  const { isAuthenticated } = useAuth();
  const isOpen = useLoginModalStore((state) => state.isOpen);
  const closeLoginModal = useLoginModalStore((state) => state.closeLoginModal);
  const [showRegister, setShowRegister] = useState(false);
  const { t } = useI18n();

  // 登录后自动关闭
  useEffect(() => {
    if (isOpen && isAuthenticated) {
      closeLoginModal();
    }
  }, [isAuthenticated, isOpen, closeLoginModal]);

  // 打开弹窗时重置状态
  useEffect(() => {
    if (isOpen) {
      setShowRegister(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100]">
      <div className="bg-surface-1 rounded-xl p-8 shadow-md w-full max-w-md mx-4 border border-border">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">
            {t.auth.loginTitle}
          </h2>
          <button
            onClick={closeLoginModal}
            className="text-ink-faint hover:text-white transition-colors cursor-pointer"
            title="关闭"
          >
            <i className="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>

        {showRegister ? (
          <RegisterForm
            onSuccess={() => {}}
            onSwitchToLogin={() => setShowRegister(false)}
          />
        ) : (
          <LoginForm
            onSuccess={() => {}}
            onSwitchToRegister={() => setShowRegister(true)}
          />
        )}
      </div>
    </div>
  );
}
