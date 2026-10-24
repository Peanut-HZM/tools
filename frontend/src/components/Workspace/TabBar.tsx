import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useI18n } from '../../i18n';
import { resolveIcon } from '../../utils/iconResolver';

export const TabBar: React.FC = () => {
  const { t } = useI18n();
  const { tabs, activeTabId, setActiveTab, removeTab, isToolSidebarVisible, toggleToolSidebar } = useWorkspaceStore();

  const handleTabKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    let targetIndex: number | null = null;
    if (event.key === 'ArrowRight') targetIndex = (index + 1) % tabs.length;
    if (event.key === 'ArrowLeft') targetIndex = (index - 1 + tabs.length) % tabs.length;
    if (event.key === 'Home') targetIndex = 0;
    if (event.key === 'End') targetIndex = tabs.length - 1;
    if (targetIndex === null) return;

    event.preventDefault();
    const targetTab = tabs[targetIndex];
    setActiveTab(targetTab.id);
    document.getElementById(`workspace-tab-${targetTab.id}`)?.focus();
  };

  return (
    <div className="flex h-11 items-center gap-1 overflow-x-auto border-b border-border bg-surface-1 px-2">
      <button
        type="button"
        onClick={toggleToolSidebar}
        className="mr-1 flex-shrink-0 rounded-md p-2 text-ink-muted transition-colors hover:bg-surface-2 hover:text-ink"
        title={isToolSidebarVisible ? t.workspace.collapseSidebar : t.workspace.expandSidebar}
        aria-label={isToolSidebarVisible ? t.workspace.collapseSidebar : t.workspace.expandSidebar}
      >
        {isToolSidebarVisible ? <ChevronLeft className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
      </button>
      <div className="mr-1 h-5 w-px flex-shrink-0 bg-border" />
      <div role="tablist" aria-label={t.workspace.toolList} className="flex min-w-max items-center gap-1">
        {tabs.map((tab, index) => {
          const isActive = tab.id === activeTabId;
          const Icon = resolveIcon(tab.toolIcon);
          return (
            <div
              key={tab.id}
              data-tab-id={tab.id}
              data-active={isActive}
              className={[
                'group flex h-8 min-w-0 max-w-[190px] items-center rounded-md border text-xs transition-colors',
                isActive
                  ? 'border-accent/25 bg-accent/10 text-accent'
                  : 'border-transparent text-ink-muted hover:border-border hover:bg-surface-2 hover:text-ink',
              ].join(' ')}
            >
              <button
                id={`workspace-tab-${tab.id}`}
                type="button"
                role="tab"
                aria-selected={isActive}
                aria-controls={`workspace-panel-${tab.id}`}
                tabIndex={isActive ? 0 : -1}
                className="flex min-w-0 flex-1 items-center gap-2 px-2.5 py-1.5 text-left"
                onClick={() => setActiveTab(tab.id)}
                onKeyDown={(event) => handleTabKeyDown(event, index)}
              >
                <Icon className="h-3.5 w-3.5 flex-shrink-0" />
                <span className="truncate">{tab.toolName}</span>
              </button>
              <button
                type="button"
                className={[
                  'mr-1 flex-shrink-0 rounded px-1 text-sm',
                  isActive
                    ? 'text-accent/70 hover:bg-accent/10 hover:text-accent'
                    : 'text-ink-faint hover:text-ink hover:bg-surface-3',
                ].join(' ')}
                onClick={() => removeTab(tab.id)}
                title={t.workspace.closeTab}
                aria-label={`${t.workspace.closeTab}: ${tab.toolName}`}
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};