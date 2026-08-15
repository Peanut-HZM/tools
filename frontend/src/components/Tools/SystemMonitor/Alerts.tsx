// frontend/src/components/Tools/SystemMonitor/Alerts.tsx
import { useEffect, useState, useCallback } from 'react';
import { useMonitorStore } from '../../../stores/monitorStore';
import * as monitorApi from '../../../api/monitorApi';
import type { AlertRule, AlertLog, MonitorSettings } from '../../../api/monitorApi';
import ConfirmModal from './components/ConfirmModal';

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
      {error && <div className="text-sm text-red-400">{error}</div>}

      {/* 通知设置 */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
        <div className="text-sm text-white font-medium mb-3">通知设置</div>
        <div className="flex items-center gap-3">
          <input
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            placeholder="Webhook 地址（钉钉/企业微信/飞书机器人）"
            value={settings.webhook_url}
            onChange={(e) => setSettings({ ...settings, webhook_url: e.target.value })}
          />
          <button className="px-3 py-2 rounded-lg text-sm bg-emerald-600 hover:bg-emerald-500 text-white" onClick={saveSettings}>保存</button>
        </div>
        <div className="text-xs text-slate-600 mt-2">
          采集间隔 {settings.collect_interval} 秒 · 告警触发后通过 Webhook 推送，同时在本页记录站内通知
        </div>
      </div>

      {/* 规则列表 */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800">
          <div className="text-sm text-white font-medium">告警规则</div>
          <button className="px-3 py-1.5 rounded-lg text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
            onClick={() => setEditing({ ...EMPTY_FORM, id: '' })}>
            <i className="fas fa-plus mr-1" />新建规则
          </button>
        </div>
        {rules.length === 0 ? (
          <div className="text-center text-slate-600 py-8 text-sm">暂无告警规则</div>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-slate-800">
                <th className="text-left px-4 py-2">服务器</th>
                <th className="text-left px-4 py-2">条件</th>
                <th className="text-left px-4 py-2">持续时间</th>
                <th className="text-left px-4 py-2">状态</th>
                <th className="text-right px-4 py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id} className="border-b border-slate-800/50 last:border-0">
                  <td className="px-4 py-2 text-slate-300">{serverName(r.server_id)}</td>
                  <td className="px-4 py-2 text-slate-300">
                    {METRIC_LABELS[r.metric] || r.metric} {r.operator} {r.threshold}
                  </td>
                  <td className="px-4 py-2 text-slate-500">连续 {r.duration} 次</td>
                  <td className="px-4 py-2">
                    <button
                      className={r.enabled ? 'text-emerald-400' : 'text-slate-500'}
                      onClick={async () => {
                        await monitorApi.updateAlert(r.id, { enabled: !r.enabled });
                        await loadRules();
                      }}
                    >
                      {r.enabled ? '已启用' : '已停用'}
                    </button>
                  </td>
                  <td className="px-4 py-2 text-right space-x-2">
                    <button className="text-slate-400 hover:text-white"
                      onClick={() => setEditing({ server_id: r.server_id, metric: r.metric, operator: r.operator, threshold: String(r.threshold), duration: String(r.duration), enabled: r.enabled, id: r.id })}>
                      编辑
                    </button>
                    <button className="text-red-400/80 hover:text-red-300" onClick={() => setDeleting(r)}>删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 触发记录 */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800">
          <div className="text-sm text-white font-medium">触发记录</div>
          <button className="px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300" onClick={markRead}>全部已读</button>
        </div>
        {logs.length === 0 ? (
          <div className="text-center text-slate-600 py-8 text-sm">暂无告警记录</div>
        ) : (
          <div className="divide-y divide-slate-800/50">
            {logs.map((log) => (
              <div key={log.id} className={`px-4 py-2.5 flex items-center gap-3 ${log.is_read ? 'opacity-60' : ''}`}>
                <span className={`h-2 w-2 rounded-full shrink-0 ${log.status === 'firing' ? 'bg-red-500' : 'bg-emerald-500'}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-slate-300">
                    <span className="text-white font-medium">{log.server_name}</span>
                    <span className="mx-1.5 text-slate-600">·</span>
                    {METRIC_LABELS[log.metric] || log.metric}
                    <span className="ml-1.5 text-red-400">{log.actual_value}</span>
                    <span className="ml-1.5 text-slate-600">{log.status === 'firing' ? '触发' : '恢复'}</span>
                  </div>
                  <div className="text-xs text-slate-600 mt-0.5">{fmtTime(log.notified_at)}</div>
                </div>
              </div>
            ))}
          </div>
        )}
        {logTotal > 20 && (
          <div className="flex justify-end items-center gap-2 px-4 py-2 text-xs text-slate-500">
            <button className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40"
              disabled={logPage <= 1} onClick={() => { setLogPage(logPage - 1); loadLogs(logPage - 1); }}>上一页</button>
            <span>{logPage} / {Math.max(1, Math.ceil(logTotal / 20))}</span>
            <button className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40"
              disabled={logPage >= Math.ceil(logTotal / 20)} onClick={() => { setLogPage(logPage + 1); loadLogs(logPage + 1); }}>下一页</button>
          </div>
        )}
      </div>

      {/* 编辑弹窗 */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setEditing(null)}>
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 w-[420px] space-y-3" onClick={(e) => e.stopPropagation()}>
            <div className="text-white font-medium">{editing.id ? '编辑规则' : '新建规则'}</div>
            <div className="flex gap-3">
              <select className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                value={editing.server_id} onChange={(e) => setEditing({ ...editing, server_id: e.target.value })}>
                <option value="all">全部服务器</option>
                {servers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <select className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                value={editing.metric} onChange={(e) => setEditing({ ...editing, metric: e.target.value })}>
                {METRIC_OPTIONS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>
            <div className="flex gap-3">
              <select className="w-24 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                value={editing.operator} onChange={(e) => setEditing({ ...editing, operator: e.target.value })}>
                {OPERATORS.map((op) => <option key={op} value={op}>{op}</option>)}
              </select>
              <input className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                placeholder="阈值" value={editing.threshold} onChange={(e) => setEditing({ ...editing, threshold: e.target.value })} />
              <input className="w-28 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                placeholder="连续次数" value={editing.duration} onChange={(e) => setEditing({ ...editing, duration: e.target.value })} />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-400">
              <input type="checkbox" checked={editing.enabled} onChange={(e) => setEditing({ ...editing, enabled: e.target.checked })} />
              启用规则
            </label>
            {formError && <div className="text-sm text-red-400">{formError}</div>}
            <div className="flex justify-end gap-3 pt-2">
              <button className="px-4 py-1.5 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800" onClick={() => setEditing(null)}>取消</button>
              <button className="px-4 py-1.5 rounded-lg text-sm text-white bg-emerald-600 hover:bg-emerald-500" onClick={saveRule}>保存</button>
            </div>
          </div>
        </div>
      )}

      <ConfirmModal
        open={!!deleting}
        title="删除规则"
        message={`确定删除该告警规则（${deleting ? METRIC_LABELS[deleting.metric] : ''} ${deleting?.operator} ${deleting?.threshold}）？`}
        onConfirm={async () => {
          if (!deleting) return;
          await monitorApi.deleteAlert(deleting.id);
          setDeleting(null);
          await loadRules();
        }}
        onCancel={() => setDeleting(null)}
        danger
      />
    </div>
  );
}
