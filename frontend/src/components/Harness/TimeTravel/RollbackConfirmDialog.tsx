// frontend/src/components/Harness/TimeTravel/RollbackConfirmDialog.tsx
import { useState } from 'react';

export function RollbackConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  currentHeadLabel,
  targetLabel,
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  currentHeadLabel: string;
  targetLabel: string;
}) {
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    if (!confirmed) return;
    setLoading(true);
    try {
      await onConfirm();
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-lg w-full max-w-md mx-4 p-5">
        <h2 className="text-lg font-semibold mb-4">确认回滚</h2>
        <div className="mb-4 text-sm">
          <div className="mb-2">
            当前 head: <strong>{currentHeadLabel}</strong>
          </div>
          <div className="mb-4">
            回滚到: <strong>{targetLabel}</strong>
          </div>
          <div className="bg-yellow-50 p-3 rounded text-yellow-800 mb-3">
            ⚠️ 后续 checkpoint 将被标记为 detached，不会删除数据，可通过创建分支恢复。
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            <span>我已了解回滚将影响 head 指针</span>
          </label>
        </div>
        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-gray-600">
            取消
          </button>
          <button
            onClick={handleConfirm}
            disabled={!confirmed || loading}
            className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
          >
            {loading ? '回滚中...' : '确认回滚'}
          </button>
        </div>
      </div>
    </div>
  );
}
