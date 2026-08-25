import { useState, useEffect } from 'react';
import { LLMConfig, CreateLLMConfigRequest, LLMConfigCategory } from '../../../services/llmConfigApi';

interface ConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateLLMConfigRequest) => Promise<void>;
  editingConfig?: LLMConfig | null;
  isLoading?: boolean;
}

export default function ConfigModal({ isOpen, onClose, onSubmit, editingConfig, isLoading }: ConfigModalProps) {
  const [formData, setFormData] = useState<CreateLLMConfigRequest>({
    name: '',
    provider_type: 'openai',
    base_url: 'https://api.openai.com/v1',
    api_key: '',
    model_name: 'gpt-4',
    category: 'chat',
    notes: '',
    is_default: false,
    is_active: true,
  });

  // 当编辑配置打开时，填充数据
  useEffect(() => {
    if (editingConfig) {
      setFormData({
        name: editingConfig.name,
        provider_type: editingConfig.provider_type,
        base_url: editingConfig.base_url,
        api_key: '', // API Key 不回填
        model_name: editingConfig.model_name,
        category: editingConfig.category || 'chat',
        notes: editingConfig.notes || '',
        is_default: editingConfig.is_default,
        is_active: editingConfig.is_active,
      });
    } else {
      // 重置表单
      setFormData({
        name: '',
        provider_type: 'openai',
        base_url: 'https://api.openai.com/v1',
        api_key: '',
        model_name: 'gpt-4',
        category: 'chat',
        notes: '',
        is_default: false,
        is_active: true,
      });
    }
  }, [editingConfig, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(formData);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* 弹窗内容 */}
      <div className="relative bg-surface-1 rounded-xl shadow-lg w-full max-w-2xl max-h-[90vh] overflow-hidden border border-border">
        {/* 头部 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-1/50">
          <h3 className="text-lg font-semibold text-ink-inverse">
            {editingConfig ? '编辑配置' : '添加新配置'}
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-ink-muted hover:text-ink-inverse transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 配置名称 */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-ink-muted mb-2">
                配置名称 <span className="text-danger">*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 bg-canvas border border-border rounded-lg text-ink-inverse placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-accent"
                placeholder="例如：OpenAI GPT-4"
                required
              />
            </div>

            {/* 供应商 */}
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-2">
                供应商 <span className="text-danger">*</span>
              </label>
              <input
                type="text"
                list="provider-suggestions"
                value={formData.provider_type}
                onChange={(e) => setFormData({ ...formData, provider_type: e.target.value })}
                className="w-full px-3 py-2 bg-canvas border border-border rounded-lg text-ink-inverse placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-accent"
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
              </datalist>
            </div>

            {/* 分类 */}
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-2">
                分类 <span className="text-danger">*</span>
              </label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value as LLMConfigCategory })}
                className="w-full px-3 py-2 bg-canvas border border-border rounded-lg text-ink-inverse focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <option value="chat">对话类型</option>
                <option value="code">编程类型</option>
              </select>
            </div>

            {/* Base URL */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-ink-muted mb-2">
                Base URL <span className="text-danger">*</span>
              </label>
              <input
                type="url"
                value={formData.base_url}
                onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                className="w-full px-3 py-2 bg-canvas border border-border rounded-lg text-ink-inverse placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-accent"
                placeholder="https://api.openai.com/v1"
                required
              />
            </div>

            {/* 模型名称 */}
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-2">
                模型名称 <span className="text-danger">*</span>
              </label>
              <input
                type="text"
                value={formData.model_name}
                onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                className="w-full px-3 py-2 bg-canvas border border-border rounded-lg text-ink-inverse placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-accent"
                placeholder="例如：gpt-4"
                required
              />
            </div>

            {/* API Key */}
            <div>
              <label className="block text-sm font-medium text-ink-muted mb-2">
                API Key <span className="text-danger">*</span>
                {editingConfig && <span className="text-ink-muted text-xs ml-2">（留空保持原值）</span>}
              </label>
              <input
                type="password"
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                className="w-full px-3 py-2 bg-canvas border border-border rounded-lg text-ink-inverse placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-accent"
                placeholder={editingConfig ? '••••••••' : '请输入 API Key'}
                required={!editingConfig}
              />
            </div>

            {/* 备注 */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-ink-muted mb-2">
                备注
              </label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="w-full px-3 py-2 bg-canvas border border-border rounded-lg text-ink-inverse placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-accent"
                placeholder="可选备注，方便识别此配置"
                rows={2}
              />
            </div>

            {/* 复选框 */}
            <div className="md:col-span-2 flex gap-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_default}
                  onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                  className="w-4 h-4 rounded border-border bg-canvas text-cyan-600 focus:ring-accent"
                />
                <span className="text-ink-muted">设为默认配置</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="w-4 h-4 rounded border-border bg-canvas text-cyan-600 focus:ring-accent"
                />
                <span className="text-ink-muted">启用配置</span>
              </label>
            </div>
          </div>

          {/* 底部按钮 */}
          <div className="flex gap-4 mt-6 pt-4 border-t border-border">
            <button
              type="submit"
              disabled={isLoading}
              className="px-6 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? '保存中...' : (editingConfig ? '保存修改' : '创建配置')}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 bg-surface-2 hover:bg-surface-3 text-ink-inverse rounded-lg transition-colors"
            >
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
