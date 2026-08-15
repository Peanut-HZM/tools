// frontend/src/components/Tools/SystemMonitor/components/ServerCard.test.tsx
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { ServerCard } from './ServerCard';
import type { MonitorServer } from '../../../../api/monitorApi';

afterEach(() => {
  cleanup();
});

const server: MonitorServer = {
  id: 'srv-1',
  user_id: 'u1',
  name: 'web1',
  server_type: 'ssh',
  host: '10.0.0.1',
  port: 22,
  username: 'root',
  status: 'online',
  created_at: '2026-01-01T00:00:00',
  metric: { cpu_percent: 12.5, mem_percent: 55, disk_percent: 40, net_recv_rate: 100, net_sent_rate: 200, disk_read_rate: 0, disk_write_rate: 0 },
};

describe('ServerCard', () => {
  it('渲染服务器名称与状态', () => {
    render(<ServerCard server={server} onSelect={() => {}} />);
    expect(screen.getByText('web1')).toBeTruthy();
    expect(screen.getByText(/12.5%/)).toBeTruthy();
  });

  it('离线服务器显示错误信息', () => {
    const offline = { ...server, status: 'offline', last_error: '连接超时' };
    render(<ServerCard server={offline} onSelect={() => {}} />);
    expect(screen.getByText(/连接超时/)).toBeTruthy();
  });

  it('点击卡片触发 onSelect', () => {
    const onSelect = vi.fn();
    render(<ServerCard server={server} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('web1'));
    expect(onSelect).toHaveBeenCalledWith('srv-1');
  });
});
