import { NavLink, useLocation } from 'react-router-dom';
import { Home, Store, GraduationCap, User } from 'lucide-react';
import { useI18n } from '../../i18n';

/**
 * 移动端底部玻璃 Tab 栏（M1 方案，design.md §7）。
 * 仅 md 以下显示；沉浸路由（/tools/*、/workspace）由 Layout 控制不渲染。
 */
const TABS = [
  { to: '/', key: 'home', Icon: Home, match: (p: string) => p === '/' },
  { to: '/marketplace', key: 'marketplace', Icon: Store, match: (p: string) => p.startsWith('/marketplace') },
  { to: '/courses', key: 'courses', Icon: GraduationCap, match: (p: string) => p.startsWith('/courses') },
  { to: '/account-settings', key: 'profile', Icon: User, match: (p: string) => p.startsWith('/account-settings') },
] as const;

export default function MobileTabBar() {
  const { t } = useI18n();
  const { pathname } = useLocation();
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 px-3 pb-[max(env(safe-area-inset-bottom),0.75rem)] pt-2 pointer-events-none">
      {/* 玻璃浮条：pointer-events 恢复为 auto，两侧留白区不拦截页面点击 */}
      <div className="glass-panel rounded-2xl flex items-stretch justify-around pointer-events-auto">
        {TABS.map(({ to, key, Icon, match }) => {
          const active = match(pathname);
          return (
            <NavLink
              key={to}
              to={to}
              className={`flex flex-col items-center justify-center gap-0.5 min-h-[56px] min-w-[64px] px-3 rounded-xl transition-colors ${
                active ? 'text-accent' : 'text-ink-faint hover:text-ink-muted'
              }`}
            >
              {/* 激活态图标发光（M1 设计稿：紧贴 8px 品牌紫辉光） */}
              <Icon className={`w-5 h-5 ${active ? 'drop-shadow-[0_0_8px_rgba(122,108,255,0.8)]' : ''}`} />
              <span className="text-[10px] leading-none">{t.nav[key]}</span>
              {/* 激活态渐变底标 */}
              {active && <span className="w-6 h-0.5 rounded-full bg-[image:var(--gradient-brand)]" />}
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}
