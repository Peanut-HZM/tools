// frontend/src/components/Tools/SystemMonitor/components/SystemInfoCards.tsx
import type { MonitorServer } from '../../../../api/monitorApi';
import { Server, Laptop, Code, Clock, Network, User, Tag, Zap } from 'lucide-react';
import { Card } from '@/components/ui/Card';

interface SystemInfoCardsProps {
  info: Record<string, string | number> | null;
  server: MonitorServer;
}

/** 系统信息卡片网格（8 张） */
export default function SystemInfoCards({ info, server }: SystemInfoCardsProps) {
  const cards = [
    { icon: Server, label: '主机', value: info?.hostname || server.name },
    { icon: Laptop, label: '系统', value: info?.os ? String(info.os).slice(0, 40) : server.server_type === 'local' ? '加载中' : 'Linux' },
    { icon: Code, label: '内核', value: info?.kernel ? String(info.kernel) : '-' },
    { icon: Clock, label: '运行时间', value: info?.uptime_text ? String(info.uptime_text) : '-' },
    { icon: Network, label: '地址', value: server.host || '本机' },
    { icon: User, label: '用户', value: server.username || '-' },
    { icon: Tag, label: '类型', value: server.server_type === 'local' ? '本机' : 'SSH 远程' },
    { icon: Zap, label: '状态', value: server.status === 'online' ? '在线' : server.status === 'offline' ? '离线' : server.status === 'error' ? '异常' : '待采集' },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
        <Card key={card.label} className="p-3 bg-canvas">
          <div className="flex items-center gap-1.5 text-xs text-ink-faint mb-1">
            <Icon className="w-4 h-4" />
            {card.label}
          </div>
          <div className="text-sm text-ink font-medium break-all">{card.value}</div>
        </Card>
        );
      })}
    </div>
  );
}
