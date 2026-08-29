/**
 * TraceViewer 组件
 *
 * Phase 3-Plan-1C / Task 5
 * 展示 agent trace 列表，点击单条 trace 展开 steps 表格。
 *
 * - 5 秒轮询刷新
 * - 错误行红底高亮
 * - loading / empty / error 状态
 */
import { useEffect, useState } from 'react';
import { listTraces, getTrace } from '../../api/harnessTracesApi';
import type { Trace, TraceStep } from '../../types/harness';

interface TraceViewerProps {
  agentId: string;
  conversationId?: string;
}

export function TraceViewer({ agentId, conversationId }: TraceViewerProps) {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [selected, setSelected] = useState<Trace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTraces = async (isInitial = false) => {
    try {
      if (isInitial) setLoading(true);
      setError(null);
      const res = await listTraces(agentId, conversationId);
      setTraces(res.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  useEffect(() => {
    loadTraces(true);
    const interval = setInterval(() => loadTraces(false), 5000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId, conversationId]);

  const handleSelect = async (trace: Trace) => {
    if (selected?.id === trace.id) {
      setSelected(null);
      return;
    }
    try {
      const detail = await getTrace(agentId, trace.id);
      setSelected(detail);
    } catch (e) {
      console.error('Failed to load trace detail:', e);
    }
  };

  if (loading) {
    return <div className="p-4 text-center text-gray-500">加载中...</div>;
  }
  if (error) {
    return (
      <div className="p-4 text-center text-red-500">
        加载失败: {error}
      </div>
    );
  }
  if (traces.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        本次对话还没有执行记录
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      <div className="space-y-1">
        {traces.map((t) => (
          <div
            key={t.id}
            onClick={() => handleSelect(t)}
            className={`flex items-center gap-3 p-2 rounded cursor-pointer hover:bg-gray-50 ${
              selected?.id === t.id ? 'bg-blue-50' : ''
            }`}
          >
            <StatusIcon status={t.status} />
            <span className="text-sm text-gray-700 flex-1 truncate">
              {t.input_text.slice(0, 80)}
            </span>
            <span className="text-xs text-gray-500">
              {formatDuration(t.total_duration_ms)}
            </span>
            <span className="text-xs text-gray-500">{t.total_tokens} tok</span>
            <span className="text-xs text-gray-400">
              {t.started_at ? new Date(t.started_at).toLocaleTimeString() : '-'}
            </span>
          </div>
        ))}
      </div>

      {selected && selected.steps && selected.steps.length > 0 && (
        <div className="border-t pt-3">
          <div className="text-sm font-medium mb-2">Steps</div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-1">#</th>
                <th className="pb-1">类型</th>
                <th className="pb-1">耗时</th>
                <th className="pb-1">Tokens</th>
                <th className="pb-1">模型 / 工具</th>
              </tr>
            </thead>
            <tbody>
              {selected.steps.map((s) => (
                <StepRow key={s.id} step={s} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StepRow({ step }: { step: TraceStep }) {
  const hasError =
    step.metadata && (step.metadata as Record<string, unknown>).error;
  return (
    <tr className={`border-b ${hasError ? 'bg-red-50' : ''}`}>
      <td className="py-1">{step.step_index}</td>
      <td className="py-1">{step.step_type}</td>
      <td className="py-1">{formatDuration(step.duration_ms)}</td>
      <td className="py-1">{step.tokens_used}</td>
      <td className="py-1">{step.llm_model || step.tool_name || '-'}</td>
    </tr>
  );
}

function StatusIcon({ status }: { status: Trace['status'] }) {
  if (status === 'running') {
    return <span className="text-blue-500 animate-spin">◌</span>;
  }
  if (status === 'success') {
    return <span className="text-green-600">✓</span>;
  }
  return <span className="text-red-600">✗</span>;
}

function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return '-';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
