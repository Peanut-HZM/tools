/**
 * 模型 Tab — 列表 + CRUD + 设置默认
 */
import { useState, useEffect } from 'react';
import { llmModelApi, LLMModel, CreateModelRequest } from '../../../services/llmModelApi';
import { llmProviderApi, LLMProvider } from '../../../services/llmProviderApi';
import { useToast } from '../../../hooks/useToast';
import ModelDialog from './ModelDialog';
import DeleteConfirmModal from './DeleteConfirmModal';

/**
 * 按 priority 升序排序模型列表；priority 相同时按 id 字典序稳定排序
 * priority 为 null/undefined 时兜底为 100
 */
export function sortModelsByPriority(models: LLMModel[]): LLMModel[] {
  return [...models].sort((a, b) => {
    const p = (a.priority ?? 100) - (b.priority ?? 100);
    return p !== 0 ? p : a.id.localeCompare(b.id);
  });
}

export default function ModelsTab() {
  const [models, setModels] = useState<LLMModel[]>([]);
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [loading, setLoading] = useState(false);

  // 弹窗状态
  const [showDialog, setShowDialog] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [editing, setEditing] = useState<LLMModel | null>(null);
  const [deleting, setDeleting] = useState<{ id: string; name: string } | null>(null);

  // 筛选
  const [categoryFilter, setCategoryFilter] = useState<'all' | 'chat' | 'code'>('all');

  const [submitting, setSubmitting] = useState(false);
  const { success, error } = useToast();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [modelsData, providersData] = await Promise.all([
        llmModelApi.list(),
        llmProviderApi.list(true),
      ]);
      setModels(modelsData);
      setProviders(providersData);
    } catch {
      error('加载数据失败');
    }
    setLoading(false);
  };

  const handleAdd = () => { setEditing(null); setShowDialog(true); };
  const handleEdit = (m: LLMModel) => { setEditing(m); setShowDialog(true); };

  const handleDeleteClick = (m: LLMModel) => {
    setDeleting({ id: m.id, name: m.name });
    setShowDeleteModal(true);
  };

  const handleDelete = async () => {
    if (!deleting) return;
    setSubmitting(true);
    try {
      await llmModelApi.delete(deleting.id);
      success('模型已删除');
      setShowDeleteModal(false);
      setDeleting(null);
      loadData();
    } catch { error('删除失败'); }
    setSubmitting(false);
  };

  const handleSubmit = async (data: CreateModelRequest) => {
    setSubmitting(true);
    try {
      if (editing) {
        await llmModelApi.update(editing.id, data);
        success('模型已更新');
      } else {
        await llmModelApi.create(data);
        success('模型已创建');
      }
      setShowDialog(false);
      setEditing(null);
      loadData();
    } catch (err: any) {
      error(err?.response?.data?.detail || (editing ? '更新失败' : '创建失败'));
      throw err;
    }
    setSubmitting(false);
  };

  // 设为全局默认
  const handleSetDefault = async (id: string, name: string) => {
    try {
      await llmModelApi.setDefault(id);
      success(`已将 "${name}" 设为全局默认`);
      loadData();
    } catch { error('设置默认失败'); }
  };

  // 设为分类默认
  const handleSetCategoryDefault = async (m: LLMModel) => {
    try {
      await llmModelApi.setDefault(m.id, m.category);
      success(`已将 "${m.name}" 设为 [${m.category === 'chat' ? '对话' : '编程'}] 分类默认`);
      loadData();
    } catch { error('设置分类默认失败'); }
  };

  const getCategoryLabel = (c: string) => c === 'code' ? '编程' : '对话';
  const getCategoryColor = (c: string) =>
    c === 'code'
      ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
      : 'bg-blue-500/20 text-blue-400 border-blue-500/30';

  const filtered = sortModelsByPriority(
    categoryFilter === 'all' ? models : models.filter((m) => m.category === categoryFilter)
  );

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <p className="text-slate-400 text-sm">管理大模型（关联供应商，设置默认等）</p>
        <button
          onClick={handleAdd}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors flex items-center gap-2"
        >
          <span>+</span><span>新建模型</span>
        </button>
      </div>

      {/* 分类筛选 */}
      <div className="flex gap-2 mb-4">
        {([['all', '全部'], ['chat', '对话'], ['code', '编程']] as const).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setCategoryFilter(key)}
            className={`px-4 py-2 rounded-lg transition-colors ${
              categoryFilter === key
                ? 'bg-cyan-600 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
          <p className="text-slate-400 mt-2">加载中...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-slate-700 rounded-lg p-12 text-center border border-slate-600">
          <div className="text-6xl mb-4">🤖</div>
          <h3 className="text-lg font-medium text-white mb-2">暂无模型</h3>
          <p className="text-slate-400 mb-4">新建模型以开始使用大模型功能</p>
          <button onClick={handleAdd} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors">
            新建模型
          </button>
        </div>
      ) : (
        <div className="bg-slate-700 rounded-lg border border-slate-600 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-800">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">名称</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">模型标识</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">供应商</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-slate-300">分类</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">优先级</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">默认</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">状态</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-slate-300">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-600">
              {filtered.map((m) => (
                <tr key={m.id} className="hover:bg-slate-600/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="text-white font-medium">{m.name}</div>
                    {m.notes && (
                      <div className="text-xs text-slate-500 mt-1 truncate max-w-[180px]" title={m.notes}>
                        📝 {m.notes}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-sm text-cyan-300">{m.model_name}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-slate-300 text-sm">{m.provider_name || '-'}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getCategoryColor(m.category)}`}>
                      {getCategoryLabel(m.category)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="font-mono text-sm text-amber-300">{m.priority ?? 100}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex flex-col items-center gap-1">
                      {m.is_default ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
                          ★ 全局
                        </span>
                      ) : (
                        <button
                          onClick={() => handleSetDefault(m.id, m.name)}
                          className="text-xs text-slate-400 hover:text-cyan-400 transition-colors"
                        >
                          设全局
                        </button>
                      )}
                      {m.is_default_for_category ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
                          ★ 分类
                        </span>
                      ) : (
                        <button
                          onClick={() => handleSetCategoryDefault(m)}
                          className="text-xs text-slate-400 hover:text-yellow-400 transition-colors"
                        >
                          设分类
                        </button>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                      m.is_active
                        ? 'bg-green-500/20 text-green-400 border-green-500/30'
                        : 'bg-red-500/20 text-red-400 border-red-500/30'
                    }`}>
                      {m.is_active ? '启用' : '禁用'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        onClick={() => handleEdit(m)}
                        className="px-2 py-1 text-xs bg-yellow-600/20 text-yellow-400 border border-yellow-500/30 rounded hover:bg-yellow-600/30 transition-colors"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDeleteClick(m)}
                        className="px-2 py-1 text-xs bg-red-600/20 text-red-400 border border-red-500/30 rounded hover:bg-red-600/30 transition-colors"
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

      <ModelDialog
        isOpen={showDialog}
        onClose={() => { setShowDialog(false); setEditing(null); }}
        onSubmit={handleSubmit}
        editing={editing}
        providers={providers}
        isLoading={submitting}
      />

      <DeleteConfirmModal
        isOpen={showDeleteModal}
        onClose={() => { setShowDeleteModal(false); setDeleting(null); }}
        onConfirm={handleDelete}
        configName={deleting?.name || ''}
        isLoading={submitting}
      />
    </div>
  );
}
