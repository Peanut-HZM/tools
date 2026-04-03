import { useState } from 'react';
import { useAuth } from '../../stores/authStore';
import LoginForm from '../Auth/LoginForm';
import RegisterForm from '../Auth/RegisterForm';
import { useI18n } from '../../i18n';
import { useNavigate } from 'react-router-dom';
import ChangePasswordModal from '../Common/ChangePasswordModal';

export default function LoginButton() {
  const { isAuthenticated, user, logout, isLoading } = useAuth();
  const [showModal, setShowModal] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false);
  const { t } = useI18n();
  const navigate = useNavigate();

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
        {t.common.loading}
      </div>
    );
  }

  if (isAuthenticated && user) {
    return (
      <div className="relative">
        <div className="flex items-center gap-3">
          <span className="text-slate-300 text-sm">
            {user.username}
          </span>
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="bg-slate-700 hover:bg-slate-600 text-white px-3 py-2 rounded-lg transition-colors cursor-pointer"
          >
            <i className="fa-solid fa-chevron-down"></i>
          </button>
        </div>

        {/* User Menu Dropdown */}
        {showUserMenu && (
          <div className="absolute right-0 mt-2 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-lg z-50">
            <button
              onClick={() => {
                navigate('/account-settings');
                setShowUserMenu(false);
              }}
              className="w-full text-left px-4 py-2 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors text-sm"
            >
              <i className="fa-solid fa-user-gear mr-2"></i>
              账户设置
            </button>
            <button
              onClick={() => {
                setShowChangePasswordModal(true);
                setShowUserMenu(false);
              }}
              className="w-full text-left px-4 py-2 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors text-sm"
            >
              <i className="fa-solid fa-key mr-2"></i>
              修改密码
            </button>
            <hr className="border-slate-700 my-1" />
            <button
              onClick={handleLogout}
              className="w-full text-left px-4 py-2 text-red-400 hover:bg-slate-700 hover:text-red-300 transition-colors text-sm"
            >
              <i className="fa-solid fa-right-from-bracket mr-2"></i>
              {t.auth.logout}
            </button>
          </div>
        )}

        <ChangePasswordModal
          isOpen={showChangePasswordModal}
          onClose={() => setShowChangePasswordModal(false)}
        />
      </div>
    );
  }

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className="bg-cyan-500 hover:bg-cyan-600 text-white px-4 py-2 rounded-lg whitespace-nowrap transition-colors cursor-pointer"
      >
        {t.auth.login}
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
