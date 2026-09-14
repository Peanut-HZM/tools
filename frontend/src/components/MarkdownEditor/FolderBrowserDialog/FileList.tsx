/**
 * FileList - 文件列表组件
 * 展示当前目录下的文件和文件夹列表，含表头和加载/空状态
 */
import React from 'react';
import type { FileManagerItem } from '../../../types/markdownEditor';
import FileItemRow from './FileItemRow';

interface FileListProps {
  items: FileManagerItem[];
  selectedItems: string[];
  onSelect: (path: string) => void;
  onDoubleClick: (item: FileManagerItem) => void;
  onContextMenu: (e: React.MouseEvent, item: FileManagerItem) => void;
  loading?: boolean;
}

export default function FileList({
  items,
  selectedItems,
  onSelect,
  onDoubleClick,
  onContextMenu,
  loading,
}: FileListProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-32 text-ink-muted">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-accent mr-2"></div>
        加载中...
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-8 text-ink-muted">
        空目录
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto">
      {/* 表头 */}
      <div className="flex items-center gap-2 px-3 py-2 text-xs text-ink-faint border-b border-border bg-surface-2/30 sticky top-0">
        <span className="shrink-0 w-6"></span>
        <span className="flex-1">名称</span>
        <span className="text-xs w-20 text-right">类型</span>
        <span className="text-xs w-24 text-right">大小</span>
        <span className="text-xs w-32 text-right">修改时间</span>
      </div>
      {/* 文件列表 */}
      {items.map((item) => (
        <FileItemRow
          key={item.path}
          item={item}
          isSelected={selectedItems.includes(item.path)}
          onSelect={onSelect}
          onDoubleClick={onDoubleClick}
          onContextMenu={onContextMenu}
        />
      ))}
    </div>
  );
}
