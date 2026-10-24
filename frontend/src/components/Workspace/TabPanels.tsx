import { AlertTriangle } from 'lucide-react';
import React from 'react';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { toolComponentMap } from './toolComponents';
import { useI18n } from '../../i18n';

const EDGE_TO_EDGE_TOOLS = new Set([
  'k8s-tool',
  'database-tool',
  'ssh-tool',
  'redis-tool',
  'markdown-editor',
  'token-usage',
  'cursor-history',
  'http-api-client',
  'product-manager',
]);

export const SESSION_KEEP_ALIVE_TOOLS = new Set([
  'database-tool',
  'ssh-tool',
  'markdown-editor',
  'redis-tool',
  'token-usage',
  'json-formatter',
  'calendar',
  'ai-assistant',
  'key-generator',
  'ocr-tool',
  'ocr',
  'asr-tool',
  'asr',
  'markitdown-converter',
  'learning-share',
  'course-platform',
  'cross-share',
  'cursor-history',
  'openclaw',
  'product-manager',
  'image-downloader',
  'video-downloader',
  'image-generation',
  'video-generation',
  'system-monitor',
]);

/**
 * 标签面板容器
 * 标签面板容器。
 * 仅保活仍依赖组件内存保存草稿、筛选或流式任务的工具；关闭标签时照常卸载。
 * 已使用 URL/独立 Store 或没有工作上下文的工具切换时卸载，避免所有工具长期运行。
 */
export const TabPanels: React.FC = () => {
  const { tabs, activeTabId } = useWorkspaceStore();
  const { t } = useI18n();

  if (tabs.length === 0) return null;

  return (
    <div className="flex-1 min-h-0 overflow-hidden">
      {tabs.map((tab) => {
        const isActive = tab.id === activeTabId;
        if (!isActive && !SESSION_KEEP_ALIVE_TOOLS.has(tab.toolId)) {
          return null;
        }
        const ToolComponent = toolComponentMap[tab.toolId];
        if (!ToolComponent) {
          return (
            <div
              key={tab.id}
              id={`workspace-panel-${tab.id}`}
              role="tabpanel"
              aria-labelledby={`workspace-tab-${tab.id}`}
              style={{ display: isActive ? 'flex' : 'none' }}
              className="h-full items-center justify-center text-ink-faint"
            >
              <div className="text-center">
                <AlertTriangle className="w-10 h-10 mb-4" />
                <p>{t.workspace.unknownTool}: {tab.toolId}</p>
              </div>
            </div>
          );
        }
        return (
          <div
            key={tab.id}
            id={`workspace-panel-${tab.id}`}
            role="tabpanel"
            aria-labelledby={`workspace-tab-${tab.id}`}
            style={{ display: isActive ? 'flex' : 'none' }}
            className={`h-full flex-col ${EDGE_TO_EDGE_TOOLS.has(tab.toolId) ? 'p-0' : 'p-4'}`}
          >
            <ToolComponent />
          </div>
        );
      })}
    </div>
  );
};
