import { useState } from 'react';
import { Link } from 'react-router-dom';
import SearchBar from './SearchBar';
import LoginButton from './LoginButton';
import { useI18n } from '../../i18n';
import ContactModal from '../ContactModal/ContactModal';
import { useAuth } from '../../stores/authStore';
import { safeGetItem, safeSetItem } from '../../utils/localStorage';

interface HeaderProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  onSearch: () => void;
}

const STORAGE_KEY = 'header-collapsed';

export default function Header({ searchValue, onSearchChange, onSearch }: HeaderProps) {
  const { t, language, toggleLanguage } = useI18n();
  const { user } = useAuth();
  const [isContactModalOpen, setIsContactModalOpen] = useState(false);

  const [isCollapsed, setIsCollapsed] = useState(() => safeGetItem(STORAGE_KEY) === 'true');

  const toggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      safeSetItem(STORAGE_KEY, String(next));
      return next;
    });
  };

  // 折叠状态：显示迷你横条
  if (isCollapsed) {
    return (
      <header className="sticky top-0 z-40 bg-surface-1 border-b border-border h-8 flex items-center justify-center">
        <button
          onClick={toggleCollapse}
          className="px-3 py-1 rounded text-ink-faint hover:text-ink transition-colors cursor-pointer"
          title="展开导航"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
      </header>
    );
  }

  // 展开状态：原始 Header（尚未添加折叠按钮，下一步添加）
  return (
    <>
      <header className="sticky top-0 z-40 bg-surface-1 border-b border-border">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-10">
            <Link
              to="/"
              className="text-2xl font-['Pacifico'] bg-gradient-to-br from-accent to-accent-secondary bg-clip-text text-transparent"
              key={language}
            >
              {t.common.logo}
            </Link>
          </div>
          <div className="flex items-center space-x-4">
            <SearchBar
              value={searchValue}
              onChange={onSearchChange}
              onSearch={onSearch}
            />
            {user?.role === 'admin' && (
              <Link
                to="/admin"
                className="px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium transition-colors cursor-pointer"
              >
                {t.nav.admin}
              </Link>
            )}
            <button
              onClick={() => setIsContactModalOpen(true)}
              className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors cursor-pointer"
            >
              {t.nav.contactUs}
            </button>
            <button
              onClick={toggleLanguage}
              className="px-3 py-1.5 rounded-lg bg-surface-2 hover:bg-surface-3 text-ink-muted text-sm font-medium transition-colors border border-border cursor-pointer"
              title={language === 'zh-CN' ? 'Switch to English' : '切换到中文'}
            >
              {language === 'zh-CN' ? 'EN' : '中'}
            </button>
            <button
              onClick={toggleCollapse}
              className="px-2 py-1.5 rounded-lg bg-surface-2 hover:bg-surface-3 text-ink-muted text-sm transition-colors cursor-pointer"
              title="折叠导航"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="18 15 12 9 6 15" />
              </svg>
            </button>
            <LoginButton />
          </div>
        </div>
      </header>

      {/* 联系我们弹窗 */}
      <ContactModal
        isOpen={isContactModalOpen}
        onClose={() => setIsContactModalOpen(false)}
      />
    </>
  );
}
