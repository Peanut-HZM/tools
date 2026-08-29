// frontend/src/components/Harness/TimeTravel/MergePickerDialog.tsx
import { useState } from 'react';
import type { Branch, Checkpoint } from '../../../types/harnessCheckpoint';

export function MergePickerDialog({
  isOpen,
  onClose,
  onConfirm,
  branches,
  checkpointsByBranch,
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (pickedIds: string[], newName: string) => Promise<void>;
  branches: Branch[];
  checkpointsByBranch: Record<string, Checkpoint[]>;
}) {
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [newName, setNewName] = useState('合并分支');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const toggle = (id: string) => {
    const next = new Set(picked);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setPicked(next);
  };

  const handleConfirm = async () => {
    if (picked.size < 2 || !newName.trim()) return;
    setLoading(true);
    try {
      await onConfirm(Array.from(picked), newName.trim());
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-lg w-full max-w-2xl mx-4 p-5 max-h-[80vh] overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">Pick-from 合并</h2>
        {branches.map((b) => (
          <div key={b.id} className="mb-4">
            <h3 className="font-medium text-sm mb-2">{b.name}</h3>
            <div className="space-y-1">
              {(checkpointsByBranch[b.id] || []).map((cp) => (
                <label
                  key={cp.id}
                  className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={picked.has(cp.id)}
                    onChange={() => toggle(cp.id)}
                  />
                  <span className="text-sm">
                    step {cp.step_index} — {cp.phase}
                  </span>
                </label>
              ))}
            </div>
          </div>
        ))}
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="新分支名"
          className="w-full px-3 py-2 border rounded mb-3"
          maxLength={100}
        />
        <div className="text-xs text-gray-500 mb-3">
          已选 {picked.size} 个 checkpoint（至少 2 个）
        </div>
        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-gray-600">
            取消
          </button>
          <button
            onClick={handleConfirm}
            disabled={picked.size < 2 || !newName.trim() || loading}
            className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
          >
            {loading ? '合并中...' : '创建合并分支'}
          </button>
        </div>
      </div>
    </div>
  );
}
