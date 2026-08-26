/**
 * 底部面板的标签栏组件
 * 显示所有打开的资源标签，支持切换和关闭
 */
import React from 'react';
import { Box, X } from 'lucide-react';
import { useK8sStore, type ResourceTab } from '../../../../stores/k8sStore';

/**
 * 根据资源类型返回对应的状态指示图标
 * 当前统一使用通用图标，后续可按 type 区分
 */
const getStatusIcon = (_tab: ResourceTab): React.ReactNode => {
  // 可以通过 query 获取 pod 状态，这里先用通用图标
  return <Box className="w-3 h-3 flex-shrink-0" />;
};

export const TabBar: React.FC = () => {
  const { openedTabs, activeTabId, setActiveTab, closeResourceTab } = useK8sStore();

  return (
    <div className="flex items-center gap-1 px-2 py-1 bg-surface-1 border-b border-border overflow-x-auto">
      {openedTabs.map((tab) => {
        const isActive = tab.id === activeTabId;
        return (
          <div
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded cursor-pointer transition-colors min-w-[120px] max-w-[200px] ${
              isActive
                ? 'bg-accent/20 text-blue-300 border border-blue-500/40'
                : 'bg-surface-2/50 text-ink-muted hover:bg-surface-2 hover:text-ink border border-transparent'
            }`}
          >
            {/* 状态指示图标 */}
            {getStatusIcon(tab)}
            {/* 资源名称，超长截断 */}
            <span className="text-xs truncate flex-1">{tab.name}</span>
            {/* 命名空间 */}
            <span className="text-[10px] text-ink-faint flex-shrink-0">{tab.namespace}</span>
            {/* 关闭按钮：激活态蓝色，非激活态灰色，hover 均变红 */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                closeResourceTab(tab.id);
              }}
              className={`ml-1 transition-colors flex-shrink-0 ${
                isActive ? 'text-accent-info hover:text-danger' : 'text-ink-faint hover:text-danger'
              }`}
              title="关闭标签"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        );
      })}

      {openedTabs.length === 0 && (
        <div className="text-xs text-ink-faint px-2">
          点击 Pod 行打开详情
        </div>
      )}
    </div>
  );
};
