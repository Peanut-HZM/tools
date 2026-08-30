import { useState, useEffect } from 'react';
import { agentApi, Agent, AgentHarnessUpdate } from '../../services/agentApi';
import EvalDialog from './EvalDialog';
import { useToast } from '../../hooks/useToast';
import { Badge } from '@/components/ui/Badge';

/** 默认 embedding 配置 */
const DEFAULT_EMBEDDING_CONFIG: Record<string, any> = {
  embedding_provider: 'openai',
  embedding_model: 'text-embedding-3-small',
  embedding_api_key: '',
  embedding_base_url: '',
  auto_inject: true,
  auto_inject_top_k: 5,
  auto_inject_threshold: 0.7,
  auto_inject_timeout_seconds: 5,
};

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
    icon_color: 'bg-accent',
    category: 'AI工具',
  });
  // P2-④: 可见性（提交时随 formData 一并保存）

  // Harness 扩展字段
  const [memoryLongTermEnabled, setMemoryLongTermEnabled] = useState(false);
  const [memoryProceduralEnabled, setMemoryProceduralEnabled] = useState(false);
  const [sandboxEnabled, setSandboxEnabled] = useState(false);
  const [visibility, setVisibility] = useState<'public' | 'private' | 'unlisted'>('public');
  const [evalAgent, setEvalAgent] = useState<Agent | null>(null);
  const [memoryLongTermConfig, setMemoryLongTermConfig] = useState<Record<string, any>>(
    { ...DEFAULT_EMBEDDING_CONFIG },
  );

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
      icon_color: 'bg-accent',
      category: 'AI工具',
    });
    setMemoryLongTermEnabled(false);
    setMemoryLongTermConfig({ ...DEFAULT_EMBEDDING_CONFIG });
    setEditingId(null);
    setVisibility('public');
    setShowForm(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      let agentId: string;
      const payload = { ...formData, visibility };
      if (editingId) {
        await agentApi.updateAgent(editingId, payload);
        agentId = editingId;
      } else {
        const created = await agentApi.createAgent(payload);
        agentId = created.id;
      }
      // 保存 harness 扩展字段
      const harnessData: AgentHarnessUpdate = {
        memory_procedural_enabled: memoryProceduralEnabled,
        sandbox_enabled: sandboxEnabled,
        memory_long_term_enabled: memoryLongTermEnabled,
        memory_long_term_config: memoryLongTermEnabled
          ? { ...memoryLongTermConfig }
          : {},
      };
      await agentApi.updateAgentHarness(agentId, harnessData);
      success(editingId ? 'Agent更新成功' : 'Agent创建成功');
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

  // P2-④: 导出 Agent bundle（下载 JSON 文件）
  const handleExport = async (agent: Agent) => {
    try {
      const bundle = await agentApi.exportAgentBundle(agent.id);
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `agent-${agent.name}.bundle.json`;
      link.click();
      URL.revokeObjectURL(url);
      success('导出成功（注意：bundle 可能含工具连接配置，请勿外传）');
    } catch (err) {
      error('导出失败');
      console.error('Failed to export agent:', err);
    }
  };

  // P2-④: 导入 Agent bundle（文件选择）
  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    try {
      const text = await file.text();
      const bundle = JSON.parse(text);
      const result = await agentApi.importAgentBundle(bundle);
      const warnText = result.warnings.length > 0 ? `（警告: ${result.warnings.join('; ')}）` : '';
      success(`导入成功: ${result.agent.name}${warnText}`);
      loadAgents();
    } catch (err) {
      error(err instanceof Error ? err.message : '导入失败（文件格式不合法？）');
      console.error('Failed to import agent:', err);
    }
  };

  const handleEdit = async (agent: Agent) => {
    setEditingId(agent.id);
    setVisibility(agent.visibility ?? 'public');
    setFormData({
      name: agent.name,
      description: agent.description,
      system_prompt: agent.system_prompt,
      icon: agent.icon,
      icon_color: agent.icon_color,
      category: agent.category,
    });
    // 加载 harness 扩展字段
    try {
      const harness = await agentApi.getAgentHarness(agent.id);
      setMemoryLongTermEnabled(!!harness.memory_long_term_enabled);
      setMemoryProceduralEnabled(!!harness.memory_procedural_enabled);
      setSandboxEnabled(!!harness.sandbox_enabled);
      setMemoryLongTermConfig({
        ...DEFAULT_EMBEDDING_CONFIG,
        ...(harness.memory_long_term_config || {}),
      });
    } catch (err) {
      console.warn('加载 harness 配置失败:', err);
      setMemoryLongTermEnabled(false);
      setMemoryLongTermConfig({ ...DEFAULT_EMBEDDING_CONFIG });
    }
    setShowForm(true);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-ink">Agent管理</h2>
        <div className="flex items-center gap-3">
          <label className="px-4 py-2 bg-surface-2 hover:bg-surface-3 text-ink rounded-lg transition-colors cursor-pointer">
            导入 bundle
            <input
              type="file"
              accept=".json,application/json"
              className="hidden"
              onChange={handleImportFile}
            />
          </label>
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 bg-accent hover:bg-accent-hover text-ink-inverse rounded-lg transition-colors flex items-center gap-2"
          >
            <span>+</span>
            <span>添加Agent</span>
          </button>
        </div>
      </div>

      {/* Agent表单 */}
      {showForm && (
        <div className="bg-surface-2 rounded-lg p-6 mb-6 border border-border">
          <h3 className="text-lg font-semibold text-ink mb-4">
            {editingId ? '编辑Agent' : '添加新Agent'}
          </h3>
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-ink-muted mb-2">
                  Agent名称 <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 bg-surface-1 border border-border rounded-lg text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
                  placeholder="例如：产品经理助手"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-ink-muted mb-2">
                  分类 <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full px-3 py-2 bg-surface-1 border border-border rounded-lg text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
                  placeholder="例如：AI工具"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-ink-muted mb-2">
                  可见性
                </label>
                <select
                  value={visibility}
                  onChange={(e) => setVisibility(e.target.value as 'public' | 'private' | 'unlisted')}
                  className="w-full px-3 py-2 bg-surface-1 border border-border rounded-lg text-ink focus:outline-none focus:ring-2 focus:ring-accent"
                >
                  <option value="public">public（所有人可用，进市场）</option>
                  <option value="unlisted">unlisted（所有人可用，不进市场）</option>
                  <option value="private">private（仅自己与管理员）</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-ink-muted mb-2">
                  描述 <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 bg-surface-1 border border-border rounded-lg text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
                  placeholder="简短描述Agent的功能"
                  required
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-ink-muted mb-2">
                  系统提示词 <span className="text-danger">*</span>
                </label>
                <textarea
                  value={formData.system_prompt}
                  onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                  className="w-full px-3 py-2 bg-surface-1 border border-border rounded-lg text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent h-32"
                  placeholder="定义Agent的角色和能力..."
                  required
                />
                <p className="text-xs text-ink-faint mt-1">
                  系统提示词决定了Agent的行为和能力
                </p>
              </div>
            </div>

            {/* 长期记忆开关 */}
            <div className="border-t border-border pt-4 mb-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={memoryLongTermEnabled}
                  onChange={(e) => setMemoryLongTermEnabled(e.target.checked)}
                  className="h-4 w-4 rounded border-border text-accent focus:ring-accent"
                />
                <span className="text-sm font-medium text-ink-muted">
                  启用长期记忆
                </span>
              </label>
              <p className="text-xs text-ink-faint mt-1 ml-7">
                开启后 Agent 将跨会话保留用户相关记忆
              </p>
            </div>

            {/* 程序性记忆（技能）开关 */}
            <div className="border-t border-border pt-4 mb-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={memoryProceduralEnabled}
                  onChange={(e) => setMemoryProceduralEnabled(e.target.checked)}
                  className="h-4 w-4 rounded border-border text-accent focus:ring-accent"
                />
                <span className="text-sm font-medium text-ink-muted">
                  启用技能（程序性记忆）
                </span>
              </label>
              <p className="text-xs text-ink-faint mt-1 ml-7">
                开启后 Agent 可沉淀/复用命名操作流程（skill_save / skill_read）
              </p>
            </div>

            {/* 代码沙箱开关 */}
            <div className="border-t border-border pt-4 mb-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={sandboxEnabled}
                  onChange={(e) => setSandboxEnabled(e.target.checked)}
                  className="h-4 w-4 rounded border-border text-accent focus:ring-accent"
                />
                <span className="text-sm font-medium text-ink-muted">
                  启用代码沙箱（文件读写 + 代码执行）
                </span>
              </label>
              <p className="text-xs text-ink-faint mt-1 ml-7">
                开启后 Agent 可在工作区内读写文件并执行 Python（进程级隔离，无网络/文件系统强隔离）
              </p>
            </div>

            {/* Embedding 配置块 */}
            {memoryLongTermEnabled && (
              <div className="space-y-3 mb-4 p-4 bg-surface-1 rounded-lg border border-border">
                <h4 className="font-medium text-sm text-ink">Embedding 配置</h4>

                <div>
                  <label className="block text-sm text-ink-muted mb-1">Provider</label>
                  <select
                    value={memoryLongTermConfig?.embedding_provider || 'openai'}
                    onChange={(e) => setMemoryLongTermConfig({
                      ...memoryLongTermConfig,
                      embedding_provider: e.target.value,
                    })}
                    className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                  >
                    <option value="openai">OpenAI</option>
                    <option value="dashscope">DashScope (通义千问)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-ink-muted mb-1">模型名</label>
                  <input
                    type="text"
                    value={memoryLongTermConfig?.embedding_model || 'text-embedding-3-small'}
                    onChange={(e) => setMemoryLongTermConfig({
                      ...memoryLongTermConfig,
                      embedding_model: e.target.value,
                    })}
                    className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-ink text-sm placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
                    placeholder="text-embedding-3-small"
                  />
                </div>

                <div>
                  <label className="block text-sm text-ink-muted mb-1">
                    API Key（可选，留空使用全局默认）
                  </label>
                  <input
                    type="password"
                    value={memoryLongTermConfig?.embedding_api_key || ''}
                    onChange={(e) => setMemoryLongTermConfig({
                      ...memoryLongTermConfig,
                      embedding_api_key: e.target.value,
                    })}
                    className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-ink text-sm placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
                    placeholder="sk-..."
                  />
                </div>

                <div>
                  <label className="block text-sm text-ink-muted mb-1">
                    Base URL（可选）
                  </label>
                  <input
                    type="text"
                    value={memoryLongTermConfig?.embedding_base_url || ''}
                    onChange={(e) => setMemoryLongTermConfig({
                      ...memoryLongTermConfig,
                      embedding_base_url: e.target.value,
                    })}
                    className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-ink text-sm placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
                    placeholder="https://api.openai.com/v1"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={memoryLongTermConfig?.auto_inject !== false}
                    onChange={(e) => setMemoryLongTermConfig({
                      ...memoryLongTermConfig,
                      auto_inject: e.target.checked,
                    })}
                    id="auto-inject"
                    className="h-4 w-4 rounded border-border text-accent focus:ring-accent"
                  />
                  <label htmlFor="auto-inject" className="text-sm text-ink-muted">
                    自动检索注入
                  </label>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-sm text-ink-muted mb-1">Top K</label>
                    <input
                      type="number"
                      value={memoryLongTermConfig?.auto_inject_top_k ?? 5}
                      onChange={(e) => setMemoryLongTermConfig({
                        ...memoryLongTermConfig,
                        auto_inject_top_k: parseInt(e.target.value) || 5,
                      })}
                      className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                      min={1} max={20}
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-ink-muted mb-1">相似度阈值</label>
                    <input
                      type="number"
                      value={memoryLongTermConfig?.auto_inject_threshold ?? 0.7}
                      onChange={(e) => setMemoryLongTermConfig({
                        ...memoryLongTermConfig,
                        auto_inject_threshold: parseFloat(e.target.value) || 0.7,
                      })}
                      className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                      min={0} max={1} step={0.05}
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-ink-muted mb-1">超时（秒）</label>
                    <input
                      type="number"
                      value={memoryLongTermConfig?.auto_inject_timeout_seconds ?? 5}
                      onChange={(e) => setMemoryLongTermConfig({
                        ...memoryLongTermConfig,
                        auto_inject_timeout_seconds: parseInt(e.target.value) || 5,
                      })}
                      className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                      min={1} max={30}
                    />
                  </div>
                </div>
              </div>
            )}

            <div className="flex gap-4">
              <button
                type="submit"
                className="px-6 py-2 bg-accent hover:bg-accent-hover text-ink-inverse rounded-lg transition-colors"
              >
                {editingId ? '保存修改' : '创建Agent'}
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="px-6 py-2 bg-surface-3 hover:bg-surface-3 text-ink rounded-lg transition-colors"
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
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
          <p className="text-ink-muted mt-2">加载中...</p>
        </div>
      ) : agents.length === 0 ? (
        <div className="bg-surface-2 rounded-lg p-12 text-center border border-border">
          <div className="text-6xl mb-4">🤖</div>
          <h3 className="text-lg font-medium text-ink mb-2">暂无Agent</h3>
          <p className="text-ink-muted mb-4">添加一个Agent以开始使用</p>
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 bg-accent hover:bg-accent-hover text-ink-inverse rounded-lg transition-colors"
          >
            添加Agent
          </button>
        </div>
      ) : (
        <div className="bg-surface-2 rounded-lg border border-border overflow-hidden">
          <table className="w-full">
            <thead className="bg-surface-1">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-ink-muted">Agent名称</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-ink-muted">描述</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-ink-muted">默认</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-ink-muted">状态</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-ink-muted">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {agents.map((agent) => (
                <tr key={agent.id} className="hover:bg-surface-3/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="text-ink font-medium">{agent.name}</div>
                    <div className="text-xs text-ink-muted">{agent.category}</div>
                  </td>
                  <td className="px-4 py-3 text-ink-muted max-w-[300px] truncate">
                    {agent.description}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {agent.is_default ? (
                      <Badge variant="success">
                        默认
                      </Badge>
                    ) : (
                      <button
                        onClick={() => handleSetDefault(agent.id, agent.name)}
                        className="text-sm text-ink-muted hover:text-accent transition-colors"
                      >
                        设为默认
                      </button>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge variant={agent.is_active ? 'success' : 'destructive'}>
                      {agent.is_active ? '启用' : '禁用'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <button
                        onClick={() => handleEdit(agent)}
                        className="px-3 py-1 text-sm bg-warning/20 text-warning border border-warning/30 rounded hover:bg-warning/30 transition-colors"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => setEvalAgent(agent)}
                        className="px-3 py-1 text-sm bg-accent/20 text-accent border border-accent/30 rounded hover:bg-accent/30 transition-colors"
                      >
                        评估
                      </button>
                      <button
                        onClick={() => handleExport(agent)}
                        className="px-3 py-1 text-sm bg-surface-2 text-ink border border-border rounded hover:bg-surface-3 transition-colors"
                      >
                        导出
                      </button>
                      <button
                        onClick={() => handleDelete(agent.id, agent.name)}
                        className="px-3 py-1 text-sm bg-danger/20 text-danger border border-danger/30 rounded hover:bg-danger/30 transition-colors"
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
      )}

      {/* P3-⑨: 评测弹窗 */}
      {evalAgent && (
        <EvalDialog
          agentId={evalAgent.id}
          agentName={evalAgent.name}
          onClose={() => setEvalAgent(null)}
        />
      )}
    </div>
  );
}
