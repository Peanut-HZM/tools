import { useEffect, useState } from 'react';
import { useAuth } from '../../stores/authStore';
import { useNavigate, Outlet, Link, useLocation } from 'react-router-dom';
import Header from '../Header/Header';

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
    return <div className="min-h-screen flex items-center justify-center bg-canvas text-ink-inverse">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-accent"></div>
    </div>;
  }

  if (!isAuthenticated || user?.role !== 'admin') {
    return null;
  }

  const menuItems = [
    { path: '/admin', label: '仪表盘', icon: 'fa-chart-line' },
    { path: '/admin/tools', label: '工具管理', icon: 'fa-toolbox' },
    { path: '/admin/users', label: '用户管理', icon: 'fa-users' },
    { path: '/admin/contact-messages', label: '留言管理', icon: 'fa-envelope' },
    { path: '/admin/conversations', label: '对话管理', icon: 'fa-comments' },
    { path: '/admin/agents', label: 'Agent 管理', icon: 'fa-robot' },
    { path: '/admin/settings', label: '系统设置', icon: 'fa-cog' },
    { path: '/admin/oss', label: 'OSS 文件管理', icon: 'fa-cloud-upload-alt' },
    { path: '/admin/llm-configs', label: '大模型配置', icon: 'fa-brain' },
    { path: '/admin/course', label: '课程管理', icon: 'fa-graduation-cap' },
    { path: '/admin/openclaw', label: 'OpenClaw 管理', icon: 'fa-comments' },
    { path: '/admin/image-generation', label: '图像生成管理', icon: 'fa-image' },
  ];

  return (
    <div className="h-screen bg-canvas flex flex-col overflow-hidden">
      <Header
        searchValue={searchValue}
        onSearchChange={setSearchValue}
        onSearch={() => {}}
      />

      <div className="flex flex-1 w-full px-6 py-8 gap-8 min-h-0">
        {/* Sidebar - 固定不随内容滚动 */}
        <aside className="w-64 flex-shrink-0 overflow-y-auto">
          <div className="bg-gradient-to-br from-surface-1 to-canvas rounded-xl p-4 border border-border/50 shadow-xl">
            <div className="flex items-center space-x-3 mb-6 px-4">
              <div className="w-10 h-10 bg-gradient-to-br from-accent to-accent-info rounded-lg flex items-center justify-center">
                <i className="fas fa-shield-alt text-ink-inverse text-lg"></i>
              </div>
              <h2 className="text-xl font-bold text-ink-inverse">后台管理</h2>
            </div>
            <nav className="space-y-1">
              {menuItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`group flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                    location.pathname === item.path
                      ? 'bg-gradient-to-r from-accent/20 to-accent-info/10 text-accent border border-accent/30 shadow-lg shadow-accent/10'
                      : 'text-ink-muted hover:bg-surface-2/50 hover:text-ink-inverse hover:translate-x-1'
                  }`}
                >
                  <i className={`fas ${item.icon} w-5 text-center ${location.pathname === item.path ? 'text-accent' : 'text-ink-faint group-hover:text-ink-inverse'}`}></i>
                  <span className="font-medium">{item.label}</span>
                </Link>
              ))}
            </nav>
          </div>
        </aside>

        {/* Main Content - 仅内容区域可滚动 */}
        <main className="flex-1 bg-gradient-to-br from-surface-1 to-canvas rounded-xl p-6 border border-border/50 shadow-xl overflow-y-auto">
          <Outlet />
        </main>
      </div>

    </div>
  );
}
