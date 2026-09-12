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
  Menu,
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
  // 移动端（lg 以下）玻璃抽屉开关：由管理条汉堡按钮触发
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        navigate('/');
      } else if (user?.role !== 'admin') {
        navigate('/');
      }
    }
  }, [isAuthenticated, user, isLoading, navigate]);

  // 抽屉打开期间监听 Esc 键关闭（参考 Dialog 组件惯例，卸载/关闭时移除监听）
  useEffect(() => {
    if (!drawerOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDrawerOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [drawerOpen]);

  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center bg-canvas text-ink">
      {/* 启动加载态：Admin 域标准 border spinner（类串与其他加载态一致） */}
      <div className="h-8 w-8 rounded-full border-2 border-accent border-t-transparent animate-spin"></div>
    </div>;
  }

  if (!isAuthenticated || user?.role !== 'admin') {
    return null;
  }

  // 菜单激活判定：仪表盘 /admin 精确匹配，其余按前缀匹配以覆盖子路由（如 /admin/tools/:id）
  const isItemActive = (path: string) =>
    path === '/admin' ? location.pathname === '/admin' : location.pathname.startsWith(path);

  // 当前激活菜单项：供移动端管理条右侧显示当前页名（无匹配时不显示）
  const activeItem = ADMIN_MENU_GROUPS.flatMap((group) => group.items).find((item) =>
    isItemActive(item.path),
  );

  return (
    <div className="h-screen bg-canvas flex flex-col overflow-hidden">
      <Header
        searchValue={searchValue}
        onSearchChange={setSearchValue}
        onSearch={() => {}}
      />

      {/* 玻璃化改版：侧栏升级为贴边全高导航轨，行容器不再承担内边距（间距由导航轨与主内容区各自承担） */}
      <div className="flex flex-1 w-full min-h-0">
        {/* Sidebar - 全高导航轨（仅桌面 lg+ 显示）：glass-panel 玻璃底，去上/下/左描边仅保留右侧玻璃描边与主区分隔；固定不随内容滚动；lg 以下由移动端抽屉接管 */}
        <aside className="hidden lg:flex lg:flex-col lg:w-64 lg:flex-shrink-0 overflow-y-auto glass-panel rounded-none border-y-0 border-l-0">
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

        {/* Main Content - 仅内容区域可滚动：去渐变与容器阴影，直接落在画布底色上；min-w-0 防宽内容撑破行；内边距移入内容包裹层，让移动端管理条可通栏吸顶 */}
        <main className="flex-1 min-w-0 bg-canvas overflow-y-auto">
          {/* 移动端管理条（lg 以下显示）：sticky 吸顶，内含汉堡按钮 + 标题 + 当前页名；z-40 低于抽屉的 z-50 */}
          <div className="lg:hidden sticky top-0 z-40 glass-panel rounded-none border-x-0 border-t-0 flex items-center gap-2 h-14 px-3">
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              aria-label="打开管理菜单"
              aria-expanded={drawerOpen}
              className="h-11 w-11 flex-shrink-0 flex items-center justify-center rounded-lg text-ink-muted hover:text-ink hover:bg-glass-bg border border-glass-border transition-colors duration-200"
            >
              <Menu className="w-5 h-5" />
            </button>
            <span className="text-base font-semibold text-ink">管理后台</span>
            {/* 当前页名：右侧弱化显示，帮助移动端用户定位所在页面 */}
            {activeItem && (
              <span className="ml-auto text-sm text-ink-faint truncate pr-1">{activeItem.label}</span>
            )}
          </div>
          <div className="p-6">
            <Outlet />
          </div>
        </main>
      </div>

      {/* 移动端玻璃抽屉（lg 以下渲染）：遮罩点击 / Esc / 菜单跳转均会关闭 */}
      {drawerOpen && (
        <div className="lg:hidden">
          {/* 遮罩：半透明画布底 + 背景模糊，点击空白处关闭 */}
          <div
            className="fixed inset-0 z-50 bg-canvas/60 backdrop-blur-sm"
            onClick={() => setDrawerOpen(false)}
            aria-hidden="true"
          />
          {/* 抽屉：左侧滑入的全高玻璃面板，分组菜单与激活态类串同桌面侧栏 */}
          <aside className="fixed left-0 top-0 bottom-0 z-50 w-72 glass-panel rounded-none overflow-y-auto">
            <div className="p-4">
              <div className="flex items-center space-x-3 mb-6 px-4">
                <div className="w-10 h-10 tint tint-violet rounded-lg">
                  <Shield className="w-5 h-5" />
                </div>
                <h2 className="text-xl font-bold text-ink">后台管理</h2>
              </div>
              <nav>
                {ADMIN_MENU_GROUPS.map((group, groupIndex) => (
                  <div key={group.title}>
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
                            onClick={() => setDrawerOpen(false)}
                            className={`group flex items-center space-x-3 px-4 py-3 rounded-lg border transition-all duration-200 ${
                              isActive
                                ? 'text-white bg-[image:var(--gradient-brand)] shadow-[shadow:var(--shadow-glow-accent)] border-transparent hover:border-transparent'
                                : 'text-ink-muted hover:text-ink hover:bg-glass-bg border-glass-border'
                            }`}
                          >
                            <span
                              className={`w-5 text-center flex items-center justify-center ${
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
        </div>
      )}

      {/* 全局 ⌘K 命令面板：与 Layout.tsx 挂载方式一致，修复 /admin 下搜索图标点击无响应（面板此前不在 Admin 域内） */}
      <CommandPalette />
    </div>
  );
}
