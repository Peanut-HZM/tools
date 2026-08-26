import { useEffect } from 'react';
import { useMonitorStore } from '../../../stores/monitorStore';
import * as monitorApi from '../../../api/monitorApi';
import ServerList from './ServerList';
import Overview from './Overview';
import History from './History';
import Processes from './Processes';
import Services from './Services';
import Alerts from './Alerts';
import { Server, Gauge, LineChart, List, Settings, Bell } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';

const TABS = [
  { key: 'servers', label: '服务器列表', icon: Server },
  { key: 'overview', label: '总览', icon: Gauge },
  { key: 'history', label: '历史趋势', icon: LineChart },
  { key: 'processes', label: '进程', icon: List },
  { key: 'services', label: '服务', icon: Settings },
  { key: 'alerts', label: '告警', icon: Bell },
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
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-col h-full">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
          <TabsList className="bg-surface-2">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              return (
              <TabsTrigger key={tab.key} value={tab.key} className="data-[state=active]:bg-emerald-600/20 data-[state=active]:text-success">
                <Icon className="w-3 h-3" />
                {tab.label}
                {tab.key === 'alerts' && unreadAlerts > 0 && (
                  <Badge variant="destructive" className="absolute -top-1 -right-1 text-[10px] min-w-[16px] h-4 px-1 rounded-full border-border">
                    {unreadAlerts > 99 ? '99+' : unreadAlerts}
                  </Badge>
                )}
              </TabsTrigger>
              );
            })}
          </TabsList>
        </div>
        {/* 页签内容 */}
        <div className="flex-1 min-h-0 overflow-y-auto p-4">
          <TabsContent value="servers"><ServerList /></TabsContent>
          <TabsContent value="overview"><Overview /></TabsContent>
          <TabsContent value="history"><History /></TabsContent>
          <TabsContent value="processes"><Processes /></TabsContent>
          <TabsContent value="services"><Services /></TabsContent>
          <TabsContent value="alerts"><Alerts /></TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
