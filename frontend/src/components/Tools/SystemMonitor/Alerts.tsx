// frontend/src/components/Tools/SystemMonitor/Alerts.tsx
import { useEffect, useState, useCallback } from 'react';
import { Plus } from 'lucide-react';
import { useMonitorStore } from '../../../stores/monitorStore';
import * as monitorApi from '../../../api/monitorApi';
import type { AlertRule, AlertLog, MonitorSettings } from '../../../api/monitorApi';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

const METRIC_OPTIONS = [
  { value: 'cpu_percent', label: 'CPU 使用率' },
  { value: 'memory_percent', label: '内存使用率' },
  { value: 'disk_percent', label: '磁盘使用率' },
  { value: 'load_avg', label: '负载（1分钟）' },
  { value: 'net_recv_rate', label: '网络接收速率' },
  { value: 'net_sent_rate', label: '网络发送速率' },
];

const OPERATORS = ['>', '>=', '<', '<='];

const METRIC_LABELS: Record<string, string> = Object.fromEntries(METRIC_OPTIONS.map((m) => [m.value, m.label]));

interface RuleForm {
  id?: string;
  server_id: string;
  metric: string;
  operator: string;
  threshold: string;
  duration: string;
  enabled: boolean;
}

const EMPTY_FORM: RuleForm = { server_id: 'all', metric: 'cpu_percent', operator: '>', threshold: '90', duration: '3', enabled: true };

