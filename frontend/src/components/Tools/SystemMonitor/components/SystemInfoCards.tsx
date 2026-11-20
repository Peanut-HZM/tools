// frontend/src/components/Tools/SystemMonitor/components/SystemInfoCards.tsx
/**
 * 系统信息卡片网格
 *
 * 设计参考 awesome-design-md / Linear：
 * 标签用 11px eyebrow 小字 + 图标，值用 13px 中等字重、可换行；
 * 卡片统一 surface-1 + hairline 边框，悬停只提亮边框，不做位移（信息区保持稳定）。
 */
import type { MonitorServer } from '../../../../api/monitorApi';
import { Server, Laptop, Code, Clock, Network, User, Tag, Zap } from 'lucide-react';

interface SystemInfoCardsProps {
  info: Record<string, string | number> | null;
  server: MonitorServer;
}

const STATUS_TEXT: Record<string, { label: string; tone: string }> = {
  online: { label: '在线', tone: 'text-accent-success' },
  offline: { label: '离线', tone: 'text-accent-danger' },
  error: { label: '异常', tone: 'text-accent-warning' },
  disabled: { label: '已停用', tone: 'text-ink-faint' },
};

/** 系统信息卡片网格（8 张） */
export default function SystemInfoCards({ info, server }: SystemInfoCardsProps) {
  const status = STATUS_TEXT[server.status] ?? { label: '待采集', tone: 'text-ink-faint' };
  const cards = [
    { icon: Server, label: '主机名', value: info?.hostname || server.name },
    {
      icon: Laptop,
      label: '操作系统',
      value: info?.os ? String(info.os).slice(0, 48) : server.server_type === 'local' ? '加载中' : 'Linux',
    },
    { icon: Code, label: '内核', value: info?.kernel ? String(info.kernel) : '—' },
    { icon: Clock, label: '运行时间', value: info?.uptime_text ? String(info.uptime_text) : '—' },
    { icon: Network, label: '地址', value: server.host || '本机' },
    { icon: User, label: '登录用户', value: server.username || '—' },
    { icon: Tag, label: '接入方式', value: server.server_type === 'local' ? '本机' : 'SSH 远程' },
    { icon: Zap, label: '状态', value: status.label, tone: status.tone },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div
            key={card.label}
            className="rounded-xl border border-border bg-surface-1 px-3 py-2.5 transition-colors hover:border-border-strong"
          >
            <div className="flex items-center gap-1.5 text-[11px] text-ink-faint">
              <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />
              {card.label}
            </div>
            <div
              className={`mt-1 break-all text-[13px] font-medium leading-snug ${card.tone ?? 'text-ink'}`}
              title={String(card.value)}
            >
              {card.value}
            </div>
          </div>
        );
      })}
    </div>
  );
}
