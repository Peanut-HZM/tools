import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import type { Tool } from '../../types';
import { resolveIcon } from '../../utils/iconResolver';
import { useI18n } from '../../i18n';

interface HomeToolSidebarProps {
  tools: Tool[];
  onToolClick?: (toolId: string) => void;
}

export default function HomeToolSidebar({ tools, onToolClick }: HomeToolSidebarProps) {
  const { t } = useI18n();
  const [query, setQuery] = useState('');
  const groupedTools = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    const filtered = keyword
      ? tools.filter((tool) => tool.title.toLowerCase().includes(keyword))
      : tools;

    return filtered.reduce<Record<string, Tool[]>>((groups, tool) => {
      const category = tool.category || t.home.uncategorizedTools;
      groups[category] = [...(groups[category] || []), tool];
      return groups;
    }, {});
  }, [query, t.home.uncategorizedTools, tools]);

  return (
    <aside className="hidden w-52 shrink-0 border-r border-border bg-surface-1 lg:flex lg:flex-col">
      <div className="p-3">
        <label className="relative block">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-faint" />
          <input
            aria-label={t.home.navigationSearchLabel}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t.home.navigationSearchPlaceholder}
            className="h-8 w-full rounded-lg border border-border bg-canvas pl-8 pr-2 text-xs text-ink outline-none placeholder:text-ink-faint focus:border-accent"
          />
        </label>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 pb-4">
        {Object.entries(groupedTools).map(([category, categoryTools]) => (
          <section key={category} className="mb-4">
            <h2 className="mb-1 px-2 text-[11px] font-medium text-ink-faint">{category}</h2>
            <div className="space-y-0.5">
              {categoryTools.map((tool) => {
                const Icon = resolveIcon(tool.icon);
                return (
                  <button
                    key={tool.id}
                    type="button"
                    onClick={() => onToolClick?.(tool.id)}
                    className="flex h-8 w-full items-center gap-2 rounded-md px-2 text-left text-xs text-ink-muted transition-colors hover:bg-accent/10 hover:text-accent"
                  >
                    <Icon className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{tool.title}</span>
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </nav>
    </aside>
  );
}
