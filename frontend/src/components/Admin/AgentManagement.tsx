import { useState, useEffect } from 'react';
import { agentApi, Agent } from '../../services/agentApi';
import { useToast } from '../../hooks/useToast';
export default function AgentManagement() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const { success, error  } = useToast();

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    system_prompt: '',
    icon: 'fa-robot',
    icon_color: 'bg-blue-500',
    category: 'AI工具',
  });

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    setLoading(true);
    try {
      const data = await agentApi.getAgents();
      setAgents(data);
    } catch (err) {
      error('加载Agent列表失败');
      console.error('Failed to load agents:', err);
    }
    setLoading(false);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      system_prompt: '',
      icon: 'fa-robot',
      icon_color: 'bg-blue-500',
      category: 'AI工具',
    });
    setEditingId(null);
    setShowForm(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await agentApi.updateAgent(editingId, formData);
        success('Agent更新成功');
      } else {
        await agentApi.createAgent(formData);
        success('Agent创建成功');
      }
      resetForm();
      loadAgents();
    } catch (err) {
      error(editingId ? '更新Agent失败' : '创建Agent失败');
      console.error('Failed to save agent:', err);
    }
  };

  const handleSetDefault = async (id: string, name: string) => {
    try {
      await agentApi.setDefaultAgent(id);
      success(`已将 "${name}" 设为默认Agent`);
      loadAgents();
    } catch (err) {
      error('设置默认Agent失败');
      console.error('Failed to set default agent:', err);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确定要删除Agent "${name}" 吗？此操作不可恢复。`)) return;
    try {
      await agentApi.deleteAgent(id);
      success('Agent删除成功');
      loadAgents();
    } catch (err) {
      error('删除Agent失败');
      console.error('Failed to delete agent:', err);
    }
  };

  const handleEdit = (agent: Agent) => {
    setEditingId(agent.id);
    setFormData({
      name: agent.name,
      description: agent.description,
      system_prompt: agent.system_prompt,
      icon: agent.icon,
      icon_color: agent.icon_color,
      category: agent.category,
    });
    setShowForm(true);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">Agent管理</h2>
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors flex items-center gap-2"
        >
          <span>+</span>
          <span>添加Agent</span>
        </button>
      </div>

      {/* Agent表单 */}
      {showForm && (
        <div className="bg-slate-700 rounded-lg p-6 mb-6 border border-slate-600">
          <h3 className="text-lg font-semibold text-white mb-4">
            {editingId ? '编辑Agent' : '添加新Agent'}
          </h3>
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Agent名称 <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  placeholder="例如：产品经理助手"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  分类 <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  placeholder="例如：AI工具"
                  required
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  描述 <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  placeholder="简短描述Agent的功能"
                  required
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  系统提示词 <span className="text-red-400">*</span>
                </label>
                <textarea
                  value={formData.system_prompt}
                  onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 h-32"
                  placeholder="定义Agent的角色和能力..."
                  required
                />
                <p className="text-xs text-slate-500 mt-1">
                  系统提示词决定了Agent的行为和能力
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <button
                type="submit"
                className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
              >
                {editingId ? '保存修改' : '创建Agent'}
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="px-6 py-2 bg-slate-600 hover:bg-slate-500 text-white rounded-lg transition-colors"
              >
                取消
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Agent列表 */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
          <p className="text-slate-400 mt-2">加载中...</p>
        </div>
      ) : agents.length === 0 ? (
        <div className="bg-slate-700 rounded-lg p-12 text-center border border-slate-600">
          <div className="text-6xl mb-4">🤖</div>
          <h3 className="text-lg font-medium text-white mb-2">暂无Agent</h3>
          <p className="text-slate-400 mb-4">添加一个Agent以开始使用</p>
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
          >
            添加Agent
          </button>
        </div>
      ) : (
        <div className="bg-slate-700 rounded-lg border border-slate-600 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-800">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">Agent名称</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">描述</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">默认</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">状态</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-600">
              {agents.map((agent) => (
                <tr key={agent.id} className="hover:bg-slate-600/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="text-white font-medium">{agent.name}</div>
                    <div className="text-xs text-slate-400">{agent.category}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-300 max-w-[300px] truncate">
                    {agent.description}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {agent.is_default ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
                        默认
                      </span>
                    ) : (
                      <button
                        onClick={() => handleSetDefault(agent.id, agent.name)}
                        className="text-sm text-slate-400 hover:text-cyan-400 transition-colors"
                      >
                        设为默认
                      </button>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                      agent.is_active
                        ? 'bg-green-500/20 text-green-400 border-green-500/30'
                        : 'bg-red-500/20 text-red-400 border-red-500/30'
                    }`}>
                      {agent.is_active ? '启用' : '禁用'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <button
                        onClick={() => handleEdit(agent)}
                        className="px-3 py-1 text-sm bg-yellow-600/20 text-yellow-400 border border-yellow-500/30 rounded hover:bg-yellow-600/30 transition-colors"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDelete(agent.id, agent.name)}
                        className="px-3 py-1 text-sm bg-red-600/20 text-red-400 border border-red-500/30 rounded hover:bg-red-600/30 transition-colors"
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}    </div>
  );
}
