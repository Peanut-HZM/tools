// frontend/src/components/Harness/TimeTravel/BranchCreateDialog.tsx
import { useState } from 'react';

export function BranchCreateDialog({
  isOpen,
  onClose,
  onConfirm,
  sourceLabel,
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (name: string, startWithMessages: boolean) => Promise<void>;
  sourceLabel: string;
}) {
  const [name, setName] = useState('');
  const [startWithMessages, setStartWithMessages] = useState(true);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    if (!name.trim()) return;
    setLoading(true);
    try {
      await onConfirm(name.trim(), startWithMessages);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-lg w-full max-w-md mx-4 p-5">
        <h2 className="text-lg font-semibold mb-4">创建分支</h2>
        <div className="mb-4 text-sm text-gray-600">从 checkpoint 创建：{sourceLabel}</div>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="分支名称"
          className="w-full px-3 py-2 border rounded mb-3"
          maxLength={100}
        />
        <label className="flex items-center gap-2 cursor-pointer mb-4">
          <input
            type="checkbox"
            checked={startWithMessages}
            onChange={(e) => setStartWithMessages(e.target.checked)}
          />
          <span className="text-sm">复制源 checkpoint 的消息作为起点</span>
        </label>
        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-gray-600">
            取消
          </button>
          <button
            onClick={handleConfirm}
            disabled={!name.trim() || loading}
            className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
          >
            {loading ? '创建中...' : '创建'}
          </button>
        </div>
      </div>
    </div>
  );
}
