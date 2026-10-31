/**
 * StorageNoticeBar - 无远程服务器时的提示条
 */
import React from 'react';

interface StorageNoticeBarProps {
  serverAvailable: boolean;
  localPath: string;
  /** 清空本地数据回调（可选） */
  onClearLocalData?: () => void;
}

const StorageNoticeBar: React.FC<StorageNoticeBarProps> = ({
  serverAvailable,
  localPath,
  onClearLocalData,
}) => {
  if (serverAvailable) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-2 mb-2 rounded border border-accent-info/50 bg-accent-info/10 text-xs text-ink-muted">
      <span>ℹ️</span>
      <span className="flex-1">
        当前未配置远程服务器，所有凭据将仅保存在本机
        {localPath && <span className="ml-1 text-ink-faint">（{localPath}）</span>}
      </span>
      {onClearLocalData && (
        <button
          onClick={onClearLocalData}
          className="px-2 py-1 rounded border border-border hover:border-accent-danger text-ink-faint hover:text-accent-danger"
        >
          清空本地数据
        </button>
      )}
    </div>
  );
};

export default StorageNoticeBar;
