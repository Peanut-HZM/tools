/**
 * 集合右键菜单
 * 仿 RequestContextMenu 模式：固定定位、点击外部关闭
 */

import { useEffect, useRef } from 'react';
import { Pencil, Trash2 } from 'lucide-react';
import { Collection } from '../../../../services/httpClientApi';
import { Button } from '@/components/ui/Button';

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
      className="fixed z-[9999] bg-surface-1 border border-border rounded-lg shadow-md py-1 min-w-[160px]"
      style={{ left: x, top: y }}
    >
      <Button
        variant="ghost"
        size="sm"
        onClick={() => {
          onRename(collection);
          onClose();
        }}
        className="w-full justify-start rounded-none px-4 py-2 text-sm font-normal"
      >
        <Pencil className="w-4 h-4 mr-2 text-ink-faint" />
        重命名
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => {
          onDelete(collection);
          onClose();
        }}
        className="w-full justify-start rounded-none px-4 py-2 text-sm font-normal text-danger hover:bg-danger/10 hover:text-danger"
      >
        <Trash2 className="w-4 h-4 mr-2" />
        删除集合
      </Button>
    </div>
  );
}
