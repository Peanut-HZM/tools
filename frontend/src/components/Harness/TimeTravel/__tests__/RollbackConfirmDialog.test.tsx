// frontend/src/components/Harness/TimeTravel/__tests__/RollbackConfirmDialog.test.tsx
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { RollbackConfirmDialog } from '../RollbackConfirmDialog';

afterEach(cleanup);

describe('RollbackConfirmDialog', () => {
  it('renders when open', () => {
    render(
      <RollbackConfirmDialog
        isOpen
        onClose={() => {}}
        onConfirm={async () => {}}
        currentHeadLabel="step 5"
        targetLabel="step 3"
      />
    );
    expect(screen.getByRole('heading', { name: '确认回滚' })).toBeTruthy();
    expect(screen.getByText(/step 5/)).toBeTruthy();
    expect(screen.getByText(/step 3/)).toBeTruthy();
  });

  it('does not render when closed', () => {
    const { container } = render(
      <RollbackConfirmDialog
        isOpen={false}
        onClose={() => {}}
        onConfirm={async () => {}}
        currentHeadLabel="step 5"
        targetLabel="step 3"
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it('confirm button disabled until checkbox checked', () => {
    render(
      <RollbackConfirmDialog
        isOpen
        onClose={() => {}}
        onConfirm={async () => {}}
        currentHeadLabel="step 5"
        targetLabel="step 3"
      />
    );
    const btn = screen.getByRole('button', { name: '确认回滚' }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);

    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);
    expect(btn.disabled).toBe(false);
  });

  it('calls onConfirm when confirmed', async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    render(
      <RollbackConfirmDialog
        isOpen
        onClose={() => {}}
        onConfirm={onConfirm}
        currentHeadLabel="step 5"
        targetLabel="step 3"
      />
    );
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: '确认回滚' }));
    expect(onConfirm).toHaveBeenCalled();
  });
});
