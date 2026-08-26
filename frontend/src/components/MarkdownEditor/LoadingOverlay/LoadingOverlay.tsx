/**
 * Loading Overlay Component - Displays loading state with spinner
 */
interface LoadingOverlayProps {
  message?: string;
  fullScreen?: boolean;
}

export default function LoadingOverlay({ 
  message = '加载中...', 
  fullScreen = false 
}: LoadingOverlayProps) {
  const containerClass = fullScreen 
    ? 'fixed inset-0 bg-black/50 flex items-center justify-center z-50'
    : 'absolute inset-0 bg-canvas/50 flex items-center justify-center z-40';

  return (
    <div className={containerClass}>
      <div className="bg-surface-1 rounded-lg p-6 flex flex-col items-center gap-4 shadow-md">
        <div className="relative">
          <div className="w-12 h-12 border-4 border-border rounded-full"></div>
          <div className="absolute top-0 left-0 w-12 h-12 border-4 border-accent-cyan rounded-full border-t-transparent animate-spin"></div>
        </div>
        <span className="text-ink text-sm">{message}</span>
      </div>
    </div>
  );
}
