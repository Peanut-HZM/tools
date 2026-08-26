/**
 * 侧边栏导航组件
 */
import React from 'react';

type PanelType = 'messages' | 'files' | 'devices' | 'settings';

interface SidebarProps {
  activePanel: PanelType;
  onSelectPanel: (panel: PanelType) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activePanel, onSelectPanel }) => {
  const menuItems: Array<{ id: PanelType; icon: string; label: string }> = [
    { id: 'messages', icon: '💬', label: '消息' },
    { id: 'files', icon: '📁', label: '文件' },
    { id: 'devices', icon: '📱', label: '设备' },
    { id: 'settings', icon: '⚙️', label: '设置' },
  ];

  return (
    <aside className="w-64 bg-surface-1/50 backdrop-blur-sm border-r border-border h-full flex flex-col">
      <nav className="p-4 flex-1 overflow-y-auto">
        <div className="space-y-2">
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => onSelectPanel(item.id)}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
                activePanel === item.id
                  ? 'bg-accent border-2 border-accent text-white'
                  : 'bg-surface-2/50 border border-border text-ink-muted hover:bg-surface-2 hover:text-ink'
              }`}
            >
              <span className="text-2xl">{item.icon}</span>
              <span className="font-medium">{item.label}</span>
            </button>
          ))}
        </div>

        {/* Quick Tips */}
        <div className="mt-8 p-4 bg-accent/10 border border-border rounded-lg">
          <div className="flex items-start space-x-2">
            <span className="text-xl">💡</span>
            <div className="text-ink-muted text-sm">
              <p>快捷提示：</p>
              <p className="mt-1">按 Ctrl+V 快速粘贴剪贴板内容</p>
            </div>
          </div>
        </div>
      </nav>
    </aside>
  );
};

export default Sidebar;
