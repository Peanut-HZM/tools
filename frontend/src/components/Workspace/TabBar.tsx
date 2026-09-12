import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useI18n } from '../../i18n';
import { resolveIcon } from '../../utils/iconResolver';

export const TabBar: React.FC = () => {
  const { t } = useI18n();
  const { tabs, activeTabId, setActiveTab, removeTab, isToolSidebarVisible, toggleToolSidebar } = useWorkspaceStore();

  return (
    <div className="flex items-end glass-panel border-x-0 border-t-0 rounded-none h-10 px-2 gap-0.5 overflow-x-auto">
      {/* 玻璃化改版：标签栏走 glass-panel 玻璃底，贴边展示故去掉左右/顶部描边（同 Header 悬浮条模式） */}
      {/* 工具列表展开/折叠按钮 */}
      <button
        onClick={toggleToolSidebar}
        className="self-center p-1.5 mr-1 text-ink-muted hover:text-ink hover:bg-surface-2 rounded transition-colors flex-shrink-0"
        title={isToolSidebarVisible ? t.workspace.collapseSidebar : t.workspace.expandSidebar}
        aria-label={isToolSidebarVisible ? t.workspace.collapseSidebar : t.workspace.expandSidebar}
      >
        {isToolSidebarVisible ? <ChevronLeft className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
      </button>
      {/* 标签页分隔线 */}
      <div className="self-stretch w-px bg-surface-2 mr-1"></div>
      {tabs.map((tab) => {
        const isActive = tab.id === activeTabId;
        const Icon = resolveIcon(tab.toolIcon);
        return (
          <div
            key={tab.id}
            data-tab-id={tab.id}
            data-active={isActive}
            className={[
              // 玻璃化改版：chip 改为圆角胶囊，激活态用品牌渐变底 + 发光阴影，非激活态用玻璃底 hover 提亮
              'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm cursor-pointer transition-colors min-w-0 max-w-[180px] group',
              isActive
                ? 'text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)]'
                : 'text-ink-muted hover:text-ink hover:bg-glass-bg',
            ].join(' ')}
            onClick={() => setActiveTab(tab.id)}
          >
            <Icon className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">{tab.toolName}</span>
            <button
              className={[
                // 关闭 ×：激活态在品牌渐变底上用白色系保证可读性；非激活态沿用墨色 hover
                'ml-1 rounded px-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity',
                isActive
                  ? 'text-white/70 hover:text-white hover:bg-white/20'
                  : 'text-ink-faint hover:text-ink hover:bg-surface-3',
              ].join(' ')}
              onClick={(e) => {
                e.stopPropagation();
                removeTab(tab.id);
              }}
              title={t.workspace.closeTab}
            >
              ×
            </button>
          </div>
        );
      })}
    </div>
  );
};