/**
 * Checkpoint 时间旅行 API 封装
 *
 * Phase 3-Plan-1D / Task 5
 * 提供分支 / checkpoint 的增删改查、手动写入、回滚与合并能力，
 * 对接后端 /api/v1/harness/conversations/{conversation_id} 系列接口。
 */
import { authedFetch } from './http';
import type {
  Branch,
  Checkpoint,
  CreateBranchRequest,
  MergeRequest,
  RollbackResponse,
} from '../types/harnessCheckpoint';

const BASE = (convId: string) =>
  `/api/v1/harness/conversations/${convId}`;

export async function listBranches(convId: string): Promise<Branch[]> {
  const res = await authedFetch(BASE(convId) + '/branches');
  if (!res.ok) {
    throw new Error(`Failed to list branches: ${res.status}`);
  }
  return res.json();
}

export async function createBranch(
  convId: string,
  req: CreateBranchRequest
): Promise<{ branch: Branch; first_checkpoint: Checkpoint }> {
  const res = await authedFetch(BASE(convId) + '/branches', {
    method: 'POST',
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    throw new Error(`Failed to create branch: ${res.status}`);
  }
  return res.json();
}

export async function getBranch(convId: string, branchId: string): Promise<Branch> {
  const res = await authedFetch(BASE(convId) + `/branches/${branchId}`);
  if (!res.ok) {
    throw new Error(`Failed to get branch: ${res.status}`);
  }
  return res.json();
}

export async function updateBranch(
  convId: string,
  branchId: string,
  patch: { name?: string; is_archived?: boolean }
): Promise<Branch> {
  const res = await authedFetch(BASE(convId) + `/branches/${branchId}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    throw new Error(`Failed to update branch: ${res.status}`);
  }
  return res.json();
}

export async function deleteBranch(convId: string, branchId: string): Promise<void> {
  const res = await authedFetch(BASE(convId) + `/branches/${branchId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error(`Failed to delete branch: ${res.status}`);
  }
}

export async function listCheckpoints(
  convId: string,
  branchId: string,
  includeDetached = false
): Promise<Checkpoint[]> {
  const url =
    BASE(convId) + `/branches/${branchId}/checkpoints?include_detached=${includeDetached}`;
  const res = await authedFetch(url);
  if (!res.ok) {
    throw new Error(`Failed to list checkpoints: ${res.status}`);
  }
  return res.json();
}

export async function getCheckpoint(
  convId: string,
  checkpointId: string
): Promise<Checkpoint> {
  const res = await authedFetch(BASE(convId) + `/checkpoints/${checkpointId}`);
  if (!res.ok) {
    throw new Error(`Failed to get checkpoint: ${res.status}`);
  }
  return res.json();
}

export async function writeManualCheckpoint(
  convId: string,
  stepIndex: number,
  phase: string,
  messages: unknown[],
  scratchState: Record<string, unknown> = {},
  label?: string
): Promise<Checkpoint> {
  const params = new URLSearchParams({
    step_index: String(stepIndex),
    phase,
    messages: JSON.stringify(messages),
    scratch_state: JSON.stringify(scratchState),
  });
  if (label) params.set('label', label);
  const res = await authedFetch(BASE(convId) + `/checkpoints?${params}`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Failed to write checkpoint: ${res.status}`);
  }
  return res.json();
}

export async function rollback(
  convId: string,
  checkpointId: string
): Promise<RollbackResponse> {
  const res = await authedFetch(BASE(convId) + `/checkpoints/${checkpointId}/rollback`, {
    method: 'POST',
  });
  if (!res.ok) {
    throw new Error(`Failed to rollback: ${res.status}`);
  }
  return res.json();
}

export async function mergeBranches(
  convId: string,
  branchId: string,
  req: MergeRequest
): Promise<{ branch: Branch; merge_commit: Checkpoint }> {
  const res = await authedFetch(BASE(convId) + `/branches/${branchId}/merge`, {
    method: 'POST',
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    throw new Error(`Failed to merge branches: ${res.status}`);
  }
  return res.json();
}
