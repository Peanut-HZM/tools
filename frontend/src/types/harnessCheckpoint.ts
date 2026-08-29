/**
 * Checkpoint 时间旅行 类型定义
 *
 * Phase 3-Plan-1D / Task 5
 * 字段命名与后端 Pydantic schema 严格对齐（snake_case）。
 */

export interface MessageSnapshotItem {
  id: string;
  sender_type: string;
  role: string;
  content: string;
  message_type?: string | null;
  sent_at?: string | null;
  tool_calls?: unknown[] | null;
  tool_call_id?: string | null;
  tool_name?: string | null;
  attachments?: unknown[] | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface Checkpoint {
  id: string;
  conversation_id: string;
  branch_id: string;
  parent_checkpoint_id: string | null;
  step_index: number;
  phase: string;
  checkpoint_kind: 'auto' | 'manual' | 'branch_point' | 'merge_commit';
  label: string | null;
  merge_parents: string[] | null;
  is_head: boolean;
  messages_snapshot: MessageSnapshotItem[];
  agent_state: Record<string, unknown>;
  created_at: string;
}

export interface Branch {
  id: string;
  conversation_id: string;
  name: string;
  parent_branch_id: string | null;
  head_checkpoint_id: string | null;
  is_archived: boolean;
  created_at: string;
  closed_at: string | null;
}

export interface CreateBranchRequest {
  source_checkpoint_id: string;
  name: string;
  start_with_messages: boolean;
}

export interface MergeRequest {
  picked_checkpoint_ids: string[];
  new_branch_name: string;
}

export interface RollbackResponse {
  conversation_head_checkpoint_id: string;
  detached_checkpoint_count: number;
  target_checkpoint: Checkpoint;
}
