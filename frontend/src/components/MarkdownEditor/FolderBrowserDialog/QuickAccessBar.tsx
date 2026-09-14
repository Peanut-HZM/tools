/**
 * QuickAccessBar - 快速访问工具栏
 * 提供常用目录的快捷跳转按钮
 */
import React from 'react';

interface QuickAccessBarProps {
  onNavigate: (path: string) => void;
}

/** 快速访问项定义 */
interface QuickAccessItem {
  name: string;
  path: string;
  icon: string;
}

/** 快速访问列表（通用路径，后端会基于实际环境解析） */
const QUICK_ACCESS_ITEMS: QuickAccessItem[] = [
  { name: 'Home', path: '~', icon: '🏠' },
  { name: 'Desktop', path: '~/Desktop', icon: '🖥️' },
  { name: 'Documents', path: '~/Documents', icon: '📁' },
  { name: 'Downloads', path: '~/Downloads', icon: '📥' },
  { name: 'Projects', path: '~/Projects', icon: '📝' },
];

export default function QuickAccessBar({ onNavigate }: QuickAccessBarProps) {
  return (
    <div className="flex items-center gap-2 px-2">
      {QUICK_ACCESS_ITEMS.map((item) => (
        <button
          key={item.name}
          onClick={() => onNavigate(item.path)}
          className="px-2 py-1 text-xs text-ink-muted hover:text-accent-cyan rounded hover:bg-surface-2 transition-colors cursor-pointer"
          title={item.path}
        >
          <span className="mr-1">{item.icon}</span>
          {item.name}
        </button>
      ))}
    </div>
  );
}
