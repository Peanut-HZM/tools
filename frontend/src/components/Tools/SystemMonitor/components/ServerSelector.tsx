// frontend/src/components/Tools/SystemMonitor/components/ServerSelector.tsx
import type { MonitorServer } from '../../../../api/monitorApi';

interface ServerSelectorProps {
  servers: MonitorServer[];
  value: string | null;
  onChange: (id: string) => void;
  disabled?: boolean;
}

/** 服务器选择器：下拉切换当前监控目标 */
export default function ServerSelector({ servers, value, onChange, disabled }: ServerSelectorProps) {
  return (
    <select
      className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-emerald-500 disabled:opacity-50"
      value={value ?? ''}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      data-testid="server-selector"
    >
      {servers.length === 0 && <option value="">暂无服务器</option>}
      {servers.map((s) => (
        <option key={s.id} value={s.id}>
          {s.name}{s.status !== 'online' ? '（离线）' : ''}
        </option>
      ))}
    </select>
  );
}
