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
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-cyan-500"></div>
        <p className="mt-4 text-slate-400">{igT.loadDegradationLoading}</p>
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

      {/* 当前状态 */}
      {status && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">{igT.currentDegradationStatus}</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-700 rounded-lg p-4">
              <div className="text-slate-400 text-xs mb-1">{igT.degradationStatus}</div>
              <div
                className={`text-lg font-bold ${
                  status.is_degraded ? 'text-red-400' : 'text-green-400'
                }`}
              >
                {status.is_degraded ? igT.degraded : igT.normal}
              </div>
            </div>
            <div className="bg-slate-700 rounded-lg p-4">
              <div className="text-slate-400 text-xs mb-1">{igT.failureCount}</div>
              <div className="text-lg font-bold text-white">{status.failure_count}</div>
            </div>
            <div className="bg-slate-700 rounded-lg p-4">
              <div className="text-slate-400 text-xs mb-1">{igT.degradedAt}</div>
              <div className="text-sm text-white">
                {status.degraded_at
                  ? new Date(status.degraded_at).toLocaleString()
                  : '-'}
              </div>
            </div>
          </div>

          {status.is_degraded && (
            <div className="mt-4 flex justify-end">
              <button
                onClick={handleReset}
                disabled={resetting}
                className="bg-red-600 hover:bg-red-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg transition-colors"
              >
                {resetting ? igT.resetting : igT.manualReset}
              </button>
            </div>
          )}
        </div>
      )}

      {/* 配置编辑 */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 space-y-4">
        <h3 className="text-lg font-semibold text-white">{igT.degradationConfig}</h3>

        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="enabled"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="w-4 h-4 text-cyan-600 bg-slate-700 border-slate-600 rounded focus:ring-cyan-500"
          />
          <label htmlFor="enabled" className="text-sm text-slate-300">
            {igT.enableAutoDegradation}
          </label>
        </div>

        <div>
          <label className="block text-sm text-slate-300 mb-2">{igT.failureThreshold}</label>
          <input
            type="number"
            min="1"
            max="100"
            value={failureThreshold}
            onChange={(e) => setFailureThreshold(Number(e.target.value))}
            className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
          />
          <p className="text-xs text-slate-500 mt-1">{igT.failureThresholdRange}</p>
        </div>

        <div>
          <label className="block text-sm text-slate-300 mb-2">{igT.degradeDuration}</label>
          <input
            type="number"
            min="10"
            max="86400"
            value={degradeDurationSeconds}
            onChange={(e) => setDegradeDurationSeconds(Number(e.target.value))}
            className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
          />
          <p className="text-xs text-slate-500 mt-1">{igT.degradeDurationRange}</p>
        </div>

        <div className="flex gap-3 pt-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-cyan-600 hover:bg-cyan-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg transition-colors"
          >
            {saving ? igT.saving : igT.saveConfig}
          </button>
        </div>
      </div>
    </div>
  );
}