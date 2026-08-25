import { useState } from 'react';
import { Link } from 'react-router-dom';
import SearchBar from './SearchBar';
import LoginButton from './LoginButton';
import { useI18n } from '../../i18n';
import ContactModal from '../ContactModal/ContactModal';
import { useAuth } from '../../stores/authStore';
import { useTheme } from '../../lib/theme';
import { safeGetItem, safeSetItem } from '../../utils/localStorage';
import { Button } from "@/components/ui/Button";

interface HeaderProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  onSearch: () => void;
}

const STORAGE_KEY = 'header-collapsed';

export default function Header({ searchValue, onSearchChange, onSearch }: HeaderProps) {
  const { t, language, toggleLanguage } = useI18n();
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
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
        <Button
          onClick={toggleCollapse}
          variant="ghost"
          size="sm"
          className="text-ink-faint hover:text-ink"
          title="展开导航"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </Button>
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
              <Button
                asChild
              >
                <Link
                  to="/admin"
                  className="bg-accent-secondary hover:opacity-90 text-ink-inverse"
                >
                  {t.nav.admin}
                </Link>
              </Button>
            )}
            <Button
              onClick={() => setIsContactModalOpen(true)}
            >
              {t.nav.contactUs}
            </Button>
            <Button
              onClick={toggleLanguage}
              variant="outline"
              className="text-ink-muted"
              title={language === 'zh-CN' ? 'Switch to English' : '切换到中文'}
            >
              {language === 'zh-CN' ? 'EN' : '中'}
            </Button>
            <Button
              onClick={() => setTheme(theme === 'dark' ? 'light' : theme === 'light' ? 'system' : 'dark')}
              variant="outline"
              className="text-ink-muted"
              title={`主题: ${theme === 'dark' ? '暗色' : theme === 'light' ? '亮色' : '跟随系统'}`}
            >
              {theme === 'dark' ? '🌙' : theme === 'light' ? '☀️' : ''}
            </Button>
            <Button
              onClick={toggleCollapse}
              variant="secondary"
              size="sm"
              title="折叠导航"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="18 15 12 9 6 15" />
              </svg>
            </Button>
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
