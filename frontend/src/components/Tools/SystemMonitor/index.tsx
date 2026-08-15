import { useEffect } from 'react';
import { useMonitorStore } from '../../../stores/monitorStore';
import * as monitorApi from '../../../api/monitorApi';
import ServerList from './ServerList';
import Overview from './Overview';
import History from './History';
import Processes from './Processes';
import Services from './Services';
import Alerts from './Alerts';

const TABS = [
  { key: 'servers', label: '服务器列表', icon: 'fa-server' },
  { key: 'overview', label: '总览', icon: 'fa-gauge-high' },
  { key: 'history', label: '历史趋势', icon: 'fa-chart-line' },
  { key: 'processes', label: '进程', icon: 'fa-list' },
  { key: 'services', label: '服务', icon: 'fa-cogs' },
  { key: 'alerts', label: '告警', icon: 'fa-bell' },
] as const;

/** 系统监控主容器：六页签导航 + 服务器状态管理 */
export default function SystemMonitor() {
  const { servers, setServers, activeTab, setActiveTab, selectedServerId, setSelectedServerId, unreadAlerts, setUnreadAlerts } = useMonitorStore();

  // 加载服务器列表 + 告警未读数
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [serverList, logs] = await Promise.all([monitorApi.getServers(), monitorApi.getAlertLogs(1, 1)]);
        if (cancelled) return;
        setServers(serverList);
        setUnreadAlerts(logs.unread_count);
        // 无选中时默认选第一台，已有选中则保留（store 签名仅接受值，经 getState 读取当前选中）
        setSelectedServerId(useMonitorStore.getState().selectedServerId ?? serverList[0]?.id ?? null);
      } catch {
        /* 加载失败静默处理，页签仍可切换 */
      }
    };
    load();
    const timer = setInterval(() => {
      monitorApi.getServers().then((list) => {
        if (!cancelled) { setServers(list); setSelectedServerId(useMonitorStore.getState().selectedServerId ?? list[0]?.id ?? null); }
      }).catch(() => {});
    }, 10000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [setServers, setSelectedServerId, setUnreadAlerts]);

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                activeTab === tab.key ? 'bg-emerald-600/20 text-emerald-400' : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
              onClick={() => setActiveTab(tab.key)}
            >
              <i className={`fas ${tab.icon} text-xs`} />
              {tab.label}
              {tab.key === 'alerts' && unreadAlerts > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] rounded-full min-w-[16px] h-4 px-1 flex items-center justify-center">
                  {unreadAlerts > 99 ? '99+' : unreadAlerts}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>
      {/* 页签内容 */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        {activeTab === 'servers' && <ServerList />}
        {activeTab === 'overview' && <Overview />}
        {activeTab === 'history' && <History />}
        {activeTab === 'processes' && <Processes />}
        {activeTab === 'services' && <Services />}
        {activeTab === 'alerts' && <Alerts />}
      </div>
    </div>
  );
}
