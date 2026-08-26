import { useState } from 'react';
import { OpenTab } from '../../../../stores/httpClientStore';
import { Plus, FileCode, Pencil, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

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
        <Button
          variant="ghost"
          size="sm"
          onClick={onCreateNewRequest}
          className="text-accent-secondary hover:text-accent-secondary"
        >
          <Plus className="w-4 h-4 mr-2" />
          新建请求
        </Button>
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
              ? 'bg-surface-2 text-ink border-t-2 border-t-accent-secondary'
              : 'text-ink-muted hover:bg-surface-2/50 border-t-2 border-t-transparent'
            }
          `}
          onClick={() => onTabClick(tab.requestId)}
        >
          <FileCode
            className={`w-3 h-3 ${
              tab.requestId === activeTabId ? 'text-accent-secondary' : 'text-ink-faint'
            }`}
          />
          {editingId === tab.requestId ? (
            <Input
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
              className="flex-1 h-6 text-sm px-1 py-0.5 min-w-0"
            />
          ) : (
            <>
              <span className="truncate flex-1">{tab.request.name}</span>
              {onRename && (
                <Button
                  variant="ghost"
                  size="icon"
                  title="重命名"
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingId(tab.requestId);
                    setEditingName(tab.request.name);
                  }}
                  className="h-6 w-6 text-ink-faint hover:text-ink-muted"
                >
                  <Pencil className="w-3 h-3" />
                </Button>
              )}
            </>
          )}
          {tab.isModified && (
            <span className="w-2 h-2 bg-warning rounded-full flex-shrink-0"></span>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={(e) => {
              e.stopPropagation();
              onTabClose(tab.requestId);
            }}
            className="h-6 w-6 text-ink-faint hover:text-danger"
          >
            <X className="w-3 h-3" />
          </Button>
        </div>
      ))}
    </div>
  );
}
