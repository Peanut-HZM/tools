import { useEffect, useState } from 'react';
import { useAuth } from '../../stores/authStore';
import { useNavigate, Outlet, Link, useLocation } from 'react-router-dom';
import Header from '../Header/Header';
import Footer from '../Footer/Footer';

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
    return <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white">Loading...</div>;
  }

  if (!isAuthenticated || user?.role !== 'admin') {
    return null;
  }

  const menuItems = [
    { path: '/admin', label: '仪表盘' },
    { path: '/admin/tools', label: '工具管理' },
    { path: '/admin/users', label: '用户管理' },
    { path: '/admin/conversations', label: '对话管理' },
    { path: '/admin/agents', label: 'Agent管理' },
    { path: '/admin/settings', label: '系统设置' },
    { path: '/admin/oss', label: 'OSS 文件管理' },
    { path: '/admin/llm-configs', label: '大模型配置' },
  ];

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      <Header 
        searchValue={searchValue}
        onSearchChange={setSearchValue}
        onSearch={() => {}} 
      />
      
      <div className="flex flex-1 container mx-auto px-6 py-8 gap-8">
        {/* Sidebar */}
        <aside className="w-64 flex-shrink-0">
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h2 className="text-xl font-bold text-white mb-6 px-4">后台管理</h2>
            <nav className="space-y-2">
              {menuItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`block px-4 py-2 rounded transition-colors ${
                    location.pathname === item.path
                      ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                      : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 bg-slate-800 rounded-lg p-6 border border-slate-700 min-h-[600px]">
          <Outlet />
        </main>
      </div>

      <Footer />
    </div>
  );
}
