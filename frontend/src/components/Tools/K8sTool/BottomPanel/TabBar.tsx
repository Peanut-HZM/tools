/**
 * 底部面板的标签栏组件
 * 显示所有打开的资源标签，支持切换和关闭
 */
import React from 'react';
import { useK8sStore } from '../../../../stores/k8sStore';

export const TabBar: React.FC = () => {
  const { openedTabs, activeTabId, setActiveTab, closeResourceTab } = useK8sStore();

  return (
    <div className="flex items-center gap-1 px-2 py-1 bg-slate-800 border-b border-slate-700 overflow-x-auto">
      {openedTabs.map((tab) => {
        const isActive = tab.id === activeTabId;
        return (
          <div
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded cursor-pointer transition-colors ${
              isActive
                ? 'bg-blue-600/20 text-blue-300 border border-blue-500/40'
                : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700 hover:text-slate-200 border border-transparent'
            }`}
          >
            <i className="fas fa-cube text-xs"></i>
            <span className="text-xs truncate max-w-[150px]">{tab.name}</span>
            <span className="text-[10px] text-slate-500">{tab.namespace}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                closeResourceTab(tab.id);
              }}
              className="ml-1 text-slate-500 hover:text-red-400 transition-colors"
              title="关闭标签"
            >
              <i className="fas fa-times text-xs"></i>
            </button>
          </div>
        );
      })}

      {openedTabs.length === 0 && (
        <div className="text-xs text-slate-500 px-2">
          点击 Pod 行打开详情
        </div>
      )}
    </div>
  );
};
