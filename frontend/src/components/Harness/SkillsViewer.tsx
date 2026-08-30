/**
 * SkillsViewer — Agent 技能（程序性记忆）查看器
 *
 * P2-② Memory procedural
 * 功能：
 *  - 列出当前用户对指定 Agent 的全部技能
 *  - 新增技能（name / trigger / content）
 *  - 删除指定技能
 *  - 显示每条技能的使用次数与启用状态
 */
import React, { useState, useEffect, useCallback } from 'react';
import { harnessSkillsApi, SkillEntry } from '../../api/harnessSkillsApi';

interface SkillsViewerProps {
  agentId: string;
}

export const SkillsViewer: React.FC<SkillsViewerProps> = ({ agentId }) => {
  const [skills, setSkills] = useState<SkillEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  // 新增表单
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [trigger, setTrigger] = useState('');
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadSkills = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const result = await harnessSkillsApi.list(agentId);
      setSkills(result.records);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : '加载技能失败';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    if (agentId) {
      loadSkills();
    }
  }, [loadSkills, agentId]);

  const handleDelete = async (skillName: string) => {
    if (!window.confirm(`确定要删除技能 "${skillName}" 吗？此操作不可恢复。`)) return;
    try {
      setError('');
      await harnessSkillsApi.remove(agentId, skillName);
      setSkills((prev) => prev.filter((s) => s.name !== skillName));
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : '删除失败';
      setError(message);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !trigger.trim() || !content.trim()) {
      setError('name / trigger / content 均为必填');
      return;
    }
    setSubmitting(true);
    try {
      setError('');
      await harnessSkillsApi.create(agentId, {
        name: name.trim(),
        trigger: trigger.trim(),
        content: content.trim(),
      });
      setName('');
      setTrigger('');
      setContent('');
      setShowForm(false);
      await loadSkills();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '保存失败';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* 操作栏 */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setShowForm((v) => !v)}
          className="px-4 py-2 bg-accent hover:bg-accent-hover text-ink-inverse rounded-lg transition-colors"
        >
          {showForm ? '收起表单' : '新增技能'}
        </button>
        <button
          type="button"
          onClick={loadSkills}
          disabled={loading}
          className="px-4 py-2 bg-surface-2 hover:bg-surface-3 text-ink rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          刷新
        </button>
      </div>

      {/* 新增表单 */}
      {showForm && (
        <form onSubmit={handleCreate} className="space-y-2 p-3 border border-border rounded-lg bg-surface-1">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="技能名（如 deploy_check）"
            maxLength={100}
            className="w-full px-3 py-2 bg-canvas border border-border rounded text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <input
            type="text"
            value={trigger}
            onChange={(e) => setTrigger(e.target.value)}
            placeholder="何时使用（触发条件）"
            className="w-full px-3 py-2 bg-canvas border border-border rounded text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="技能完整内容（步骤/规则）"
            rows={4}
            className="w-full px-3 py-2 bg-canvas border border-border rounded text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 bg-accent hover:bg-accent-hover text-ink-inverse rounded-lg transition-colors disabled:opacity-50"
          >
            {submitting ? '保存中...' : '保存技能'}
          </button>
        </form>
      )}

      {error && <div className="text-danger text-sm">{error}</div>}

      {loading ? (
        <div className="text-ink-muted text-sm">加载中...</div>
      ) : skills.length === 0 ? (
        <div className="text-ink-muted text-sm">暂无技能。在对话中让 Agent 调用 skill_save 沉淀，或点击"新增技能"手动添加。</div>
      ) : (
        <ul className="space-y-2">
          {skills.map((s) => (
            <li
              key={s.name}
              className="p-3 border border-border rounded-lg bg-surface-1 space-y-1"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-ink text-sm">
                  {s.name}
                  {!s.is_enabled && (
                    <span className="ml-2 text-xs text-ink-muted">（已禁用）</span>
                  )}
                </span>
                <button
                  type="button"
                  onClick={() => handleDelete(s.name)}
                  className="text-xs text-danger hover:underline"
                >
                  删除
                </button>
              </div>
              <div className="text-xs text-ink-muted">触发：{s.trigger}</div>
              <pre className="text-xs text-ink whitespace-pre-wrap font-mono bg-canvas p-2 rounded border border-border/50 max-h-40 overflow-y-auto">
                {s.content}
              </pre>
              <div className="text-xs text-ink-muted">使用次数：{s.use_count}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
