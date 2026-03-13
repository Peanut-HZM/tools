import { useState, useEffect } from 'react';
import { adminConversationApi, ConversationListItem, ConversationStats, ModelUsageStat } from '../../services/adminConversationApi';
import { useToast } from '../../hooks/useToast';
export default function ConversationManagement() {
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [stats, setStats] = useState<ConversationStats | null>(null);
  const [modelStats, setModelStats] = useState<ModelUsageStat[]>([]);
  const [loading, setLoading] = useState(false);
  const { success, error  } = useToast();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [convData, statsData, modelData] = await Promise.all([
        adminConversationApi.getConversations({ limit: 50 }),
        adminConversationApi.getStats(),
        adminConversationApi.getModelStats(),
      ]);
      setConversations(convData);
      setStats(statsData);
      setModelStats(modelData);
    } catch (err) {
      error('加载数据失败');
      console.error('Failed to load data:', err);
    }
    setLoading(false);
  };

  const handleDelete = async (id: string, title: string) => {
    if (!confirm(`确定要删除对话"${title || '未命名'}"吗？此操作不可恢复。`)) return;
    try {
      await adminConversationApi.deleteConversation(id);
      success('对话已删除');
      loadData();
    } catch (err) {
      error('删除失败');
      console.error('Failed to delete:', err);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  const formatNumber = (num: number) => {
    return num?.toLocaleString() || '0';
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-white mb-6">对话管理</h2>

      {/* 统计卡片 */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
            <p className="text-slate-400 text-sm">总对话数</p>
            <p className="text-2xl font-bold text-white">{formatNumber(stats.total_conversations)}</p>
          </div>
          <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
            <p className="text-slate-400 text-sm">总消息数</p>
            <p className="text-2xl font-bold text-white">{formatNumber(stats.total_messages)}</p>
          </div>
          <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
            <p className="text-slate-400 text-sm">总Token消耗</p>
            <p className="text-2xl font-bold text-cyan-400">{formatNumber(stats.total_tokens)}</p>
          </div>
          <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
            <p className="text-slate-400 text-sm">今日Token消耗</p>
            <p className="text-2xl font-bold text-green-400">{formatNumber(stats.today_tokens)}</p>
          </div>
        </div>
      )}

      {/* 模型使用统计 */}
      {modelStats.length > 0 && (
        <div className="bg-slate-700 rounded-lg p-6 mb-6 border border-slate-600">
          <h3 className="text-lg font-semibold text-white mb-4">模型使用统计</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {modelStats.map((stat) => (
              <div key={stat.model_name} className="bg-slate-800 rounded-lg p-4">
                <p className="text-white font-medium">{stat.model_name}</p>
                <p className="text-slate-400 text-sm">
                  调用: {stat.usage_count} 次 | Token: {formatNumber(stat.total_tokens)}
                </p>
                <div className="mt-2 bg-slate-600 rounded-full h-2">
                  <div
                    className="bg-cyan-500 h-2 rounded-full"
                    style={{ width: `${stat.percentage}%` }}
                  />
                </div>
                <p className="text-xs text-slate-400 mt-1">{stat.percentage}%</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 对话列表 */}
      <div className="bg-slate-700 rounded-lg border border-slate-600 overflow-hidden">
        <div className="p-4 border-b border-slate-600 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-white">对话列表</h3>
          <button
            onClick={loadData}
            disabled={loading}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm disabled:opacity-50"
          >
            {loading ? '加载中...' : '刷新'}
          </button>
        </div>

        {conversations.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <p>暂无对话记录</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-slate-800">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">对话标题</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">用户</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">消息数</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">Token消耗</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">创建时间</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-600">
              {conversations.map((conv) => (
                <tr key={conv.id} className="hover:bg-slate-600/50">
                  <td className="px-4 py-3">
                    <div className="text-white font-medium truncate max-w-[200px]">
                      {conv.title || '未命名对话'}
                    </div>
                    <div className="text-xs text-slate-400">{conv.current_stage}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{conv.username}</td>
                  <td className="px-4 py-3 text-center text-slate-300">{conv.message_count}</td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-cyan-400 font-medium">{formatNumber(conv.total_tokens)}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-sm">{formatDate(conv.created_at)}</td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleDelete(conv.id, conv.title || '')}
                      className="px-3 py-1 text-sm bg-red-600/20 text-red-400 border border-red-500/30 rounded hover:bg-red-600/30"
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>    </div>
  );
}
