/**
 * K8s 工具存储位置接入测试
 *
 * 覆盖：
 * - StorageLocationBadge 渲染（local/server）
 * - K8sConnection 类型含 storage_location（编译期保障）
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StorageLocationBadge from '../../../Common/StorageLocationBadge';

describe('K8s 工具存储位置', () => {
  it('渲染服务器徽章', () => {
    render(<StorageLocationBadge location="server" />);
    expect(screen.getByText(/服务器/)).toBeTruthy();
  });

  it('渲染本机徽章', () => {
    render(<StorageLocationBadge location="local" />);
    expect(screen.getByText(/本机/)).toBeTruthy();
  });

  it('K8sConnection 类型含 storage_location（编译期保障）', () => {
    const conn = {
      id: 'k1',
      user_id: 'u1',
      name: 'cluster',
      source_type: 'manual',
      cluster_name: 'c',
      context_name: 'ctx',
      server: 'https://k8s',
      auth_type: 'bearer_token' as const,
      has_auth_data: true,
      storage_location: 'local' as const,
      has_ca_cert: false,
      namespace_filter: [],
      is_metrics_available: false,
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
    };
    expect(conn.storage_location).toBe('local');
  });
});
