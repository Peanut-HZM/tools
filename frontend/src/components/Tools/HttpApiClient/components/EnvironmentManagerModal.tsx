/**
 * EnvironmentManagerModal - 环境管理弹窗（Apifox 风格）
 *
 * 功能：
 * - 环境列表：新建 / 重命名 / 删除 / 激活
 * - 每个环境：前置 URL（baseUrl）+ 变量表（Key-Value）
 */

import { useState, useEffect } from 'react';
import { X, Plus, Trash2, Check, Globe2, Pencil } from 'lucide-react';
import {
  Environment,
  createEnvironment,
  updateEnvironment,
  deleteEnvironment,
} from '../../../../services/httpClientApi';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useToast } from '../../../../contexts/ToastContext';

interface EnvironmentManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  environments: Environment[];
  activeEnvironment: Environment | null;
  /** 环境数据变更后由父组件重新加载 */
  onChanged: () => void;
}

export default function EnvironmentManagerModal({
  isOpen,
  onClose,
  environments,
  activeEnvironment,
  onChanged,
}: EnvironmentManagerModalProps) {
  const toast = useToast();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [nameDraft, setNameDraft] = useState('');
  const [newEnvName, setNewEnvName] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setSelectedId(activeEnvironment?.id || environments[0]?.id || null);
    }
  }, [isOpen, activeEnvironment, environments]);

  const selected = environments.find(e => e.id === selectedId) || null;

  const handleCreate = async () => {
    const name = newEnvName.trim();
    if (!name) return;
    setSaving(true);
    try {
      const created = await createEnvironment({ name, is_active: false });
      setNewEnvName('');
      setSelectedId(created.id);
      onChanged();
      toast.success('环境已创建');
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || '创建环境失败');
    } finally {
      setSaving(false);
    }
  };

  const handleRename = async (env: Environment) => {
    const name = nameDraft.trim();
    setEditingName(null);
    if (!name || name === env.name) return;
    try {
      await updateEnvironment(env.id, { name });
      onChanged();
      toast.success('环境已重命名');
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || '重命名失败');
    }
  };

  const handleDelete = async (env: Environment) => {
    if (!confirm(`确定删除环境 "${env.name}"？其中的变量将一并删除。`)) return;
    try {
      await deleteEnvironment(env.id);
      if (selectedId === env.id) setSelectedId(null);
      onChanged();
      toast.success('环境已删除');
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || '删除失败');
    }
  };

  const handleActivate = async (env: Environment) => {
    try {
      await updateEnvironment(env.id, { is_active: true });
      onChanged();
      toast.success(`已切换到环境「${env.name}」`);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || '激活失败');
    }
  };

  // 更新 baseUrl / 变量（输入即保存，防抖由后端幂等保证）
  const patchEnv = async (envId: string, patch: { base_url?: string; variables?: Record<string, string> }) => {
    try {
      await updateEnvironment(envId, patch);
      onChanged();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || '保存失败');
    }
  };

  const handleBaseUrlChange = (env: Environment, value: string) => {
    // 保存时去掉尾部斜杠（与后端一致）
    patchEnv(env.id, { base_url: value.replace(/\/+$/, '') });
  };

  const handleVariablesChange = (env: Environment, varsText: string) => {
    const variables: Record<string, string> = {};
    for (const line of varsText.split('\n')) {
      if (!line.trim()) continue;
      const idx = line.indexOf(':') !== -1 ? line.indexOf(':') : line.indexOf('=');
      if (idx > 0) {
        const key = line.slice(0, idx).trim();
        const value = line.slice(idx + 1).trim();
        if (key) variables[key] = value;
      }
    }
    patchEnv(env.id, { variables });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-surface-1 rounded-lg w-full max-w-3xl max-h-[80vh] flex flex-col border border-border">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Globe2 className="w-5 h-5 text-accent-secondary" />
            <h2 className="text-lg font-semibold">环境管理</h2>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        <div className="flex-1 flex overflow-hidden">
          {/* 左侧：环境列表 */}
          <div className="w-56 border-r border-border flex flex-col overflow-hidden">
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {environments.map(env => (
                <div
                  key={env.id}
                  onClick={() => setSelectedId(env.id)}
                  className={`
                    group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors
                    ${selectedId === env.id ? 'bg-accent-secondary/15 text-ink' : 'text-ink-muted hover:bg-surface-2/60'}
                  `}
                >
                  {env.is_active && <span className="w-1.5 h-1.5 rounded-full bg-success flex-shrink-0" title="当前激活" />}
                  {editingName === env.id ? (
                    <Input
                      autoFocus
                      value={nameDraft}
                      onChange={(e) => setNameDraft(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      onBlur={() => handleRename(env)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleRename(env);
                        if (e.key === 'Escape') setEditingName(null);
                      }}
                      className="h-6 text-sm px-1"
                    />
                  ) : (
                    <span className="flex-1 truncate">{env.name}</span>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-5 w-5 opacity-0 group-hover:opacity-100 text-ink-faint hover:text-ink"
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingName(env.id);
                      setNameDraft(env.name);
                    }}
                  >
                    <Pencil className="w-3 h-3" />
                  </Button>
                </div>
              ))}
            </div>
            {/* 新建环境 */}
            <div className="p-2 border-t border-border flex items-center gap-1">
              <Input
                type="text"
                value={newEnvName}
                onChange={(e) => setNewEnvName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                placeholder="新环境名称"
                className="h-8 text-xs"
              />
              <Button variant="ghost" size="icon" onClick={handleCreate} disabled={saving || !newEnvName.trim()} className="h-8 w-8 text-accent-secondary">
                <Plus className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* 右侧：环境详情 */}
          <div className="flex-1 overflow-y-auto p-5">
            {!selected ? (
              <div className="text-ink-faint text-sm text-center py-16">
                选择左侧环境查看详情，或新建一个环境
              </div>
            ) : (
              <div className="space-y-5">
                {/* 激活按钮 */}
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">{selected.name}</h3>
                  {selected.is_active ? (
                    <span className="text-xs text-success flex items-center gap-1">
                      <Check className="w-3.5 h-3.5" />
                      当前激活
                    </span>
                  ) : (
                    <Button variant="outline" size="sm" onClick={() => handleActivate(selected)} className="text-xs h-7">
                      <Check className="w-3.5 h-3.5 mr-1" />
                      激活此环境
                    </Button>
                  )}
                </div>

                {/* 前置 URL */}
                <div className="space-y-1.5">
                  <label className="text-sm text-ink-muted font-medium">前置 URL（baseUrl）</label>
                  <Input
                    type="text"
                    defaultValue={selected.base_url || ''}
                    key={`base-${selected.id}-${selected.base_url}`}
                    onBlur={(e) => handleBaseUrlChange(selected, e.target.value)}
                    placeholder="https://api.example.com/v1（请求路径以 / 开头时自动拼接）"
                    className="text-sm font-mono"
                  />
                  <p className="text-xs text-ink-faint">
                    请求 URL 以 <code className="text-accent-secondary">/</code> 开头时自动拼接此前缀；
                    也可以在 URL 中使用 <code className="text-accent-secondary">{'{{baseUrl}}'}</code> 手动引用
                  </p>
                </div>

                {/* 变量表 */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-sm text-ink-muted font-medium">环境变量</label>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 text-ink-faint hover:text-danger"
                      title="删除环境"
                      onClick={() => handleDelete(selected)}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                  <textarea
                    key={`vars-${selected.id}`}
                    defaultValue={Object.entries(selected.variables || {})
                      .map(([k, v]) => `${k}: ${v}`)
                      .join('\n')}
                    onBlur={(e) => handleVariablesChange(selected, e.target.value)}
                    placeholder={'变量名: 变量值（每行一条，支持冒号或等号分隔）\n例如：\ntoken: eyJhbGci...\nuserId: 12345'}
                    className="w-full h-40 bg-canvas text-ink px-3 py-2 rounded-lg border border-border
                               font-mono text-sm resize-none focus:border-accent-secondary focus:outline-none"
                  />
                  <p className="text-xs text-ink-faint">
                    失焦自动保存。在请求中通过 <code className="text-accent-secondary">{'{{变量名}}'}</code> 引用；
                    断言/提取变量会把结果写入这里
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
