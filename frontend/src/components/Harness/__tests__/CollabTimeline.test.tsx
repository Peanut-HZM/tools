/** CollabTimeline 单元测试（P3-⑪） */
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CollabTimeline, buildChain, extractHandoffs } from '../CollabTimeline';
import type { TraceStep } from '../../../types/harness';

function mkStep(index: number, stepType: string, metadata: Record<string, unknown> | null): TraceStep {
  return {
    id: `s-${index}`,
    step_index: index,
    step_type: stepType,
    created_at: null,
    duration_ms: 10,
    tokens_used: 0,
    tool_name: null,
    llm_model: null,
    input_summary: null,
    output_summary: null,
    metadata,
  };
}

const FROM = { id: 'a1', name: 'AgentA' };
const TO = { id: 'a2', name: 'AgentB' };

describe('extractHandoffs', () => {
  it('仅提取 handoff 类型且 metadata 合法的 steps', () => {
    const steps = [
      mkStep(0, 'llm_call', null),
      mkStep(1, 'handoff', { from_agent: FROM, to_agent: TO, reason: 'r1' }),
      mkStep(2, 'handoff', { from_agent: { id: 'x' } }), // 形状异常 → 跳过
      mkStep(3, 'handoff', { from_agent: FROM, to_agent: TO, reason: '' }),
    ];
    const records = extractHandoffs(steps);
    expect(records).toHaveLength(2);
    expect(records[0].from.name).toBe('AgentA');
  });
});

describe('buildChain', () => {
  it('连续同名去重', () => {
    const records = [
      { stepIndex: 1, from: FROM, to: TO, reason: '' },
      { stepIndex: 3, from: TO, to: TO, reason: '' },
      { stepIndex: 5, from: TO, to: { id: 'a3', name: 'AgentC' }, reason: '' },
    ];
    expect(buildChain(records)).toEqual(['AgentA', 'AgentB', 'AgentC']);
  });
});

describe('CollabTimeline', () => {
  it('无 handoff 时不渲染', () => {
    const { container } = render(<CollabTimeline steps={[mkStep(0, 'llm_call', null)]} />);
    expect(container.firstChild).toBeNull();
  });

  it('渲染协作链与交接明细', () => {
    render(
      <CollabTimeline
        steps={[mkStep(2, 'handoff', { from_agent: FROM, to_agent: TO, reason: '用户要求' })]}
      />,
    );
    expect(screen.getByTestId('collab-timeline')).toBeTruthy();
    expect(screen.getByText('AgentA')).toBeInTheDocument();
    expect(screen.getByText('AgentB')).toBeInTheDocument();
    expect(screen.getByText(/用户要求/)).toBeInTheDocument();
  });
});
