import { useState, useEffect } from 'react';
import { AlertCircle, Wrench, LineChart, Calculator, Trophy, Inbox } from 'lucide-react';
import { getDashboardStats, DashboardStats } from '../../api/adminApi';
import { useToast } from '../../hooks/useToast';

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const { error  } = useToast();

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
          {/* Admin 域标准加载 spinner（玻璃化规范统一，后续页面复用） */}
          <div className="h-8 w-8 rounded-full border-2 border-accent border-t-transparent animate-spin mx-auto mb-4"></div>
          <p className="text-ink-muted">加载中...</p>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <AlertCircle className="w-20 h-20 text-danger mb-4" />
          <p className="text-ink text-lg">无法加载数据</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Page Header */}
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-ink mb-2">仪表盘</h2>
        <p className="text-ink-muted">欢迎使用后台管理系统，这里是您的数据概览</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {/* 总工具数卡片 */}
        <div className="group glass-card hover-lift rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-accent to-accent-hover rounded-lg flex items-center justify-center">
              <Wrench className="w-5 h-5 text-white" />
            </div>
            <span className="text-xs text-ink-faint uppercase font-medium">实时数据</span>
          </div>
          <h3 className="text-ink-muted text-sm font-medium mb-1">总工具数</h3>
          <p className="text-4xl font-bold text-ink">{stats.total_tools}</p>
        </div>

        {/* 总访问次数卡片 */}
        <div className="group glass-card hover-lift rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-accent-secondary to-accent rounded-lg flex items-center justify-center">
              <LineChart className="w-5 h-5 text-white" />
            </div>
            <span className="text-xs text-ink-faint uppercase font-medium">累计统计</span>
          </div>
          <h3 className="text-ink-muted text-sm font-medium mb-1">总访问次数</h3>
          <p className="text-4xl font-bold bg-gradient-to-r from-accent-secondary to-accent bg-clip-text text-transparent">{stats.total_visits.toLocaleString()}</p>
        </div>

        {/* 新增卡片 - 平均访问 */}
        <div className="group glass-card hover-lift rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            {/* 装饰性品牌渐变图标底：中性指标卡，无成功/失败状态语义 */}
            <div className="w-12 h-12 bg-[image:var(--gradient-brand)] rounded-lg flex items-center justify-center">
              <Calculator className="w-5 h-5 text-white" />
            </div>
            <span className="text-xs text-ink-faint uppercase font-medium">平均值</span>
          </div>
          <h3 className="text-ink-muted text-sm font-medium mb-1">平均访问/工具</h3>
          {/* 装饰性品牌渐变数字（非状态色语义），沿用 bg-clip-text 渐变文字模式 */}
          <p className="text-4xl font-bold bg-[image:var(--gradient-brand)] bg-clip-text text-transparent">
            {stats.total_tools > 0 ? Math.round(stats.total_visits / stats.total_tools).toLocaleString() : 0}
          </p>
        </div>
      </div>

      {/* Popular Tools Chart/Table */}
      <div className="glass-card rounded-xl overflow-hidden p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-bold text-ink flex items-center">
              <Trophy className="w-5 h-5 text-warning mr-3" />
              热门工具排行
            </h3>
            <p className="text-ink-muted text-sm mt-1">查看最受欢迎的工具</p>
          </div>
          <div className="px-4 py-2 bg-accent/10 border border-accent/30 rounded-lg">
            <span className="text-accent text-sm font-medium">Top {stats.popular_tools.length}</span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border">
                <th className="px-6 py-4 text-ink-muted font-medium text-sm uppercase">排名</th>
                <th className="px-6 py-4 text-ink-muted font-medium text-sm uppercase">工具名称</th>
                <th className="px-6 py-4 text-ink-muted font-medium text-sm uppercase">访问次数</th>
                <th className="px-6 py-4 text-ink-muted font-medium text-sm uppercase">进度条</th>
                <th className="px-6 py-4 text-ink-muted font-medium text-sm uppercase">最后访问时间</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {stats.popular_tools.length === 0 ? (
                <tr>
                  {/* 空态：Admin 域标准玻璃容器，保留原 Inbox 图标与文案 */}
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <div className="glass-card rounded-xl px-6 py-10">
                      <Inbox className="w-16 h-16 text-ink-faint mb-4" />
                      <p className="text-ink-faint">暂无数据</p>
                    </div>
                  </td>
                </tr>
              ) : (
                stats.popular_tools.map((tool, index) => (
                  <tr key={tool.tool_id} className="hover:bg-glass-bg transition-colors">
                    <td className="px-6 py-4">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                        index === 0 ? 'bg-warning/20 text-warning' :
                        index === 1 ? 'bg-ink-faint/20 text-ink-muted' :
                        index === 2 ? 'bg-accent-warm/20 text-accent-warm' :
                        'bg-surface-3 text-ink-muted'
                      }`}>
                        {index + 1}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-medium text-ink">{tool.tool_name}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-accent font-semibold tabular-nums">{tool.visit_count.toLocaleString()}</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="w-32 h-2 bg-surface-3 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-accent to-accent-secondary rounded-full transition-all duration-500"
                          style={{ width: `${Math.min((tool.visit_count / (stats.popular_tools[0]?.visit_count || 1)) * 100, 100)}%` }}
                        />
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-ink-muted text-sm">
                        {new Date(tool.last_visited).toLocaleString('zh-CN')}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>    </div>
  );
}
