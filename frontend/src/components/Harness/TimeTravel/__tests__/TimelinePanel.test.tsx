// frontend/src/components/Harness/TimeTravel/__tests__/TimelinePanel.test.tsx
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { TimelinePanel } from '../TimelinePanel';

afterEach(cleanup);

vi.mock('../../../../api/harnessCheckpointsApi', () => ({
  listBranches: vi.fn().mockResolvedValue([]),
  listCheckpoints: vi.fn().mockResolvedValue([]),
  rollback: vi.fn(),
  createBranch: vi.fn(),
  mergeBranches: vi.fn(),
}));

describe('TimelinePanel', () => {
  it('renders empty state when no branches', async () => {
    render(<TimelinePanel conversationId="conv-1" />);
    await waitFor(() => {
      expect(screen.getByText(/时间旅行/)).toBeTruthy();
    });
  });
});
