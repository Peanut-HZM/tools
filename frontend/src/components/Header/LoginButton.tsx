import { useState } from 'react';
import { useAuth } from '../../stores/authStore';
import { useLoginModalStore } from '../../stores/loginModalStore';
import { useI18n } from '../../i18n';
import { useNavigate } from 'react-router-dom';
import ChangePasswordModal from '../Common/ChangePasswordModal';

export default function LoginButton() {
  const { isAuthenticated, user, logout, isLoading } = useAuth();
  const openLoginModal = useLoginModalStore((state) => state.openLoginModal);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false);
  const { t } = useI18n();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
  };

  if (isLoading) {
    return (
      <div className="text-ink-muted px-4 py-2">
        {t.common.loading}
      </div>
    );
  }

  if (isAuthenticated && user) {
    return (
      <div className="relative">
        <div className="flex items-center gap-3">
          <span className="text-ink-muted text-sm">
            {user.username}
          </span>
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="bg-surface-2 hover:bg-surface-3 text-ink-inverse px-3 py-2 rounded-lg transition-colors cursor-pointer"
          >
            <i className="fa-solid fa-chevron-down"></i>
          </button>
        </div>

        {/* User Menu Dropdown */}
        {showUserMenu && (
          <div className="absolute right-0 mt-2 w-48 bg-surface-1 border border-border rounded-lg shadow-lg z-50">
            <button
              onClick={() => {
                navigate('/account-settings');
                setShowUserMenu(false);
              }}
              className="w-full text-left px-4 py-2 text-ink-muted hover:bg-surface-2 hover:text-ink-inverse transition-colors text-sm"
            >
              <i className="fa-solid fa-user-gear mr-2"></i>
              账户设置
            </button>
            <button
              onClick={() => {
                setShowChangePasswordModal(true);
                setShowUserMenu(false);
              }}
              className="w-full text-left px-4 py-2 text-ink-muted hover:bg-surface-2 hover:text-ink-inverse transition-colors text-sm"
            >
              <i className="fa-solid fa-key mr-2"></i>
              修改密码
            </button>
            <hr className="border-border my-1" />
            <button
              onClick={handleLogout}
              className="w-full text-left px-4 py-2 text-danger hover:bg-surface-2 hover:text-danger transition-colors text-sm"
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
    <button
      onClick={openLoginModal}
      className="bg-accent hover:bg-accent-hover text-white px-4 py-2 rounded-lg whitespace-nowrap transition-colors cursor-pointer"
    >
      {t.auth.login}
    </button>
  );
}
