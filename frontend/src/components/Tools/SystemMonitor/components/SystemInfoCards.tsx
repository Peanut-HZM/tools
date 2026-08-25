// frontend/src/components/Tools/SystemMonitor/components/SystemInfoCards.tsx
import type { MonitorServer } from '../../../../api/monitorApi';

interface SystemInfoCardsProps {
  info: Record<string, string | number> | null;
  server: MonitorServer;
}

/** 系统信息卡片网格（8 张） */
export default function SystemInfoCards({ info, server }: SystemInfoCardsProps) {
  const cards = [
    { icon: 'fa-server', label: '主机', value: info?.hostname || server.name },
    { icon: 'fa-laptop', label: '系统', value: info?.os ? String(info.os).slice(0, 40) : server.server_type === 'local' ? '加载中' : 'Linux' },
    { icon: 'fa-code', label: '内核', value: info?.kernel ? String(info.kernel) : '-' },
    { icon: 'fa-clock', label: '运行时间', value: info?.uptime_text ? String(info.uptime_text) : '-' },
    { icon: 'fa-network-wired', label: '地址', value: server.host || '本机' },
    { icon: 'fa-user', label: '用户', value: server.username || '-' },
    { icon: 'fa-tag', label: '类型', value: server.server_type === 'local' ? '本机' : 'SSH 远程' },
    { icon: 'fa-bolt', label: '状态', value: server.status === 'online' ? '在线' : server.status === 'offline' ? '离线' : server.status === 'error' ? '异常' : '待采集' },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {cards.map((card) => (
        <div key={card.label} className="bg-canvas rounded-xl p-3 border border-border">
          <div className="flex items-center gap-1.5 text-xs text-ink-faint mb-1">
            <i className={`fas ${card.icon}`} />
            {card.label}
          </div>
          <div className="text-sm text-ink-inverse font-medium break-all">{card.value}</div>
        </div>
      ))}
    </div>
  );
}
