/**
 * 降级配置 Tab — Task 12.1
 * 显示降级状态 + 编辑配置 + 手动解除按钮
 */
import { useEffect, useState } from 'react';
import {
  getDegradationStatus,
  updateDegradationConfig,
  resetDegradation,
  DegradationStatus,
} from '../../../../api/adminImageGenerationApi';
import { useI18n } from '../../../../i18n';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

export default function DegradationConfigPanel() {
  const { t } = useI18n();
  const igT = t.imageGeneration.admin;
  const [status, setStatus] = useState<DegradationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 表单状态
  const [enabled, setEnabled] = useState(false);
  const [failureThreshold, setFailureThreshold] = useState(5);
  const [degradeDurationSeconds, setDegradeDurationSeconds] = useState(300);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getDegradationStatus();
      setStatus(data);
      setEnabled(data.enabled);
      setFailureThreshold(data.failure_threshold);
      setDegradeDurationSeconds(data.degrade_duration_seconds);
    } catch (e) {
      setError(e instanceof Error ? e.message : igT.loadDegradationFailed);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setMessage(null);
      const updated = await updateDegradationConfig({
        enabled,
        failure_threshold: failureThreshold,
        degrade_duration_seconds: degradeDurationSeconds,
      });
      setStatus(updated);
      setMessage({ type: 'success', text: igT.saveDegradationSuccess });
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : igT.saveFailed });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm(igT.manualResetConfirm)) return;
    try {
      setResetting(true);
      setMessage(null);
      await resetDegradation();
      setMessage({ type: 'success', text: igT.resetDegradedSuccess });
      await loadStatus();
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : igT.resetFailedText });
    } finally {
      setResetting(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-16">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-accent"></div>
        <p className="mt-4 text-ink-muted">{igT.loadDegradationLoading}</p>
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

      {/* 当前状态 */}
      {status && (
        <Card>
          <CardHeader>
            <CardTitle>{igT.currentDegradationStatus}</CardTitle>
          </CardHeader>
          <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="bg-surface-2">
              <CardContent className="p-4">
                <div className="text-ink-muted text-xs mb-1">{igT.degradationStatus}</div>
                <div
                  className={`text-lg font-bold ${
                    status.is_degraded ? 'text-danger' : 'text-success'
                  }`}
                >
                  {status.is_degraded ? igT.degraded : igT.normal}
                </div>
              </CardContent>
            </Card>
            <Card className="bg-surface-2">
              <CardContent className="p-4">
                <div className="text-ink-muted text-xs mb-1">{igT.failureCount}</div>
                <div className="text-lg font-bold text-ink">{status.failure_count}</div>
              </CardContent>
            </Card>
            <Card className="bg-surface-2">
              <CardContent className="p-4">
                <div className="text-ink-muted text-xs mb-1">{igT.degradedAt}</div>
                <div className="text-sm text-ink">
                  {status.degraded_at
                    ? new Date(status.degraded_at).toLocaleString()
                    : '-'}
                </div>
              </CardContent>
            </Card>
          </div>

          {status.is_degraded && (
            <div className="mt-4 flex justify-end">
              <Button
                variant="destructive"
                onClick={handleReset}
                disabled={resetting}
                className="disabled:bg-surface-3 disabled:cursor-not-allowed"
              >
                {resetting ? igT.resetting : igT.manualReset}
              </Button>
            </div>
          )}
          </CardContent>
        </Card>
      )}

      {/* 配置编辑 */}
      <Card>
        <CardHeader>
          <CardTitle>{igT.degradationConfig}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">

        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="enabled"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="w-4 h-4 text-cyan-600 bg-surface-2 border-border rounded focus:ring-accent"
          />
          <label htmlFor="enabled" className="text-sm text-ink-muted">
            {igT.enableAutoDegradation}
          </label>
        </div>

        <div>
          <label className="block text-sm text-ink-muted mb-2">{igT.failureThreshold}</label>
          <input
            type="number"
            min="1"
            max="100"
            value={failureThreshold}
            onChange={(e) => setFailureThreshold(Number(e.target.value))}
            className="w-full bg-surface-2 border border-border text-ink px-3 py-2 rounded focus:outline-none focus:border-accent"
          />
          <p className="text-xs text-ink-faint mt-1">{igT.failureThresholdRange}</p>
        </div>

        <div>
          <label className="block text-sm text-ink-muted mb-2">{igT.degradeDuration}</label>
          <input
            type="number"
            min="10"
            max="86400"
            value={degradeDurationSeconds}
            onChange={(e) => setDegradeDurationSeconds(Number(e.target.value))}
            className="w-full bg-surface-2 border border-border text-ink px-3 py-2 rounded focus:outline-none focus:border-accent"
          />
          <p className="text-xs text-ink-faint mt-1">{igT.degradeDurationRange}</p>
        </div>

        <div className="flex gap-3 pt-4">
          <Button
            onClick={handleSave}
            disabled={saving}
            className="disabled:bg-surface-3 disabled:cursor-not-allowed"
          >
            {saving ? igT.saving : igT.saveConfig}
          </Button>
        </div>
        </CardContent>
      </Card>
    </div>
  );
}