import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Moon, Sun, Monitor, Search, Shield, Mail } from 'lucide-react';
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
  // 当前路由路径：用于导航链接激活判定
  const { pathname } = useLocation();

  // 桌面导航项：match 为激活判定函数（首页全等匹配，其余按路径前缀匹配）
  const NAV_ITEMS = [
    { to: '/', label: t.nav.home, match: (p: string) => p === '/' },
    { to: '/marketplace', label: t.nav.marketplace, match: (p: string) => p.startsWith('/marketplace') },
    { to: '/courses', label: t.nav.courses, match: (p: string) => p.startsWith('/courses') },
    { to: '/tech-contents', label: t.nav.techContents, match: (p: string) => p.startsWith('/tech-contents') },
  ];

  return (
    <>
      {/* 玻璃悬浮条：glass-panel 提供半透明模糊底 + 描边，去掉左右/顶部边框使其贴边 */}
      <header className="sticky top-0 z-40 glass-panel border-x-0 border-t-0 rounded-none">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          {/* 左侧：渐变 Logo + 桌面导航 */}
          <div className="flex items-center space-x-6 min-w-0">
            <Link
              to="/"
              className="text-2xl font-extrabold tracking-tight gradient-text shrink-0"
              key={language}
            >
              {t.common.logo}
            </Link>
            {/* 桌面导航链接（移动端收纳，完整移动端导航属阶段⑦） */}
            <nav className="hidden md:flex items-center space-x-1">
              {NAV_ITEMS.map((item) => {
                const isActive = item.match(pathname);
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={`inline-flex flex-col px-3 py-2 rounded-lg whitespace-nowrap transition-colors ${
                      isActive
                        ? 'text-ink bg-glass-bg'
                        : 'text-ink-muted hover:text-ink hover:bg-glass-bg'
                    }`}
                  >
                    {item.label}
                    {/* 激活态 2px 品牌渐变下划线；非激活渲染透明占位，避免切换页面时布局抖动 */}
                    <span
                      aria-hidden="true"
                      className={`block h-0.5 rounded-full ${
                        isActive ? 'bg-[image:var(--gradient-brand)]' : 'bg-transparent'
                      }`}
                    />
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* 右侧：搜索 + 功能按钮组 */}
          <div className="flex items-center space-x-2 shrink-0">
            {/* 桌面端搜索条（lg 起显示：md 区间容器宽度不足以同时容纳完整导航与搜索条，改用搜索图标按钮打开 ⌘K 面板） */}
            <div className="hidden lg:block">
              <SearchBar
                value={searchValue}
                onChange={onSearchChange}
                onSearch={onSearch}
              />
            </div>
            {/* 移动端/平板搜索图标：点击派发 open-command-palette 自定义事件，
                由 Task 12 的命令面板监听并打开（lg 起显示完整搜索条，此按钮隐藏） */}
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => window.dispatchEvent(new CustomEvent('open-command-palette'))}
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
            {/* 主题切换：暗色 → 亮色 → 跟随系统 循环 */}
            <Button
              variant="ghost"
              size="icon"
              className="hidden md:inline-flex"
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
