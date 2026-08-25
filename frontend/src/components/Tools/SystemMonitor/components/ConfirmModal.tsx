// frontend/src/components/Tools/SystemMonitor/components/ConfirmModal.tsx
interface ConfirmModalProps {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
}

/** 通用确认弹窗 */
export default function ConfirmModal({ open, title, message, onConfirm, onCancel, danger }: ConfirmModalProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onCancel}>
      <div className="bg-canvas border border-border rounded-xl p-5 w-96 max-w-[90vw]" onClick={(e) => e.stopPropagation()}>
        <div className="text-ink-inverse font-medium mb-2">{title}</div>
        <div className="text-ink-muted text-sm mb-5">{message}</div>
        <div className="flex justify-end gap-3">
          <button className="px-4 py-1.5 rounded-lg text-sm text-ink-muted hover:text-ink-inverse hover:bg-surface-1" onClick={onCancel}>取消</button>
          <button
            className={`px-4 py-1.5 rounded-lg text-sm text-ink-inverse ${danger ? 'bg-red-600 hover:bg-red-500' : 'bg-emerald-600 hover:bg-emerald-500'}`}
            onClick={onConfirm}
          >
            确认
          </button>
        </div>
      </div>
    </div>
  );
}
