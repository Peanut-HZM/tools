// frontend/src/components/Tools/SystemMonitor/components/ConfirmModal.tsx
import { Button } from '@/components/ui/Button';

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
          <Button variant="ghost" onClick={onCancel}>取消</Button>
          <Button variant={danger ? 'destructive' : 'default'} onClick={onConfirm}>
            确认
          </Button>
        </div>
      </div>
    </div>
  );
}