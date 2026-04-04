import { OpenTab } from '../../../../stores/httpClientStore';
import { HttpRequest } from '../../../../services/httpClientApi';

interface RequestTabsProps {
  openTabs: OpenTab[];
  activeTabId: string | null;
  onTabClick: (tabId: string) => void;
  onTabClose: (tabId: string) => void;
  onCreateNewRequest?: () => void;
}

export default function RequestTabs({
  openTabs,
  activeTabId,
  onTabClick,
  onTabClose,
  onCreateNewRequest,
}: RequestTabsProps) {
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
          <span className="truncate flex-1">{tab.request.name}</span>
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
