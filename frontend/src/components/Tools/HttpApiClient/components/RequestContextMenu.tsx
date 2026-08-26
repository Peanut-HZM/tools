/**
 * 请求右键菜单
 */

import { useState, useEffect, useRef } from 'react';
import { HttpRequest, Collection } from '../../../../services/httpClientApi';
import { Pencil, Copy, ChevronRight, Trash2, Folder } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface ContextMenuProps {
  request: HttpRequest;
  collections: Collection[];
  x: number;
  y: number;
  onRename?: (request: HttpRequest) => void;
  onDuplicate: (request: HttpRequest, targetCollectionId: string) => void;
  onDelete: (requestId: string) => void;
  onClose: () => void;
}

export default function RequestContextMenu({
  request,
  collections,
  x,
  y,
  onRename,
  onDuplicate,
  onDelete,
  onClose,
}: ContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const [showSubmenu, setShowSubmenu] = useState(false);
  const [subX, setSubX] = useState(0);
  const [subY, setSubY] = useState(0);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  const handleDuplicateClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowSubmenu(true);
    const rect = (e.target as HTMLElement).getBoundingClientRect();
    setSubX(rect.left - 180);
    setSubY(rect.top);
  };

  const handleDuplicate = (targetCollectionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onDuplicate(request, targetCollectionId);
    onClose();
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm(`确定删除请求 "${request.name}" 吗？`)) {
      onDelete(request.id);
      onClose();
    }
  };

  return (
    <>
      <div
        ref={menuRef}
        className="fixed z-[9999] bg-surface-1 border border-border rounded-lg shadow-md py-1 min-w-[160px]"
        style={{ left: x, top: y }}
      >
        {/* 重命名请求 */}
        {onRename && (
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onRename(request);
              onClose();
            }}
            className="w-full justify-start rounded-none px-4 py-2 text-sm font-normal"
          >
            <Pencil className="w-4 h-4 mr-2 text-ink-faint" />
            重命名
          </Button>
        )}

        {/* 复制请求 */}
        <div className="relative">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDuplicateClick}
            className="w-full justify-start rounded-none px-4 py-2 text-sm font-normal flex justify-between"
          >
            <span>
              <Copy className="w-4 h-4 mr-2 text-ink-faint inline" />
              复制请求
            </span>
            <ChevronRight className="w-3 h-3 text-ink-faint" />
          </Button>
        </div>

        {/* 删除请求 */}
        <Button
          variant="ghost"
          size="sm"
          onClick={handleDelete}
          className="w-full justify-start rounded-none px-4 py-2 text-sm font-normal text-danger hover:bg-danger/10 hover:text-danger"
        >
          <Trash2 className="w-4 h-4 mr-2" />
          删除请求
        </Button>
      </div>

      {/* 复制目标集合子菜单 */}
      {showSubmenu && (
        <div
          className="fixed z-[9999] bg-surface-1 border border-border rounded-lg shadow-md py-1 min-w-[180px]"
          style={{ left: subX, top: subY }}
        >
          {collections.length === 0 ? (
            <div className="px-4 py-2 text-xs text-ink-faint">暂无集合</div>
          ) : (
            collections.map(c => (
              <Button
                key={c.id}
                variant="ghost"
                size="sm"
                onClick={(e) => handleDuplicate(c.id, e)}
                className="w-full justify-start rounded-none px-4 py-2 text-sm font-normal"
              >
                <Folder className="w-3 h-3 mr-2 text-ink-faint" />
                <span className="truncate">{c.name}</span>
              </Button>
            ))
          )}
        </div>
      )}
    </>
  );
}
