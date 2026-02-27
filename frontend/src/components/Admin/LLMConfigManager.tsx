import React, { useState, useEffect } from 'react';
import { llmConfigApi, LLMConfig } from '../../services/llmConfigApi';

const LLMConfigManager: React.FC = () => {
  const [configs, setConfigs] = useState<LLMConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    provider_type: 'openai',
    base_url: 'https://api.openai.com/v1',
    api_key: '',
    model_name: 'gpt-4',
    is_default: false,
  });

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    setLoading(true);
    try {
      const data = await llmConfigApi.getConfigs();
      setConfigs(data);
    } catch (error) {
      console.error('Failed to load configs:', error);
    }
    setLoading(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await llmConfigApi.updateConfig(editingId, formData);
      } else {
        await llmConfigApi.createConfig(formData);
      }
      setShowForm(false);
      setEditingId(null);
      setFormData({
        name: '',
        provider_type: 'openai',
        base_url: 'https://api.openai.com/v1',
        api_key: '',
        model_name: 'gpt-4',
        is_default: false,
      });
      loadConfigs();
    } catch (error) {
      console.error('Failed to save config:', error);
    }
  };

  const handleTest = async (id: string) => {
    try {
      const result = await llmConfigApi.testConnection(id);
      alert(result.success ? `连接成功! 延迟: ${result.latency_ms}ms` : `连接失败: ${result.message}`);
    } catch (error) {
      alert('测试连接失败');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除此配置吗？')) return;
    try {
      await llmConfigApi.deleteConfig(id);
      loadConfigs();
    } catch (error) {
      alert('删除失败');
    }
  };

  const handleSetDefault = async (id: string) => {
    try {
      await llmConfigApi.setDefault(id);
      loadConfigs();
    } catch (error) {
      alert('设置默认配置失败');
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">大模型配置管理</h2>
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          添加配置
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-slate-800 p-6 rounded-lg mb-6">
          <h3 className="text-lg font-semibold text-white mb-4">
            {editingId ? '编辑配置' : '添加配置'}
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-300 mb-2">配置名称</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 bg-slate-700 text-white rounded"
                required
              />
            </div>
            <div>
              <label className="block text-slate-300 mb-2">供应商</label>
              <select
                value={formData.provider_type}
                onChange={(e) => setFormData({ ...formData, provider_type: e.target.value })}
                className="w-full px-3 py-2 bg-slate-700 text-white rounded"
              >
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="azure_openai">Azure OpenAI</option>
                <option value="baidu">百度文心</option>
                <option value="aliyun">阿里通义</option>
                <option value="other">其他</option>
              </select>
            </div>
            <div>
              <label className="block text-slate-300 mb-2">Base URL</label>
              <input
                type="text"
                value={formData.base_url}
                onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                className="w-full px-3 py-2 bg-slate-700 text-white rounded"
                required
              />
            </div>
            <div>
              <label className="block text-slate-300 mb-2">模型名称</label>
              <input
                type="text"
                value={formData.model_name}
                onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                className="w-full px-3 py-2 bg-slate-700 text-white rounded"
                required
              />
            </div>
            <div className="col-span-2">
              <label className="block text-slate-300 mb-2">API Key</label>
              <input
                type="password"
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                className="w-full px-3 py-2 bg-slate-700 text-white rounded"
                required={!editingId}
                placeholder={editingId ? '留空则保持不变' : ''}
              />
            </div>
          </div>
          <div className="flex gap-4 mt-6">
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              保存
            </button>
            <button
              type="button"
              onClick={() => {
                setShowForm(false);
                setEditingId(null);
              }}
              className="px-4 py-2 bg-slate-600 text-white rounded hover:bg-slate-700"
            >
              取消
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="text-white">加载中...</div>
      ) : (
        <div className="bg-slate-800 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-700">
              <tr>
                <th className="px-4 py-3 text-left text-slate-300">名称</th>
                <th className="px-4 py-3 text-left text-slate-300">供应商</th>
                <th className="px-4 py-3 text-left text-slate-300">模型</th>
                <th className="px-4 py-3 text-left text-slate-300">默认</th>
                <th className="px-4 py-3 text-left text-slate-300">状态</th>
                <th className="px-4 py-3 text-left text-slate-300">操作</th>
              </tr>
            </thead>
            <tbody>
              {configs.map((config) => (
                <tr key={config.id} className="border-t border-slate-700">
                  <td className="px-4 py-3 text-white">{config.name}</td>
                  <td className="px-4 py-3 text-slate-300">{config.provider_type}</td>
                  <td className="px-4 py-3 text-slate-300">{config.model_name}</td>
                  <td className="px-4 py-3">
                    {config.is_default ? (
                      <span className="text-green-400">✓ 默认</span>
                    ) : (
                      <button
                        onClick={() => handleSetDefault(config.id)}
                        className="text-blue-400 hover:text-blue-300"
                      >
                        设为默认
                      </button>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={config.is_active ? 'text-green-400' : 'text-red-400'}>
                      {config.is_active ? '启用' : '禁用'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleTest(config.id)}
                        className="text-blue-400 hover:text-blue-300"
                      >
                        测试
                      </button>
                      <button
                        onClick={() => {
                          setEditingId(config.id);
                          setFormData({
                            name: config.name,
                            provider_type: config.provider_type,
                            base_url: config.base_url,
                            api_key: '',
                            model_name: config.model_name,
                            is_default: config.is_default,
                          });
                          setShowForm(true);
                        }}
                        className="text-yellow-400 hover:text-yellow-300"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDelete(config.id)}
                        className="text-red-400 hover:text-red-300"
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
    </div>
  );
};

export default LLMConfigManager;
