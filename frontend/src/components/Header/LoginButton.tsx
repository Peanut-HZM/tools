import { useState } from 'react';
import { useAuth } from '../../stores/authStore';
import { useLoginModalStore } from '../../stores/loginModalStore';
import { useI18n } from '../../i18n';
import { useNavigate } from 'react-router-dom';
import ChangePasswordModal from '../Common/ChangePasswordModal';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/DropdownMenu';
import { ChevronDown, UserCog, Key, LogOut } from 'lucide-react';

export default function LoginButton() {
  const { isAuthenticated, user, logout, isLoading } = useAuth();
  const openLoginModal = useLoginModalStore((state) => state.openLoginModal);
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
          <DropdownMenu>
            <DropdownMenuTrigger
              className="bg-surface-2 hover:bg-surface-3 text-ink px-3 py-2 rounded-lg transition-colors cursor-pointer"
              aria-label="用户菜单"
            >
              <ChevronDown className="w-4 h-4" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onSelect={() => navigate('/account-settings')}
              >
                <UserCog className="w-4 h-4 mr-2" />
                账户设置
              </DropdownMenuItem>
              <DropdownMenuItem
                onSelect={() => setShowChangePasswordModal(true)}
              >
                <Key className="w-4 h-4 mr-2" />
                修改密码
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onSelect={handleLogout}
                className="text-danger focus:text-danger"
              >
                <LogOut className="w-4 h-4 mr-2" />
                {t.auth.logout}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

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
      className="bg-accent hover:bg-accent-hover text-ink-inverse px-4 py-2 rounded-lg whitespace-nowrap transition-colors cursor-pointer"
    >
      {t.auth.login}
    </button>
  );
}
