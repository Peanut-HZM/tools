/**
 * FileManager - 文件管理器核心组件
 * 整合 QuickAccessBar、PathInput、FileList、FileContextMenu
 *
 * 「打开文件夹」对话框的浏览内核，能力要求：
 * - 可进入服务器上的**任意**目录（绝对路径 / ~ / 相对路径），不局限于工作区根目录
 * - 隐藏文件与隐藏目录可见（可一键切换显示/隐藏）
 * - 确认时回传**绝对路径**，直接作为工作区根目录（避免相对路径导致打开失败）
 */
import React, { useState, useCallback, useEffect, useRef } from 'react';
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
import { ensureFileExtension, resolveRenameName } from '../../../utils/filenameUtils';

interface FileManagerProps {
  /** 确认选择：回传绝对路径 */
  onConfirm: (path: string) => void;
  /** 取消（可选） */
  onCancel?: () => void;
  /** 初始路径（通常是当前工作区根目录） */
  initialPath?: string;
}

/** 每页加载数量 */
const PAGE_SIZE = 200;

/** 计算父目录（兼容 POSIX 与 Windows 盘符） */
function getParentPath(currentPath: string): string | null {
  if (!currentPath) return null;
  const trimmed = currentPath.replace(/\\/g, '/').replace(/\/+$/, '');
  if (!trimmed) return null;

  // Windows 盘符根（C: / C:/）没有上一层
  if (/^[A-Za-z]:$/.test(trimmed)) return null;

  const idx = trimmed.lastIndexOf('/');
  if (idx < 0) return '/';
  if (idx === 0) return '/';

  const parent = trimmed.slice(0, idx);
  // 盘符根（如 "C:"）需要补回斜杠，否则会被当成相对路径
  return /^[A-Za-z]:$/.test(parent) ? `${parent}/` : parent;
}

