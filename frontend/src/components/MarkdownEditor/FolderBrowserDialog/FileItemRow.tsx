/**
 * FileItemRow - 文件列表项组件
 * 单行文件/文件夹展示，支持选中、双击打开、右键菜单
 */
import React from 'react';
import type { FileManagerItem } from '../../../types/markdownEditor';

interface FileItemRowProps {
  item: FileManagerItem;
  isSelected: boolean;
  onSelect: (path: string) => void;
  onDoubleClick: (item: FileManagerItem) => void;
  onContextMenu: (e: React.MouseEvent, item: FileManagerItem) => void;
}

/** 格式化文件大小 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '-';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

/** 根据文件类型返回图标 */
function getFileIcon(item: FileManagerItem): string {
  if (item.type === 'directory') return '📁';
  if (item.extension === '.md') return '📄';
  if (['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'].includes(item.extension)) return '🖼️';
  if (item.extension === '.pdf') return '📕';
  return '📄';
}

export default function FileItemRow({
  item,
  isSelected,
  onSelect,
  onDoubleClick,
  onContextMenu,
}: FileItemRowProps) {
  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 text-sm cursor-pointer transition-colors border-b border-border/50 ${
        isSelected ? 'bg-accent/20 text-accent-cyan' : 'hover:bg-surface-2'
      }`}
      onClick={() => onSelect(item.path)}
      onDoubleClick={() => onDoubleClick(item)}
      onContextMenu={(e) => onContextMenu(e, item)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(item.path);
        }
      }}
    >
      <span className="shrink-0 w-6 text-center">{getFileIcon(item)}</span>
      <span className="flex-1 truncate">{item.name}</span>
      <span className="text-ink-faint text-xs w-20 text-right">
        {item.type === 'directory' ? '文件夹' : '文件'}
      </span>
      <span className="text-ink-faint text-xs w-24 text-right">
        {item.type === 'directory' ? '-' : formatFileSize(item.size)}
      </span>
      <span className="text-ink-faint text-xs w-32 text-right">
        {new Date(item.modified_at).toLocaleString('zh-CN')}
      </span>
    </div>
  );
}
