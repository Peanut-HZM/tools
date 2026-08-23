/**
 * 供应商新建/编辑弹窗
 */
import { useState, useEffect } from 'react';
import { CreateProviderRequest, LLMProvider } from '../../../services/llmProviderApi';

interface ProviderDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateProviderRequest) => Promise<void>;
  editing?: LLMProvider | null;
  isLoading?: boolean;
}

/** 供应商类型选项 */
const PROVIDER_TYPES = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'azure_openai', label: 'Azure OpenAI' },
  { value: 'baidu', label: '百度文心' },
  { value: 'aliyun', label: '阿里通义' },
  { value: 'doubao_seedream', label: '豆包 Seedream' },
  { value: 'qwen_image', label: '通义万相' },
  { value: 'zhipu', label: '智谱 AI' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'moonshot', label: '月之暗面' },
  { value: 'other', label: '其他' },
];

export default function ProviderDialog({ isOpen, onClose, onSubmit, editing, isLoading }: ProviderDialogProps) {
  const [formData, setFormData] = useState<CreateProviderRequest>({
    name: '',
    provider_type: 'openai',
    base_url: '',
    api_key: '',
    notes: '',
    is_active: true,
  });

  useEffect(() => {
    if (editing) {
      setFormData({
        name: editing.name,
        provider_type: editing.provider_type,
        base_url: editing.base_url,
        api_key: '',
        notes: editing.notes || '',
        is_active: editing.is_active,
      });
    } else {
      setFormData({ name: '', provider_type: 'openai', base_url: '', api_key: '', notes: '', is_active: true });
    }
  }, [editing, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(formData);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-slate-800 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden border border-slate-700">
        {/* 头部 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700 bg-slate-800/50">
          <h3 className="text-lg font-semibold text-white">
            {editing ? '编辑供应商' : '新建供应商'}
          </h3>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white transition-colors">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 名称 */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                名称 <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="例如：OpenAI-peanut"
                required
              />
            </div>

            {/* 供应商类型 */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                供应商类型 <span className="text-red-400">*</span>
              </label>
              <select
                value={formData.provider_type}
                onChange={(e) => setFormData({ ...formData, provider_type: e.target.value })}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-cyan-500"
              >
                {PROVIDER_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>

            {/* Base URL */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Base URL <span className="text-red-400">*</span>
              </label>
              <input
                type="url"
                value={formData.base_url}
                onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="https://api.openai.com/v1"
                required
              />
            </div>

            {/* API Key */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                API Key <span className="text-red-400">*</span>
                {editing && <span className="text-slate-400 text-xs ml-2">（留空保持原值）</span>}
              </label>
              <input
                type="password"
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder={editing ? '••••••••' : '请输入 API Key'}
                required={!editing}
              />
            </div>

            {/* 备注 */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-slate-300 mb-2">备注</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="可选备注"
                rows={2}
              />
            </div>

            {/* 启用 */}
            <div className="md:col-span-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-900 text-cyan-600 focus:ring-cyan-500"
                />
                <span className="text-slate-300">启用</span>
              </label>
            </div>
          </div>

          {/* 底部按钮 */}
          <div className="flex gap-4 mt-6 pt-4 border-t border-slate-700">
            <button
              type="submit"
              disabled={isLoading}
              className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? '保存中...' : (editing ? '保存修改' : '创建')}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
            >
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
