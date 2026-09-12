import React, { createContext, useContext, useCallback, ReactNode, useEffect } from 'react';
import { toast as sonnerToast, Toaster } from 'sonner';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastContextType {
  toasts: never[]; // sonner 内部管理，此数组为空
  toast: string;
  showToast: (message: string, type?: ToastType, duration?: number) => void;
  addToast: (message: string, type?: ToastType, duration?: number) => string;
  removeToast: (id: string) => void;
  success: (message: string, duration?: number) => string;
  error: (message: string, duration?: number) => string;
  warning: (message: string, duration?: number) => string;
  info: (message: string, duration?: number) => string;
  clearAll: () => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

// 默认持续时间（毫秒）
const DEFAULT_DURATION: Record<ToastType, number> = {
  success: 3000,
  info: 3000,
  warning: 5000,
  error: 5000,
};

// 类型对应的图标
const typeIcons: Record<ToastType, string> = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
};

// 类型对应的左侧色条与图标颜色（style 内联使用 rgb(var()) 形式，随主题 accent token 联动）
// icon 用实色：0.3 透明度图标对比度约 2:1，低于 WCAG 非文本元素 3:1 要求；border 保留 /0.3 弱化色条
const typeColors: Record<ToastType, { border: string; icon: string }> = {
  success: { border: 'rgb(var(--accent-success) / 0.3)', icon: 'rgb(var(--accent-success))' },
  error: { border: 'rgb(var(--accent-danger) / 0.3)', icon: 'rgb(var(--accent-danger))' },
  warning: { border: 'rgb(var(--accent-warning) / 0.3)', icon: 'rgb(var(--accent-warning))' },
  info: { border: 'rgb(var(--accent-info) / 0.3)', icon: 'rgb(var(--accent-info))' },
};

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const showToast = useCallback((message: string, type: ToastType = 'info', duration?: number) => {
    const icon = typeIcons[type];
    const colors = typeColors[type];
    const toastDuration = duration ?? DEFAULT_DURATION[type];

    sonnerToast.custom(
      (t) => (
        <div
          className={`
            glass-panel
            flex items-center gap-3 px-5 py-4 rounded-xl
            text-ink
            max-w-[400px] min-w-[280px]
          `}
          style={{
            // 左侧类型色条保留（区分 success/error/warning/info）
            borderLeft: `4px solid ${colors.border}`,
          }}
        >
          <span className="text-xl font-bold" style={{ color: colors.icon }}>{icon}</span>
          <span className="text-sm flex-1 break-words leading-relaxed">{message}</span>
        </div>
      ),
      {
        duration: toastDuration,
        position: 'top-right',
      }
    );

    return `toast-${Date.now()}`;
  }, []);

  const addToast = useCallback((message: string, type: ToastType = 'info', duration?: number) => {
    return showToast(message, type, duration);
  }, [showToast]);

  const removeToast = useCallback((id: string) => {
    // sonner 自动管理，此方法保留用于兼容性
    sonnerToast.dismiss(id);
  }, []);

  const success = useCallback((message: string, duration?: number) =>
    addToast(message, 'success', duration), [addToast]);

  const error = useCallback((message: string, duration?: number) =>
    addToast(message, 'error', duration), [addToast]);

  const warning = useCallback((message: string, duration?: number) =>
    addToast(message, 'warning', duration), [addToast]);

  const info = useCallback((message: string, duration?: number) =>
    addToast(message, 'info', duration), [addToast]);

  const clearAll = useCallback(() => {
    sonnerToast.dismiss();
  }, []);

  const value = {
    toasts: [],
    toast: '',
    showToast,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
    clearAll,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <Toaster
        position="top-right"
        toastOptions={{
          // 玻璃面板：透明底 + 细描边 + 模糊（inline style 覆盖 sonner 默认实色底）
          style: {
            background: 'var(--glass-bg-strong)',
            color: 'rgb(var(--ink-default))',
            border: '1px solid var(--glass-border)',
            borderRadius: 'var(--radius-xl)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            boxShadow: 'var(--shadow-glass)',
          },
        }}
        theme="dark"
        richColors
      />
    </ToastContext.Provider>
  );
};

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
