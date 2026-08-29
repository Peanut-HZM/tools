// frontend/src/components/Harness/TimeTravel/__tests__/MergePickerDialog.test.tsx
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { MergePickerDialog } from '../MergePickerDialog';

afterEach(cleanup);

const branches = [{ id: 'b1', name: '主线', conversation_id: 'c1', parent_branch_id: null, head_checkpoint_id: 'cp1', is_archived: false, created_at: '2026-01-01T00:00:00', closed_at: null }];

const checkpointsByBranch = {
  b1: [
    { id: 'cp1', conversation_id: 'c1', branch_id: 'b1', parent_checkpoint_id: null, step_index: 1, phase: 'after_user', checkpoint_kind: 'auto' as const, label: null, merge_parents: null, is_head: true, messages_snapshot: [], agent_state: {}, created_at: '2026-01-01T00:00:00' },
    { id: 'cp2', conversation_id: 'c1', branch_id: 'b1', parent_checkpoint_id: 'cp1', step_index: 2, phase: 'after_tool', checkpoint_kind: 'auto' as const, label: null, merge_parents: null, is_head: false, messages_snapshot: [], agent_state: {}, created_at: '2026-01-01T00:01:00' },
  ],
};

describe('MergePickerDialog', () => {
  it('renders branches and checkpoints', () => {
    render(
      <MergePickerDialog
        isOpen
        onClose={() => {}}
        onConfirm={async () => {}}
        branches={branches}
        checkpointsByBranch={checkpointsByBranch}
      />
    );
    expect(screen.getByText('主线')).toBeTruthy();
    expect(screen.getByText(/step 1/)).toBeTruthy();
  });

  it('confirm disabled with < 2 selected', () => {
    render(
      <MergePickerDialog
        isOpen
        onClose={() => {}}
        onConfirm={async () => {}}
        branches={branches}
        checkpointsByBranch={checkpointsByBranch}
      />
    );
    const btn = screen.getByText('创建合并分支') as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it('calls onConfirm with picked ids', async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    render(
      <MergePickerDialog
        isOpen
        onClose={() => {}}
        onConfirm={onConfirm}
        branches={branches}
        checkpointsByBranch={checkpointsByBranch}
      />
    );
    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[0]); // cp1
    fireEvent.click(checkboxes[1]); // cp2
    fireEvent.click(screen.getByText('创建合并分支'));
    expect(onConfirm).toHaveBeenCalledWith(['cp1', 'cp2'], expect.any(String));
  });
});
