import { Home, Search } from 'lucide-react';
import React, { useContext, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useI18n } from '../../i18n';
import { AuthContext } from '../../stores/authStore';
import { useLoginModalStore } from '../../stores/loginModalStore';
import { resolveIcon } from '../../utils/iconResolver';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import type { Tool } from '../../types';
import { getStandaloneToolPath } from '../../lib/toolNavigation';

interface Props {
  tools: Tool[];
}

export const WorkspaceSidebar: React.FC<Props> = ({ tools }) => {
  const navigate = useNavigate();
  const { t } = useI18n();
  const { tabs, addTab, isToolSidebarVisible, toggleToolSidebar } = useWorkspaceStore();
  const [searchQuery, setSearchQuery] = useState('');
  const { isAuthenticated } = useContext(AuthContext);
  const openLoginModal = useLoginModalStore((state) => state.openLoginModal);

  const openedToolIds = new Set(tabs.map((t) => t.toolId));

  const groupedTools = useMemo(
    () => tools
      .filter((tool) => tool.title.toLowerCase().includes(searchQuery.toLowerCase()))
      .reduce<Record<string, Tool[]>>((groups, tool) => {
        const category = tool.category || t.home.uncategorizedTools;
        return {
          ...groups,
          [category]: [...(groups[category] || []), tool],
        };
      }, {}),
    [searchQuery, t.home.uncategorizedTools, tools]
  );

  const handleToolClick = (tool: Tool) => {
    // 登录拦截：检查工具是否需要登录
    if (tool.require_login && !isAuthenticated) {
      openLoginModal();
      return;
    }
    const standalonePath = getStandaloneToolPath(tool.id);
    if (standalonePath) {
      navigate(standalonePath);
      return;
    }
    addTab({ id: tool.id, title: tool.title, icon: tool.icon });
    if (window.matchMedia?.('(max-width: 1023px)').matches) {
      toggleToolSidebar();
    }
  };

  const handleGoHome = () => {
    navigate('/');
  };

  if (!isToolSidebarVisible) {
    return null;
  }

  return (
    <>
      <button
        type="button"
        aria-label={t.workspace.collapseSidebar}
        className="absolute inset-0 z-20 bg-slate-950/20 backdrop-blur-[1px] lg:hidden"
        onClick={toggleToolSidebar}
      />
      <aside className="absolute inset-y-0 left-0 z-30 flex h-full w-56 shrink-0 flex-col border-r border-border bg-surface-1 shadow-xl lg:relative lg:z-auto lg:shadow-none">
        <div className="border-b border-border p-3">
          <Button variant="ghost" onClick={handleGoHome} className="h-9 w-full justify-start gap-2 px-2 text-ink-muted hover:text-ink">
            <Home className="h-4 w-4" />
            <span>{t.workspace.home}</span>
          </Button>
          <div className="relative mt-2">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-faint" />
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t.workspace.searchPlaceholder}
              className="h-8 py-1.5 pl-8 pr-2 text-xs"
            />
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3" aria-label={t.workspace.toolList}>
          {Object.entries(groupedTools).map(([category, categoryTools]) => (
            <section key={category} className="mb-4">
              <h2 className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-wider text-ink-faint">
                {category}
              </h2>
              <div className="space-y-0.5">
                {categoryTools.map((tool) => {
                  const isOpened = openedToolIds.has(tool.id);
                  const Icon = resolveIcon(tool.icon);
                  return (
                    <button
                      key={tool.id}
                      type="button"
                      data-tool-id={tool.id}
                      data-active={isOpened}
                      className={[
                        'flex h-9 w-full items-center gap-2 rounded-md px-2 text-left text-xs transition-colors',
                        isOpened
                          ? 'bg-accent/10 font-medium text-accent'
                          : 'text-ink-muted hover:bg-surface-2 hover:text-ink',
                      ].join(' ')}
                      onClick={() => handleToolClick(tool)}
                    >
                      <Icon className="h-4 w-4 flex-shrink-0" />
                      <span className="truncate">{tool.title}</span>
                    </button>
                  );
                })}
              </div>
            </section>
          ))}
        </nav>
      </aside>
    </>
  );
};
