/**
 * StorageLocationBadge 测试
 */
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import StorageLocationBadge from '../StorageLocationBadge';

// 项目未启用 RTL 自动清理（vitest globals 未开启），需手动清理避免用例间 DOM 串扰
afterEach(() => {
  cleanup();
});

describe('StorageLocationBadge', () => {
  it('local 显示「本机」', () => {
    render(<StorageLocationBadge location="local" />);
    expect(screen.getByText(/本机/)).toBeTruthy();
  });

  it('server 显示「服务器」', () => {
    render(<StorageLocationBadge location="server" />);
    expect(screen.getByText(/服务器/)).toBeTruthy();
  });
});
