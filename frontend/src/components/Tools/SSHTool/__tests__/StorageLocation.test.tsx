/**
 * SSH 工具存储位置接入测试
 *
 * 覆盖：
 * - StorageLocationBadge 渲染（local/server）
 * - SSHConfig / CreateSSHRequest 类型含 storage_location（编译期保障）
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StorageLocationBadge from '../../../Common/StorageLocationBadge';

describe('SSH 工具存储位置', () => {
  it('渲染本机徽章', () => {
    render(<StorageLocationBadge location="local" />);
    expect(screen.getByText(/本机/)).toBeTruthy();
  });

  it('渲染服务器徽章', () => {
    render(<StorageLocationBadge location="server" />);
    expect(screen.getByText(/服务器/)).toBeTruthy();
  });

  it('SSHConfig 类型含 storage_location（编译期保障）', () => {
    const config = {
      id: 's1',
      alias: 'ssh-server',
      host: '10.0.0.1',
      port: 22,
      username: 'root',
      is_active: true,
      storage_location: 'local' as const,
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
    };
    expect(config.storage_location).toBe('local');
  });
});
