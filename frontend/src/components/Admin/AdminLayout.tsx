import { useEffect, useState, ReactNode } from 'react';
import { useAuth } from '../../stores/authStore';
import { useNavigate, Outlet, Link, useLocation } from 'react-router-dom';
import Header from '../Header/Header';
import CommandPalette from '../Common/CommandPalette';
import {
  LineChart,
  Wrench,
  Users,
  Mail,
  MessagesSquare,
  Bot,
  Settings,
  CloudUpload,
  Brain,
  GraduationCap,
  Shield,
  Plug,
} from 'lucide-react';

// 后台菜单三组分组（纯前端数据，不改路由）：组内项的 path/label/icon 自原 12 项菜单原样搬移
// 导出供测试或其他后台入口复用
export const ADMIN_MENU_GROUPS: Array<{
  title: string;
  items: Array<{ path: string; label: string; icon: ReactNode }>;
}> = [
  {
    title: '概览',
    items: [
      { path: '/admin', label: '仪表盘', icon: <LineChart className="w-5 h-5" /> },
    ],
  },
  {
    title: '内容管理',
    items: [
      { path: '/admin/tools', label: '工具管理', icon: <Wrench className="w-5 h-5" /> },
      { path: '/admin/course', label: '课程管理', icon: <GraduationCap className="w-5 h-5" /> },
      { path: '/admin/agents', label: 'Agent 管理', icon: <Bot className="w-5 h-5" /> },
      { path: '/admin/conversations', label: '对话管理', icon: <MessagesSquare className="w-5 h-5" /> },
      { path: '/admin/contact-messages', label: '留言管理', icon: <Mail className="w-5 h-5" /> },
    ],
  },
  {
    title: '系统',
    items: [
      { path: '/admin/users', label: '用户管理', icon: <Users className="w-5 h-5" /> },
      { path: '/admin/oss', label: 'OSS 文件管理', icon: <CloudUpload className="w-5 h-5" /> },
      { path: '/admin/llm-configs', label: '大模型配置', icon: <Brain className="w-5 h-5" /> },
      { path: '/admin/openclaw', label: 'OpenClaw 管理', icon: <MessagesSquare className="w-5 h-5" /> },
      { path: '/admin/mcp', label: 'MCP 工具', icon: <Plug className="w-5 h-5" /> },
      { path: '/admin/settings', label: '系统设置', icon: <Settings className="w-5 h-5" /> },
    ],
  },
];

export default function AdminLayout() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchValue, setSearchValue] = useState('');

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        navigate('/');
      } else if (user?.role !== 'admin') {
        navigate('/');
      }
    }
  }, [isAuthenticated, user, isLoading, navigate]);

  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center bg-canvas text-ink">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-accent"></div>
    </div>;
  }

  if (!isAuthenticated || user?.role !== 'admin') {
    return null;
  }

  // 菜单激活判定：仪表盘 /admin 精确匹配，其余按前缀匹配以覆盖子路由（如 /admin/tools/:id）
  const isItemActive = (path: string) =>
    path === '/admin' ? location.pathname === '/admin' : location.pathname.startsWith(path);

  return (
    <div className="h-screen bg-canvas flex flex-col overflow-hidden">
      <Header
        searchValue={searchValue}
        onSearchChange={setSearchValue}
        onSearch={() => {}}
      />

      {/* 玻璃化改版：侧栏升级为贴边全高导航轨，行容器不再承担内边距（间距由导航轨与主内容区各自承担） */}
      <div className="flex flex-1 w-full min-h-0">
        {/* Sidebar - 全高导航轨：glass-panel 玻璃底，去上/下/左描边仅保留右侧玻璃描边与主区分隔；固定不随内容滚动 */}
        <aside className="w-64 flex-shrink-0 overflow-y-auto glass-panel rounded-none border-y-0 border-l-0">
          <div className="p-4">
            <div className="flex items-center space-x-3 mb-6 px-4">
              {/* 徽标块：tint chip（低饱和紫底 + 同色描边与同色图标）替换品牌渐变实心底 */}
              <div className="w-10 h-10 tint tint-violet rounded-lg">
                <Shield className="w-5 h-5" />
              </div>
              <h2 className="text-xl font-bold text-ink">后台管理</h2>
            </div>
            <nav>
              {ADMIN_MENU_GROUPS.map((group, groupIndex) => (
                <div key={group.title}>
                  {/* 组标题：弱化小号大写字距标题；第一组紧跟徽标块，缩小上间距避免双重留白 */}
                  <div
                    className={`text-[10px] uppercase tracking-widest text-ink-faint px-3 pb-1 ${
                      groupIndex === 0 ? 'pt-1' : 'pt-4'
                    }`}
                  >
                    {group.title}
                  </div>
                  <div className="space-y-1">
                    {group.items.map((item) => {
                      const isActive = isItemActive(item.path);
                      return (
                        <Link
                          key={item.path}
                          to={item.path}
                          className={`group flex items-center space-x-3 px-4 py-3 rounded-lg border transition-all duration-200 ${
                            isActive
                              ? // 激活态：品牌渐变底 + 发光阴影的玻璃 chip（透明描边避免与渐变打架）
                                'text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)] border-transparent hover:border-transparent'
                              : // 非激活态：弱化文字色，hover 提亮玻璃底
                                'text-ink-muted hover:text-ink hover:bg-glass-bg border-glass-border'
                          }`}
                        >
                          <span
                            className={`w-5 text-center flex items-center justify-center ${
                              // 激活 chip 为渐变底，图标改用白色保证对比度
                              isActive ? 'text-white' : 'text-ink-faint group-hover:text-ink'
                            }`}
                          >
                            {item.icon}
                          </span>
                          <span className="font-medium">{item.label}</span>
                        </Link>
                      );
                    })}
                  </div>
                </div>
              ))}
            </nav>
          </div>
        </aside>

        {/* Main Content - 仅内容区域可滚动：去渐变与容器阴影，直接落在画布底色上；min-w-0 防宽内容撑破行 */}
        <main className="flex-1 min-w-0 bg-canvas p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>

      {/* 全局 ⌘K 命令面板：与 Layout.tsx 挂载方式一致，修复 /admin 下搜索图标点击无响应（面板此前不在 Admin 域内） */}
      <CommandPalette />
    </div>
  );
}
