import React from 'react';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import type { Tool } from '../../types';

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
  const { addTab } = useWorkspaceStore();

  const featuredTools = FEATURED_TOOL_IDS
    .map((id) => tools.find((t) => t.id === id))
    .filter((t): t is Tool => t !== undefined);

  const handleOpenTool = (tool: Tool) => {
    addTab({ id: tool.id, title: tool.title, icon: tool.icon });
  };

  return (
    <div className="flex-1 flex items-center justify-center bg-slate-900">
      <div className="text-center max-w-md">
        <i className="fas fa-tools text-6xl text-slate-600 mb-6"></i>
        <h2 className="text-2xl font-bold text-slate-200 mb-2">开始使用</h2>
        <p className="text-slate-400 mb-8">
          从左侧工具列表选择一个工具，或点击下方快捷入口
        </p>
        {featuredTools.length > 0 && (
          <div className="grid grid-cols-3 gap-3">
            {featuredTools.map((tool) => (
              <button
                key={tool.id}
                onClick={() => handleOpenTool(tool)}
                className="flex flex-col items-center gap-2 p-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-slate-600 rounded-lg transition-colors"
              >
                <i className={[tool.icon, 'text-xl text-blue-400'].join(' ')}></i>
                <span className="text-xs text-slate-300">{tool.title}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
