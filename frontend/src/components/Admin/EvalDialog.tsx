/**
 * EvalDialog — Agent 评测弹窗
 *
 * P3-⑨ Agent 评估框架
 * 输入用例集（JSON），运行评测（回答生成 + LLM Judge 打分），展示通过率/均分/case 明细。
 */
import React, { useState } from 'react';
import { agentApi, AgentEvalRunDetail } from '../../services/agentApi';

interface EvalDialogProps {
  agentId: string;
  agentName: string;
  onClose: () => void;
}

const SAMPLE_CASES = JSON.stringify(
  [
    { input: '什么是 HTTP 200 状态码？', expected: '说明 200 表示请求成功' },
    { input: '用一句话介绍你自己', expected: '给出符合角色定位的自我介绍' },
  ],
  null,
  2,
);

const EvalDialog: React.FC<EvalDialogProps> = ({ agentId, agentName, onClose }) => {
  const [name, setName] = useState(`评测-${new Date().toLocaleDateString()}`);
  const [casesText, setCasesText] = useState(SAMPLE_CASES);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<AgentEvalRunDetail | null>(null);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    let cases: Array<{ input: string; expected: string }>;
    try {
      cases = JSON.parse(casesText);
      if (!Array.isArray(cases) || cases.length === 0) throw new Error('empty');
      for (const c of cases) {
        if (typeof c.input !== 'string' || typeof c.expected !== 'string') {
          throw new Error('shape');
        }
      }
    } catch {
      setError('用例必须是 [{"input": "...", "expected": "..."}] 格式的非空数组');
      return;
    }
    setRunning(true);
    try {
      const run = await agentApi.runAgentEval(agentId, { name: name.trim(), cases });
      const detail = await agentApi.getAgentEval(agentId, run.id);
      setResult(detail);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '评测失败');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface-1 rounded-lg p-6 w-full max-w-2xl border border-border/50 shadow-xl max-h-[85vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4 text-ink">
          评测 Agent：{agentName}
        </h2>

        <form onSubmit={handleRun}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1 text-ink">批次名称</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded bg-canvas text-ink focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-1 text-ink">
              用例集（JSON：input / expected）
            </label>
            <textarea
              value={casesText}
              onChange={(e) => setCasesText(e.target.value)}
              rows={6}
              className="w-full px-3 py-2 border border-border rounded bg-canvas text-ink font-mono text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>

          {error && <div className="text-danger text-sm mb-4">{error}</div>}

          <div className="flex justify-end gap-3 mb-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-ink-muted hover:text-ink"
              disabled={running}
            >
              关闭
            </button>
            <button
              type="submit"
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-60"
              disabled={running}
            >
              {running ? '评测中（含 LLM 调用，可能较慢）...' : '运行评测'}
            </button>
          </div>
        </form>

        {result && (
          <div className="border-t border-border pt-4">
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="p-3 bg-surface-2 rounded-lg text-center">
                <div className="text-2xl font-bold text-ink">
                  {result.passed_cases}/{result.total_cases}
                </div>
                <div className="text-xs text-ink-muted">通过用例</div>
              </div>
              <div className="p-3 bg-surface-2 rounded-lg text-center">
                <div className="text-2xl font-bold text-ink">
                  {(result.avg_score * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-ink-muted">平均分</div>
              </div>
              <div className="p-3 bg-surface-2 rounded-lg text-center">
                <div className="text-2xl font-bold text-ink">
                  {(result.total_duration_ms / 1000).toFixed(1)}s
                </div>
                <div className="text-xs text-ink-muted">总耗时</div>
              </div>
            </div>

            <ul className="space-y-2">
              {result.cases.map((c) => (
                <li key={c.id} className="p-3 border border-border rounded-lg bg-canvas text-sm">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-ink font-medium">{c.input}</span>
                    <span
                      className={
                        c.status === 'error'
                          ? 'text-danger'
                          : c.score >= 0.7
                            ? 'text-green-600'
                            : 'text-warning'
                      }
                    >
                      {c.status === 'error' ? '执行失败' : `${(c.score * 100).toFixed(0)}%`}
                    </span>
                  </div>
                  {c.judge_reasoning && (
                    <div className="text-xs text-ink-muted">评语：{c.judge_reasoning}</div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default EvalDialog;
