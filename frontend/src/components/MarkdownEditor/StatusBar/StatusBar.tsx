/**
 * StatusBar Component - Displays file and editor status
 */
import type { SaveStatus } from '../../../types/markdownEditor';

interface StatusBarProps {
  filePath: string;
  cursorLine: number;
  cursorColumn: number;
  saveStatus: SaveStatus;
  lastSaveTime: Date | null;
}

const statusLabels: Record<SaveStatus, string> = {
  saved: '已保存',
  unsaved: '未保存',
  saving: '保存中...',
  error: '保存失败'
};

const statusColors: Record<SaveStatus, string> = {
  saved: 'text-success',
  unsaved: 'text-accent-warning',
  saving: 'text-accent',
  error: 'text-danger'
};

export default function StatusBar({
  filePath,
  cursorLine,
  cursorColumn,
  saveStatus,
  lastSaveTime
}: StatusBarProps) {
  const formatTime = (date: Date | null) => {
    if (!date) return '';
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <div className="h-6 bg-surface-1 border-t border-border flex items-center justify-between px-4 text-xs text-ink-muted">
      {/* Left side - File path */}
      <div className="flex items-center gap-4">
        <span className="truncate max-w-xs" title={filePath}>
          {filePath || '未选择文件'}
        </span>
      </div>

      {/* Right side - Status info */}
      <div className="flex items-center gap-4">
        {/* Cursor position */}
        <span>
          行 {cursorLine}, 列 {cursorColumn}
        </span>

        {/* Save status */}
        <span className={statusColors[saveStatus]}>
          {statusLabels[saveStatus]}
          {saveStatus === 'saved' && lastSaveTime && (
            <span className="ml-1 text-ink-faint">
              ({formatTime(lastSaveTime)})
            </span>
          )}
        </span>
      </div>
    </div>
  );
}
