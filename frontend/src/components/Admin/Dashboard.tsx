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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-500 mx-auto mb-4"></div>
          <p className="text-slate-400">加载中...</p>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <i className="fas fa-exclamation-circle text-5xl text-red-500 mb-4"></i>
          <p className="text-white text-lg">无法加载数据</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Page Header */}
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-white mb-2">仪表盘</h2>
        <p className="text-slate-400">欢迎使用后台管理系统，这里是您的数据概览</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {/* 总工具数卡片 */}
        <div className="group bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 border border-slate-700 hover:border-cyan-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/10 hover:-translate-y-1">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
              <i className="fas fa-toolbox text-white text-lg"></i>
            </div>
            <span className="text-xs text-slate-500 uppercase font-medium">实时数据</span>
          </div>
          <h3 className="text-slate-400 text-sm font-medium mb-1">总工具数</h3>
          <p className="text-4xl font-bold text-white">{stats.total_tools}</p>
        </div>

        {/* 总访问次数卡片 */}
        <div className="group bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 border border-slate-700 hover:border-cyan-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/10 hover:-translate-y-1">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center">
              <i className="fas fa-chart-line text-white text-lg"></i>
            </div>
            <span className="text-xs text-slate-500 uppercase font-medium">累计统计</span>
          </div>
          <h3 className="text-slate-400 text-sm font-medium mb-1">总访问次数</h3>
          <p className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">{stats.total_visits.toLocaleString()}</p>
        </div>

        {/* 新增卡片 - 平均访问 */}
        <div className="group bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 border border-slate-700 hover:border-purple-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-purple-500/10 hover:-translate-y-1">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center">
              <i className="fas fa-calculator text-white text-lg"></i>
            </div>
            <span className="text-xs text-slate-500 uppercase font-medium">平均值</span>
          </div>
          <h3 className="text-slate-400 text-sm font-medium mb-1">平均访问/工具</h3>
          <p className="text-4xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            {stats.total_tools > 0 ? Math.round(stats.total_visits / stats.total_tools).toLocaleString() : 0}
          </p>
        </div>
      </div>

      {/* Popular Tools Chart/Table */}
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 border border-slate-700/50 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-bold text-white flex items-center">
              <i className="fas fa-trophy text-yellow-500 mr-3"></i>
              热门工具排行
            </h3>
            <p className="text-slate-400 text-sm mt-1">查看最受欢迎的工具</p>
          </div>
          <div className="px-4 py-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg">
            <span className="text-cyan-400 text-sm font-medium">Top {stats.popular_tools.length}</span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="px-6 py-4 text-slate-400 font-medium text-sm uppercase">排名</th>
                <th className="px-6 py-4 text-slate-400 font-medium text-sm uppercase">工具名称</th>
                <th className="px-6 py-4 text-slate-400 font-medium text-sm uppercase">访问次数</th>
                <th className="px-6 py-4 text-slate-400 font-medium text-sm uppercase">进度条</th>
                <th className="px-6 py-4 text-slate-400 font-medium text-sm uppercase">最后访问时间</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {stats.popular_tools.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <i className="fas fa-inbox text-4xl text-slate-600 mb-4"></i>
                    <p className="text-slate-500">暂无数据</p>
                  </td>
                </tr>
              ) : (
                stats.popular_tools.map((tool, index) => (
                  <tr key={tool.tool_id} className="hover:bg-slate-700/30 transition-colors">
                    <td className="px-6 py-4">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                        index === 0 ? 'bg-yellow-500/20 text-yellow-400' :
                        index === 1 ? 'bg-slate-400/20 text-slate-300' :
                        index === 2 ? 'bg-amber-600/20 text-amber-500' :
                        'bg-slate-700 text-slate-400'
                      }`}>
                        {index + 1}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-medium text-white">{tool.tool_name}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-cyan-400 font-semibold">{tool.visit_count.toLocaleString()}</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="w-32 h-2 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all duration-500"
                          style={{ width: `${Math.min((tool.visit_count / (stats.popular_tools[0]?.visit_count || 1)) * 100, 100)}%` }}
                        />
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-slate-400 text-sm">
                        {new Date(tool.last_visited).toLocaleString('zh-CN')}
                      </span>
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
