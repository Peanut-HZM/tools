// frontend/src/components/Harness/TimeTravel/__tests__/BranchCreateDialog.test.tsx
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { BranchCreateDialog } from '../BranchCreateDialog';

afterEach(cleanup);

describe('BranchCreateDialog', () => {
  it('renders input + checkbox', () => {
    render(
      <BranchCreateDialog
        isOpen
        onClose={() => {}}
        onConfirm={async () => {}}
        sourceLabel="step 3"
      />
    );
    expect(screen.getByPlaceholderText('分支名称')).toBeTruthy();
    expect(screen.getByRole('checkbox')).toBeTruthy();
  });

  it('confirm button disabled when name empty', () => {
    render(
      <BranchCreateDialog
        isOpen
        onClose={() => {}}
        onConfirm={async () => {}}
        sourceLabel="step 3"
      />
    );
    const btn = screen.getByText('创建') as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it('calls onConfirm with name', async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    render(
      <BranchCreateDialog
        isOpen
        onClose={() => {}}
        onConfirm={onConfirm}
        sourceLabel="step 3"
      />
    );
    fireEvent.change(screen.getByPlaceholderText('分支名称'), {
      target: { value: '实验分支' },
    });
    fireEvent.click(screen.getByText('创建'));
    expect(onConfirm).toHaveBeenCalledWith('实验分支', true);
  });
});
