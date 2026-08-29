// Agent 追踪（Trace）类型定义
// 用于记录 Agent 执行过程的完整链路

export interface Trace {
  id: string;
  agent_id: string;
  agent_name: string;
  conversation_id: string;
  turn_id: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string;
  ended_at?: string;
  total_steps: number;
  total_tokens?: number;
  error_message?: string;
}

export interface TraceDetail extends Trace {
  steps: TraceStep[];
  parent_trace_id?: string;
  child_traces?: Trace[];
}

export interface TraceStep {
  id: string;
  trace_id: string;
  step_index: number;
  step_type: 'llm_call' | 'tool_call' | 'handoff' | 'guardrail' | 'memory' | 'custom';
  name: string;
  started_at: string;
  ended_at?: string;
  duration_ms?: number;
  input?: any;
  output?: any;
  tokens_used?: number;
  error?: string;
  metadata?: Record<string, any>;
}
