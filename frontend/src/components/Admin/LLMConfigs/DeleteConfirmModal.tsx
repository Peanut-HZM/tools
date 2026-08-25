import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

interface DeleteConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  configName: string;
  isLoading?: boolean;
}

export default function DeleteConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  configName,
  isLoading
}: DeleteConfirmModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* 弹窗内容 */}
      <Card className="relative shadow-lg w-full max-w-md">
        {/* 头部 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-danger/20 flex items-center justify-center">
              <svg className="w-6 h-6 text-danger" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-ink-inverse">确认删除</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-ink-muted hover:text-ink-inverse transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 内容 */}
        <div className="p-6">
          <p className="text-ink-muted mb-4">
            确定要删除配置 <span className="text-ink-inverse font-medium">"{configName}"</span> 吗？
          </p>
          <p className="text-danger text-sm">
            ⚠️ 此操作不可恢复，请谨慎操作！
          </p>
        </div>

        {/* 底部按钮 */}
        <div className="flex gap-4 px-6 py-4 border-t border-border bg-surface-1/50">
          <Button
            onClick={onConfirm}
            disabled={isLoading}
            variant="destructive"
          >
            {isLoading ? '删除中...' : '确认删除'}
          </Button>
          <Button onClick={onClose} variant="secondary">
            取消
          </Button>
        </div>
      </Card>
    </div>
  );
}
