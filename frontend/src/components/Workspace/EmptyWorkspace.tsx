import { Wrench } from 'lucide-react';
import React from 'react';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useI18n } from '../../i18n';
import type { Tool } from '../../types';
import { resolveIcon } from '../../utils/iconResolver';

interface Props {
  tools: Tool[];
}

/** 常用工具 ID 列表（快捷入口） */
const FEATURED_TOOL_IDS = [
  'k8s-tool',
  'ssh-tool',
  'database-tool',
  'redis-tool',
  'markdown-editor',
  'json-formatter',
];

export const EmptyWorkspace: React.FC<Props> = ({ tools }: Props) => {
  const { t } = useI18n();
  const { addTab } = useWorkspaceStore();

  const featuredTools = FEATURED_TOOL_IDS
    .map((id) => tools.find((tool) => tool.id === id))
    .filter((tool): tool is Tool => tool !== undefined);

  const handleOpenTool = (tool: Tool) => {
    addTab({ id: tool.id, title: tool.title, icon: tool.icon });
  };

  return (
    <div className="flex-1 flex items-center justify-center bg-canvas">
      <div className="text-center max-w-md">
        <Wrench className="w-16 h-16 text-ink-faint mb-6" />
        <h2 className="text-2xl font-bold text-ink mb-2">{t.workspace.welcome}</h2>
        <p className="text-ink-muted mb-8">
          {t.workspace.welcomeHint}
        </p>
        {featuredTools.length > 0 && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {featuredTools.map((tool) => {
              const Icon = resolveIcon(tool.icon);
              return (
                <button
                  key={tool.id}
                  onClick={() => handleOpenTool(tool)}
                  className="flex flex-col items-center gap-2 rounded-lg border border-border bg-surface-1 p-4 transition-colors hover:bg-surface-2 hover:border-border"
                >
                  <Icon className="h-5 w-5 text-accent-info" />
                  <span className="text-xs text-ink-muted">{tool.title}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
