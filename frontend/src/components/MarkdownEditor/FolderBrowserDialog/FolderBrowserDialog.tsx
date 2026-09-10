/**
 * FolderBrowserDialog - 文件夹浏览对话框
 * 单栏目录列表布局
 * 支持面包屑导航、返回上层、手动路径输入
 */
import { useState, useEffect, useCallback } from 'react';
import { browseDirectories } from '../../../api/markdownEditorApi';
import type {
  DirectoryBrowseData,
  DirectoryItem,
  BreadcrumbItem,
} from '../../../types/markdownEditor';
import './FolderBrowserDialog.css';

// ==================== Props ====================

interface FolderBrowserDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (path: string) => void;
  rootPath: string;
}

// ==================== 主组件 ====================

export default function FolderBrowserDialog({
  open,
  onClose,
  onConfirm,
  rootPath,
}: FolderBrowserDialogProps) {
  const [currentPath, setCurrentPath] = useState('');
  const [data, setData] = useState<DirectoryBrowseData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showManualInput, setShowManualInput] = useState(false);
  const [manualPath, setManualPath] = useState('');
  const [selectedDirPath, setSelectedDirPath] = useState('');

  /** 加载指定路径的目录内容 */
  const loadDirectory = useCallback(async (path: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await browseDirectories(path);
      setData(result);
      setCurrentPath(result.current_path);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : '加载目录失败';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  /** 对话框打开时初始化 */
  useEffect(() => {
    if (open) {
      loadDirectory('');
      setShowManualInput(false);
      setManualPath('');
      setSelectedDirPath('');
    }
  }, [open, loadDirectory]);

  /** 点击左侧目录项 */
  const handleSelectDir = useCallback(
    (dirPath: string) => {
      setSelectedDirPath(dirPath);
      loadDirectory(dirPath);
    },
    [loadDirectory],
  );

  /** 返回上层目录 */
  const handleGoUp = useCallback(() => {
    if (!currentPath) return;
    const parts = currentPath.split('/');
    parts.pop();
    const parentPath = parts.join('/');
    setSelectedDirPath(parentPath);
    loadDirectory(parentPath);
  }, [currentPath, loadDirectory]);

  /** 面包屑导航点击 */
  const handleBreadcrumbClick = useCallback(
    (crumbPath: string) => {
      setSelectedDirPath(crumbPath);
      loadDirectory(crumbPath);
    },
    [loadDirectory],
  );

  /** 确认选择当前文件夹 */
  const handleConfirm = useCallback(() => {
    // 如果 currentPath 是 "."（根目录），传空字符串
    const pathToConfirm = currentPath === '.' ? '' : currentPath;
    onConfirm(pathToConfirm);
  }, [currentPath, onConfirm]);

  /** 手动路径确认 */
  const handleManualConfirm = useCallback(() => {
    const trimmed = manualPath.trim();
    if (trimmed) {
      onConfirm(trimmed);
    }
  }, [manualPath, onConfirm]);

  /** 处理遮罩层点击（只在点击遮罩本身时关闭） */
  const handleOverlayClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    },
    [onClose],
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={handleOverlayClick}
    >
      <div
        className="bg-surface-1 rounded-xl shadow-lg w-[700px] h-[520px] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ===== 标题栏 ===== */}
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h3 className="text-lg font-semibold text-ink">选择文件夹</h3>
          <button
            onClick={onClose}
            className="text-ink-muted hover:text-ink cursor-pointer text-lg"
            aria-label="关闭"
          >
            ✕
          </button>
        </div>

        {/* ===== 工具栏：返回上层 + 面包屑 + 手动输入 ===== */}
        <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-surface-2/30">
          <button
            onClick={handleGoUp}
            disabled={!currentPath}
            className="px-2 py-1 text-sm text-ink-muted hover:text-ink disabled:opacity-30 cursor-pointer disabled:cursor-default rounded hover:bg-surface-2 transition-colors"
            title="返回上层目录"
          >
            ← 返回上层
          </button>

          {/* 面包屑导航 */}
          <div className="flex items-center gap-1 text-sm text-ink-muted flex-1 min-w-0 overflow-x-auto">
            {/* 根目录按钮 */}
            <button
              onClick={() => handleBreadcrumbClick('')}
              className={`hover:text-accent-cyan cursor-pointer transition-colors ${
                !currentPath ? 'text-ink font-medium' : ''
              }`}
            >
              根目录
            </button>
            {data?.breadcrumbs.length > 0 && <span className="text-ink-faint">/</span>}
            {data?.breadcrumbs.map((crumb: BreadcrumbItem, i: number) => (
              <span key={crumb.path || 'root'} className="flex items-center gap-1 shrink-0">
                {i > 0 && <span className="text-ink-faint">/</span>}
                <button
                  onClick={() => handleBreadcrumbClick(crumb.path)}
                  className={`hover:text-accent-cyan cursor-pointer transition-colors ${
                    crumb.path === currentPath ? 'text-ink font-medium' : ''
                  }`}
                >
                  {crumb.name}
                </button>
              </span>
            ))}
          </div>

          <button
            onClick={() => setShowManualInput(!showManualInput)}
            className="px-2 py-1 text-xs text-ink-muted hover:text-ink cursor-pointer rounded hover:bg-surface-2 transition-colors shrink-0"
          >
            {showManualInput ? '收起' : '手动输入'}
          </button>
        </div>

        {/* ===== 手动路径输入（条件显示） ===== */}
        {showManualInput && (
          <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-surface-2/20">
            <input
              type="text"
              value={manualPath}
              onChange={(e) => setManualPath(e.target.value)}
              placeholder="输入文件夹路径，例如 /home/user/docs"
              className="flex-1 px-2 py-1.5 text-sm bg-surface-2 border border-border rounded text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-accent-cyan/50"
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleManualConfirm();
              }}
            />
            <button
              onClick={handleManualConfirm}
              className="px-3 py-1.5 text-sm bg-accent text-ink-inverse rounded cursor-pointer hover:bg-accent-hover transition-colors"
            >
              确认
            </button>
          </div>
        )}

        {/* ===== 内容区：目录列表 ===== */}
        <div className="flex-1 overflow-auto">
            {loading ? (
              <LoadingState />
            ) : error ? (
              <ErrorState message={error} />
            ) : (
              <>
                {data?.directories.map((dir: DirectoryItem) => (
                  <DirectoryItemRow
                    key={dir.path}
                    dir={dir}
                    isSelected={dir.path === selectedDirPath}
                    onSelect={handleSelectDir}
                  />
                ))}
                {data?.directories.length === 0 && (
                  <EmptyState text="无子目录" />
                )}
              </>
            )}
        </div>

        {/* ===== 底部：路径信息 + 操作按钮 ===== */}
        <div className="px-4 py-3 border-t border-border flex items-center justify-between">
          <div className="text-sm text-ink-muted truncate flex-1 mr-4">
            {rootPath && (
              <span className="mr-3">根目录: {rootPath}</span>
            )}
            <span>已选择: /{currentPath || '(根目录)'}</span>
          </div>
          <div className="flex gap-2 shrink-0">
            <button
              onClick={onClose}
              className="px-4 py-1.5 text-sm text-ink-muted hover:text-ink cursor-pointer rounded hover:bg-surface-2 transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleConfirm}
              className="px-4 py-1.5 text-sm bg-accent text-ink-inverse rounded cursor-pointer hover:bg-accent-hover transition-colors"
            >
              选择此文件夹
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==================== 子组件 ====================

/** 目录列表行 */
interface DirectoryItemRowProps {
  dir: DirectoryItem;
  isSelected: boolean;
  onSelect: (path: string) => void;
}

function DirectoryItemRow({ dir, isSelected, onSelect }: DirectoryItemRowProps) {
  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 text-sm cursor-pointer transition-colors ${
        isSelected
          ? 'bg-accent/20 text-accent-cyan'
          : 'text-ink-muted hover:bg-surface-2'
      }`}
      onClick={() => onSelect(dir.path)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(dir.path);
        }
      }}
    >
      <span className="shrink-0">📁</span>
      <span className="truncate flex-1">{dir.name}</span>
      {dir.has_children && (
        <span className="text-xs text-ink-faint shrink-0">▸</span>
      )}
    </div>
  );
}

/** 加载状态 */
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full text-ink-muted text-sm">
      <div className="folder-browser-spinner mr-2" />
      加载中...
    </div>
  );
}

/** 错误状态 */
function ErrorState({ message }: { message: string }) {
  return (
    <div className="text-danger text-sm p-4">{message}</div>
  );
}

/** 空状态 */
function EmptyState({ text }: { text: string }) {
  return (
    <div className="text-ink-muted text-sm text-center py-8">{text}</div>
  );
}
