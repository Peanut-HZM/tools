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
      <div className="flex items-center bg-slate-800 border-b border-slate-700 px-4 py-2 flex-shrink-0">
        <button
          onClick={onCreateNewRequest}
          className="text-purple-400 hover:text-purple-300 transition-colors text-sm"
        >
          <i className="fas fa-plus mr-2"></i>
          新建请求
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center bg-slate-800 border-b border-slate-700 overflow-x-auto flex-shrink-0">
      {openTabs.map(tab => (
        <div
          key={tab.requestId}
          className={`
            flex items-center gap-2 px-4 py-2 border-r border-slate-700 cursor-pointer
            transition-colors text-sm min-w-[160px] max-w-[240px]
            ${tab.requestId === activeTabId
              ? 'bg-slate-700 text-white border-t-2 border-t-purple-500'
              : 'text-slate-400 hover:bg-slate-700/50 border-t-2 border-t-transparent'
            }
          `}
          onClick={() => onTabClick(tab.requestId)}
        >
          <i
            className={`fas fa-file-code text-xs ${
              tab.requestId === activeTabId ? 'text-purple-400' : 'text-slate-500'
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
                }
              }}
              className="flex-1 bg-slate-900 text-white text-sm px-1 py-0.5 rounded
                         border border-purple-500 focus:outline-none min-w-0"
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
                  className="text-slate-500 hover:text-slate-300 transition-colors text-xs"
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
            className="text-slate-500 hover:text-red-400 transition-colors text-xs"
          >
            <i className="fas fa-times"></i>
          </button>
        </div>
      ))}
    </div>
  );
}
