import React from 'react';
import { User, Shield, Settings } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';
import { AccountSection, NavItem } from './types';

interface AccountSidebarProps {
  activeSection: AccountSection;
  onSectionChange: (section: AccountSection) => void;
}

const navItems: Array<NavItem> = [
  {
    id: 'basic',
    label: '基本信息',
    description: '查看您的个人信息',
    icon: <User className="w-5 h-5" />,
  },
  {
    id: 'security',
    label: '安全设置',
    description: '管理密码和安全选项',
    icon: <Shield className="w-5 h-5" />,
  },
  {
    id: 'preferences',
    label: '偏好设置',
    description: '自定义使用偏好',
    icon: <Settings className="w-5 h-5" />,
  },
];

export default function AccountSidebar({ activeSection, onSectionChange }: AccountSidebarProps) {
  return (
    <>
      {/* Desktop 侧边栏 - lg 及以上 */}
      <aside className="hidden lg:block w-72 flex-shrink-0">
        <nav className="space-y-2">
          {navItems.map((item) => (
            <Button
              key={item.id}
              onClick={() => onSectionChange(item.id)}
              variant={activeSection === item.id ? 'outline' : 'ghost'}
              className={cn(
                'w-full justify-start gap-3 h-auto py-3 px-4 text-left',
                activeSection === item.id
                  ? // 激活态：品牌渐变底 + 发光阴影的玻璃 chip（透明描边避免与渐变打架）
                    'text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)] border-transparent'
                  : // 非激活态：弱化文字色，hover 提亮玻璃底
                    'text-ink-muted hover:text-ink hover:bg-glass-bg border border-glass-border'
              )}
              type="button"
            >
              <span className={cn(
                'flex-shrink-0 mt-0.5',
                // 激活 chip 为渐变底，图标改用白色保证对比度
                activeSection === item.id ? 'text-white' : 'text-ink-faint'
              )}>
                {item.icon}
              </span>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm">{item.label}</div>
                <div className={cn(
                  'text-xs mt-0.5',
                  // 激活 chip 为渐变底，描述文字用半透明白保证可读性
                  activeSection === item.id ? 'text-white/70' : 'text-ink-faint'
                )}>
                  {item.description}
                </div>
              </div>
            </Button>
          ))}
        </nav>
      </aside>

      {/* Tablet/Mobile 顶部标签页 */}
      <div className="lg:hidden w-full">
        <nav className="flex gap-2 overflow-x-auto pb-2">
          {navItems.map((item) => (
            <Button
              key={item.id}
              onClick={() => onSectionChange(item.id)}
              variant={activeSection === item.id ? 'outline' : 'ghost'}
              className={cn(
                'flex-shrink-0 whitespace-nowrap rounded-full',
                activeSection === item.id
                  ? // 激活态：品牌渐变底 + 发光阴影的玻璃 chip（透明描边避免与渐变打架）
                    'text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)] border-transparent'
                  : // 非激活态：弱化文字色，hover 提亮玻璃底
                    'text-ink-muted hover:text-ink hover:bg-glass-bg border border-glass-border'
              )}
              type="button"
            >
              {item.label}
            </Button>
          ))}
        </nav>
      </div>
    </>
  );
}
