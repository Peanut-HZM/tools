// frontend/src/components/Tools/SystemMonitor/components/AddServerModal.tsx
import { useState } from 'react';
import type { SSHConfig } from '../../../../api/sshToolApi';
import * as monitorApi from '../../../../api/monitorApi';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/Card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

interface AddServerModalProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  sshConfigs: SSHConfig[];
}

/** 添加服务器弹窗：手动填写 / 从 SSH 配置导入 */
export default function AddServerModal({ open, onClose, onSaved, sshConfigs }: AddServerModalProps) {
  const [mode, setMode] = useState<'manual' | 'ssh'>('manual');
  const [form, setForm] = useState({
    name: '', host: '', port: '22', username: 'root', password: '', group_name: '',
  });
  const [sshConfigId, setSshConfigId] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  const submit = async () => {
    setError('');
    setSaving(true);
    try {
      if (mode === 'ssh') {
        if (!sshConfigId) { setError('请选择 SSH 配置'); return; }
        await monitorApi.importFromSsh(sshConfigId);
      } else {
        if (!form.name || !form.host) { setError('服务器名称和地址必填'); return; }
        await monitorApi.createServer({
          name: form.name, host: form.host, port: Number(form.port),
          username: form.username, password: form.password || undefined,
          group_name: form.group_name || undefined,
        });
      }
      onSaved();
      onClose();
    } catch (e: any) {
      setError(e.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <Card className="p-5 w-[480px] max-w-[92vw]" onClick={(e) => e.stopPropagation()}>
        <CardHeader className="p-0 mb-4 flex flex-row items-center justify-between">
          <CardTitle className="text-base font-medium text-ink">添加监控服务器</CardTitle>
          <button className="text-ink-faint hover:text-ink" onClick={onClose}>✕</button>
        </CardHeader>
        <CardContent className="p-0">
        <div className="flex gap-2 mb-4">
          <button
            className={`px-3 py-1.5 rounded-lg text-sm ${mode === 'manual' ? 'bg-emerald-600 text-ink-inverse' : 'bg-surface-1 text-ink-muted'}`}
            onClick={() => setMode('manual')}
          >
            手动填写
          </button>
          <button
            className={`px-3 py-1.5 rounded-lg text-sm ${mode === 'ssh' ? 'bg-emerald-600 text-ink-inverse' : 'bg-surface-1 text-ink-muted'}`}
            onClick={() => setMode('ssh')}
          >
            从 SSH 配置导入
          </button>
        </div>
        {mode === 'manual' ? (
          <div className="space-y-3">
            <Input
              placeholder="服务器名称 *" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <div className="flex gap-3">
              <Input className="flex-1"
                placeholder="IP/域名 *" value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} />
              <Input className="w-24"
                placeholder="端口" value={form.port} onChange={(e) => setForm({ ...form, port: e.target.value })} />
            </div>
            <div className="flex gap-3">
              <Input className="flex-1"
                placeholder="用户名" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
              <Input className="flex-1"
                placeholder="密码（或留空用密钥）" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </div>
            <Input
              placeholder="分组（可选）" value={form.group_name} onChange={(e) => setForm({ ...form, group_name: e.target.value })} />
          </div>
        ) : (
          <div>
            {sshConfigs.length === 0 ? (
              <div className="text-sm text-ink-faint py-3">暂无 SSH 配置，请先在 SSH 工具中添加</div>
            ) : (
              <Select value={sshConfigId} onValueChange={setSshConfigId}>
                <SelectTrigger>
                  <SelectValue placeholder="请选择 SSH 配置" />
                </SelectTrigger>
                <SelectContent>
                  {sshConfigs.map((c) => (
                    <SelectItem key={c.id} value={c.id}>{c.alias}（{c.host}）</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            <div className="text-xs text-ink-faint mt-2">导入后凭据独立管理，与 SSH 工具互不影响</div>
          </div>
        )}
        {error && <div className="text-sm text-danger mt-3">{error}</div>}
        </CardContent>
        <CardFooter className="p-0 mt-5 flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose}>取消</Button>
          <button className="px-4 py-1.5 rounded-lg text-sm text-ink-inverse bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50" onClick={submit} disabled={saving}>
            {saving ? '保存中...' : '保存'}
          </button>
        </CardFooter>
      </Card>
    </div>
  );
}
