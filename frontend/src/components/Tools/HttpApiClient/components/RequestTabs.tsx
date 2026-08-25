import { useState } from 'react';
import { OpenTab } from '../../../../stores/httpClientStore';

interface RequestTabsProps {
  openTabs: OpenTab[];
  activeTabId: string | null;
  onTabClick: (tabId: string) => void;
  onTabClose: (tabId: string) => void;
  onCreateNewRequest?: () => void;
  /** 重命名回调（父组件 updateTabRequest({ name })） */
  onRename?: (requestId: string, name: string) => void;
}

export default function RequestTabs({
  openTabs,
  activeTabId,
  onTabClick,
  onTabClose,
  onCreateNewRequest,
  onRename,
}: RequestTabsProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  // 确认改名：非空时回调父组件
  const handleConfirmRename = () => {
    if (editingId) {
      const trimmed = editingName.trim();
      if (trimmed) {
        onRename?.(editingId, trimmed);
      }
    }
    setEditingId(null);
  };

  if (openTabs.length === 0) {
    return (
      <div className="flex items-center bg-surface-1 border-b border-border px-4 py-2 flex-shrink-0">
        <button
          onClick={onCreateNewRequest}
          className="text-accent-secondary hover:text-accent-secondary transition-colors text-sm"
        >
          <i className="fas fa-plus mr-2"></i>
          新建请求
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center bg-surface-1 border-b border-border overflow-x-auto flex-shrink-0">
      {openTabs.map(tab => (
        <div
          key={tab.requestId}
          className={`
            flex items-center gap-2 px-4 py-2 border-r border-border cursor-pointer
            transition-colors text-sm min-w-[160px] max-w-[240px]
            ${tab.requestId === activeTabId
              ? 'bg-surface-2 text-ink-inverse border-t-2 border-t-accent-secondary'
              : 'text-ink-muted hover:bg-surface-2/50 border-t-2 border-t-transparent'
            }
          `}
          onClick={() => onTabClick(tab.requestId)}
        >
          <i
            className={`fas fa-file-code text-xs ${
              tab.requestId === activeTabId ? 'text-accent-secondary' : 'text-ink-faint'
            }`}
          ></i>
          {editingId === tab.requestId ? (
            <input
              autoFocus
              value={editingName}
              onChange={(e) => setEditingName(e.target.value)}
              onBlur={handleConfirmRename}
              onClick={(e) => e.stopPropagation()}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.stopPropagation();
                  handleConfirmRename();
                }
                if (e.key === 'Escape') {
                  e.stopPropagation();
                  setEditingId(null);
                  setEditingName('');
                }
              }}
              className="flex-1 bg-canvas text-ink-inverse text-sm px-1 py-0.5 rounded
                         border border-accent-secondary focus:outline-none min-w-0"
            />
          ) : (
            <>
              <span className="truncate flex-1">{tab.request.name}</span>
              {onRename && (
                <button
                  title="重命名"
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingId(tab.requestId);
                    setEditingName(tab.request.name);
                  }}
                  className="text-ink-faint hover:text-ink-muted transition-colors text-xs"
                >
                  <i className="fas fa-pencil"></i>
                </button>
              )}
            </>
          )}
          {tab.isModified && (
            <span className="w-2 h-2 bg-yellow-500 rounded-full flex-shrink-0"></span>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onTabClose(tab.requestId);
            }}
            className="text-ink-faint hover:text-danger transition-colors text-xs"
          >
            <i className="fas fa-times"></i>
          </button>
        </div>
      ))}
    </div>
  );
}
