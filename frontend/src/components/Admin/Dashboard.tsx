import { useState, useEffect } from 'react';
import { getDashboardStats, DashboardStats } from '../../api/adminApi';
import { useToast } from '../../hooks/useToast';
import { ToastContainer } from '../MarkdownEditor/Toast/Toast';

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const { toasts, removeToast, error } = useToast();

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const data = await getDashboardStats();
      setStats(data);
    } catch (e) {
      error('获取仪表盘数据失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="text-white">加载中...</div>;
  if (!stats) return <div className="text-white">无法加载数据</div>;

  return (
    <div>
      <h2 className="text-2xl font-bold text-white mb-6">仪表盘</h2>
      
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div className="bg-slate-700 rounded-lg p-6 border border-slate-600">
          <h3 className="text-slate-400 text-sm font-medium uppercase mb-2">总工具数</h3>
          <p className="text-3xl font-bold text-white">{stats.total_tools}</p>
        </div>
        <div className="bg-slate-700 rounded-lg p-6 border border-slate-600">
          <h3 className="text-slate-400 text-sm font-medium uppercase mb-2">总访问次数</h3>
          <p className="text-3xl font-bold text-cyan-400">{stats.total_visits}</p>
        </div>
      </div>

      {/* Popular Tools Chart/Table */}
      <div className="bg-slate-700 rounded-lg p-6 border border-slate-600">
        <h3 className="text-xl font-bold text-white mb-4">热门工具排行</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-slate-300">
            <thead className="bg-slate-800 text-slate-100 uppercase text-xs">
              <tr>
                <th className="px-6 py-3 rounded-l">工具名称</th>
                <th className="px-6 py-3">访问次数</th>
                <th className="px-6 py-3 rounded-r">最后访问时间</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-600">
              {stats.popular_tools.length === 0 ? (
                <tr>
                  <td colSpan={3} className="px-6 py-4 text-center text-slate-500">暂无数据</td>
                </tr>
              ) : (
                stats.popular_tools.map((tool) => (
                  <tr key={tool.tool_id} className="hover:bg-slate-600/50">
                    <td className="px-6 py-4 font-medium text-white">{tool.tool_name}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <span className="mr-2">{tool.visit_count}</span>
                        <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-cyan-500" 
                            style={{ width: `${Math.min((tool.visit_count / (stats.popular_tools[0]?.visit_count || 1)) * 100, 100)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-400">
                      {new Date(tool.last_visited).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}
