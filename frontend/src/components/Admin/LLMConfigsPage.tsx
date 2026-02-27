import { useState, useEffect } from 'react';
import { llmConfigApi, LLMConfig, CreateLLMConfigRequest } from '../../services/llmConfigApi';
import { useToast } from '../../hooks/useToast';
import { ToastContainer } from '../MarkdownEditor/Toast/Toast';

export default function LLMConfigsPage() {
  const [configs, setConfigs] = useState<LLMConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const { toasts, removeToast, success, error } = useToast();
  
  const [formData, setFormData] = useState<CreateLLMConfigRequest>({
    name: '',
    provider_type: 'openai',
    base_url: 'https://api.openai.com/v1',
    api_key: '',
    model_name: 'gpt-4',
    is_default: false,
    is_active: true,
  });

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    setLoading(true);
    try {
      const data = await llmConfigApi.getConfigs();
      setConfigs(data);
    } catch (err) {
      error('加载配置列表失败');
      console.error('Failed to load configs:', err);
    }
    setLoading(false);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      provider_type: 'openai',
      base_url: 'https://api.openai.com/v1',
      api_key: '',
      model_name: 'gpt-4',
      is_default: false,
      is_active: true,
    });
    setEditingId(null);
    setShowForm(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await llmConfigApi.updateConfig(editingId, formData);
        success('配置更新成功');
      } else {
        await llmConfigApi.createConfig(formData);
        success('配置创建成功');
      }
      resetForm();
      loadConfigs();
    } catch (err) {
      error(editingId ? '更新配置失败' : '创建配置失败');
      console.error('Failed to save config:', err);
    }
  };

  const handleTest = async (id: string) => {
    setTestingId(id);
    try {
      const result = await llmConfigApi.testConnection(id);
      if (result.success) {
        success(`连接测试成功！延迟: ${result.latency_ms}ms`);
      } else {
        error(`连接测试失败: ${result.message}`);
      }
    } catch (err) {
      error('测试连接时发生错误');
      console.error('Failed to test connection:', err);
    }
    setTestingId(null);
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确定要删除配置 "${name}" 吗？此操作不可恢复。`)) return;
    try {
      await llmConfigApi.deleteConfig(id);
      success('配置删除成功');
      loadConfigs();
    } catch (err) {
      error('删除配置失败');
      console.error('Failed to delete config:', err);
    }
  };

  const handleSetDefault = async (id: string, name: string) => {
    try {
      await llmConfigApi.setDefault(id);
      success(`已将 "${name}" 设为默认配置`);
      loadConfigs();
    } catch (err) {
      error('设置默认配置失败');
      console.error('Failed to set default config:', err);
    }
  };

  const handleEdit = (config: LLMConfig) => {
    setEditingId(config.id);
    setFormData({
      name: config.name,
      provider_type: config.provider_type,
      base_url: config.base_url,
      api_key: '', // API Key 不回填，留空表示不修改
      model_name: config.model_name,
      is_default: config.is_default,
      is_active: config.is_active,
      request_params: config.request_params,
    });
    setShowForm(true);
  };

  const getProviderLabel = (type: string) => {
    const labels: Record<string, string> = {
      openai: 'OpenAI',
      anthropic: 'Anthropic',
      azure_openai: 'Azure OpenAI',
      baidu: '百度文心',
      aliyun: '阿里通义',
      zhipu: '智谱 AI',
      openrouter: 'OpenRouter',
      deepseek: 'DeepSeek',
      moonshot: '月之暗面',
      other: '其他',
    };
    return labels[type] || type;
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">大模型配置管理</h2>
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors flex items-center gap-2"
        >
          <span>+</span>
          <span>添加配置</span>
        </button>
      </div>

      {/* 配置表单 */}
      {showForm && (
        <div className="bg-slate-700 rounded-lg p-6 mb-6 border border-slate-600">
          <h3 className="text-lg font-semibold text-white mb-4">
            {editingId ? '编辑配置' : '添加新配置'}
          </h3>
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  配置名称 <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  placeholder="例如：OpenAI GPT-4"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  供应商 <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  list="provider-suggestions"
                  value={formData.provider_type}
                  onChange={(e) => setFormData({ ...formData, provider_type: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  placeholder="例如：openai、anthropic、zhipu、openrouter 等"
                  required
                />
                <datalist id="provider-suggestions">
                  <option value="openai" />
                  <option value="anthropic" />
                  <option value="azure_openai" />
                  <option value="baidu" />
                  <option value="aliyun" />
                  <option value="zhipu" />
                  <option value="openrouter" />
                  <option value="deepseek" />
                  <option value="moonshot" />
                  <option value="other" />
                </datalist>
                <p className="text-xs text-slate-500 mt-1">
                  支持自定义输入，常用：openai、anthropic、zhipu（智谱）、openrouter 等
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Base URL <span className="text-red-400">*</span>
                </label>
                <input
                  type="url"
                  value={formData.base_url}
                  onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  placeholder="https://api.openai.com/v1"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  模型名称 <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={formData.model_name}
                  onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  placeholder="例如：gpt-4"
                  required
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  API Key <span className="text-red-400">*</span>
                  {editingId && (
                    <span className="text-slate-400 text-xs ml-2">（留空则保持原值不变）</span>
                  )}
                </label>
                <input
                  type="password"
                  value={formData.api_key}
                  onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  placeholder="请输入 API Key"
                  required={!editingId}
                />
              </div>

              <div className="md:col-span-2 flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_default}
                    onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                    className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-cyan-600 focus:ring-cyan-500"
                  />
                  <span className="text-slate-300">设为默认配置</span>
                </label>
                
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-cyan-600 focus:ring-cyan-500"
                  />
                  <span className="text-slate-300">启用配置</span>
                </label>
              </div>
            </div>

            <div className="flex gap-4">
              <button
                type="submit"
                className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
              >
                {editingId ? '保存修改' : '创建配置'}
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

      {/* 配置列表 */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
          <p className="text-slate-400 mt-2">加载中...</p>
        </div>
      ) : configs.length === 0 ? (
        <div className="bg-slate-700 rounded-lg p-12 text-center border border-slate-600">
          <div className="text-6xl mb-4">🤖</div>
          <h3 className="text-lg font-medium text-white mb-2">暂无大模型配置</h3>
          <p className="text-slate-400 mb-4">添加一个配置以开始使用大模型功能</p>
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
          >
            添加配置
          </button>
        </div>
      ) : (
        <div className="bg-slate-700 rounded-lg border border-slate-600 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-800">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">配置名称</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">供应商</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">模型</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">默认</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">状态</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-600">
              {configs.map((config) => (
                <tr key={config.id} className="hover:bg-slate-600/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="text-white font-medium">{config.name}</div>
                    <div className="text-xs text-slate-400 mt-1 truncate max-w-[200px]">
                      {config.base_url}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-600">
                      {getProviderLabel(config.provider_type)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{config.model_name}</td>
                  <td className="px-4 py-3 text-center">
                    {config.is_default ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
                        默认
                      </span>
                    ) : (
                      <button
                        onClick={() => handleSetDefault(config.id, config.name)}
                        className="text-sm text-slate-400 hover:text-cyan-400 transition-colors"
                      >
                        设为默认
                      </button>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                      config.is_active 
                        ? 'bg-green-500/20 text-green-400 border-green-500/30' 
                        : 'bg-red-500/20 text-red-400 border-red-500/30'
                    }`}>
                      {config.is_active ? '启用' : '禁用'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <button
                        onClick={() => handleTest(config.id)}
                        disabled={testingId === config.id}
                        className="px-3 py-1 text-sm bg-blue-600/20 text-blue-400 border border-blue-500/30 rounded hover:bg-blue-600/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {testingId === config.id ? '测试中...' : '测试'}
                      </button>
                      <button
                        onClick={() => handleEdit(config)}
                        className="px-3 py-1 text-sm bg-yellow-600/20 text-yellow-400 border border-yellow-500/30 rounded hover:bg-yellow-600/30 transition-colors"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDelete(config.id, config.name)}
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
      )}

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}
