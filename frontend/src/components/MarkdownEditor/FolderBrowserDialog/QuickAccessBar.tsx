/**
 * QuickAccessBar - 快速访问工具栏
 * 提供常用目录的快捷跳转按钮（路径由后端解析，~ 会展开为用户主目录）
 */
import React from 'react';

interface QuickAccessBarProps {
  onNavigate: (path: string) => void;
  /** 当前工作区根目录（作为"工作区"快捷入口） */
  workspacePath?: string;
}

/** 快速访问列表（通用路径，后端会基于实际环境解析） */
const QUICK_ACCESS_ITEMS: QuickAccessItem[] = [
  { name: '根目录', path: '/', icon: '💻' },
  { name: 'Home', path: '~', icon: '🏠' },
  { name: 'Desktop', path: '~/Desktop', icon: '🖥️' },
  { name: 'Documents', path: '~/Documents', icon: '📁' },
  { name: 'Downloads', path: '~/Downloads', icon: '📥' },
];

/** 快速访问项定义 */
interface QuickAccessItem {
  name: string;
  path: string;
  icon: string;
}

export default function QuickAccessBar({ onNavigate, workspacePath }: QuickAccessBarProps) {
  return (
    <div className="flex items-center gap-1 px-2 shrink-0">
      {QUICK_ACCESS_ITEMS.map((item) => (
        <button
          key={item.name}
          onClick={() => onNavigate(item.path)}
          className="px-2 py-1 text-xs text-ink-muted hover:text-accent-cyan rounded hover:bg-surface-2 transition-colors cursor-pointer whitespace-nowrap"
          title={item.path}
        >
          <span className="mr-1">{item.icon}</span>
          {item.name}
        </button>
      ))}
      {workspacePath && (
        <button
          onClick={() => onNavigate(workspacePath)}
          className="px-2 py-1 text-xs text-ink-muted hover:text-accent-cyan rounded hover:bg-surface-2 transition-colors cursor-pointer whitespace-nowrap"
          title={workspacePath}
        >
          <span className="mr-1">📂</span>
          工作区
        </button>
      )}
    </div>
  );
}
