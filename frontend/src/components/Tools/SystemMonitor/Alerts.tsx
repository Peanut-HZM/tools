// frontend/src/components/Tools/SystemMonitor/Alerts.tsx
/**
 * 页签⑥告警设置（规则 CRUD + Webhook 配置 + 触发记录）
 *
 * 设计参考 awesome-design-md / Linear：
 * - 顶部统计条：规则总数 / 已启用 / 未读告警
 * - 通知设置：单行表单，保存按钮右对齐，说明用 11px 注脚
 * - 规则表：条件以 mono 呈现，启用状态用可点击的圆点 + 文字
 * - 触发记录：左侧状态竖线 + 时间用 mono，未读加左侧强调条
 */
import { useEffect, useState, useCallback, useMemo } from 'react';
import { Plus, BellRing, BellOff, Webhook, CheckCheck } from 'lucide-react';
import { useMonitorStore } from '../../../stores/monitorStore';
import * as monitorApi from '../../../api/monitorApi';
import type { AlertRule, AlertLog, MonitorSettings } from '../../../api/monitorApi';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';

const METRIC_OPTIONS = [
  { value: 'cpu_percent', label: 'CPU 使用率' },
  { value: 'memory_percent', label: '内存使用率' },
  { value: 'disk_percent', label: '磁盘使用率' },
  { value: 'load_avg', label: '负载（1 分钟）' },
  { value: 'net_recv_rate', label: '网络接收速率' },
  { value: 'net_sent_rate', label: '网络发送速率' },
];

const OPERATORS = ['>', '>=', '<', '<='];

const METRIC_LABELS: Record<string, string> = Object.fromEntries(
  METRIC_OPTIONS.map((m) => [m.value, m.label]),
);

interface RuleForm {
  id?: string;
  server_id: string;
  metric: string;
  operator: string;
  threshold: string;
  duration: string;
  enabled: boolean;
}

const EMPTY_FORM: RuleForm = {
  server_id: 'all',
  metric: 'cpu_percent',
  operator: '>',
  threshold: '90',
  duration: '3',
  enabled: true,
};

/** 顶部统计小卡 */
function StatPill({
  icon: Icon,
  label,
  value,
  tone = 'text-ink',
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-1 px-3 py-2">
      <Icon className="h-3.5 w-3.5 shrink-0 text-ink-faint" aria-hidden />
      <div className="min-w-0">
        <div className="text-[10px] uppercase tracking-wide text-ink-faint">{label}</div>
        <div className={`text-sm font-semibold tabular-nums leading-tight ${tone}`}>{value}</div>
      </div>
    </div>
  );
}

