/**
 * FolderBrowserDialog - 文件夹浏览对话框
 *
 * 「打开文件夹」入口：统一的任意路径浏览器内核（FileManager），
 * 支持进入服务器上的任意目录（含以 . 开头的隐藏目录），
 * 确认后把**绝对路径**回传给调用方作为工作区根目录。
 */
import { useCallback } from 'react';
import FileManager from './FileManager';
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
        className="bg-surface-1 rounded-xl shadow-lg w-[94vw] h-[78vh] max-w-[880px] max-h-[640px] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ===== 标题栏 ===== */}
        <div className="px-4 py-3 border-b border-border flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-ink">选择文件夹</h3>
            <p className="text-xs text-ink-muted mt-0.5">
              可进入任意目录（含以 . 开头的隐藏目录），确认后作为工作区根目录
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-ink-muted hover:text-ink cursor-pointer text-lg shrink-0"
            aria-label="关闭"
          >
            ✕
          </button>
        </div>

        {/* ===== 浏览器内核 ===== */}
        <div className="flex-1 overflow-hidden">
          <FileManager
            onConfirm={onConfirm}
            onCancel={onClose}
            initialPath={rootPath || '/'}
          />
        </div>
      </div>
    </div>
  );
}
