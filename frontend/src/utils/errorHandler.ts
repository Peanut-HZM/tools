/**
 * Error Handler Utilities - Centralized error handling for the application
 */

export interface AppError {
  code: string;
  message: string;
  details?: string;
  recoverable: boolean;
}

export type ErrorCode = 
  | 'NETWORK_ERROR'
  | 'AUTH_ERROR'
  | 'TOKEN_EXPIRED'
  | 'FILE_NOT_FOUND'
  | 'PERMISSION_DENIED'
  | 'SAVE_FAILED'
  | 'LOAD_FAILED'
  | 'DELETE_FAILED'
  | 'RENAME_FAILED'
  | 'CREATE_FAILED'
  | 'VALIDATION_ERROR'
  | 'UNKNOWN_ERROR';

const errorMessages: Record<ErrorCode, { zh: string; en: string }> = {
  NETWORK_ERROR: {
    zh: '网络错误，请检查网络连接',
    en: 'Network error, please check your connection',
  },
  AUTH_ERROR: {
    zh: '认证失败，请重新登录',
    en: 'Authentication failed, please login again',
  },
  TOKEN_EXPIRED: {
    zh: '登录已过期，请重新登录',
    en: 'Session expired, please login again',
  },
  FILE_NOT_FOUND: {
    zh: '文件不存在',
    en: 'File not found',
  },
  PERMISSION_DENIED: {
    zh: '权限不足',
    en: 'Permission denied',
  },
  SAVE_FAILED: {
    zh: '保存失败',
    en: 'Save failed',
  },
  LOAD_FAILED: {
    zh: '加载失败',
    en: 'Load failed',
  },
  DELETE_FAILED: {
    zh: '删除失败',
    en: 'Delete failed',
  },
  RENAME_FAILED: {
    zh: '重命名失败',
    en: 'Rename failed',
  },
  CREATE_FAILED: {
    zh: '创建失败',
    en: 'Create failed',
  },
  VALIDATION_ERROR: {
    zh: '输入验证失败',
    en: 'Validation failed',
  },
  UNKNOWN_ERROR: {
    zh: '未知错误',
    en: 'Unknown error',
  },
};

/**
 * Parse error from API response or exception
 */
export function parseError(error: unknown, lang: 'zh-CN' | 'en-US' = 'zh-CN'): AppError {
  const langKey = lang === 'zh-CN' ? 'zh' : 'en';

  // Handle fetch/network errors
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return {
      code: 'NETWORK_ERROR',
      message: errorMessages.NETWORK_ERROR[langKey],
      recoverable: true,
    };
  }

  // Handle Error objects
  if (error instanceof Error) {
    const message = error.message.toLowerCase();

    // Check for specific error patterns
    if (message.includes('401') || message.includes('unauthorized')) {
      return {
        code: 'AUTH_ERROR',
        message: errorMessages.AUTH_ERROR[langKey],
        details: error.message,
        recoverable: true,
      };
    }

    if (message.includes('403') || message.includes('forbidden')) {
      return {
        code: 'PERMISSION_DENIED',
        message: errorMessages.PERMISSION_DENIED[langKey],
        details: error.message,
        recoverable: false,
      };
    }

    if (message.includes('404') || message.includes('not found')) {
      return {
        code: 'FILE_NOT_FOUND',
        message: errorMessages.FILE_NOT_FOUND[langKey],
        details: error.message,
        recoverable: false,
      };
    }

    if (message.includes('network') || message.includes('failed to fetch')) {
      return {
        code: 'NETWORK_ERROR',
        message: errorMessages.NETWORK_ERROR[langKey],
        details: error.message,
        recoverable: true,
      };
    }

    // Return the original error message if no pattern matches
    return {
      code: 'UNKNOWN_ERROR',
      message: error.message || errorMessages.UNKNOWN_ERROR[langKey],
      recoverable: true,
    };
  }

  // Handle string errors
  if (typeof error === 'string') {
    return {
      code: 'UNKNOWN_ERROR',
      message: error,
      recoverable: true,
    };
  }

  // Handle API error responses
  if (error && typeof error === 'object' && 'detail' in error) {
    return {
      code: 'UNKNOWN_ERROR',
      message: String((error as { detail: unknown }).detail),
      recoverable: true,
    };
  }

  // Default unknown error
  return {
    code: 'UNKNOWN_ERROR',
    message: errorMessages.UNKNOWN_ERROR[langKey],
    recoverable: true,
  };
}

/**
 * Get user-friendly error message
 */
export function getErrorMessage(code: ErrorCode, lang: 'zh-CN' | 'en-US' = 'zh-CN'): string {
  const langKey = lang === 'zh-CN' ? 'zh' : 'en';
  return errorMessages[code]?.[langKey] || errorMessages.UNKNOWN_ERROR[langKey];
}

/**
 * Check if error is recoverable (can retry)
 */
export function isRecoverableError(error: AppError): boolean {
  return error.recoverable;
}

/**
 * Check if error requires re-authentication
 */
export function requiresReauth(error: AppError): boolean {
  return error.code === 'AUTH_ERROR' || error.code === 'TOKEN_EXPIRED';
}
