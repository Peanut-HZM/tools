/**
 * 保留策略 Tab — Task 12.1
 * mode + n_days + cron + 手动触发清理
 */
import { useEffect, useState } from 'react';
import {
  getRetentionConfig,
  updateRetentionConfig,
  triggerRetentionCleanup,
  RetentionStatus,
} from '../../../../api/adminImageGenerationApi';
import { useI18n } from '../../../../i18n';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

export default function RetentionConfigPanel() {
  const { t } = useI18n();
  const igT = t.imageGeneration.admin;
  const [config, setConfig] = useState<RetentionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 表单状态
  const [mode, setMode] = useState<'keep_forever' | 'delete_after_n_days' | 'delete_if_unused_for_n_days'>(
    'keep_forever',
  );
  const [nDays, setNDays] = useState(30);
  const [cleanupCron, setCleanupCron] = useState('0 2 * * *');

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getRetentionConfig();
      setConfig(data);
      setMode(data.mode);
      setNDays(data.n_days);
      setCleanupCron(data.cleanup_cron);
    } catch (e) {
      setError(e instanceof Error ? e.message : igT.loadRetentionFailed);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setMessage(null);
      const updated = await updateRetentionConfig({
        mode,
        n_days: nDays,
        cleanup_cron: cleanupCron,
      });
      setConfig(updated);
      setMessage({ type: 'success', text: igT.saveRetentionSuccess });
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : igT.saveFailed });
    } finally {
      setSaving(false);
    }
  };

  const handleTrigger = async () => {
    if (!confirm(igT.triggerCleanupConfirm)) return;
    try {
      setTriggering(true);
      setMessage(null);
      await triggerRetentionCleanup();
      setMessage({ type: 'success', text: igT.cleanupTriggered });
      await loadConfig();
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : igT.triggerFailed });
    } finally {
      setTriggering(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-16">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-accent"></div>
        <p className="mt-4 text-ink-muted">{igT.loadRetentionLoading}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-danger/10 border border-danger text-danger px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {message && (
        <div
          className={`px-4 py-3 rounded-lg ${
            message.type === 'success'
              ? 'bg-success/10 border border-success text-success'
              : 'bg-danger/10 border border-danger text-danger'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* OSS 用量 */}
      {config && (
        <Card>
          <CardHeader>
            <CardTitle>{igT.ossUsage}</CardTitle>
          </CardHeader>
          <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="bg-surface-2">
              <CardContent className="p-4">
                <div className="text-ink-muted text-xs mb-1">{igT.totalFiles}</div>
                <div className="text-lg font-bold text-ink">{config.total_files}</div>
              </CardContent>
            </Card>
            <Card className="bg-surface-2">
              <CardContent className="p-4">
                <div className="text-ink-muted text-xs mb-1">{igT.totalSize}</div>
                <div className="text-lg font-bold text-ink">
                  {config.total_size_mb.toFixed(2)} MB
                </div>
              </CardContent>
            </Card>
          </div>
          </CardContent>
        </Card>
      )}

      {/* 策略配置 */}
      <Card>
        <CardHeader>
          <CardTitle>{igT.retentionConfig}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">

        <div>
          <label className="block text-sm text-ink-muted mb-2">{igT.cleanupMode}</label>
          <Select value={mode} onValueChange={(v) => setMode(v as typeof mode)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="keep_forever">{igT.cleanupModeKeepForever}</SelectItem>
              <SelectItem value="delete_after_n_days">{igT.cleanupModeDeleteAfterDays}</SelectItem>
              <SelectItem value="delete_if_unused_for_n_days">{igT.cleanupModeDeleteIfUnused}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="block text-sm text-ink-muted mb-2">{igT.retentionDays}</label>
          <input
            type="number"
            min="1"
            max="3650"
            value={nDays}
            onChange={(e) => setNDays(Number(e.target.value))}
            className="w-full bg-surface-2 border border-border text-ink px-3 py-2 rounded focus:outline-none focus:border-accent"
          />
          <p className="text-xs text-ink-faint mt-1">{igT.retentionDaysRange}</p>
        </div>

        <div>
          <label className="block text-sm text-ink-muted mb-2">{igT.cleanupCron}</label>
          <input
            type="text"
            value={cleanupCron}
            onChange={(e) => setCleanupCron(e.target.value)}
            placeholder={igT.cleanupCronPlaceholder}
            className="w-full bg-surface-2 border border-border text-ink px-3 py-2 rounded focus:outline-none focus:border-accent"
          />
          <p className="text-xs text-ink-faint mt-1">{igT.cleanupCronExample}</p>
        </div>

        <div className="flex gap-3 pt-4">
          <Button
            onClick={handleSave}
            disabled={saving}
            className="disabled:bg-surface-3 disabled:cursor-not-allowed"
          >
            {saving ? igT.saving : igT.saveConfig}
          </Button>
          <Button
            onClick={handleTrigger}
            disabled={triggering}
            className="bg-accent-warm hover:bg-orange-700 disabled:bg-surface-3 disabled:cursor-not-allowed text-white"
          >
            {triggering ? igT.triggering : igT.triggerCleanup}
          </Button>
        </div>
        </CardContent>
      </Card>
    </div>
  );
}