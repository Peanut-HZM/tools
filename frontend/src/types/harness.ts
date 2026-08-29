/**
 * Harness Traces 类型定义
 *
 * Phase 3-Plan-1C / Task 4
 * 字段命名与后端 Pydantic schema 严格对齐（snake_case）。
 *
 * 注意：types/trace.ts 已存在 legacy Trace 类型，本文件独立定义
 * Agent Harness 的 Trace/TraceStep，避免冲突。
 */

export interface TraceStep {
  id: string;
  step_index: number;
  step_type: string;
  created_at: string | null;
  duration_ms: number | null;
  tokens_used: number;
  tool_name: string | null;
  llm_model: string | null;
  input_summary: string | null;
  output_summary: string | null;
  metadata: Record<string, unknown> | null;
}

export interface Trace {
  id: string;
  conversation_id: string;
  agent_id: string;
  user_id: string;
  input_text: string;
  output_text: string | null;
  status: 'running' | 'success' | 'error' | 'timeout' | 'guardrail_blocked' | 'handoff';
  started_at: string | null;
  completed_at: string | null;
  total_duration_ms: number;
  total_steps: number;
  total_tokens: number;
  error_message: string | null;
  steps?: TraceStep[];
}

export interface TraceListResponse {
  items: Trace[];
  total: number;
  page: number;
  page_size: number;
}
