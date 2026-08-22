/**
 * 集合右键菜单
 * 仿 RequestContextMenu 模式：固定定位、点击外部关闭
 */

import { useEffect, useRef } from 'react';
import { Collection } from '../../../../services/httpClientApi';

interface CollectionContextMenuProps {
  collection: Collection;
  x: number;
  y: number;
  onRename: (collection: Collection) => void;
  onDelete: (collection: Collection) => void;
  onClose: () => void;
}

export default function CollectionContextMenu({
  collection,
  x,
  y,
  onRename,
  onDelete,
  onClose,
}: CollectionContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  return (
    <div
      ref={menuRef}
      className="fixed z-[9999] bg-slate-800 border border-slate-700 rounded-lg shadow-xl py-1 min-w-[160px]"
      style={{ left: x, top: y }}
    >
      <button
        onClick={() => {
          onRename(collection);
          onClose();
        }}
        className="w-full text-left px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 flex items-center"
      >
        <i className="fas fa-pencil mr-2 text-slate-500"></i>
        重命名
      </button>
      <button
        onClick={() => {
          onDelete(collection);
          onClose();
        }}
        className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 flex items-center"
      >
        <i className="fas fa-trash mr-2"></i>
        删除集合
      </button>
    </div>
  );
}
