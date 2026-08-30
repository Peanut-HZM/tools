import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Moon, Sun, Monitor } from 'lucide-react';
import SearchBar from './SearchBar';
import LoginButton from './LoginButton';
import { useI18n } from '../../i18n';
import ContactModal from '../ContactModal/ContactModal';
import { useAuth } from '../../stores/authStore';
import { useTheme } from '../../lib/theme';
import { Button } from "@/components/ui/Button";

interface HeaderProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  onSearch: () => void;
}

export default function Header({ searchValue, onSearchChange, onSearch }: HeaderProps) {
  const { t, language, toggleLanguage } = useI18n();
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
  const [isContactModalOpen, setIsContactModalOpen] = useState(false);

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
            {user && (
              <Button asChild>
                <Link to="/marketplace" className="text-ink hover:text-accent">
                  {t.nav.marketplace}
                </Link>
              </Button>
            )}
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
              {theme === 'dark' ? <Moon className="w-4 h-4" /> : theme === 'light' ? <Sun className="w-4 h-4" /> : <Monitor className="w-4 h-4" />}
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
