import { useState } from 'react';
import { Plus, Server } from 'lucide-react';
import { useMonitorStore } from '../../../stores/monitorStore';
import type { MonitorServer } from '../../../api/monitorApi';
import * as monitorApi from '../../../api/monitorApi';
import * as sshApi from '../../../api/sshToolApi';
import { ServerCard } from './components/ServerCard';
import AddServerModal from './components/AddServerModal';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent } from '@/components/ui/Card';

/** 页签①服务器列表：状态卡片网格 + 添加/编辑/删除/重试 */
export default function ServerList() {
  const { servers, setServers, setSelectedServerId, setActiveTab } = useMonitorStore();
  const [addOpen, setAddOpen] = useState(false);
  const [editing, setEditing] = useState<MonitorServer | null>(null);
  const [deleting, setDeleting] = useState<MonitorServer | null>(null);
  const [sshConfigs, setSshConfigs] = useState<sshApi.SSHConfig[]>([]);
  const [error, setError] = useState('');

  const refresh = async () => {
    try {
      setServers(await monitorApi.getServers());
    } catch (e: any) {
      setError(e.message || '加载失败');
    }
  };

  const openAdd = async () => {
    setError('');
    try {
      setSshConfigs(await sshApi.getSSHConfigs());
    } catch { setSshConfigs([]); }
    setAddOpen(true);
  };

  const handleDelete = async () => {
    if (!deleting) return;
    try {
      await monitorApi.deleteServer(deleting.id);
      setDeleting(null);
      await refresh();
    } catch (e: any) {
      setError(e.message || '删除失败');
      setDeleting(null);
    }
  };

  const handleRetry = async (server: MonitorServer) => {
    try {
      await monitorApi.retryServer(server.id);
      await refresh();
    } catch (e: any) {
      setError(e.message || '重试失败');
    }
  };

  const enter = (id: string) => {
    setSelectedServerId(id);
    setActiveTab('overview');
  };

  const groups: Record<string, MonitorServer[]> = {};
  for (const s of servers) {
    const g = s.group_name || '默认分组';
    (groups[g] ||= []).push(s);
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="text-sm text-ink-muted">共 {servers.length} 台服务器</div>
        <button className="px-3 py-1.5 rounded-lg text-sm bg-emerald-600 hover:bg-emerald-500 text-ink-inverse" onClick={openAdd}>
          <Plus className="w-3.5 h-3.5 mr-1.5" />添加服务器
        </button>
      </div>
      {error && <div className="text-sm text-danger">{error}</div>}
      {Object.entries(groups).map(([group, list]) => (
        <div key={group}>
          <div className="text-xs text-ink-faint mb-2">{group}</div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-3">
            {list.map((server) => (
              <ServerCard
                key={server.id}
                server={server}
                onSelect={enter}
                onEdit={(s) => setEditing(s)}
                onDelete={(s) => setDeleting(s)}
                onRetry={handleRetry}
              />
            ))}
          </div>
        </div>
      ))}
      {servers.length === 0 && (
        <div className="text-center text-ink-faint py-16">
          <Server className="w-10 h-10 mb-3 block text-ink-faint" />
          暂无监控服务器，点击右上角添加
        </div>
      )}
      <AddServerModal open={addOpen} onClose={() => setAddOpen(false)} onSaved={refresh} sshConfigs={sshConfigs} />
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setEditing(null)}>
          <Card className="bg-canvas p-5 w-[400px]" onClick={(e) => e.stopPropagation()}>
            <div className="text-ink font-medium mb-3">编辑服务器（编辑后需手动触发采集）</div>
            <Input
              className="w-full mb-3"
              defaultValue={editing.name}
              placeholder="服务器名称"
              id="edit-name"
            />
            <div className="flex justify-end gap-3">
              <Button variant="ghost" onClick={() => setEditing(null)}>取消</Button>
              <button
                className="px-4 py-1.5 rounded-lg text-sm text-ink-inverse bg-emerald-600 hover:bg-emerald-500"
                onClick={async () => {
                  const nameInput = document.getElementById('edit-name') as HTMLInputElement;
                  try {
                    await monitorApi.updateServer(editing.id, { name: nameInput.value });
                    setEditing(null);
                    await refresh();
                  } catch (e: any) {
                    setError(e.message || '更新失败');
                  }
                }}
              >
                保存
              </button>
            </div>
          </Card>
        </div>
      )}
      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(open) => { if (!open) setDeleting(null); }}
        title="删除服务器"
        description={`确定删除监控服务器「${deleting?.name}」？其历史指标与关联告警记录将保留。`}
        confirmText="删除"
        variant="destructive"
        onConfirm={handleDelete}
      />
    </div>
  );
}