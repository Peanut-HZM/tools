import { Home, Search } from 'lucide-react';
import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '../../stores/workspaceStore';
import { useI18n } from '../../i18n';
import { AuthContext } from '../../stores/authStore';
import { useLoginModalStore } from '../../stores/loginModalStore';
import { resolveIcon } from '../../utils/iconResolver';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import type { Tool } from '../../types';

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

  const filteredTools = tools.filter((tool) =>
    tool.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleToolClick = (tool: Tool) => {
    // 登录拦截：检查工具是否需要登录
    if (tool.require_login && !isAuthenticated) {
      openLoginModal();
      return;
    }
    addTab({ id: tool.id, title: tool.title, icon: tool.icon });
  };

  const handleGoHome = () => {
    navigate('/');
  };

  if (!isToolSidebarVisible) {
    return null;
  }

  return (
    <div className="w-52 glass-panel rounded-none border-y-0 border-l-0 flex flex-col h-full">
      {/* 玻璃化改版：全高导航轨走 glass-panel 玻璃底，仅保留右侧描边与主区分隔（阶段④确立模式） */}
      {/* 首页按钮：走 ui/Button default（.btn-primary 品牌渐变底） */}
      <div className="p-3 border-b border-border">
        <Button onClick={handleGoHome} className="w-full gap-2">
          <Home className="w-4 h-4" />
          <span>{t.workspace.home}</span>
        </Button>
      </div>

      {/* 搜索框：走 ui/Input 玻璃输入框，保留左内嵌搜索图标 */}
      <div className="px-3 py-2 border-b border-border">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 text-ink-faint w-3 h-3" />
          <Input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t.workspace.searchPlaceholder}
            className="h-8 py-1.5 pl-7 pr-2 text-xs"
          />
        </div>
      </div>

      {/* 工具列表 */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        <div className="text-[10px] text-ink-faint uppercase font-semibold tracking-wider px-2 mb-2">
          {t.workspace.toolList}
        </div>
        <div className="space-y-0.5">
          {filteredTools.map((tool) => {
            const isOpened = openedToolIds.has(tool.id);
            // FA class 字符串解析为 lucide 组件（与 TabBar 同一套 iconResolver，避免依赖 FA CDN）
            const Icon = resolveIcon(tool.icon);
            return (
              <div
                key={tool.id}
                data-tool-id={tool.id}
                data-active={isOpened}
                className={[
                  'flex items-center gap-2 px-3 py-2 rounded-md text-sm cursor-pointer transition-colors',
                  isOpened
                    ? 'bg-accent/20 text-accent'
                    : 'text-ink-muted hover:bg-glass-bg hover:text-ink',
                ].join(' ')}
                onClick={() => handleToolClick(tool)}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span className="truncate">{tool.title}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
