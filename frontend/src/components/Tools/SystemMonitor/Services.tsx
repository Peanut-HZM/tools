// frontend/src/components/Tools/SystemMonitor/Services.tsx
import { useEffect, useState, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';
import { useMonitorStore } from '../../../stores/monitorStore';
import * as monitorApi from '../../../api/monitorApi';
import type { ServiceInfo } from '../../../api/monitorApi';
import ServerSelector from './components/ServerSelector';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

/** 页签⑤服务管理：systemd 服务列表与启停 */
export default function Services() {
  const { servers, selectedServerId, setSelectedServerId } = useMonitorStore();
  const [services, setServices] = useState<ServiceInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [sudoOk, setSudoOk] = useState(false);
  const [confirm, setConfirm] = useState<{ unit: string; action: 'start' | 'stop' | 'restart' } | null>(null);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  const load = useCallback(async () => {
    if (!selectedServerId) return;
    setLoading(true);
    try {
      const [svcRes, privRes] = await Promise.all([
        monitorApi.getServices(selectedServerId),
        monitorApi.getPrivileges(selectedServerId),
      ]);
      setServices(svcRes.services);
      setSudoOk(privRes.sudo_available);
    } catch (e: any) {
      setError(e.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [selectedServerId]);

  useEffect(() => { load(); }, [load]);

  const doAction = async () => {
    if (!confirm || !selectedServerId) return;
    try {
      await monitorApi.serviceAction(selectedServerId, confirm.unit, confirm.action);
      setConfirm(null);
      await load();
    } catch (e: any) {
      setError(e.message || '操作失败');
      setConfirm(null);
    }
  };

  const filtered = services.filter((s) => search === '' || s.name.includes(search));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <ServerSelector servers={servers} value={selectedServerId} onChange={setSelectedServerId} />
        <Input
          className="flex-1 min-w-[180px]"
          placeholder="搜索服务名"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Button variant="secondary" size="sm" onClick={load}>
          <RefreshCw className="w-3.5 h-3.5 mr-1.5" />刷新
        </Button>
      </div>
      {!sudoOk && selectedServerId && (
        <div className="text-xs text-amber-400/80 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
          当前用户可能没有 sudo 权限，服务操作可能需要 root 或无密码 sudo
        </div>
      )}
      {error && <div className="text-sm text-danger">{error}</div>}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-ink-faint border-b border-border">
              <th className="text-left px-3 py-2">服务名</th>
              <th className="text-left px-3 py-2">状态</th>
              <th className="text-left px-3 py-2 hidden md:table-cell">描述</th>
              <th className="text-left px-3 py-2 hidden lg:table-cell">开机自启</th>
              <th className="text-right px-3 py-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((s) => {
              const running = s.state === 'running';
              return (
                <tr key={s.name} className="border-b border-border/50 last:border-0 hover:bg-surface-1/30">
                  <td className="px-3 py-2 text-ink font-mono">{s.name}</td>
                  <td className="px-3 py-2">
                    <Badge variant={running ? 'success' : 'destructive'} className="text-[10px]">
                      {s.state}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-ink-faint hidden md:table-cell max-w-[280px] truncate">{s.description}</td>
                  <td className="px-3 py-2 text-ink-muted hidden lg:table-cell">{s.enabled ? '已启用' : '未启用'}</td>
                  <td className="px-3 py-2 text-right space-x-2">
                    {running ? (
                      <>
                        <button className="text-amber-400/80 hover:text-amber-300" onClick={() => setConfirm({ unit: s.name, action: 'restart' })}>重启</button>
                        <button className="text-danger/80 hover:text-red-300" onClick={() => setConfirm({ unit: s.name, action: 'stop' })}>停止</button>
                      </>
                    ) : (
                      <button className="text-success/80 hover:text-emerald-300" onClick={() => setConfirm({ unit: s.name, action: 'start' })}>启动</button>
                    )}
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && !loading && (
              <tr><td colSpan={5} className="px-3 py-10 text-center text-ink-faint">暂无服务</td></tr>
            )}
          </tbody>
        </table>
        </CardContent>
      </Card>
      <ConfirmDialog
        open={!!confirm}
        onOpenChange={(open) => { if (!open) setConfirm(null); }}
        title="服务操作"
        description={`确定要${confirm?.action === 'start' ? '启动' : confirm?.action === 'stop' ? '停止' : '重启'}服务 ${confirm?.unit}？`}
        onConfirm={doAction}
      />
    </div>
  );
}