import React from 'react';

interface ErrorMessageProps {
  message: string;
  type?: 'error' | 'warning' | 'info';
  onClose?: () => void;
  className?: string;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  message,
  type = 'error',
  onClose,
  className = '',
}) => {
  const typeStyles = {
    error: 'bg-danger/10 border-danger/30 text-danger',
    warning: 'bg-warning/10 border-warning/30 text-warning',
    info: 'bg-accent-info/10 border-accent-info/30 text-accent-info',
  };

  const icons = {
    error: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
      </svg>
    ),
    warning: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
      </svg>
    ),
    info: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
      </svg>
    ),
  };

  return (
    <div
      className={`flex items-start p-4 rounded-lg border ${typeStyles[type]} ${className}`}
      role="alert"
    >
      <div className="flex-shrink-0">{icons[type]}</div>
      <div className="ml-3 flex-1">
        <p className="text-sm">{message}</p>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="ml-4 flex-shrink-0 hover:opacity-75 transition-opacity"
        >
          <span className="sr-only">关闭</span>
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      )}
    </div>
  );
};

interface ApiErrorProps {
  error: Error | null;
  onRetry?: () => void;
  className?: string;
}

export const ApiError: React.FC<ApiErrorProps> = ({ error, onRetry, className = '' }) => {
  if (!error) return null;

  const getErrorMessage = (err: Error): string => {
    // 网络错误
    if (err.message.includes('Network') || err.message.includes('Failed to fetch')) {
      return '网络连接失败，请检查网络设置后重试';
    }
    // 认证错误
    if (err.message.includes('401')) {
      return '登录已过期，请重新登录';
    }
    // 权限错误
    if (err.message.includes('403')) {
      return '没有权限执行此操作';
    }
    // 资源不存在
    if (err.message.includes('404')) {
      return '请求的资源不存在';
    }
    // 服务器错误
    if (err.message.includes('500')) {
      return '服务器错误，请稍后重试';
    }
    // 默认错误
    return err.message || '发生未知错误';
  };

  return (
    <div className={className}>
      <ErrorMessage
        message={getErrorMessage(error)}
        type="error"
        onClose={onRetry ? undefined : () => {}}
      />
      {onRetry && (
        <div className="mt-4 flex justify-center">
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-accent-info text-ink-inverse rounded-lg hover:bg-accent-info/90 transition-colors"
          >
            重试
          </button>
        </div>
      )}
    </div>
  );
};

interface ValidationErrorProps {
  field: string;
  message: string;
}

export const ValidationError: React.FC<ValidationErrorProps> = ({ field, message }) => {
  return (
    <div className="text-danger text-sm mt-1">
      <span className="font-medium">{field}:</span> {message}
    </div>
  );
};

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="p-4">
          <ErrorMessage
            message={this.state.error?.message || '组件渲染失败'}
            type="error"
          />
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="mt-4 px-4 py-2 bg-accent-info text-ink-inverse rounded-lg hover:bg-accent-info/90"
          >
            重新加载
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
