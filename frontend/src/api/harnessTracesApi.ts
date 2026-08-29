/**
 * Harness Agent Traces API 客户端
 *
 * Phase 3-Plan-1C / Task 4
 * 提供 listTraces / getTrace 封装，基于项目约定的 authedFetch。
 */
import { authedFetch } from './http';
import type { Trace, TraceListResponse } from '../types/harness';

/**
 * 列出指定 agent 的 traces（可按 conversation 过滤 + 分页）
 */
export async function listTraces(
  agentId: string,
  conversationId?: string,
  page = 1,
  pageSize = 20,
): Promise<TraceListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (conversationId) params.set('conversation_id', conversationId);

  const res = await authedFetch(
    `/api/v1/harness/agents/${agentId}/traces?${params}`,
  );
  if (!res.ok) {
    throw new Error(`Failed to list traces: ${res.status}`);
  }
  return res.json();
}

/**
 * 获取单条 trace 详情（含 steps）
 */
export async function getTrace(
  agentId: string,
  traceId: string,
): Promise<Trace> {
  const res = await authedFetch(
    `/api/v1/harness/agents/${agentId}/traces/${traceId}`,
  );
  if (!res.ok) {
    throw new Error(`Failed to get trace: ${res.status}`);
  }
  return res.json();
}
