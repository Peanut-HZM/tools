/**
 * FileContextMenu - 右键菜单组件
 * 根据文件/文件夹类型显示不同的操作菜单
 */
import React, { useEffect, useRef } from 'react';
import type { FileManagerItem } from '../../../types/markdownEditor';

interface FileContextMenuProps {
  item: FileManagerItem;
  position: { x: number; y: number };
  onAction: (action: string, item: FileManagerItem) => void;
  onClose: () => void;
}

/** 菜单项定义 */
interface MenuItem {
  label: string;
  action: string;
}

/** 文件夹的右键菜单项 */
const DIRECTORY_MENU_ITEMS: MenuItem[] = [
  { label: '进入', action: 'open' },
  { label: '新建文件夹', action: 'newFolder' },
  { label: '新建文件', action: 'newFile' },
  { label: '重命名', action: 'rename' },
  { label: '复制', action: 'copy' },
  { label: '移动', action: 'move' },
  { label: '删除', action: 'delete' },
];

/** 文件的右键菜单项 */
const FILE_MENU_ITEMS: MenuItem[] = [
  { label: '打开', action: 'open' },
  { label: '下载', action: 'download' },
  { label: '重命名', action: 'rename' },
  { label: '复制', action: 'copy' },
  { label: '移动', action: 'move' },
  { label: '删除', action: 'delete' },
];

export default function FileContextMenu({
  item,
  position,
  onAction,
  onClose,
}: FileContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  /** 点击菜单外部时关闭 */
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  /** Escape 键关闭 */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const menuItems = item.type === 'directory' ? DIRECTORY_MENU_ITEMS : FILE_MENU_ITEMS;

  return (
    <div
      ref={menuRef}
      className="fixed bg-surface-1 border border-border rounded shadow-lg py-1 z-50 min-w-[140px]"
      style={{ left: position.x, top: position.y }}
    >
      {menuItems.map((menuItem) => (
        <button
          key={menuItem.action}
          onClick={() => {
            onAction(menuItem.action, item);
            onClose();
          }}
          className={`block w-full px-4 py-1.5 text-sm text-left hover:bg-surface-2 transition-colors cursor-pointer ${
            menuItem.action === 'delete' ? 'text-danger' : 'text-ink'
          }`}
        >
          {menuItem.label}
        </button>
      ))}
    </div>
  );
}
