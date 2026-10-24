import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Boxes, Moon, Sun, Monitor, Search, Shield, Mail } from 'lucide-react';
import SearchBar from './SearchBar';
import LoginButton from './LoginButton';
import { useI18n } from '../../i18n';
import ContactModal from '../ContactModal/ContactModal';
import { useAuth } from '../../stores/authStore';
import { useTheme } from '../../lib/theme';
import { NAV_ROUTES, OPEN_COMMAND_PALETTE_EVENT } from '../../lib/navigation';
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
  // 当前路由路径：用于导航链接激活判定
  const { pathname } = useLocation();

  return (
    <>
      <header className="sticky top-0 z-40 h-14 border-b border-border bg-surface-1/95 backdrop-blur">
        <div className="flex h-full w-full items-center justify-between px-4">
          <div className="flex min-w-0 items-center gap-7">
            <Link
              to="/"
              className="flex shrink-0 items-center gap-2 text-base font-bold tracking-tight text-ink"
              key={language}
            >
              <span className="grid h-7 w-7 place-items-center rounded-lg bg-[image:var(--gradient-brand)] text-white shadow-sm">
                <Boxes className="h-4 w-4" />
              </span>
              {t.common.logo}
            </Link>
            <nav className="hidden h-14 items-center gap-1 md:flex">
              {NAV_ROUTES.map((item) => {
                const isActive = item.match(pathname);
                const label = t.nav[item.key];
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={`relative inline-flex h-14 items-center px-3 text-xs whitespace-nowrap transition-colors ${
                      isActive
                        ? 'font-medium text-accent'
                        : 'text-ink-muted hover:text-ink'
                    }`}
                  >
                    {label}
                    <span
                      aria-hidden="true"
                      className={`absolute inset-x-3 bottom-0 h-0.5 rounded-full ${
                        isActive ? 'bg-accent' : 'bg-transparent'
                      }`}
                    />
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="flex shrink-0 items-center gap-1.5">
            <div className="hidden lg:block">
              <SearchBar
                value={searchValue}
                onChange={onSearchChange}
                onSearch={onSearch}
              />
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => window.dispatchEvent(new CustomEvent(OPEN_COMMAND_PALETTE_EVENT))}
              aria-label={t.common.search}
              title={t.common.search}
            >
              <Search className="w-4 h-4" />
            </Button>
            {/* 后台管理入口：仅管理员可见，桌面端图标化 */}
            {user?.role === 'admin' && (
              <Button asChild variant="ghost" size="icon" className="hidden md:inline-flex" title={t.nav.admin}>
                <Link to="/admin" aria-label={t.nav.admin}>
                  <Shield className="w-4 h-4" />
                </Link>
              </Button>
            )}
            {/* 联系我们：桌面端图标化（移动端入口归入阶段⑦完整导航） */}
            <Button
              variant="ghost"
              size="icon"
              className="hidden md:inline-flex"
              onClick={() => setIsContactModalOpen(true)}
              aria-label={t.nav.contactUs}
              title={t.nav.contactUs}
            >
              <Mail className="w-4 h-4" />
            </Button>
            {/* 语言切换：中文/英文循环 */}
            <Button
              variant="ghost"
              size="icon"
              className="hidden md:inline-flex"
              onClick={toggleLanguage}
              title={language === 'zh-CN' ? 'Switch to English' : '切换到中文'}
            >
              {language === 'zh-CN' ? 'EN' : '中'}
            </Button>
            {/* 主题切换：暗色 → 亮色 → 跟随系统 循环（移动端常显：主题属高频操作，不随桌面导航收纳隐藏） */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === 'dark' ? 'light' : theme === 'light' ? 'system' : 'dark')}
              title={`主题: ${theme === 'dark' ? '暗色' : theme === 'light' ? '亮色' : '跟随系统'}`}
            >
              {theme === 'dark' ? <Moon className="w-4 h-4" /> : theme === 'light' ? <Sun className="w-4 h-4" /> : <Monitor className="w-4 h-4" />}
            </Button>
            {/* 登录按钮 / 用户菜单（移动端保留头像入口） */}
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
