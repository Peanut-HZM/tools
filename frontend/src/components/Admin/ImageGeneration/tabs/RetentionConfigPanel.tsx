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
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-cyan-500"></div>
        <p className="mt-4 text-slate-400">{igT.loadRetentionLoading}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {message && (
        <div
          className={`px-4 py-3 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-500/10 border border-green-500 text-green-400'
              : 'bg-red-500/10 border border-red-500 text-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* OSS 用量 */}
      {config && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">{igT.ossUsage}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-700 rounded-lg p-4">
              <div className="text-slate-400 text-xs mb-1">{igT.totalFiles}</div>
              <div className="text-lg font-bold text-white">{config.total_files}</div>
            </div>
            <div className="bg-slate-700 rounded-lg p-4">
              <div className="text-slate-400 text-xs mb-1">{igT.totalSize}</div>
              <div className="text-lg font-bold text-white">
                {config.total_size_mb.toFixed(2)} MB
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 策略配置 */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 space-y-4">
        <h3 className="text-lg font-semibold text-white">{igT.retentionConfig}</h3>

        <div>
          <label className="block text-sm text-slate-300 mb-2">{igT.cleanupMode}</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as typeof mode)}
            className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
          >
            <option value="keep_forever">{igT.cleanupModeKeepForever}</option>
            <option value="delete_after_n_days">{igT.cleanupModeDeleteAfterDays}</option>
            <option value="delete_if_unused_for_n_days">{igT.cleanupModeDeleteIfUnused}</option>
          </select>
        </div>

        <div>
          <label className="block text-sm text-slate-300 mb-2">{igT.retentionDays}</label>
          <input
            type="number"
            min="1"
            max="3650"
            value={nDays}
            onChange={(e) => setNDays(Number(e.target.value))}
            className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
          />
          <p className="text-xs text-slate-500 mt-1">{igT.retentionDaysRange}</p>
        </div>

        <div>
          <label className="block text-sm text-slate-300 mb-2">{igT.cleanupCron}</label>
          <input
            type="text"
            value={cleanupCron}
            onChange={(e) => setCleanupCron(e.target.value)}
            placeholder={igT.cleanupCronPlaceholder}
            className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
          />
          <p className="text-xs text-slate-500 mt-1">{igT.cleanupCronExample}</p>
        </div>

        <div className="flex gap-3 pt-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-cyan-600 hover:bg-cyan-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg transition-colors"
          >
            {saving ? igT.saving : igT.saveConfig}
          </button>
          <button
            onClick={handleTrigger}
            disabled={triggering}
            className="bg-orange-600 hover:bg-orange-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg transition-colors"
          >
            {triggering ? igT.triggering : igT.triggerCleanup}
          </button>
        </div>
      </div>
    </div>
  );
}