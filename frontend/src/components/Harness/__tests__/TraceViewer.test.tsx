/**
 * TraceViewer 单元测试
 *
 * Phase 3-Plan-1C / Task 5
 * 覆盖：
 *  - 空状态「还没有执行记录」
 *  - 列表渲染（耗时 + tokens）
 *  - 点击 trace 加载 steps 表格
 *  - loading 状态
 *  - error 状态
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TraceViewer } from '../TraceViewer';
import * as api from '../../../api/harnessTracesApi';

vi.mock('../../../api/harnessTracesApi', () => ({
  listTraces: vi.fn(),
  getTrace: vi.fn(),
}));

const mockedListTraces = vi.mocked(api.listTraces);
const mockedGetTrace = vi.mocked(api.getTrace);

const AGENT_ID = 'agent-1';
const CONV_ID = 'conv-1';

describe('TraceViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when no traces', async () => {
    mockedListTraces.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    render(<TraceViewer agentId={AGENT_ID} conversationId={CONV_ID} />);

    await waitFor(() => {
      expect(screen.getByText(/还没有执行记录/i)).toBeTruthy();
    });
  });

  it('renders trace list', async () => {
    mockedListTraces.mockResolvedValue({
      items: [
        {
          id: 'trace-1',
          conversation_id: CONV_ID,
          agent_id: AGENT_ID,
          user_id: 'u1',
          input_text: 'hello',
          output_text: 'hi',
          status: 'success',
          started_at: '2026-08-29T10:00:00Z',
          completed_at: '2026-08-29T10:00:01Z',
          total_duration_ms: 1200,
          total_steps: 2,
          total_tokens: 420,
          error_message: null,
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    });

    render(<TraceViewer agentId={AGENT_ID} conversationId={CONV_ID} />);

    await waitFor(() => {
      expect(screen.getByText(/420/)).toBeTruthy();
      expect(screen.getByText(/1\.2s/)).toBeTruthy();
    });
  });

  it('clicks trace to load steps', async () => {
    mockedListTraces.mockResolvedValue({
      items: [
        {
          id: 'trace-1',
          conversation_id: CONV_ID,
          agent_id: AGENT_ID,
          user_id: 'u1',
          input_text: 'hi',
          output_text: null,
          status: 'success',
          started_at: '2026-08-29T10:00:00Z',
          completed_at: null,
          total_duration_ms: 800,
          total_steps: 1,
          total_tokens: 100,
          error_message: null,
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    });
    mockedGetTrace.mockResolvedValue({
      id: 'trace-1',
      conversation_id: CONV_ID,
      agent_id: AGENT_ID,
      user_id: 'u1',
      input_text: 'hi',
      output_text: 'hello',
      status: 'success',
      started_at: '2026-08-29T10:00:00Z',
      completed_at: '2026-08-29T10:00:01Z',
      total_duration_ms: 800,
      total_steps: 1,
      total_tokens: 100,
      error_message: null,
      steps: [
        {
          id: 'step-1',
          step_index: 0,
          step_type: 'llm_call',
          created_at: '2026-08-29T10:00:00Z',
          duration_ms: 700,
          tokens_used: 90,
          tool_name: null,
          llm_model: 'gpt-4',
          input_summary: 'user asked',
          output_summary: 'model answered',
          metadata: null,
        },
      ],
    });

    render(<TraceViewer agentId={AGENT_ID} conversationId={CONV_ID} />);

    await waitFor(() => expect(screen.getByText(/100/)).toBeTruthy());

    // 点击 trace 行（包含 "100" 文本的元素）
    fireEvent.click(screen.getByText(/100/));

    await waitFor(() => {
      expect(mockedGetTrace).toHaveBeenCalledWith(AGENT_ID, 'trace-1');
      expect(screen.getByText('gpt-4')).toBeTruthy();
    });
  });

  it('shows loading state', () => {
    mockedListTraces.mockReturnValue(new Promise(() => {})); // 永不 resolve
    render(<TraceViewer agentId={AGENT_ID} conversationId={CONV_ID} />);
    expect(screen.getByText(/加载中/i)).toBeTruthy();
  });

  it('shows error state', async () => {
    mockedListTraces.mockRejectedValue(new Error('network fail'));
    render(<TraceViewer agentId={AGENT_ID} conversationId={CONV_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/加载失败/i)).toBeTruthy();
    });
  });
});
