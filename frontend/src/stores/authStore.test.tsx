/**
 * authStore 单元测试 — 验证 authVersion 递增语义与 markUnauthorized 行为
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { AuthProvider, useAuth } from './authStore';

// mock 网络层：验证 authVersion 语义不依赖真实后端
vi.mock('../api/authApi', () => ({
  login: vi.fn().mockResolvedValue({
    token: 't',
    user_id: 'u1',
    username: 'tester',
    email: 't@t.com',
    role: 'user',
  }),
  verifyToken: vi.fn().mockResolvedValue(false),
  getCurrentUser: vi.fn(),
  removeAuthToken: vi.fn(),
  logout: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('../api/tokenUsageApi', () => ({
  syncTokenUsage: vi.fn().mockResolvedValue({}),
}));

const wrapper = ({ children }: { children: ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

describe('authVersion', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('初始 authVersion 为 0', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.authVersion).toBe(0);
  });

  it('login 成功后 authVersion +1', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.login('tester', 'password');
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.authVersion).toBe(1);
  });

  it('logout 后 authVersion +1', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    await act(async () => {
      await result.current.login('tester', 'password');
    });

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.authVersion).toBe(2);
  });
});

describe('markUnauthorized', () => {
  it('已登录时调用：authVersion +1，状态归零', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    await act(async () => {
      await result.current.login('tester', 'password');
    });

    act(() => {
      result.current.markUnauthorized();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.authVersion).toBe(2);
  });

  it('未登录时连续调用：authVersion 不再递增', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.markUnauthorized();
    });
    act(() => {
      result.current.markUnauthorized();
    });

    expect(result.current.authVersion).toBe(0);
  });

  it('同一渲染内连续两次 markUnauthorized 只递增一次 authVersion', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    await act(async () => {
      await result.current.login('tester', 'password');
    });

    act(() => {
      result.current.markUnauthorized();
      result.current.markUnauthorized();
    });

    expect(result.current.authVersion).toBe(2);
  });
});
