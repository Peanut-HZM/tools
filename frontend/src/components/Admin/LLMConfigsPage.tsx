import { useState, useEffect } from 'react';
import { llmConfigApi, LLMConfig, CreateLLMConfigRequest } from '../../services/llmConfigApi';
import { useToast } from '../../hooks/useToast';
import { ApiKeyDisplay, ConfigModal, DeleteConfirmModal } from './LLMConfigs';

export default function LLMConfigsPage() {
  const [configs, setConfigs] = useState<LLMConfig[]>([]);
  const [loading, setLoading] = useState(false);
  
  // 弹窗状态
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [editingConfig, setEditingConfig] = useState<LLMConfig | null>(null);
  const [deletingConfig, setDeletingConfig] = useState<{ id: string; name: string } | null>(null);
  
  // 加载状态
  const [submitting, setSubmitting] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  
  // 分类筛选
  const [categoryFilter, setCategoryFilter] = useState<'all' | 'chat' | 'code'>('all');

  const { success, error  } = useToast();

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

  // 处理新增
  const handleAdd = () => {
    setEditingConfig(null);
    setShowConfigModal(true);
  };

  // 处理编辑
  const handleEdit = (config: LLMConfig) => {
    setEditingConfig(config);
    setShowConfigModal(true);
  };

  // 处理删除
  const handleDeleteClick = (config: LLMConfig) => {
    setDeletingConfig({ id: config.id, name: config.name });
    setShowDeleteModal(true);
  };

  // 确认删除
  const handleDelete = async () => {
    if (!deletingConfig) return;
    
    setSubmitting(true);
    try {
      await llmConfigApi.deleteConfig(deletingConfig.id);
      success('配置删除成功');
      setShowDeleteModal(false);
      setDeletingConfig(null);
      loadConfigs();
    } catch (err) {
      error('删除配置失败');
      console.error('Failed to delete config:', err);
    }
    setSubmitting(false);
  };

  // 处理表单提交
  const handleSubmit = async (data: CreateLLMConfigRequest) => {
    setSubmitting(true);
    try {
      if (editingConfig) {
        await llmConfigApi.updateConfig(editingConfig.id, data);
        success('配置更新成功');
      } else {
        await llmConfigApi.createConfig(data);
        success('配置创建成功');
      }
      setShowConfigModal(false);
      setEditingConfig(null);
      loadConfigs();
    } catch (err) {
      error(editingConfig ? '更新配置失败' : '创建配置失败');
      console.error('Failed to save config:', err);
      throw err; // 重新抛出错误，让 Modal 知道提交失败
    }
    setSubmitting(false);
  };

  // 测试连接
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

  // 设置默认
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

  const getCategoryLabel = (category?: string) => {
    return category === 'code' ? '编程' : '对话';
  };

  const getCategoryColor = (category?: string) => {
    return category === 'code' 
      ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
      : 'bg-blue-500/20 text-blue-400 border-blue-500/30';
  };

  // 筛选配置
  const filteredConfigs = categoryFilter === 'all' 
    ? configs 
    : configs.filter(c => c.category === categoryFilter);

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">大模型配置管理</h2>
        <button
          onClick={handleAdd}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors flex items-center gap-2"
        >
          <span>+</span>
          <span>添加配置</span>
        </button>
      </div>

      {/* 分类筛选 */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setCategoryFilter('all')}
          className={`px-4 py-2 rounded-lg transition-colors ${
            categoryFilter === 'all'
              ? 'bg-cyan-600 text-white'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          }`}
        >
          全部
        </button>
        <button
          onClick={() => setCategoryFilter('chat')}
          className={`px-4 py-2 rounded-lg transition-colors ${
            categoryFilter === 'chat'
              ? 'bg-blue-600 text-white'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          }`}
        >
          对话类型
        </button>
        <button
          onClick={() => setCategoryFilter('code')}
          className={`px-4 py-2 rounded-lg transition-colors ${
            categoryFilter === 'code'
              ? 'bg-purple-600 text-white'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          }`}
        >
          编程类型
        </button>
      </div>

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
            onClick={handleAdd}
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
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">分类</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">API Key</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">默认</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">状态</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-600">
              {filteredConfigs.map((config) => (
                <tr key={config.id} className="hover:bg-slate-600/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="text-white font-medium">{config.name}</div>
                    <div className="text-xs text-slate-400 mt-1 truncate max-w-[200px]">
                      {config.base_url}
                    </div>
                    {config.notes && (
                      <div className="text-xs text-slate-500 mt-1 truncate max-w-[200px]" title={config.notes}>
                        📝 {config.notes}
                      </div>
                    )}
                    <div className="text-xs text-slate-500 mt-1">
                      创建于: {new Date(config.created_at).toLocaleDateString('zh-CN')}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-600">
                      {getProviderLabel(config.provider_type)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getCategoryColor(config.category)}`}>
                      {getCategoryLabel(config.category)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <ApiKeyDisplay 
                      apiKeySuffix={config.api_key_suffix}
                      fullApiKey={config.api_key_suffix ? `sk-xxxx...${config.api_key_suffix}` : undefined}
                    />
                  </td>
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
                  <td className="px-4 py-3">
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
                        onClick={() => handleDeleteClick(config)}
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

      {/* 新增/编辑弹窗 */}
      <ConfigModal
        isOpen={showConfigModal}
        onClose={() => {
          setShowConfigModal(false);
          setEditingConfig(null);
        }}
        onSubmit={handleSubmit}
        editingConfig={editingConfig}
        isLoading={submitting}
      />

      {/* 删除确认弹窗 */}
      <DeleteConfirmModal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setDeletingConfig(null);
        }}
        onConfirm={handleDelete}
        configName={deletingConfig?.name || ''}
        isLoading={submitting}
      />    </div>
  );
}
