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
    <aside className="w-64 bg-black/20 backdrop-blur-sm border-r border-white/10">
      <nav className="p-4">
        <div className="space-y-2">
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => onSelectPanel(item.id)}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all ${
                activePanel === item.id
                  ? 'bg-yellow-500/20 border-2 border-yellow-500 text-white'
                  : 'bg-white/5 border border-white/10 text-white/80 hover:bg-white/10 hover:text-white'
              }`}
            >
              <span className="text-2xl">{item.icon}</span>
              <span className="font-medium">{item.label}</span>
            </button>
          ))}
        </div>

        {/* Quick Tips */}
        <div className="mt-8 p-4 bg-purple-500/20 border border-purple-500 rounded-xl">
          <div className="flex items-start space-x-2">
            <span className="text-xl">💡</span>
            <div className="text-white/70 text-sm">
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
