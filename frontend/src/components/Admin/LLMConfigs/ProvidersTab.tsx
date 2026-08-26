/**
 * 供应商 Tab — 列表 + CRUD + 连通性测试 + 揭示 Key
 */
import { useState, useEffect } from 'react';
import { llmProviderApi, LLMProvider, CreateProviderRequest } from '../../../services/llmProviderApi';
import { useToast } from '../../../hooks/useToast';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import ProviderDialog from './ProviderDialog';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import ApiKeyDisplay from './ApiKeyDisplay';

export default function ProvidersTab() {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [loading, setLoading] = useState(false);

  // 弹窗状态
  const [showDialog, setShowDialog] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [editing, setEditing] = useState<LLMProvider | null>(null);
  const [deleting, setDeleting] = useState<{ id: string; name: string } | null>(null);

  // 操作状态
  const [submitting, setSubmitting] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [revealedKey, setRevealedKey] = useState<Record<string, string>>({});

  const { success, error } = useToast();

  useEffect(() => { loadProviders(); }, []);

  const loadProviders = async () => {
    setLoading(true);
    try {
      const data = await llmProviderApi.list();
      setProviders(data);
    } catch {
      error('加载供应商列表失败');
    }
    setLoading(false);
  };

  // 新建
  const handleAdd = () => { setEditing(null); setShowDialog(true); };

  // 编辑
  const handleEdit = (p: LLMProvider) => { setEditing(p); setShowDialog(true); };

  // 删除确认
  const handleDeleteClick = (p: LLMProvider) => {
    setDeleting({ id: p.id, name: p.name });
    setShowDeleteModal(true);
  };

  // 确认删除
  const handleDelete = async () => {
    if (!deleting) return;
    setSubmitting(true);
    try {
      await llmProviderApi.delete(deleting.id);
      success('供应商已删除');
      setShowDeleteModal(false);
      setDeleting(null);
      loadProviders();
    } catch (err: any) {
      error(err?.response?.data?.detail || '删除失败');
    }
    setSubmitting(false);
  };

  // 提交表单
  const handleSubmit = async (data: CreateProviderRequest) => {
    setSubmitting(true);
    try {
      if (editing) {
        const payload: any = { ...data };
        if (!payload.api_key) delete payload.api_key;
        await llmProviderApi.update(editing.id, payload);
        success('供应商已更新');
      } else {
        await llmProviderApi.create(data);
        success('供应商已创建');
      }
      setShowDialog(false);
      setEditing(null);
      loadProviders();
    } catch (err: any) {
      error(err?.response?.data?.detail || (editing ? '更新失败' : '创建失败'));
      throw err;
    }
    setSubmitting(false);
  };

  // 切换启用
  const handleToggle = async (p: LLMProvider) => {
    try {
      await llmProviderApi.toggle(p.id);
      success(`${p.name} 已${p.is_active ? '禁用' : '启用'}`);
      loadProviders();
    } catch { error('切换状态失败'); }
  };

  // 测试连通性
  const handleTest = async (id: string) => {
    setTestingId(id);
    try {
      const result = await llmProviderApi.testConnection(id);
      if (result.success) {
        success(`连接成功！延迟: ${result.latency_ms}ms`);
      } else {
        error(`连接失败: ${result.message}`);
      }
    } catch { error('测试连接异常'); }
    setTestingId(null);
  };

  // 揭示 Key
  const handleReveal = async (id: string) => {
    if (revealedKey[id]) {
      // 已揭示 → 隐藏
      setRevealedKey((prev) => { const n = { ...prev }; delete n[id]; return n; });
      return;
    }
    try {
      const result = await llmProviderApi.reveal(id);
      setRevealedKey((prev) => ({ ...prev, [id]: result.api_key }));
    } catch { error('揭示 API Key 失败'); }
  };

  const getProviderLabel = (type: string) => {
    const labels: Record<string, string> = {
      openai: 'OpenAI', anthropic: 'Anthropic', azure_openai: 'Azure OpenAI',
      baidu: '百度文心', aliyun: '阿里通义', doubao_seedream: '豆包 Seedream',
      qwen_image: '通义万相', zhipu: '智谱 AI', openrouter: 'OpenRouter',
      deepseek: 'DeepSeek', moonshot: '月之暗面', other: '其他',
    };
    return labels[type] || type;
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <p className="text-ink-muted text-sm">管理大模型供应商（API Key、连接地址等）</p>
        <Button onClick={handleAdd} className="flex items-center gap-2">
          <span>+</span><span>新建供应商</span>
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
          <p className="text-ink-muted mt-2">加载中...</p>
        </div>
      ) : providers.length === 0 ? (
        <Card className="bg-surface-2 p-12 text-center">
          <div className="text-6xl mb-4">🔑</div>
          <h3 className="text-lg font-medium text-ink-inverse mb-2">暂无供应商</h3>
          <p className="text-ink-muted mb-4">新建供应商以开始配置大模型</p>
          <Button onClick={handleAdd}>
            新建供应商
          </Button>
        </Card>
      ) : (
        <Card className="bg-surface-2 overflow-hidden p-0">
          <table className="w-full">
            <thead className="bg-surface-1">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-ink-muted">名称</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-ink-muted">厂商</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-ink-muted">Base URL</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-ink-muted">API Key</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-ink-muted">状态</th>
                <th className="px-4 py-3 text-center text-sm font-medium text-ink-muted">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {providers.map((p) => (
                <tr key={p.id} className="hover:bg-surface-3/50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="text-ink-inverse font-medium">{p.name}</div>
                    {p.notes && (
                      <div className="text-xs text-ink-faint mt-1 truncate max-w-[200px]" title={p.notes}>
                        📝 {p.notes}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="secondary">
                      {getProviderLabel(p.provider_type)}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-ink-muted text-sm truncate max-w-[250px]" title={p.base_url}>
                      {p.base_url}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <ApiKeyDisplay
                      apiKeySuffix={p.api_key_suffix}
                      fullApiKey={revealedKey[p.id]}
                    />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button onClick={() => handleToggle(p)}>
                      <Badge variant={p.is_active ? 'success' : 'destructive'}>
                        {p.is_active ? '启用' : '禁用'}
                      </Badge>
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        onClick={() => handleTest(p.id)}
                        disabled={testingId === p.id}
                        className="px-2 py-1 text-xs bg-accent-info/20 text-accent-info border border-blue-500/30 rounded hover:bg-blue-600/30 transition-colors disabled:opacity-50"
                      >
                        {testingId === p.id ? '测试中...' : '测试'}
                      </button>
                      <button
                        onClick={() => handleReveal(p.id)}
                        className="px-2 py-1 text-xs bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 rounded hover:bg-emerald-600/30 transition-colors"
                      >
                        {revealedKey[p.id] ? '隐藏' : 'Key'}
                      </button>
                      <button
                        onClick={() => handleEdit(p)}
                        className="px-2 py-1 text-xs bg-yellow-600/20 text-yellow-400 border border-yellow-500/30 rounded hover:bg-yellow-600/30 transition-colors"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDeleteClick(p)}
                        className="px-2 py-1 text-xs bg-danger/20 text-danger border border-red-500/30 rounded hover:bg-red-600/30 transition-colors"
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <ProviderDialog
        isOpen={showDialog}
        onClose={() => { setShowDialog(false); setEditing(null); }}
        onSubmit={handleSubmit}
        editing={editing}
        isLoading={submitting}
      />

      <ConfirmDialog
        open={showDeleteModal}
        onOpenChange={(open) => { if (!open) { setShowDeleteModal(false); setDeleting(null); } }}
        title="确认删除"
        description={`确定要删除配置 "${deleting?.name || ''}" 吗？此操作不可恢复，请谨慎操作！`}
        confirmText="确认删除"
        variant="destructive"
        onConfirm={handleDelete}
      />
    </div>
  );
}
