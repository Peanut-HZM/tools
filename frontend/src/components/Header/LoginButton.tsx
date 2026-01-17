import { useState } from 'react';
import { useAuth } from '../../stores/authStore';
import LoginForm from '../Auth/LoginForm';
import RegisterForm from '../Auth/RegisterForm';

export default function LoginButton() {
  const { isAuthenticated, user, logout, isLoading } = useAuth();
  const [showModal, setShowModal] = useState(false);
  const [showRegister, setShowRegister] = useState(false);

  const handleLogout = async () => {
    await logout();
  };

  const handleLoginSuccess = () => {
    setShowModal(false);
    setShowRegister(false);
  };

  if (isLoading) {
    return (
      <div className="text-slate-400 px-4 py-2">
        加载中...
      </div>
    );
  }

  if (isAuthenticated && user) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-slate-300 text-sm">
          {user.username}
        </span>
        <button
          onClick={handleLogout}
          className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg whitespace-nowrap transition-colors cursor-pointer"
        >
          退出
        </button>
      </div>
    );
  }

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className="bg-cyan-500 hover:bg-cyan-600 text-white px-4 py-2 rounded-lg whitespace-nowrap transition-colors cursor-pointer"
      >
        登录
      </button>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="relative">
            <button
              onClick={() => {
                setShowModal(false);
                setShowRegister(false);
              }}
              className="absolute -top-2 -right-2 w-8 h-8 bg-slate-700 hover:bg-slate-600 rounded-full flex items-center justify-center text-white z-10 cursor-pointer"
            >
              ×
            </button>
            {showRegister ? (
              <RegisterForm
                onSuccess={handleLoginSuccess}
                onSwitchToLogin={() => setShowRegister(false)}
              />
            ) : (
              <LoginForm
                onSuccess={handleLoginSuccess}
                onSwitchToRegister={() => setShowRegister(true)}
              />
            )}
          </div>
        </div>
      )}
    </>
  );
}
