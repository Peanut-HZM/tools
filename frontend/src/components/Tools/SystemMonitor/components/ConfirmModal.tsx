// frontend/src/components/Tools/SystemMonitor/components/ConfirmModal.tsx
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/Card';

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
      <Card className="p-5 w-96 max-w-[90vw]" onClick={(e) => e.stopPropagation()}>
        <CardHeader className="p-0 mb-2">
          <CardTitle className="text-base font-medium text-ink">{title}</CardTitle>
        </CardHeader>
        <CardContent className="p-0 text-ink-muted text-sm mb-5">{message}</CardContent>
        <CardFooter className="p-0 flex justify-end gap-3">
          <Button variant="ghost" onClick={onCancel}>取消</Button>
          <Button variant={danger ? 'destructive' : 'default'} onClick={onConfirm}>
            确认
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}