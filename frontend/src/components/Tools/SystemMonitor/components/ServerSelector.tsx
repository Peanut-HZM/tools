// frontend/src/components/Tools/SystemMonitor/components/ServerSelector.tsx
import type { MonitorServer } from '../../../../api/monitorApi';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

interface ServerSelectorProps {
  servers: MonitorServer[];
  value: string | null;
  onChange: (id: string) => void;
  disabled?: boolean;
}

/** 服务器选择器：下拉切换当前监控目标 */
export default function ServerSelector({ servers, value, onChange, disabled }: ServerSelectorProps) {
  return (
    <Select
      value={value ?? ''}
      disabled={disabled}
      onValueChange={(v) => {
        if (v) onChange(v);
      }}
    >
      <SelectTrigger className="bg-canvas border border-border rounded-lg focus:border-emerald-500" data-testid="server-selector">
        <SelectValue placeholder="暂无服务器" />
      </SelectTrigger>
      <SelectContent>
        {servers.length === 0 && <SelectItem value="__none__" disabled>暂无服务器</SelectItem>}
        {servers.map((s) => (
          <SelectItem key={s.id} value={s.id}>
            {s.name}{s.status !== 'online' ? '（离线）' : ''}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