export default function FileManager({ onConfirm, onCancel, initialPath = '' }: FileManagerProps) {
  const [currentPath, setCurrentPath] = useState(initialPath);
  const [pathInput, setPathInput] = useState(initialPath);
  const [items, setItems] = useState<FileManagerItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<FileManagerItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [page, setPage] = useState(1);
  const [includeHidden, setIncludeHidden] = useState(true);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; item: FileManagerItem } | null>(null);

  /**
   * include_hidden 通过 ref 读取：让 loadDirectory 保持稳定引用，
   * 避免切换"显示隐藏文件"时重复触发初始加载 effect。
   */
  const includeHiddenRef = useRef(includeHidden);
  includeHiddenRef.current = includeHidden;

  /** 加载目录（成功返回 true，失败返回 false） */
  const loadDirectory = useCallback(async (path: string, pageNum: number = 1, append: boolean = false): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      const result = await browseFileManager(path, pageNum, PAGE_SIZE, includeHiddenRef.current);
      // 加载更多是追加，不是替换（否则"加载更多"会丢掉前面的内容）
      setItems((prev) => (append && pageNum > 1 ? [...prev, ...result.items] : result.items));
      setBreadcrumbs(result.breadcrumbs);
      setHasMore(result.has_more);
      setCurrentPath(result.current_path);
      setPathInput(result.current_path);
      setPage(pageNum);
      if (!append) {
        setSelectedItem(null);
      }
      return true;
    } catch (e) {
      const message = e instanceof Error ? e.message : '加载目录失败';
      setError(message);
      if (!append) {
        setItems([]);
        setBreadcrumbs([]);
        setHasMore(false);
      }
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * 初始加载。
   * 配置的工作区目录若已被外部删除，自动回退到文件系统根目录，
   * 保证「打开文件夹」在任何时候都能进入任意目录。
   */
  useEffect(() => {
    let cancelled = false;
    const target = initialPath || '/';
    void (async () => {
      const ok = await loadDirectory(target);
      if (!ok && !cancelled && target !== '/') {
        await loadDirectory('/');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [initialPath, loadDirectory]);

  /** 路径输入跳转 */
  const handlePathSubmit = useCallback(() => {
    const target = pathInput.trim();
    if (!target) return;
    loadDirectory(target);
  }, [pathInput, loadDirectory]);

  /** 快速访问导航 */
  const handleQuickAccess = useCallback((path: string) => {
    loadDirectory(path);
  }, [loadDirectory]);

  /** 切换隐藏文件显示 */
  const handleToggleHidden = useCallback(() => {
    const next = !includeHidden;
    setIncludeHidden(next);
    includeHiddenRef.current = next;
    loadDirectory(currentPath);
  }, [includeHidden, currentPath, loadDirectory]);

  /** 选择条目（文件夹可选为工作区根目录） */
  const handleSelect = useCallback((item: FileManagerItem) => {
    setSelectedItem(item);
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
    const parent = getParentPath(currentPath);
    if (!parent) return;
    loadDirectory(parent);
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
            // 文件改名时沿用原扩展名（输入带扩展名则原样使用）；文件夹保持原样
            const finalName =
              item.type === 'directory' ? newName : resolveRenameName(newName, item.name);
            const result = await renameFileManagerItem(item.path, finalName);
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
            // 仅当文件名完全没有扩展名时才默认补 .md，已有扩展名的保持原样
            const result = await createFileManagerItem(
              currentPath,
              ensureFileExtension(fileName),
              'file'
            );
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

  /** 确认目标：优先选中的文件夹，否则为当前目录 */
  const confirmTarget =
    selectedItem && selectedItem.type === 'directory' ? selectedItem.path : currentPath;
  /** 选中了文件时不能作为工作区根目录 */
  const blockedByFile = !!selectedItem && selectedItem.type === 'file';

  /** 确认选择 */
  const handleConfirm = useCallback(() => {
    if (blockedByFile) return;
    if (!confirmTarget) return;
    onConfirm(confirmTarget);
  }, [blockedByFile, confirmTarget, onConfirm]);

  return (
    <div className="flex flex-col h-full">
      {/* 工具栏 */}
      <div className="flex items-center gap-2 px-2 py-2 border-b border-border bg-surface-2/30">
        <button
          onClick={handleGoUp}
          disabled={!currentPath || !getParentPath(currentPath)}
          className="px-2 py-1 text-sm text-ink-muted hover:text-ink disabled:opacity-30 cursor-pointer disabled:cursor-default rounded hover:bg-surface-2 transition-colors shrink-0"
          title="返回上层目录"
        >
          ← 上层
        </button>
        <QuickAccessBar onNavigate={handleQuickAccess} workspacePath={initialPath} />
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
              title={crumb.path}
            >
              {crumb.name}
            </button>
          </React.Fragment>
        ))}
      </div>

      {/* 显示隐藏文件开关 */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-border bg-surface-2/20">
        <label className="flex items-center gap-2 text-xs text-ink-muted cursor-pointer select-none">
          <input
            type="checkbox"
            checked={includeHidden}
            onChange={handleToggleHidden}
            className="accent-accent-cyan cursor-pointer"
          />
          显示隐藏文件（以 . 开头）
        </label>
        <span className="text-xs text-ink-faint">
          共 {items.length} 项{breadcrumbs.length > 0 ? ` · ${currentPath}` : ''}
        </span>
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
        selectedItems={selectedItem ? [selectedItem.path] : []}
        onSelect={handleSelect}
        onDoubleClick={handleDoubleClick}
        onContextMenu={handleContextMenu}
        loading={loading}
      />

      {/* 加载更多 */}
      {hasMore && (
        <button
          onClick={() => loadDirectory(currentPath, page + 1, true)}
          className="w-full py-2 text-sm text-ink-muted hover:text-accent-cyan transition-colors border-t border-border cursor-pointer"
        >
          加载更多...
        </button>
      )}

      {/* 底部确认栏 */}
      <div className="px-3 py-2 border-t border-border flex items-center justify-between gap-2">
        <div className="text-sm text-ink-muted truncate flex-1 mr-4">
          {blockedByFile ? (
            <span className="text-danger">只能选择文件夹（当前选中的是文件）</span>
          ) : (
            <span title={confirmTarget}>将打开: {confirmTarget || '(未知路径)'}</span>
          )}
        </div>
        <div className="flex gap-2 shrink-0">
          {onCancel && (
            <button
              onClick={onCancel}
              className="px-4 py-1.5 text-sm text-ink-muted hover:text-ink cursor-pointer rounded hover:bg-surface-2 transition-colors"
            >
              取消
            </button>
          )}
          <button
            onClick={handleConfirm}
            disabled={blockedByFile || !confirmTarget}
            className="px-4 py-1.5 text-sm bg-accent text-ink-inverse rounded cursor-pointer hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-default"
          >
            选择此文件夹
          </button>
        </div>
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
