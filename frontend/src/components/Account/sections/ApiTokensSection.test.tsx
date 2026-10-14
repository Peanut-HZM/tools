/**
 * API Token 管理组件测试
 * 覆盖：列表渲染、创建返回明文一次性展示、撤销二次确认
 */
import React from 'react';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import ApiTokensSection from './ApiTokensSection';
import * as api from '../../../api/userTokenApi';

vi.mock('../../../api/userTokenApi');

const mocked = vi.mocked(api);

const tokens = [
  {
    id: 't1',
    name: 'claude-code',
    token_prefix: 'pat_abc12345',
    created_at: '2026-10-14T10:00:00',
    last_used_at: null,
    expires_at: null,
    revoked: false,
  },
];

describe('ApiTokensSection', () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.resetAllMocks();
    // userTokenApi 以命名导出对象提供，mock 其方法
    mocked.userTokenApi.list.mockResolvedValue(tokens);
  });

  it('渲染已有 Token 列表（只显示前缀）', async () => {
    render(<ApiTokensSection />);
    expect(await screen.findByText('claude-code')).toBeTruthy();
    expect(screen.getByText(/pat_abc12345/)).toBeTruthy();
  });

  it('创建成功后明文只展示一次并支持复制', async () => {
    mocked.userTokenApi.create.mockResolvedValue({ ...tokens[0], token: 'pat_FULL_SECRET' });
    render(<ApiTokensSection />);
    await screen.findByText('claude-code');
    fireEvent.change(screen.getByPlaceholderText('令牌名称，如 claude-code-local'), {
      target: { value: 'new-token' },
    });
    fireEvent.click(screen.getByRole('button', { name: /创建/ }));
    expect(await screen.findByText('pat_FULL_SECRET')).toBeTruthy();
    expect(screen.getByText(/仅此一次/)).toBeTruthy();
    // 关闭明文提示后列表刷新，不再含明文
    fireEvent.click(screen.getByRole('button', { name: /我已保存/ }));
    await waitFor(() => expect(screen.queryByText('pat_FULL_SECRET')).toBeNull());
  });

  it('撤销需二次确认', async () => {
    window.confirm = vi.fn(() => true);
    mocked.userTokenApi.revoke.mockResolvedValue(undefined);
    render(<ApiTokensSection />);
    await screen.findByText('claude-code');
    fireEvent.click(screen.getByRole('button', { name: /撤销/ }));
    expect(window.confirm).toHaveBeenCalled();
    await waitFor(() => expect(mocked.userTokenApi.revoke).toHaveBeenCalledWith('t1'));
  });
});
