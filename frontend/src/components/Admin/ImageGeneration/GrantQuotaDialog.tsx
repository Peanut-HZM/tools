/**
 * 分配/编辑配额对话框 — Task 12.1
 * daily_limit, monthly_limit, valid_from, valid_until, notes
 */
import { useEffect, useState } from 'react';
import {
  grantQuota,
  GrantQuotaRequest,
  QuotaUser,
} from '../../../api/adminImageGenerationApi';

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
      setError(e instanceof Error ? e.message : '操作失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 max-w-md w-full">
        <h3 className="text-xl font-bold text-white mb-4">
          {existing ? '编辑配额' : '分配配额'}
        </h3>

        <div className="mb-4">
          <div className="text-sm text-slate-400 mb-1">用户ID</div>
          <div className="text-white font-mono text-sm bg-slate-700 px-3 py-2 rounded">
            {userId}
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500 text-red-400 px-3 py-2 rounded text-sm mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-slate-300 mb-2">每日调用上限</label>
            <input
              type="number"
              min="0"
              max="10000"
              value={dailyLimit}
              onChange={(e) => setDailyLimit(Number(e.target.value))}
              required
              className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
            />
            <p className="text-xs text-slate-500 mt-1">范围：0 ~ 10000</p>
          </div>

          <div>
            <label className="block text-sm text-slate-300 mb-2">每月调用上限</label>
            <input
              type="number"
              min="0"
              max="300000"
              value={monthlyLimit}
              onChange={(e) => setMonthlyLimit(Number(e.target.value))}
              required
              className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
            />
            <p className="text-xs text-slate-500 mt-1">范围：0 ~ 300000</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-slate-300 mb-2">生效开始时间</label>
              <input
                type="datetime-local"
                value={validFrom}
                onChange={(e) => setValidFrom(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-2">生效结束时间</label>
              <input
                type="datetime-local"
                value={validUntil}
                onChange={(e) => setValidUntil(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm text-slate-300 mb-2">备注</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={200}
              rows={3}
              placeholder="选填，最多 200 字符"
              className="w-full bg-slate-700 border border-slate-600 text-white px-3 py-2 rounded focus:outline-none focus:border-cyan-500 resize-none"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 bg-cyan-600 hover:bg-cyan-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg transition-colors"
            >
              {submitting ? '提交中...' : '确认'}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="flex-1 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 text-white px-4 py-2 rounded-lg transition-colors border border-slate-600"
            >
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}