/**
 * 分配/编辑配额对话框 — Task 12.1
 * daily_limit, monthly_limit, valid_from, valid_until, notes
 */
import { useState } from 'react';
import {
  grantQuota,
  GrantQuotaRequest,
  QuotaUser,
} from '../../../api/adminImageGenerationApi';
import { useI18n } from '../../../i18n';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

interface GrantQuotaDialogProps {
  userId: string;
  existing?: QuotaUser | null;
  onClose: () => void;
  onSuccess: () => void;
}

export default function GrantQuotaDialog({
  userId,
  existing,
  onClose,
  onSuccess,
}: GrantQuotaDialogProps) {
  const { t } = useI18n();
  const igT = t.imageGeneration.admin;
  const [dailyLimit, setDailyLimit] = useState(existing?.daily_limit ?? 10);
  const [monthlyLimit, setMonthlyLimit] = useState(existing?.monthly_limit ?? 200);
  const [validFrom, setValidFrom] = useState(
    existing?.valid_from ? existing.valid_from.slice(0, 16) : '',
  );
  const [validUntil, setValidUntil] = useState(
    existing?.valid_until ? existing.valid_until.slice(0, 16) : '',
  );
  const [notes, setNotes] = useState(existing?.notes ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setError(null);
      const data: GrantQuotaRequest = {
        daily_limit: dailyLimit,
        monthly_limit: monthlyLimit,
        notes: notes || null,
      };
      if (validFrom) data.valid_from = new Date(validFrom).toISOString();
      if (validUntil) data.valid_until = new Date(validUntil).toISOString();
      await grantQuota(userId, data);
      onSuccess();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : t.imageGeneration.errors.defaultError);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="p-6 max-w-md w-full">
        <h3 className="text-xl font-bold text-ink-inverse mb-4">
          {existing ? igT.editQuota : igT.grantQuota}
        </h3>

        <div className="mb-4">
          <div className="text-sm text-ink-muted mb-1">{igT.userId}</div>
          <div className="text-ink-inverse text-sm bg-surface-2 px-3 py-2 rounded">
            {userId}
          </div>
        </div>

        {error && (
          <div className="bg-danger/10 border border-danger text-danger px-3 py-2 rounded text-sm mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-ink-muted mb-2">{igT.dailyLimit}</label>
            <input
              type="number"
              min="0"
              max="10000"
              value={dailyLimit}
              onChange={(e) => setDailyLimit(Number(e.target.value))}
              required
              className="w-full bg-surface-2 border border-border text-ink-inverse px-3 py-2 rounded focus:outline-none focus:border-accent"
            />
            <p className="text-xs text-ink-faint mt-1">{igT.dailyLimitRange}</p>
          </div>

          <div>
            <label className="block text-sm text-ink-muted mb-2">{igT.monthlyLimit}</label>
            <input
              type="number"
              min="0"
              max="300000"
              value={monthlyLimit}
              onChange={(e) => setMonthlyLimit(Number(e.target.value))}
              required
              className="w-full bg-surface-2 border border-border text-ink-inverse px-3 py-2 rounded focus:outline-none focus:border-accent"
            />
            <p className="text-xs text-ink-faint mt-1">{igT.monthlyLimitRange}</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-ink-muted mb-2">{igT.validFrom}</label>
              <input
                type="datetime-local"
                value={validFrom}
                onChange={(e) => setValidFrom(e.target.value)}
                className="w-full bg-surface-2 border border-border text-ink-inverse px-3 py-2 rounded focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-sm text-ink-muted mb-2">{igT.validUntil}</label>
              <input
                type="datetime-local"
                value={validUntil}
                onChange={(e) => setValidUntil(e.target.value)}
                className="w-full bg-surface-2 border border-border text-ink-inverse px-3 py-2 rounded focus:outline-none focus:border-accent"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm text-ink-muted mb-2">{igT.notes}</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={200}
              rows={3}
              placeholder={igT.notesPlaceholder}
              className="w-full bg-surface-2 border border-border text-ink-inverse px-3 py-2 rounded focus:outline-none focus:border-accent resize-none"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <Button
              type="submit"
              disabled={submitting}
              className="flex-1 disabled:bg-surface-3 disabled:cursor-not-allowed"
            >
              {submitting ? igT.submitting : igT.confirm}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={submitting}
              className="flex-1 disabled:bg-surface-1"
            >
              {igT.cancel}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}