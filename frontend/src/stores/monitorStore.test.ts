// frontend/src/stores/monitorStore.test.ts
import { describe, it, expect } from 'vitest';
import { useMonitorStore } from './monitorStore';

describe('monitorStore', () => {
  it('默认状态：服务器页签、无选中服务器', () => {
    const state = useMonitorStore.getState();
    expect(state.activeTab).toBe('servers');
    expect(state.selectedServerId).toBeNull();
    expect(state.unreadAlerts).toBe(0);
  });

  it('可以切换页签与选中服务器', () => {
    useMonitorStore.getState().setActiveTab('history');
    expect(useMonitorStore.getState().activeTab).toBe('history');

    useMonitorStore.getState().setSelectedServerId('srv-1');
    expect(useMonitorStore.getState().selectedServerId).toBe('srv-1');
  });

  it('可以设置服务器列表与未读数', () => {
    const fakeServer = { id: 'srv-1', name: '本机', server_type: 'local' } as any;
    useMonitorStore.getState().setServers([fakeServer]);
    expect(useMonitorStore.getState().servers).toHaveLength(1);
    useMonitorStore.getState().setUnreadAlerts(3);
    expect(useMonitorStore.getState().unreadAlerts).toBe(3);
  });
});
