/**
 * 请求右键菜单
 */

import { useState, useEffect, useRef } from 'react';
import { HttpRequest, Collection } from '../../../../services/httpClientApi';

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
        className="fixed z-[9999] bg-slate-800 border border-slate-700 rounded-lg shadow-xl py-1 min-w-[160px]"
        style={{ left: x, top: y }}
      >
        {/* 重命名请求 */}
        {onRename && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRename(request);
              onClose();
            }}
            className="w-full text-left px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 flex items-center"
          >
            <i className="fas fa-pencil mr-2 text-slate-500"></i>
            重命名
          </button>
        )}

        {/* 复制请求 */}
        <div className="relative">
          <button
            onClick={handleDuplicateClick}
            className="w-full text-left px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 flex items-center justify-between"
          >
            <span>
              <i className="fas fa-copy mr-2 text-slate-500"></i>
              复制请求
            </span>
            <i className="fas fa-chevron-right text-xs text-slate-600"></i>
          </button>
        </div>

        {/* 删除请求 */}
        <button
          onClick={handleDelete}
          className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 flex items-center"
        >
          <i className="fas fa-trash mr-2"></i>
          删除请求
        </button>
      </div>

      {/* 复制目标集合子菜单 */}
      {showSubmenu && (
        <div
          className="fixed z-[9999] bg-slate-800 border border-slate-700 rounded-lg shadow-xl py-1 min-w-[180px]"
          style={{ left: subX, top: subY }}
        >
          {collections.length === 0 ? (
            <div className="px-4 py-2 text-xs text-slate-500">暂无集合</div>
          ) : (
            collections.map(c => (
              <button
                key={c.id}
                onClick={(e) => handleDuplicate(c.id, e)}
                className="w-full text-left px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 flex items-center"
              >
                <i className="fas fa-folder mr-2 text-slate-500 text-xs"></i>
                <span className="truncate">{c.name}</span>
              </button>
            ))
          )}
        </div>
      )}
    </>
  );
}
