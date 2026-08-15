import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import SystemMonitor from './index';
import * as monitorApi from '../../../api/monitorApi';

// 任务 15 起总览/历史页为真实实现，补齐其 API mock，默认值保证渲染路径安全
vi.mock('../../../api/monitorApi', () => ({
  getServers: vi.fn(),
  getAlertLogs: vi.fn(),
  markAlertLogsRead: vi.fn(),
  getSystemInfo: vi.fn().mockResolvedValue({}),
  getPartitions: vi.fn().mockResolvedValue({ partitions: [] }),
  getOverview: vi.fn().mockResolvedValue({ server: null, metric: null }),
  getMetrics: vi.fn().mockResolvedValue({ server_id: '', range: '', points: [] }),
}));

afterEach(() => {
  cleanup();
});

const mockServers = [
  { id: 'srv-local', user_id: 'u1', name: '本机', server_type: 'local', host: '', port: 22,
    username: '', status: 'online', created_at: '2026-01-01T00:00:00',
    metric: { cpu_percent: 10, mem_percent: 20, disk_percent: 30, net_recv_rate: 0, net_sent_rate: 0, disk_read_rate: 0, disk_write_rate: 0 } },
  { id: 'srv-1', user_id: 'u1', name: 'web1', server_type: 'ssh', host: '10.0.0.1', port: 22,
    username: 'root', status: 'online', created_at: '2026-01-01T00:00:00',
    metric: { cpu_percent: 50, mem_percent: 60, disk_percent: 70, net_recv_rate: 0, net_sent_rate: 0, disk_read_rate: 0, disk_write_rate: 0 } },
];

describe('SystemMonitor 主容器', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (monitorApi.getServers as any).mockResolvedValue(mockServers);
    (monitorApi.getAlertLogs as any).mockResolvedValue({ logs: [], total: 0, unread_count: 2, page: 1, page_size: 20 });
  });

  it('渲染六页签与服务器列表', async () => {
    render(<SystemMonitor />);
    await waitFor(() => expect(screen.getByText('web1')).toBeTruthy());
    expect(screen.getByText('服务器列表')).toBeTruthy();
    expect(screen.getByText('总览')).toBeTruthy();
    expect(screen.getByText('历史趋势')).toBeTruthy();
    expect(screen.getByText('进程')).toBeTruthy();
    expect(screen.getByText('服务')).toBeTruthy();
    expect(screen.getByText('告警')).toBeTruthy();
  });

  it('切换页签', async () => {
    render(<SystemMonitor />);
    await waitFor(() => expect(screen.getByText('web1')).toBeTruthy());
    fireEvent.click(screen.getByText('总览'));
    expect(screen.getByTestId('server-selector')).toBeTruthy();
  });
});
