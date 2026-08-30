/**
 * CollabTimeline — 多 Agent 协作时间线
 *
 * P3-⑪ 多 Agent 协作可视化
 * 从 trace steps 中提取 handoff 记录，渲染 agent 交接链与明细。
 * 单 Agent 会话（无 handoff steps）不渲染任何内容。
 */
import React from 'react';
import type { TraceStep } from '../../types/harness';

interface HandoffInfo {
  id: string;
  name: string;
}

interface HandoffRecord {
  stepIndex: number;
  from: HandoffInfo;
  to: HandoffInfo;
  reason: string;
}

/** 从 steps 提取 handoff 记录（metadata 形状异常的条目跳过） */
export function extractHandoffs(steps: TraceStep[]): HandoffRecord[] {
  const records: HandoffRecord[] = [];
  for (const step of steps) {
    if (step.step_type !== 'handoff') continue;
    const meta = (step.metadata || {}) as Record<string, unknown>;
    const from = meta.from_agent as HandoffInfo | undefined;
    const to = meta.to_agent as HandoffInfo | undefined;
    if (!from?.name || !to?.name) continue;
    records.push({
      stepIndex: step.step_index,
      from,
      to,
      reason: typeof meta.reason === 'string' ? meta.reason : '',
    });
  }
  return records;
}

/** 协作链：连续同名去重（A → B → B → C ⇒ A → B → C） */
export function buildChain(records: HandoffRecord[]): string[] {
  const chain: string[] = [];
  for (const r of records) {
    if (chain.length === 0) chain.push(r.from.name);
    if (chain[chain.length - 1] !== r.to.name) chain.push(r.to.name);
  }
  return chain;
}

export const CollabTimeline: React.FC<{ steps: TraceStep[] }> = ({ steps }) => {
  const records = extractHandoffs(steps);
  if (records.length === 0) return null;
  const chain = buildChain(records);

  return (
    <div className="border-t pt-3 mb-3" data-testid="collab-timeline">
      <div className="text-sm font-medium mb-2">多 Agent 协作</div>

      {/* 协作链徽章 */}
      <div className="flex flex-wrap items-center gap-1 mb-3">
        {chain.map((name, i) => (
          <React.Fragment key={`${name}-${i}`}>
            {i > 0 && <span className="text-gray-400 mx-1">→</span>}
            <span className="px-2 py-0.5 bg-amber-100 text-amber-800 rounded-full text-xs font-medium">
              {name}
            </span>
          </React.Fragment>
        ))}
      </div>

      {/* 交接明细 */}
      <ul className="space-y-1">
        {records.map((r, i) => (
          <li key={i} className="text-xs text-gray-600">
            <span className="text-gray-400 mr-2">#{r.stepIndex}</span>
            <span className="font-medium text-gray-700">{r.from.name}</span>
            <span className="mx-1 text-amber-600">移交 →</span>
            <span className="font-medium text-gray-700">{r.to.name}</span>
            {r.reason && <span className="ml-2 text-gray-400">({r.reason})</span>}
          </li>
        ))}
      </ul>
    </div>
  );
};