/** 页签⑥告警设置：规则 CRUD + Webhook 配置 + 触发记录 */
export default function Alerts() {
  const { servers, setUnreadAlerts } = useMonitorStore();
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [logs, setLogs] = useState<AlertLog[]>([]);
  const [settings, setSettings] = useState<MonitorSettings>({ webhook_url: '', collect_interval: 30 });
  const [editing, setEditing] = useState<RuleForm | null>(null);
  const [deleting, setDeleting] = useState<AlertRule | null>(null);
  const [formError, setFormError] = useState('');
  const [error, setError] = useState('');
  const [logPage, setLogPage] = useState(1);
  const [logTotal, setLogTotal] = useState(0);

  const loadRules = useCallback(async () => {
    setRules(await monitorApi.getAlerts());
  }, []);

  const loadLogs = useCallback(async (page = 1) => {
    const data = await monitorApi.getAlertLogs(page, 20);
    setLogs(data.logs);
    setLogTotal(data.total);
    setUnreadAlerts(data.unread_count);
  }, [setUnreadAlerts]);

  useEffect(() => {
    Promise.all([loadRules(), loadLogs(), monitorApi.getSettings()])
      .then(([, , s]) => setSettings(s))
      .catch((e: any) => setError(e.message || '加载失败'));
  }, [loadRules, loadLogs]);

  const saveRule = async () => {
    if (!editing) return;
    setFormError('');
    const threshold = Number(editing.threshold);
    const duration = Number(editing.duration);
    if (Number.isNaN(threshold)) { setFormError('阈值必须是数字'); return; }
    if (Number.isNaN(duration) || duration < 1 || duration > 60) { setFormError('持续时间需在 1-60 之间'); return; }
    try {
      const payload = {
        server_id: editing.server_id, metric: editing.metric, operator: editing.operator,
        threshold, duration, enabled: editing.enabled,
      };
      if (editing.id) await monitorApi.updateAlert(editing.id, payload);
      else await monitorApi.createAlert(payload);
      setEditing(null);
      await loadRules();
    } catch (e: any) {
      setFormError(e.message || '保存失败');
    }
  };

  const markRead = async () => {
    await monitorApi.markAlertLogsRead();
    setLogs((prev) => prev.map((l) => ({ ...l, is_read: true })));
    setUnreadAlerts(0);
  };

  const saveSettings = async () => {
    try {
      await monitorApi.saveSettings(settings);
    } catch (e: any) {
      setError(e.message || '保存设置失败');
    }
  };

  const serverName = (id: string) => {
    if (id === 'all') return '全部服务器';
    return servers.find((s) => s.id === id)?.name || id;
  };

  const fmtTime = (t: string) => t.replace('T', ' ').slice(0, 19);

  return (
    <div className="space-y-6">
      {error && <div className="text-sm text-danger">{error}</div>}

      {/* 通知设置 */}
      <Card className="p-4 bg-canvas">
        <div className="text-sm text-ink font-medium mb-3">通知设置</div>
        <div className="flex items-center gap-3">
          <Input
            className="flex-1"
            placeholder="Webhook 地址（钉钉/企业微信/飞书机器人）"
            value={settings.webhook_url}
            onChange={(e) => setSettings({ ...settings, webhook_url: e.target.value })}
          />
          <button className="px-3 py-2 rounded-lg text-sm bg-success hover:opacity-90 text-ink-inverse" onClick={saveSettings}>保存</button>
        </div>
        <div className="text-xs text-ink-faint mt-2">
          采集间隔 {settings.collect_interval} 秒 · 告警触发后通过 Webhook 推送，同时在本页记录站内通知
        </div>
      </Card>

      {/* 规则列表 */}
      <Card className="overflow-hidden bg-canvas">
        <CardHeader className="px-4 py-2.5 border-b border-border flex flex-row items-center justify-between">
          <CardTitle className="text-sm font-medium text-ink">告警规则</CardTitle>
          <button className="px-3 py-1.5 rounded-lg text-xs bg-success hover:opacity-90 text-ink-inverse"
            onClick={() => setEditing({ ...EMPTY_FORM, id: '' })}>
            <Plus className="w-3.5 h-3.5 mr-1" />新建规则
          </button>
        </CardHeader>
        <CardContent className="p-0">
        {rules.length === 0 ? (
          <div className="text-center text-ink-faint py-8 text-sm">暂无告警规则</div>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-ink-faint border-b border-border">
                <th className="text-left px-4 py-2">服务器</th>
                <th className="text-left px-4 py-2">条件</th>
                <th className="text-left px-4 py-2">持续时间</th>
                <th className="text-left px-4 py-2">状态</th>
                <th className="text-right px-4 py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id} className="border-b border-border/50 last:border-0">
                  <td className="px-4 py-2 text-ink-muted">{serverName(r.server_id)}</td>
                  <td className="px-4 py-2 text-ink-muted">
                    {METRIC_LABELS[r.metric] || r.metric} {r.operator} {r.threshold}
                  </td>
                  <td className="px-4 py-2 text-ink-faint">连续 {r.duration} 次</td>
                  <td className="px-4 py-2">
                    <button
                      className={r.enabled ? 'text-success' : 'text-ink-faint'}
                      onClick={async () => {
                        await monitorApi.updateAlert(r.id, { enabled: !r.enabled });
                        await loadRules();
                      }}
                    >
                      {r.enabled ? '已启用' : '已停用'}
                    </button>
                  </td>
                  <td className="px-4 py-2 text-right space-x-2">
                    <button className="text-ink-muted hover:text-ink"
                      onClick={() => setEditing({ server_id: r.server_id, metric: r.metric, operator: r.operator, threshold: String(r.threshold), duration: String(r.duration), enabled: r.enabled, id: r.id })}>
                      编辑
                    </button>
                    <button className="text-danger/80 hover:text-danger" onClick={() => setDeleting(r)}>删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        </CardContent>
      </Card>

      {/* 触发记录 */}
      <Card className="overflow-hidden bg-canvas">
        <CardHeader className="px-4 py-2.5 border-b border-border flex flex-row items-center justify-between">
          <CardTitle className="text-sm font-medium text-ink">触发记录</CardTitle>
          <Button variant="secondary" size="sm" onClick={markRead}>全部已读</Button>
        </CardHeader>
        <CardContent className="p-0">
        {logs.length === 0 ? (
          <div className="text-center text-ink-faint py-8 text-sm">暂无告警记录</div>
        ) : (
          <div className="divide-y divide-slate-800/50">
            {logs.map((log) => (
              <div key={log.id} className={`px-4 py-2.5 flex items-center gap-3 ${log.is_read ? 'opacity-60' : ''}`}>
                <span className={`h-2 w-2 rounded-full shrink-0 ${log.status === 'firing' ? 'bg-danger' : 'bg-success'}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-ink-muted">
                    <span className="text-ink font-medium">{log.server_name}</span>
                    <span className="mx-1.5 text-ink-faint">·</span>
                    {METRIC_LABELS[log.metric] || log.metric}
                    <span className="ml-1.5 text-danger">{log.actual_value}</span>
                    <span className="ml-1.5 text-ink-faint">{log.status === 'firing' ? '触发' : '恢复'}</span>
                  </div>
                  <div className="text-xs text-ink-faint mt-0.5">{fmtTime(log.notified_at)}</div>
                </div>
              </div>
            ))}
          </div>
        )}
        {logTotal > 20 && (
          <div className="flex justify-end items-center gap-2 px-4 py-2 text-xs text-ink-faint">
            <Button variant="secondary" size="sm" disabled={logPage <= 1} onClick={() => { setLogPage(logPage - 1); loadLogs(logPage - 1); }}>上一页</Button>
            <span>{logPage} / {Math.max(1, Math.ceil(logTotal / 20))}</span>
            <Button variant="secondary" size="sm" disabled={logPage >= Math.ceil(logTotal / 20)} onClick={() => { setLogPage(logPage + 1); loadLogs(logPage + 1); }}>下一页</Button>
          </div>
        )}
        </CardContent>
      </Card>

      {/* 编辑弹窗 */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setEditing(null)}>
          <Card className="bg-canvas p-5 w-[420px] space-y-3" onClick={(e) => e.stopPropagation()}>
            <div className="text-ink font-medium">{editing.id ? '编辑规则' : '新建规则'}</div>
            <div className="flex gap-3">
              <Select value={editing.server_id} onValueChange={(v) => setEditing({ ...editing, server_id: v })}>
                <SelectTrigger className="flex-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部服务器</SelectItem>
                  {servers.map((s) => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={editing.metric} onValueChange={(v) => setEditing({ ...editing, metric: v })}>
                <SelectTrigger className="flex-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {METRIC_OPTIONS.map((m) => <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-3">
              <Select value={editing.operator} onValueChange={(v) => setEditing({ ...editing, operator: v })}>
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {OPERATORS.map((op) => <SelectItem key={op} value={op}>{op}</SelectItem>)}
                </SelectContent>
              </Select>
              <Input className="flex-1"
                placeholder="阈值" value={editing.threshold} onChange={(e) => setEditing({ ...editing, threshold: e.target.value })} />
              <Input className="w-28"
                placeholder="连续次数" value={editing.duration} onChange={(e) => setEditing({ ...editing, duration: e.target.value })} />
            </div>
            <label className="flex items-center gap-2 text-sm text-ink-muted">
              <input type="checkbox" checked={editing.enabled} onChange={(e) => setEditing({ ...editing, enabled: e.target.checked })} />
              启用规则
            </label>
            {formError && <div className="text-sm text-danger">{formError}</div>}
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="ghost" onClick={() => setEditing(null)}>取消</Button>
              <button className="px-4 py-1.5 rounded-lg text-sm text-ink-inverse bg-success hover:opacity-90" onClick={saveRule}>保存</button>
            </div>
          </Card>
        </div>
      )}

      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(open) => { if (!open) setDeleting(null); }}
        title="删除规则"
        description={`确定删除该告警规则（${deleting ? METRIC_LABELS[deleting.metric] : ''} ${deleting?.operator} ${deleting?.threshold}）？`}
        confirmText="删除"
        variant="destructive"
        onConfirm={async () => {
          if (!deleting) return;
          await monitorApi.deleteAlert(deleting.id);
          await loadRules();
        }}
      />
    </div>
  );
}
