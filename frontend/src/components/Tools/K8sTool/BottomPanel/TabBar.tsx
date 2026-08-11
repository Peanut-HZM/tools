/**
 * 底部面板的标签栏组件
 * 显示所有打开的资源标签，支持切换和关闭
 */
import React from 'react';
import { useK8sStore } from '../../../../stores/k8sStore';

/** 资源标签页数据类型（从 store 中提取） */
interface ResourceTab {
  id: string;
  type: string;
  namespace: string;
  name: string;
}

/**
 * 根据资源类型返回对应的状态指示图标
 * 当前统一使用通用图标，后续可按 type 区分
 */
const getStatusIcon = (_tab: ResourceTab): string => {
  // 可以通过 query 获取 pod 状态，这里先用通用图标
  return 'fas fa-cube';
};

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
            className={`flex items-center gap-2 px-3 py-1.5 rounded cursor-pointer transition-colors min-w-[120px] max-w-[200px] ${
              isActive
                ? 'bg-blue-600/20 text-blue-300 border border-blue-500/40'
                : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700 hover:text-slate-200 border border-transparent'
            }`}
          >
            {/* 状态指示图标 */}
            <i className={`${getStatusIcon(tab)} text-xs flex-shrink-0`}></i>
            {/* 资源名称，超长截断 */}
            <span className="text-xs truncate flex-1">{tab.name}</span>
            {/* 命名空间 */}
            <span className="text-[10px] text-slate-500 flex-shrink-0">{tab.namespace}</span>
            {/* 关闭按钮：激活态蓝色，非激活态灰色，hover 均变红 */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                closeResourceTab(tab.id);
              }}
              className={`ml-1 transition-colors flex-shrink-0 ${
                isActive ? 'text-blue-400 hover:text-red-400' : 'text-slate-500 hover:text-red-400'
              }`}
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
