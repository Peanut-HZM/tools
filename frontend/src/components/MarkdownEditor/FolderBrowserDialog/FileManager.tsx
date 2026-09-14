/**
 * FileManager - 文件管理器核心组件
 * 整合 QuickAccessBar、PathInput、FileList、FileContextMenu
 * 支持浏览任意路径、分页、右键操作
 */
import React, { useState, useCallback, useEffect } from 'react';
import {
  browseFileManager,
  copyFileItem,
  moveFileItem,
  renameFileManagerItem,
  deleteFileManagerItem,
  createFileManagerItem,
  getDownloadUrl,
} from '../../../api/markdownEditorApi';
import type { FileManagerItem, BreadcrumbItem } from '../../../types/markdownEditor';
import FileList from './FileList';
import FileContextMenu from './FileContextMenu';
import QuickAccessBar from './QuickAccessBar';
import PathInput from './PathInput';

interface FileManagerProps {
  onConfirm: (path: string) => void;
  initialPath?: string;
}

export default function FileManager({ onConfirm, initialPath = '' }: FileManagerProps) {
  const [currentPath, setCurrentPath] = useState(initialPath);
  const [pathInput, setPathInput] = useState(initialPath);
  const [items, setItems] = useState<FileManagerItem[]>([]);
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [page, setPage] = useState(1);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; item: FileManagerItem } | null>(null);

  /** 加载目录 */
  const loadDirectory = useCallback(async (path: string, pageNum: number = 1) => {
    setLoading(true);
    setError(null);
    try {
      const result = await browseFileManager(path, pageNum);
      setItems(result.items);
      setBreadcrumbs(result.breadcrumbs);
      setHasMore(result.has_more);
      setCurrentPath(result.current_path);
      setPathInput(result.current_path);
      setPage(pageNum);
      setSelectedItems([]);
    } catch (e) {
      const message = e instanceof Error ? e.message : '加载目录失败';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  /** 初始加载 */
  useEffect(() => {
    loadDirectory(initialPath || '');
  }, [initialPath, loadDirectory]);

  /** 路径输入跳转 */
  const handlePathSubmit = useCallback(() => {
    loadDirectory(pathInput);
  }, [pathInput, loadDirectory]);

  /** 快速访问导航 */
  const handleQuickAccess = useCallback((path: string) => {
    loadDirectory(path);
  }, [loadDirectory]);

  /** 选择文件 */
  const handleSelect = useCallback((path: string) => {
    setSelectedItems([path]);
  }, []);

  /** 双击打开 */
  const handleDoubleClick = useCallback((item: FileManagerItem) => {
    if (item.type === 'directory') {
      loadDirectory(item.path);
    } else if (item.is_previewable) {
      window.open(getDownloadUrl(item.path), '_blank');
    }
  }, [loadDirectory]);

  /** 右键菜单 */
  const handleContextMenu = useCallback((e: React.MouseEvent, item: FileManagerItem) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, item });
  }, []);

  /** 返回上层 */
  const handleGoUp = useCallback(() => {
    if (!currentPath || currentPath === '/') return;
    const parts = currentPath.split('/');
    parts.pop();
    const parentPath = parts.join('/') || '/';
    loadDirectory(parentPath);
  }, [currentPath, loadDirectory]);

  /** 右键菜单操作 */
  const handleMenuAction = useCallback(async (action: string, item: FileManagerItem) => {
    try {
      switch (action) {
        case 'open':
          if (item.type === 'directory') {
            loadDirectory(item.path);
          } else if (item.is_previewable) {
            window.open(getDownloadUrl(item.path), '_blank');
          }
          break;
        case 'rename': {
          const newName = prompt('新名称:', item.name);
          if (newName && newName !== item.name) {
            const result = await renameFileManagerItem(item.path, newName);
            if (result.success) {
              loadDirectory(currentPath);
            } else {
              alert(result.message || '重命名失败');
            }
          }
          break;
        }
        case 'delete':
          if (confirm(`确定删除 ${item.name}?`)) {
            const result = await deleteFileManagerItem(item.path);
            if (result.success) {
              loadDirectory(currentPath);
            } else {
              alert(result.message || '删除失败');
            }
          }
          break;
        case 'copy': {
          const copyTarget = prompt('复制到:', item.path + '_copy');
          if (copyTarget) {
            const result = await copyFileItem(item.path, copyTarget);
            if (result.success) {
              alert('复制成功');
            } else {
              alert(result.message || '复制失败');
            }
          }
          break;
        }
        case 'move': {
          const moveTarget = prompt('移动到:', item.path);
          if (moveTarget && moveTarget !== item.path) {
            const result = await moveFileItem(item.path, moveTarget);
            if (result.success) {
              alert('移动成功');
              loadDirectory(currentPath);
            } else {
              alert(result.message || '移动失败');
            }
          }
          break;
        }
        case 'download':
          window.open(getDownloadUrl(item.path), '_blank');
          break;
        case 'newFolder': {
          const folderName = prompt('文件夹名称:');
          if (folderName) {
            const result = await createFileManagerItem(currentPath, folderName, 'directory');
            if (result.success) {
              loadDirectory(currentPath);
            } else {
              alert(result.message || '创建失败');
            }
          }
          break;
        }
        case 'newFile': {
          const fileName = prompt('文件名称:');
          if (fileName) {
            const result = await createFileManagerItem(currentPath, fileName, 'file');
            if (result.success) {
              loadDirectory(currentPath);
            } else {
              alert(result.message || '创建失败');
            }
          }
          break;
        }
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : '操作失败';
      alert(message);
    }
  }, [currentPath, loadDirectory]);

  /** 确认选择 */
  const handleConfirm = useCallback(() => {
    if (selectedItems.length > 0) {
      onConfirm(selectedItems[0]);
    } else {
      onConfirm(currentPath);
    }
  }, [selectedItems, currentPath, onConfirm]);

  return (
    <div className="flex flex-col h-full">
      {/* 工具栏 */}
      <div className="flex items-center gap-2 px-2 py-2 border-b border-border bg-surface-2/30">
        <button
          onClick={handleGoUp}
          disabled={!currentPath || currentPath === '/'}
          className="px-2 py-1 text-sm text-ink-muted hover:text-ink disabled:opacity-30 cursor-pointer disabled:cursor-default rounded hover:bg-surface-2 transition-colors"
          title="返回上层目录"
        >
          ← 返回
        </button>
        <QuickAccessBar onNavigate={handleQuickAccess} />
        <PathInput
          value={pathInput}
          onChange={setPathInput}
          onSubmit={handlePathSubmit}
          loading={loading}
        />
      </div>

      {/* 面包屑 */}
      <div className="flex items-center gap-1 px-3 py-1.5 text-sm text-ink-muted border-b border-border overflow-x-auto">
        {breadcrumbs.map((crumb, i) => (
          <React.Fragment key={crumb.path || 'root'}>
            {i > 0 && <span className="text-ink-faint shrink-0">/</span>}
            <button
              onClick={() => loadDirectory(crumb.path)}
              className={`hover:text-accent-cyan cursor-pointer transition-colors whitespace-nowrap ${
                crumb.path === currentPath ? 'text-ink font-medium' : ''
              }`}
            >
              {crumb.name}
            </button>
          </React.Fragment>
        ))}
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="px-3 py-1.5 text-sm text-danger bg-danger/10 border-b border-danger/30">
          {error}
        </div>
      )}

      {/* 文件列表 */}
      <FileList
        items={items}
        selectedItems={selectedItems}
        onSelect={handleSelect}
        onDoubleClick={handleDoubleClick}
        onContextMenu={handleContextMenu}
        loading={loading}
      />

      {/* 加载更多 */}
      {hasMore && (
        <button
          onClick={() => loadDirectory(currentPath, page + 1)}
          className="w-full py-2 text-sm text-ink-muted hover:text-accent-cyan transition-colors border-t border-border cursor-pointer"
        >
          加载更多...
        </button>
      )}

      {/* 底部确认栏 */}
      <div className="px-3 py-2 border-t border-border flex items-center justify-between">
        <div className="text-sm text-ink-muted truncate flex-1 mr-4">
          <span>已选择: {selectedItems.length > 0 ? selectedItems[0] : currentPath || '(根目录)'}</span>
        </div>
        <button
          onClick={handleConfirm}
          className="px-4 py-1.5 text-sm bg-accent text-ink-inverse rounded cursor-pointer hover:bg-accent-hover transition-colors"
        >
          确认选择
        </button>
      </div>

      {/* 右键菜单 */}
      {contextMenu && (
        <FileContextMenu
          item={contextMenu.item}
          position={{ x: contextMenu.x, y: contextMenu.y }}
          onAction={handleMenuAction}
          onClose={() => setContextMenu(null)}
        />
      )}
    </div>
  );
}