/** 页签⑥告警设置：规则 CRUD + Webhook 配置 + 触发记录 */
export default function Alerts() {
  const { servers, setUnreadAlerts, unreadAlerts } = useMonitorStore();
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [logs, setLogs] = useState<AlertLog[]>([]);
  const [settings, setSettings] = useState<MonitorSettings>({
    webhook_url: '',
    collect_interval: 30,
  });
  const [editing, setEditing] = useState<RuleForm | null>(null);
  const [deleting, setDeleting] = useState<AlertRule | null>(null);
  const [formError, setFormError] = useState('');
  const [error, setError] = useState('');
  const [saved, setSaved] = useState('');
  const [logPage, setLogPage] = useState(1);
  const [logTotal, setLogTotal] = useState(0);

  const loadRules = useCallback(async () => {
    setRules(await monitorApi.getAlerts());
  }, []);

  const loadLogs = useCallback(
    async (page = 1) => {
      const data = await monitorApi.getAlertLogs(page, 20);
      setLogs(data.logs);
      setLogTotal(data.total);
      setUnreadAlerts(data.unread_count);
    },
    [setUnreadAlerts],
  );

  useEffect(() => {
    Promise.all([loadRules(), loadLogs(), monitorApi.getSettings()])
      .then(([, , s]) => setSettings(s))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : '加载失败'));
  }, [loadRules, loadLogs]);

  const saveRule = async () => {
    if (!editing) return;
    setFormError('');
    const threshold = Number(editing.threshold);
    const duration = Number(editing.duration);
    if (Number.isNaN(threshold)) {
      setFormError('阈值必须是数字');
      return;
    }
    if (Number.isNaN(duration) || duration < 1 || duration > 60) {
      setFormError('持续时间需在 1-60 之间');
      return;
    }
    try {
      const payload = {
        server_id: editing.server_id,
        metric: editing.metric,
        operator: editing.operator,
        threshold,
        duration,
        enabled: editing.enabled,
      };
      if (editing.id) await monitorApi.updateAlert(editing.id, payload);
      else await monitorApi.createAlert(payload);
      setEditing(null);
      await loadRules();
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : '保存失败');
    }
  };

  const markRead = async () => {
    await monitorApi.markAlertLogsRead();
    setLogs((prev) => prev.map((l) => ({ ...l, is_read: true })));
    setUnreadAlerts(0);
  };

  const saveSettings = async () => {
    setError('');
    setSaved('');
    try {
      await monitorApi.saveSettings(settings);
      setSaved('通知设置已保存');
      setTimeout(() => setSaved(''), 2500);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '保存设置失败');
    }
  };

  const serverName = (id: string) => {
    if (id === 'all') return '全部服务器';
    return servers.find((s) => s.id === id)?.name || id;
  };

  const fmtTime = (t: string) => t.replace('T', ' ').slice(0, 19);
  const enabledCount = useMemo(() => rules.filter((r) => r.enabled).length, [rules]);
  const totalPages = Math.max(1, Math.ceil(logTotal / 20));

  return (
    <div className="flex flex-col gap-4">
      {/* ---------- 顶部统计 ---------- */}
      <div className="flex flex-wrap items-center gap-2">
        <StatPill icon={BellRing} label="规则总数" value={`${rules.length}`} />
        <StatPill icon={BellRing} label="已启用" value={`${enabledCount}`} tone="text-accent-success" />
        <StatPill
          icon={BellOff}
          label="未读告警"
          value={`${unreadAlerts}`}
          tone={unreadAlerts > 0 ? 'text-accent-danger' : 'text-ink-faint'}
        />
      </div>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-accent-danger">
          {error}
        </div>
      )}
      {saved && (
        <div className="rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-accent-success">
          {saved}
        </div>
      )}

      {/* ---------- 通知设置 ---------- */}
      <div className="rounded-xl border border-border bg-surface-1 p-4">
        <div className="mb-2.5 flex items-center gap-1.5 text-xs font-medium text-ink">
          <Webhook className="h-3.5 w-3.5 text-ink-faint" aria-hidden />
          通知设置
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Input
            className="min-w-[220px] flex-1 text-xs"
            placeholder="Webhook 地址（钉钉 / 企业微信 / 飞书机器人）"
            value={settings.webhook_url}
            onChange={(e) => setSettings({ ...settings, webhook_url: e.target.value })}
          />
          <Button size="sm" onClick={() => void saveSettings()}>
            保存
          </Button>
        </div>
        <div className="mt-2 text-[11px] text-ink-faint">
          采集间隔 {settings.collect_interval} 秒 · 告警触发后通过 Webhook 推送，同时在本页记录站内通知
        </div>
      </div>

      {/* ---------- 告警规则 ---------- */}
      <div className="overflow-hidden rounded-xl border border-border bg-surface-1">
        <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <h3 className="text-xs font-medium text-ink">告警规则</h3>
          <Button size="sm" onClick={() => setEditing({ ...EMPTY_FORM, id: '' })}>
            <Plus className="mr-1.5 h-3.5 w-3.5" aria-hidden />
            新建规则
          </Button>
        </div>
        {rules.length === 0 ? (
          <div className="px-4 py-10 text-center text-sm text-ink-faint">
            暂无告警规则，点右上角「新建规则」开始
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-xs">
              <thead>
                <tr className="border-b border-border text-ink-faint">
                  <th className="px-4 py-2 text-left font-normal">服务器</th>
                  <th className="px-4 py-2 text-left font-normal">触发条件</th>
                  <th className="hidden px-4 py-2 text-left font-normal sm:table-cell">持续</th>
                  <th className="px-4 py-2 text-left font-normal">状态</th>
                  <th className="px-4 py-2 text-right font-normal">操作</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((r) => (
                  <tr
                    key={r.id}
                    className="group border-b border-border/60 last:border-0 hover:bg-surface-2/60"
                  >
                    <td className="max-w-[180px] truncate px-4 py-2 text-ink-muted" title={serverName(r.server_id)}>
                      {serverName(r.server_id)}
                    </td>
                    <td className="px-4 py-2">
                      <span className="font-mono text-[11px] text-ink">
                        {METRIC_LABELS[r.metric] || r.metric} {r.operator} {r.threshold}
                      </span>
                    </td>
                    <td className="hidden px-4 py-2 text-ink-faint sm:table-cell">
                      连续 {r.duration} 次
                    </td>
                    <td className="px-4 py-2">
                      <button
                        type="button"
                        onClick={async () => {
                          await monitorApi.updateAlert(r.id, { enabled: !r.enabled });
                          await loadRules();
                        }}
                        className={`inline-flex items-center gap-1.5 ${
                          r.enabled ? 'text-accent-success' : 'text-ink-faint'
                        } hover:underline`}
                        title={r.enabled ? '点击停用' : '点击启用'}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            r.enabled ? 'bg-accent-success' : 'bg-ink-faint'
                          }`}
                        />
                        {r.enabled ? '已启用' : '已停用'}
                      </button>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex items-center justify-end gap-1 opacity-60 transition-opacity group-hover:opacity-100">
                        <button
                          type="button"
                          className="rounded-md px-1.5 py-1 text-[11px] text-ink-muted hover:bg-surface-3 hover:text-ink"
                          onClick={() =>
                            setEditing({
                              server_id: r.server_id,
                              metric: r.metric,
                              operator: r.operator,
                              threshold: String(r.threshold),
                              duration: String(r.duration),
                              enabled: r.enabled,
                              id: r.id,
                            })
                          }
                        >
                          编辑
                        </button>
                        <button
                          type="button"
                          className="rounded-md px-1.5 py-1 text-[11px] text-ink-muted hover:bg-danger/10 hover:text-accent-danger"
                          onClick={() => setDeleting(r)}
                        >
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ---------- 触发记录 ---------- */}
      <div className="overflow-hidden rounded-xl border border-border bg-surface-1">
        <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-medium text-ink">触发记录</h3>
            {unreadAlerts > 0 && (
              <span className="rounded-full bg-danger/15 px-2 py-0.5 text-[10px] text-accent-danger">
                {unreadAlerts} 条未读
              </span>
            )}
          </div>
          <Button variant="secondary" size="sm" onClick={() => void markRead()} disabled={unreadAlerts === 0}>
            <CheckCheck className="mr-1.5 h-3.5 w-3.5" aria-hidden />
            全部已读
          </Button>
        </div>
        {logs.length === 0 ? (
          <div className="px-4 py-10 text-center text-sm text-ink-faint">暂无告警记录</div>
        ) : (
          <div className="divide-y divide-border">
            {logs.map((log) => {
              const firing = log.status === 'firing';
              return (
                <div
                  key={log.id}
                  className={`flex items-start gap-3 px-4 py-2.5 ${
                    log.is_read ? 'opacity-55' : ''
                  }`}
                >
                  <span
                    className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                      firing ? 'bg-accent-danger' : 'bg-accent-success'
                    }`}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-1.5 text-xs">
                      <span className="font-medium text-ink">{log.server_name}</span>
                      <span className="text-ink-faint">·</span>
                      <span className="text-ink-muted">
                        {METRIC_LABELS[log.metric] || log.metric}
                      </span>
                      <span className={`font-mono ${firing ? 'text-accent-danger' : 'text-accent-success'}`}>
                        {log.actual_value}
                      </span>
                      <span className="text-ink-faint">{firing ? '触发' : '恢复'}</span>
                    </div>
                    <div className="mt-0.5 font-mono text-[10px] text-ink-faint">
                      {fmtTime(log.notified_at)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {logTotal > 20 && (
          <div className="flex items-center justify-end gap-2 border-t border-border px-4 py-2 text-xs text-ink-faint">
            <Button
              variant="secondary"
              size="sm"
              disabled={logPage <= 1}
              onClick={() => {
                setLogPage(logPage - 1);
                void loadLogs(logPage - 1);
              }}
            >
              上一页
            </Button>
            <span className="tabular-nums">
              {logPage} / {totalPages}
            </span>
            <Button
              variant="secondary"
              size="sm"
              disabled={logPage >= totalPages}
              onClick={() => {
                setLogPage(logPage + 1);
                void loadLogs(logPage + 1);
              }}
            >
              下一页
            </Button>
          </div>
        )}
      </div>

      {/* ---------- 规则编辑弹窗 ---------- */}
      {editing && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setEditing(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={editing.id ? '编辑规则' : '新建规则'}
            className="w-full max-w-[440px] space-y-3 rounded-xl border border-border bg-surface-1 p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-sm font-semibold text-ink">
              {editing.id ? '编辑规则' : '新建规则'}
            </div>
            <div className="flex gap-2">
              <Select
                value={editing.server_id}
                onValueChange={(v) => setEditing({ ...editing, server_id: v })}
              >
                <SelectTrigger className="flex-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部服务器</SelectItem>
                  {servers.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select
                value={editing.metric}
                onValueChange={(v) => setEditing({ ...editing, metric: v })}
              >
                <SelectTrigger className="flex-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {METRIC_OPTIONS.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2">
              <Select
                value={editing.operator}
                onValueChange={(v) => setEditing({ ...editing, operator: v })}
              >
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {OPERATORS.map((op) => (
                    <SelectItem key={op} value={op}>
                      {op}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                className="flex-1"
                placeholder="阈值"
                value={editing.threshold}
                onChange={(e) => setEditing({ ...editing, threshold: e.target.value })}
              />
              <Input
                className="w-28"
                placeholder="连续次数"
                value={editing.duration}
                onChange={(e) => setEditing({ ...editing, duration: e.target.value })}
              />
            </div>
            <label className="flex items-center gap-2 text-xs text-ink-muted">
              <input
                type="checkbox"
                checked={editing.enabled}
                onChange={(e) => setEditing({ ...editing, enabled: e.target.checked })}
              />
              启用规则
            </label>
            {formError && <div className="text-xs text-accent-danger">{formError}</div>}
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="ghost" onClick={() => setEditing(null)}>
                取消
              </Button>
              <Button onClick={() => void saveRule()}>保存</Button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
        title="删除规则"
        description={`确定删除该告警规则（${
          deleting ? METRIC_LABELS[deleting.metric] : ''
        } ${deleting?.operator} ${deleting?.threshold}）？`}
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
