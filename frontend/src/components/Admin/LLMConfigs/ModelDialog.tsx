/**
 * 模型新建/编辑弹窗
 */
import { useState, useEffect, useRef } from 'react';
import { CreateModelRequest, LLMModel, ModelCategory } from '../../../services/llmModelApi';
import { LLMProvider } from '../../../services/llmProviderApi';

const STORAGE_KEY_LAST_PROVIDER = 'llm_model_last_provider_id';

interface ModelDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateModelRequest) => Promise<void>;
  editing?: LLMModel | null;
  providers: LLMProvider[];
  isLoading?: boolean;
}

export default function ModelDialog({ isOpen, onClose, onSubmit, editing, providers, isLoading }: ModelDialogProps) {
  const modelNameManualRef = useRef(false);

  const [formData, setFormData] = useState<CreateModelRequest>({
    name: '',
    model_name: '',
    provider_id: '',
    request_params: '',
    category: 'chat',
    priority: 100,
    is_default: false,
    is_default_for_category: false,
    notes: '',
    is_active: true,
  });

  useEffect(() => {
    if (editing) {
      setFormData({
        name: editing.name,
        model_name: editing.model_name,
        provider_id: editing.provider_id,
        request_params: editing.request_params || '',
        category: editing.category as ModelCategory,
        priority: editing.priority ?? 100,
        is_default: editing.is_default,
        is_default_for_category: editing.is_default_for_category,
        notes: editing.notes || '',
        is_active: editing.is_active,
      });
    } else {
      // 新建模式：供应商默认使用上次选择的，模型标识联动标记重置
      const lastProviderId = localStorage.getItem(STORAGE_KEY_LAST_PROVIDER);
      const defaultProviderId =
        lastProviderId && providers.some((p) => p.id === lastProviderId)
          ? lastProviderId
          : providers[0]?.id || '';
      setFormData({
        name: '', model_name: '', provider_id: defaultProviderId,
        request_params: '', category: 'chat', priority: 100,
        is_default: false, is_default_for_category: false,
        notes: '', is_active: true,
      });
      modelNameManualRef.current = false;
    }
  }, [editing, isOpen, providers]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(formData);
    // 新建成功后记住供应商，供下次新建使用
    if (!editing && formData.provider_id) {
      localStorage.setItem(STORAGE_KEY_LAST_PROVIDER, formData.provider_id);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-slate-800 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden border border-slate-700">
        {/* 头部 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700 bg-slate-800/50">
          <h3 className="text-lg font-semibold text-white">
            {editing ? '编辑模型' : '新建模型'}
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
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                名称 <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => {
                  const newName = e.target.value;
                  const updates: Partial<CreateModelRequest> = { name: newName };
                  // 新建模式 + 用户未手动改过模型标识 → 自动同步
                  if (!editing && !modelNameManualRef.current) {
                    updates.model_name = newName;
                  }
                  setFormData({ ...formData, ...updates });
                }}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="例如：GPT-4o"
                required
              />
            </div>

            {/* 模型标识 */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                模型标识 <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={formData.model_name}
                onFocus={() => { modelNameManualRef.current = true; }}
                onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                placeholder="例如：gpt-4o"
                required
              />
            </div>

            {/* 供应商 */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                供应商 <span className="text-red-400">*</span>
              </label>
              <select
                value={formData.provider_id}
                onChange={(e) => setFormData({ ...formData, provider_id: e.target.value })}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-cyan-500"
                required
              >
                <option value="">请选择供应商</option>
                {providers.map((p) => (
                  <option key={p.id} value={p.id}>{p.name} ({p.provider_type})</option>
                ))}
              </select>
            </div>

            {/* 分类 */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                分类 <span className="text-red-400">*</span>
              </label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value as ModelCategory })}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-cyan-500"
              >
                <option value="chat">对话 (chat)</option>
                <option value="code">代码 (code)</option>
                <option value="voice">语音 (voice)</option>
                <option value="vision">视觉 (vision)</option>
                <option value="multimodal">全模态 (multimodal)</option>
                <option value="embedding">向量 (embedding)</option>
                <option value="image_polish">图像润色 (image_polish)</option>
                <option value="image_gen">图像生成 (image_gen)</option>
              </select>
            </div>

            {/* 优先级 */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">优先级</label>
              <input
                type="number"
                min={0}
                max={9999}
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: Number(e.target.value) || 100 })}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
              <div className="text-xs text-slate-500 mt-1">数字越小越优先，默认 100</div>
            </div>

            {/* 请求参数 */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                请求参数 <span className="text-slate-400 text-xs">（JSON 格式）</span>
              </label>
              <textarea
                value={formData.request_params}
                onChange={(e) => setFormData({ ...formData, request_params: e.target.value })}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 font-mono text-sm"
                placeholder='{"temperature": 0.7, "max_tokens": 4096}'
                rows={3}
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

            {/* 复选框 */}
            <div className="md:col-span-2 flex flex-wrap gap-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_default}
                  onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-900 text-cyan-600 focus:ring-cyan-500"
                />
                <span className="text-slate-300">全局默认</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_default_for_category}
                  onChange={(e) => setFormData({ ...formData, is_default_for_category: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-900 text-cyan-600 focus:ring-cyan-500"
                />
                <span className="text-slate-300">分类默认</span>
              </label>
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
