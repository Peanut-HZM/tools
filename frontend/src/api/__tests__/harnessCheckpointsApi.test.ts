/**
 * harnessCheckpointsApi 单元测试
 *
 * Phase 3-Plan-1D / Task 5
 * 覆盖 listBranches / createBranch / mergeBranches / rollback 的 URL 与 HTTP 方法。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { authedFetch } from '../http';

vi.mock('../http', () => ({
  authedFetch: vi.fn(),
}));

import {
  listBranches,
  createBranch,
  mergeBranches,
  rollback,
} from '../harnessCheckpointsApi';

const mockedFetch = authedFetch as unknown as ReturnType<typeof vi.fn>;

const CONV_ID = 'conv-1';
const AUTHED_URL_BASE = '/api/v1/harness/conversations';

describe('harnessCheckpointsApi', () => {
  beforeEach(() => {
    mockedFetch.mockReset();
  });

  it('listBranches calls correct URL', async () => {
    mockedFetch.mockResolvedValueOnce({ ok: true, json: async () => [] });
    const result = await listBranches(CONV_ID);
    expect(mockedFetch).toHaveBeenCalledWith(`${AUTHED_URL_BASE}/${CONV_ID}/branches`);
    expect(result).toEqual([]);
  });

  it('createBranch POSTs to /branches', async () => {
    mockedFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ branch: {}, first_checkpoint: {} }),
    });
    await createBranch(CONV_ID, {
      source_checkpoint_id: 'cp-1',
      name: '实验',
      start_with_messages: true,
    });
    expect(mockedFetch).toHaveBeenCalledWith(
      `${AUTHED_URL_BASE}/${CONV_ID}/branches`,
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('source_checkpoint_id'),
      })
    );
  });

  it('mergeBranches POSTs to /branches/{id}/merge', async () => {
    mockedFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ branch: {}, merge_commit: {} }),
    });
    await mergeBranches(CONV_ID, 'branch-1', {
      picked_checkpoint_ids: ['cp-1', 'cp-2'],
      new_branch_name: '合并',
    });
    expect(mockedFetch).toHaveBeenCalledWith(
      `${AUTHED_URL_BASE}/${CONV_ID}/branches/branch-1/merge`,
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('rollback POSTs to /checkpoints/{id}/rollback', async () => {
    mockedFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    await rollback(CONV_ID, 'cp-1');
    expect(mockedFetch).toHaveBeenCalledWith(
      `${AUTHED_URL_BASE}/${CONV_ID}/checkpoints/cp-1/rollback`,
      expect.objectContaining({ method: 'POST' })
    );
  });
});
