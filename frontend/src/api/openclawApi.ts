import { getAuthHeaders } from './authApi';
import { AUTH_API_BASE_URL } from '../config/api';

const API_BASE_URL = AUTH_API_BASE_URL.replace('/auth', '');

// ============ 用户端 API ============

export interface ChatMessage {
  message: string;
  session_key?: string;
}

/**
 * 流式对话（SSE）
 */
export async function chatStream(
  message: string,
  sessionKey: string = 'main',
  onChunk: (chunk: string) => void,
  onDone?: () => void,
  onError?: (error: string) => void
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/openclaw/chat`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message, session_key: sessionKey }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '请求失败' }));
      onError?.(error.detail || `HTTP ${response.status}`);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      onError?.('浏览器不支持流式响应');
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith(':')) continue;
        if (trimmed.startsWith('data: ')) {
          const jsonStr = trimmed.slice(6);
          try {
            const data = JSON.parse(jsonStr);
            if (data.type === 'chunk' && data.content) {
              onChunk(data.content);
            } else if (data.type === 'error') {
              onError?.(data.message || '服务端错误');
            } else if (data.type === 'done') {
              onDone?.();
              return;
            }
          } catch {
            // 不完整的 JSON，等待更多数据
          }
        }
      }
    }

    onDone?.();
  } catch (err: any) {
    onError?.(err.message || '网络异常');
  }
}

/** 获取会话历史 */
export async function loadHistory(sessionKey: string = 'main', limit: number = 50) {
  const response = await fetch(`${API_BASE_URL}/openclaw/history`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ session_key: sessionKey, limit }),
  });
  if (!response.ok) throw new Error('获取历史失败');
  const data = await response.json();
  return data.messages || [];
}

/** 中止生成 */
export async function abortChat(sessionKey: string = 'main') {
  const response = await fetch(`${API_BASE_URL}/openclaw/abort`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ session_key: sessionKey }),
  });
  if (!response.ok) throw new Error('中止失败');
  return response.json();
}

/** 重置会话 */
export async function resetSession(sessionKey: string = 'main') {
  const response = await fetch(`${API_BASE_URL}/openclaw/reset?session_key=${sessionKey}`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('重置失败');
  return response.json();
}

/** 获取状态 */
export async function getStatus() {
  const response = await fetch(`${API_BASE_URL}/openclaw/status`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('获取状态失败');
  return response.json();
}

// ============ 管理端 API ============

const ADMIN_API_BASE_URL = AUTH_API_BASE_URL.replace('/auth', '/admin');

export interface OpenClawConfig {
  gateway_url: string;
  auth_mode: string;
  username: string;
  password: string;
  token: string;
  enabled: string;
  connected: boolean;
}

/** 获取配置 */
export async function getOpenClawConfig(): Promise<OpenClawConfig> {
  const response = await fetch(`${ADMIN_API_BASE_URL}/openclaw/config`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('获取配置失败');
  return response.json();
}

/** 更新配置 */
export async function updateOpenClawConfig(data: Partial<OpenClawConfig>): Promise<any> {
  const response = await fetch(`${ADMIN_API_BASE_URL}/openclaw/config`, {
    method: 'PUT',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '更新失败' }));
    throw new Error(error.detail || '更新失败');
  }
  return response.json();
}

/** 获取状态 */
export async function getOpenClawStatus() {
  const response = await fetch(`${ADMIN_API_BASE_URL}/openclaw/status`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('获取状态失败');
  return response.json();
}

/** 手动重连 */
export async function reconnectOpenClaw() {
  const response = await fetch(`${ADMIN_API_BASE_URL}/openclaw/reconnect`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '重连失败' }));
    throw new Error(error.detail || '重连失败');
  }
  return response.json();
}

/** 测试连接 */
export async function testOpenClawConnection(data: {
  gateway_url: string;
  auth_mode: string;
  username?: string;
  password?: string;
  token?: string;
}) {
  const response = await fetch(`${ADMIN_API_BASE_URL}/openclaw/test-connection`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '测试失败' }));
    throw new Error(error.detail || '测试失败');
  }
  return response.json();
}

/** 断开连接 */
export async function disconnectOpenClaw() {
  const response = await fetch(`${ADMIN_API_BASE_URL}/openclaw/disconnect`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '断开失败' }));
    throw new Error(error.detail || '断开失败');
  }
  return response.json();
}
