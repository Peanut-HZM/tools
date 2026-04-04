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

const typeColors: Record<ToastType, { border: string; bg: string; icon: string }> = {
  success: { border: '#22c55e', bg: 'rgba(34, 197, 94, 0.1)', icon: '#22c55e' },
  error: { border: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)', icon: '#ef4444' },
  warning: { border: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)', icon: '#f59e0b' },
  info: { border: '#06b6d4', bg: 'rgba(6, 182, 212, 0.1)', icon: '#06b6d4' },
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
            flex items-center gap-3 px-5 py-4 rounded-xl shadow-2xl
            bg-slate-800/95 backdrop-blur-sm border border-slate-700/50
            text-slate-100
            max-w-[400px] min-w-[280px]
          `}
          style={{
            borderLeft: `4px solid ${colors.border}`,
            background: `linear-gradient(135deg, ${colors.bg}, rgba(30, 41, 59, 0.95))`,
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
          className: 'sonner-toast-dark',
          style: {
            background: '#1e293b',
            color: '#f1f5f9',
            border: '1px solid #334155',
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
